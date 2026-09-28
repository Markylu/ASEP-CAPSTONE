extends Node
class_name VLMNavRunSession

## Turns a launch into a run: reads the command line, pins the frame size,
## points the decision client at a decider, and decides when the run is over.
##
##   godot --path first-project -- \
##       --run-id=run_2026-09-14_1830 \
##       --decider-url=http://127.0.0.1:8000 \
##       --max-steps=20
##
## With `--scripted-indices=0,3,4,2` it replays a recorded index list through
## the controller's SCRIPTED mode instead — the same trajectory, no model. That
## is how a VLM run is reproduced.
##
## The session ends the run, not the model: there is no stop action yet, so
## arrival, the step budget and the collision budget are all decided here.

signal run_ended(reason: String, steps: int)

## Hard ceiling on steps. The run ends `max_steps` whether or not it arrived.
@export var max_steps: int = 30
## Collisions tolerated before the run is called off. -1 for no limit.
@export var max_collisions: int = 3
## End the run when the goal marker reports REACHED.
@export var stop_on_goal: bool = true
## Window is pinned to this so every frame the model sees is the same shape.
## Camera FOV is horizontal (KEEP_WIDTH), so a changing window aspect silently
## changes the vertical field of view and two runs stop being comparable.
@export var frame_size: Vector2i = Vector2i(768, 768)
## Seconds before the run is abandoned, counted from launch. 0 for no limit.
@export var wall_clock_limit: float = 900.0
## Quit the process when the run ends. Off while working in the editor.
@export var quit_on_end: bool = true
## Multiplies turn and move speed, for watching a replay at a human pace. 1.0 is
## the recorded speed. Watch-only: see `--speed` in the module README — a run
## whose numbers are being cited should fly at 1.0.
@export var speed_scale: float = 1.0
## Disarm every door bank at load: the doors never open or close. `--static-doors=1`.
## Kept as an alias of `--world=initial`.
@export var static_doors: bool = false
## Which layout the run flies — the phase 1 arms (docs/phase1-test-plan.md §5):
##   `dynamic`  the site as built; the change fires at its trigger
##   `initial`  the pre-change layout for the whole run; nothing fires
##   `final`    the post-change layout from step 0; nothing fires
@export_enum("dynamic", "initial", "final") var world: String = "dynamic"
## Seeded spawn jitter (§7.3). -1 for none, the exact marker pose.
@export var spawn_seed: int = -1

const WORLDS := ["dynamic", "initial", "final"]
## Jitter bounds: lateral (world z) metres and yaw degrees, uniform in ±.
const SPAWN_JITTER_Z := 0.5
const SPAWN_JITTER_YAW_DEG := 5.0

## The jitter actually applied, recorded in run.json.
var spawn_offset: Dictionary = {}
## Which door a `final` fork run closed (s03), recorded in run.json.
var final_closed: Array = []
## Repo-relative directory the decider should record into. Empty = its default.
var run_dir: String = ""

var agent: VLMNavController
var client: VLMNavDecisionClient
## The running site's manifest, or empty when the scene has no `site.json`
## beside it — which is the case for the unmigrated `main.tscn` sandbox.
var site: SiteManifest

var collisions: int = 0
var _ending: bool = false


func _ready() -> void:
	agent = get_parent() as VLMNavController
	if agent == null:
		push_error("VLMNavRunSession must be a child of a VLMNavController")
		return
	client = _find_client()
	site = SiteManifest.for_current_scene(get_tree())

	var args := _parse_args()
	if args.is_empty() and client != null and client.decider_url == "":
		# Plain editor launch: leave the controller in whatever mode the scene
		# set, so opening main.tscn is still a manual baseline run.
		set_process(false)
		return

	_apply(args)
	agent.step_completed.connect(_on_step_completed)
	_connect_event_sources()
	if client != null:
		client.run_failed.connect(func(reason: String) -> void: _end("decision_error: " + reason, 1))
	if wall_clock_limit > 0.0:
		get_tree().create_timer(wall_clock_limit).timeout.connect(
			func() -> void: _end("wall_clock_limit", 1))

	if client != null and client.enabled():
		client.last_frame_size = frame_size
		print("VLMNAV RUN %s -> %s  (max %d steps, frame %dx%d)"
			% [client.run_id, client.decider_url, max_steps, frame_size.x, frame_size.y])
		# Not awaited: the controller proposes its first fan one process frame
		# from now, and /run/start only has to reach the decider before the
		# decision it describes.
		client.start_run({
			"max_steps": max_steps,
			# Which geometry this run flew. A number is only citable next to
			# these two — see notes/PLAN.md §5.1 on `s01@v1`.
			"site_id": site.id(),
			"site_version": site.version(),
			# Site props move in whole physics ticks, so the tick rate is part
			# of what makes a trajectory reproducible.
			"physics_ticks_per_second": Engine.physics_ticks_per_second,
			"static_doors": static_doors,
			"world": world,
			"spawn_seed": spawn_seed if spawn_seed >= 0 else null,
			"spawn_offset": spawn_offset if spawn_seed >= 0 else null,
			"final_closed": final_closed,
			"run_dir": run_dir if run_dir != "" else null,
		})


## Every site prop that reports timeline events joins one group, so the session
## does not need to know what props a site contains. A door or a light added
## later is recorded the same way with no change here.
func _connect_event_sources() -> void:
	for node in get_tree().get_nodes_in_group(SiteProp.EVENT_GROUP):
		if node.has_signal("event_fired"):
			node.event_fired.connect(_on_prop_event)


func _on_prop_event(name: String, data: Dictionary) -> void:
	print("VLMNAV EVENT %s at step %d" % [name, agent.current_step_number()])
	# Buffered into the step record AND posted on its own: the first makes
	# steps.jsonl self-contained, the second keeps the event even if the run
	# ends before the step closes.
	agent.buffer_event(name, data)
	if client != null and client.enabled():
		client.post_event(name, agent.current_step_number(), data)


func _find_client() -> VLMNavDecisionClient:
	for child in get_parent().get_children():
		if child is VLMNavDecisionClient:
			return child
	return null


# ------------------------------------------------------------------ launch args

func _parse_args() -> Dictionary:
	var out := {}
	for arg in OS.get_cmdline_user_args():
		if not arg.begins_with("--") or not arg.contains("="):
			continue
		var parts := arg.trim_prefix("--").split("=", true, 1)
		out[parts[0]] = parts[1]
	return out


func _apply(args: Dictionary) -> void:
	if args.has("frame-size"):
		var wh := str(args["frame-size"]).split("x")
		if wh.size() == 2:
			frame_size = Vector2i(int(wh[0]), int(wh[1]))
	if DisplayServer.get_name() != "headless":
		DisplayServer.window_set_size(frame_size)
		# `--window-mode=minimized` keeps an unattended sweep out of the way.
		# Godot still renders a minimized window, and the captured frames are
		# byte-identical to a visible window's; the viewport keeps frame_size.
		if str(args.get("window-mode", "")) == "minimized":
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	if args.has("max-steps"):
		max_steps = int(args["max-steps"])
	if args.has("max-collisions"):
		max_collisions = int(args["max-collisions"])
	if args.has("stop-on-goal"):
		stop_on_goal = str(args["stop-on-goal"]) not in ["0", "false", "no"]
	if args.has("speed"):
		speed_scale = maxf(float(args["speed"]), 0.01)
		# The config is a shared resource in the scene, so this run gets its own
		# copy rather than editing the one every other scene instance points at.
		agent.config = agent.config.duplicate()
		agent.config.move_speed *= speed_scale
		agent.config.turn_speed *= speed_scale
		# Site props are paced in seconds too, and a box that still slams up in
		# 0.3 s while the agent crawls would misrepresent the moment on a
		# recording. Ticks are recomputed by the setter.
		# Any prop with a `travel_seconds` setter, not only the occluder: the door
		# banks in s02 move on the same clock and would otherwise keep slamming at
		# recorded pace while the agent crawls.
		for node in get_tree().get_nodes_in_group(SiteProp.EVENT_GROUP):
			if node.has_method("set_travel_seconds"):
				node.set("travel_seconds", float(node.get("travel_seconds")) / speed_scale)
		if speed_scale != 1.0:
			print("VLMNAV SPEED x%.2f — watch mode. Do not cite numbers from this run."
				% speed_scale)

	if client != null and args.has("decider-url"):
		client.activate(str(args["decider-url"]), str(args.get("run-id", "")))
		client.frame_width = int(args["frame-width"]) if args.has("frame-width") else frame_size.x
	if client != null and args.has("freeze-world"):
		client.freeze_world = str(args["freeze-world"]) not in ["0", "false", "no"]
	if args.has("run-dir"):
		run_dir = str(args["run-dir"])
	if args.has("spawn-seed"):
		spawn_seed = int(args["spawn-seed"])
	if spawn_seed >= 0:
		_apply_spawn_jitter()

	# `--static-doors=1` predates the arms and means exactly `initial`.
	if args.has("static-doors") and str(args["static-doors"]) not in ["0", "false", "no"]:
		world = "initial"
	if args.has("world"):
		world = str(args["world"])
		if world not in WORLDS:
			push_error("--world=%s is not one of %s" % [world, WORLDS])
			world = "dynamic"
	static_doors = world == "initial"
	_apply_world()

	# Last, because it overrides the decision source `activate()` just set. A
	# replay still reports to the decider — /run/start, /step and /run/end cost
	# nothing — but SCRIPTED never emits `decision_requested`, so no model is
	# called and the trajectory is the recorded one.
	if args.has("scripted-indices"):
		var indices := PackedInt32Array()
		for token in str(args["scripted-indices"]).split(",", false):
			indices.append(int(token.strip_edges()))
		agent.scripted_indices = indices
		agent.decision_source = VLMNavController.DecisionSource.SCRIPTED
		max_steps = min(max_steps, indices.size())


## Replicates at temperature 0 differ only through their input, so each seed
## nudges the start pose (docs/phase1-test-plan.md §7.3). The same seed gives
## the same offset on every site and arm — the arms of a site are paired.
##
## Moves the rig, not the controller: the rig already sits on the Spawn marker
## (`VLMNavRig._enter_tree`), and the controller has not run `_ready` yet, so
## its cruise altitude is read after this. Lateral is world z — every site
## spawns facing -X.
func _apply_spawn_jitter() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = spawn_seed
	var dz := rng.randf_range(-SPAWN_JITTER_Z, SPAWN_JITTER_Z)
	var dyaw := rng.randf_range(-SPAWN_JITTER_YAW_DEG, SPAWN_JITTER_YAW_DEG)
	var rig := agent.get_parent() as Node3D
	rig.global_position.z += dz
	rig.rotate_y(deg_to_rad(dyaw))
	spawn_offset = {"dz": dz, "dyaw_deg": dyaw}
	print("VLMNAV SPAWN seed %d: dz %+.3f m, dyaw %+.2f°" % [spawn_seed, dz, dyaw])


## Put every site prop into the layout this arm flies. Props are under `Props`,
## which precedes `Rig` in every site scene, so their `_ready` has already run.
## Neither `initial` nor `final` emits an event: nothing changes during the run.
func _apply_world() -> void:
	if world == "dynamic":
		return
	var fork_banks := {}
	for node in get_tree().get_nodes_in_group(SiteProp.EVENT_GROUP):
		if node is TriggeredOccluder:
			if world == "final":
				(node as TriggeredOccluder).snap_deployed()
			else:
				(node as TriggeredOccluder).disarm()
		elif node is TriggeredDoorBank:
			var bank := node as TriggeredDoorBank
			if world == "initial":
				bank.disarm()
			elif bank.latch_group != &"":
				fork_banks[String(bank.name)] = bank
			else:
				bank.apply_final_state()
	if not fork_banks.is_empty():
		_close_one_fork_branch(fork_banks)
	print("VLMNAV WORLD %s — triggers disarmed%s." % [
		world, (", post-change layout at load" if world == "final" else "")])


## A latched fork (s03) has no single post-change layout: the dynamic arm closes
## whichever branch the agent enters. `final` closes the left branch on odd
## seeds and the right on even ones (§5), picked by the bank name's L/R suffix.
func _close_one_fork_branch(banks: Dictionary) -> void:
	var side := "L" if spawn_seed % 2 == 1 else "R"
	for bank_name in banks:
		var bank: TriggeredDoorBank = banks[bank_name]
		if String(bank_name).ends_with(side):
			bank.close_immediate()
			final_closed.append(bank_name)
		else:
			bank.disarm()
	if final_closed.is_empty():
		push_error("--world=final: no fork bank ends with '%s' among %s" % [side, banks.keys()])


# ------------------------------------------------------------------ termination

func _on_step_completed(pose: Dictionary) -> void:
	if _ending:
		return
	if pose.get("collided", false):
		collisions += 1
		if max_collisions >= 0 and collisions > max_collisions:
			_end("collision_budget", 1)
			return
	if stop_on_goal and _goal_reached():
		_end("goal_reached", 0)
		return
	if agent.step_count >= max_steps:
		_end("max_steps", 0)


func _goal_reached() -> bool:
	var goal: Dictionary = agent.get_manifest().get("goal", {})
	return goal.get("reached", false)


func _end(reason: String, code: int) -> void:
	if _ending:
		return
	_ending = true
	# The wall-clock timer fires while paused, so a run can end mid-decision.
	# Unpause here or an editor session (quit_on_end off) stays frozen.
	get_tree().paused = false
	# Stop the controller before it can propose again: `propose()` runs straight
	# after `step_completed`, and an extra decision here would be an extra
	# model call the run never used.
	if client != null:
		client.accepting = false
	# Only the controller's own callbacks. `process_mode` would disable the
	# whole subtree, and the decision client is in it — the closing /run/end
	# would then never be polled to completion.
	agent.set_physics_process(false)
	agent.set_process(false)
	print("VLMNAV RUN ENDED: %s after %d steps (%d collisions)"
		% [reason, agent.step_count, collisions])
	if client != null and client.enabled():
		await client.end_run(reason)
	run_ended.emit(reason, agent.step_count)
	if quit_on_end:
		get_tree().quit(code)
