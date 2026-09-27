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
@export var static_doors: bool = false

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
	# Control arm for the door sites: every bank is disarmed before the agent
	# moves, so the doors hold their initial state for the whole run and the
	# trigger never fires.
	if args.has("static-doors"):
		static_doors = str(args["static-doors"]) not in ["0", "false", "no"]
	if static_doors:
		for node in get_tree().get_nodes_in_group(SiteProp.EVENT_GROUP):
			if node is TriggeredDoorBank:
				(node as TriggeredDoorBank)._disarmed = true
		print("VLMNAV STATIC DOORS — door triggers disarmed.")

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
