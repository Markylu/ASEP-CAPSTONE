extends CharacterBody3D
class_name VLMNavController

## A player controller whose entire input surface is the VLMnav action space.
##
## No WASD. The agent alternates between offering a fan of numbered actions on
## the camera frame and executing the one that was picked: turn by theta, then
## translate r. Press the number key, click the annotation, or click the panel —
## all three land in `execute_index()`, and so does a model calling
## `submit_action()`. Nothing can express a move that was not on the frame.
##
## Zero-shot configuration: the action space is fixed geometry, not a
## navigability estimate. No depth model, no sensor. Whether an action is a good
## idea is the decision-maker's problem, which is the point — it is what the
## frame is being judged on.

signal actions_proposed(actions: Array)
signal action_started(action: PolarAction)
signal action_finished(action: PolarAction, collided: bool)
signal step_completed(pose: Dictionary)
signal decision_requested(manifest: Dictionary)

enum State { AWAITING_DECISION, TURNING, MOVING }
enum DecisionSource {
	MANUAL,    ## you: number keys, annotation clicks, panel buttons
	EXTERNAL,  ## something else calls submit_action(), e.g. the server
	SCRIPTED,  ## replay a fixed index list
}

@export var config: VLMNavConfig
@export var decision_source: DecisionSource = DecisionSource.MANUAL
## Indices replayed in SCRIPTED mode.
@export var scripted_indices: PackedInt32Array = PackedInt32Array()
## Show the selection panel. Annotations stay clickable either way.
@export var show_panel: bool = true
## The target. Leave empty and the controller takes the first node in the
## `vlmnav_goal` group, so dropping a goal_marker.tscn into the scene is enough.
@export var goal_path: NodePath

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var overlay: VLMNavOverlay = $UI/Overlay
@onready var panel: VLMNavPanel = $UI/Panel

var state: State = State.AWAITING_DECISION
var actions: Array[PolarAction] = []
var step_count: int = 0

var _current: PolarAction
var _turn_remaining: float = 0.0
var _turn_sign: float = 1.0
var _move_remaining: float = 0.0
var _collided: bool = false
var _hold_altitude: float = 0.0
var _scripted_cursor: int = 0
var _goal: VLMNavGoal
## Goal visibility as of the last `propose()`. Sampled once per step rather than
## per frame: it is what the decision was made under, and a per-frame value
## would depend on how long the model took to answer.
var _goal_los: bool = true
## Timeline events reported by site props since the last step closed. Drained
## into the step record so `steps.jsonl` says on its own when the world changed.
var _pending_events: Array = []
## Physics ticks this controller actually simulated. Unlike
## `Engine.get_physics_frames()` it stops while the tree is paused for a
## decision, so it is the clock site props move on in a frozen-world run.
var _sim_ticks: int = 0


func _ready() -> void:
	if config == null:
		config = VLMNavConfig.new()
	# The spawn marker is the authority on cruise height, not the config.
	_hold_altitude = global_position.y
	camera.fov = config.fov_deg
	# KEEP_WIDTH makes `fov` the HORIZONTAL field of view, so an action at
	# +-fov/2 lands on the left or right edge of the frame whatever the window
	# aspect is. With the default KEEP_HEIGHT the same number means vertical
	# FOV, and the fan would silently overshoot the frame on a tall window.
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	head.rotation.x = config.camera_pitch
	overlay.cfg = config
	overlay.bind_camera(camera)
	overlay.action_pressed.connect(execute_index)
	panel.action_pressed.connect(execute_index)
	panel.visible = show_panel
	_resolve_goal()
	# One frame so the Control has its real size before anything is projected.
	await get_tree().process_frame
	propose()


func _process(_delta: float) -> void:
	overlay.pose_text = "pos  %+.1f  %+.1f  %+.1f     yaw  %+.0f°" % [
		global_position.x, global_position.y, global_position.z, rad_to_deg(global_rotation.y),
	]
	overlay.queue_redraw()
	# Live, so the readout tracks the goal while it is dragged around.
	_resolve_goal()
	if _goal == null:
		panel.set_goal_info(null, 0.0, 0.0)
		return
	var d := _goal.planar_distance(global_position)
	panel.set_goal_info(
		_goal.global_position,
		d,
		_goal.bearing_from(global_position, global_transform.basis),
		d <= _goal.arrival_radius
	)


func _resolve_goal() -> void:
	if _goal != null and is_instance_valid(_goal):
		return
	if goal_path != NodePath():
		_goal = get_node_or_null(goal_path) as VLMNavGoal
	if _goal == null:
		_goal = get_tree().get_first_node_in_group(VLMNavGoal.GROUP) as VLMNavGoal


func _physics_process(delta: float) -> void:
	_sim_ticks += 1
	match state:
		State.TURNING:
			_process_turn(delta)
		State.MOVING:
			_process_move(delta)
		_:
			velocity = Vector3.ZERO
			_hold()
			move_and_slide()


# ---------------------------------------------------------------- action space

## The fan: `num_actions` evenly spaced headings across the FOV, all at
## `action_dist`, plus action 0 for turn-around. Numbered left to right so the
## frame reads the way a person reads it.
func propose() -> Array[PolarAction]:
	# Scene node order decides whether the goal has joined its group by the time
	# this node is ready, so step 0's manifest could ship without a goal while
	# every later step had one. Resolving here makes the manifest independent of
	# where the marker sits in the scene tree.
	_resolve_goal()
	_sample_goal_los()
	actions = []
	if config.include_turn_around:
		actions.append(PolarAction.turn_around())
	var spread := config.fov_rad() * 0.5 * config.fan_spread
	var n: int = max(config.num_actions, 2)
	for i in n:
		var theta := spread - 2.0 * spread * float(i) / float(n - 1)
		var a := PolarAction.new(config.action_dist, theta)
		a.index = i + 1
		actions.append(a)

	overlay.set_actions(actions, global_transform)
	overlay.annotations_visible = true
	overlay.compute_projection()
	overlay.status_text = "step %d  |  %s" % [step_count, _source_label()]
	panel.set_actions(actions, overlay.projectable_indices())
	panel.set_title("STEP %d" % step_count)
	panel.set_enabled(true)
	state = State.AWAITING_DECISION
	actions_proposed.emit(actions)

	match decision_source:
		DecisionSource.EXTERNAL:
			decision_requested.emit(get_manifest())
		DecisionSource.SCRIPTED:
			_advance_scripted()
		_:
			pass
	return actions


## What a decision-maker is told. Lists exactly the numbers drawn on the frame,
## because both come from the same projection test.
func get_manifest() -> Dictionary:
	overlay.compute_projection()
	var visible := overlay.projectable_indices()
	var entries: Array = []
	for a in actions:
		if visible.has(a.index):
			entries.append(a.to_dict())
	var manifest := {
		"step": step_count,
		"pose": _pose_dict(),
		"actions": entries,
		"config": config.to_dict(),
	}
	if _goal != null and is_instance_valid(_goal):
		var d := _goal.planar_distance(global_position)
		manifest["goal"] = {
			"position": [_goal.global_position.x, _goal.global_position.y, _goal.global_position.z],
			"distance": d,
			"bearing_deg": rad_to_deg(_goal.bearing_from(global_position, global_transform.basis)),
			"arrival_radius": _goal.arrival_radius,
			"reached": d <= _goal.arrival_radius,
			# Ground truth, not a hint: prompt.py does not read this key, so
			# adding it leaves prompt_sha and every earlier run comparable.
			"line_of_sight": _goal_los,
		}
	return manifest


# -------------------------------------------------------------------- decision

## The single entry point for every decision-maker: key, click, panel, server.
func execute_index(index: int) -> bool:
	if state != State.AWAITING_DECISION:
		return false
	var picked: PolarAction = null
	for a in actions:
		if a.index == index:
			picked = a
			break
	if picked == null:
		return false
	overlay.selected_index = index
	overlay.queue_redraw()
	panel.set_enabled(false)
	_begin(picked)
	return true


## Alias with the name an external client reaches for.
func submit_action(index: int) -> bool:
	return execute_index(index)


func _begin(a: PolarAction) -> void:
	overlay.annotations_visible = false
	_current = a
	_collided = false
	_turn_remaining = absf(a.theta)
	_turn_sign = signf(a.theta)
	_move_remaining = a.r
	state = State.TURNING if _turn_remaining > 0.001 else State.MOVING
	action_started.emit(a)


# ------------------------------------------------------------------- execution

func _process_turn(delta: float) -> void:
	velocity = Vector3.ZERO
	var step: float = _turn_remaining
	if config.turn_speed > 0.0:
		step = min(config.turn_speed * delta, _turn_remaining)
	rotate_y(_turn_sign * step)
	_turn_remaining -= step
	_hold()
	move_and_slide()
	if _turn_remaining <= 0.0001:
		state = State.MOVING


func _process_move(delta: float) -> void:
	if _move_remaining <= 0.0001:
		_finish()
		return
	var step: float = min(config.move_speed * delta, _move_remaining)
	velocity = -global_transform.basis.z * (step / delta)
	_hold()
	var before := global_position
	move_and_slide()
	var travelled := Vector2(global_position.x - before.x, global_position.z - before.z).length()
	_move_remaining -= travelled
	# A step that ends on a wall is a real outcome of the decision, not a
	# glitch: nothing filtered the action, so the choice owns the collision.
	if get_slide_collision_count() > 0 and travelled < step * 0.5:
		_collided = true
		_finish()
		return
	if _move_remaining <= 0.0001:
		_finish()


func _finish() -> void:
	velocity = Vector3.ZERO
	var finished := _current
	_current = null
	step_count += 1
	var pose := _pose_dict()
	pose["action"] = finished.to_dict() if finished != null else {}
	pose["collided"] = _collided
	if not _pending_events.is_empty():
		pose["events"] = _pending_events
		_pending_events = []
	action_finished.emit(finished, _collided)
	step_completed.emit(pose)
	propose()


## The 1-based number of the step an event happening NOW belongs to.
##
## `step_count` counts steps FINISHED, and it is incremented at the end of a
## move — so a prop that fires mid-move sees the previous step's number, while
## `steps.jsonl` files that same move one higher. Everything that timestamps an
## event uses this instead, so "deployed at step 3" and the step 3 record mean
## the same move. Between moves it names the move about to start, which is the
## one the event affects.
func current_step_number() -> int:
	return step_count + 1


## Called by whatever reports a prop event — `run_session.gd` today. The event
## rides out with the step it happened in, so a scripted run or a replay, which
## have no decisions.jsonl, still record when the world changed under them.
func buffer_event(name: String, data: Dictionary = {}) -> void:
	_pending_events.append({
		"name": name,
		"step": current_step_number(),
		"tick": Engine.get_physics_frames(),
		"sim_tick": _sim_ticks,
		"data": data,
	})


func _sample_goal_los() -> void:
	if _goal == null or not is_instance_valid(_goal):
		_goal_los = false
		return
	# From the camera, not the body: the question is whether the frame the
	# decision is made from contains the goal. `get_rid()` excludes the agent's
	# own collider, which the ray starts inside of.
	_goal_los = _goal.visible_from(camera.global_position, get_world_3d(), [get_rid()])


func _hold() -> void:
	velocity.y = clampf((_hold_altitude - global_position.y) * 4.0, -2.0, 2.0)


# ----------------------------------------------------------------------- input

func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var key := (event as InputEventKey).keycode
	if decision_source == DecisionSource.MANUAL and key >= KEY_0 and key <= KEY_9:
		execute_index(key - KEY_0)
		return
	match key:
		KEY_H:
			overlay.draw_hud = not overlay.draw_hud
			overlay.queue_redraw()
		KEY_TAB:
			panel.visible = not panel.visible


# --------------------------------------------------------------------- capture

## The annotated frame: the literal image a decision was made from. Await a
## `RenderingServer.frame_post_draw` first so the overlay is on it.
func capture_annotated_frame() -> Image:
	return get_viewport().get_texture().get_image()


## The frame a decision is made from: annotations, and nothing else.
##
## The HUD and the panel are hidden for the capture because both print
## world-frame truth — the agent's own position and yaw, the goal's world
## coordinates and exact bearing. A decision that is supposed to come from the
## image must not be able to read its way to the goal instead. Waits two frames
## so the hidden HUD and the current fan are both on the image; see
## `decision_client.gd` for why one wait is not enough.
func capture_decision_frame() -> Image:
	var hud_was := overlay.draw_hud
	var panel_was := panel.visible
	overlay.draw_hud = false
	panel.visible = false
	overlay.queue_redraw()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	overlay.draw_hud = hud_was
	panel.visible = panel_was
	overlay.queue_redraw()
	return img


## Frame with no annotations, for anything that must not see the arrows.
func capture_clean_frame() -> Image:
	var was_visible := overlay.visible
	var panel_visible := panel.visible
	overlay.visible = false
	panel.visible = false
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	overlay.visible = was_visible
	panel.visible = panel_visible
	return img


# ----------------------------------------------------------------------- utils

func _pose_dict() -> Dictionary:
	return {
		"step": step_count,
		"t": Time.get_ticks_msec() / 1000.0,
		# Physics frames elapsed. Unlike `t` this is the clock site props are
		# paced by, so an event can be placed exactly within a step. Neither
		# field survives a replay unchanged — `eval/replay.py` ignores both.
		"tick": Engine.get_physics_frames(),
		# Excludes time spent paused waiting on the decider, so it matches
		# between a live run and its replay where `tick` does not.
		"sim_tick": _sim_ticks,
		"position": [global_position.x, global_position.y, global_position.z],
		# World yaw, not local. A site spawns the agent by parenting the rig to a
		# Spawn marker, so the heading lives on the parent and `rotation.y` would
		# read 0 for the whole run. Identical to `rotation.y` in main.tscn, where
		# the controller sits at the scene root.
		"yaw": global_rotation.y,
		"pitch": head.rotation.x,
	}


func _source_label() -> String:
	match decision_source:
		DecisionSource.MANUAL:
			return "press a number, click an arrow, or use the panel"
		DecisionSource.EXTERNAL:
			return "awaiting server"
		_:
			return "scripted"


func _advance_scripted() -> void:
	if _scripted_cursor >= scripted_indices.size():
		overlay.status_text = "scripted route complete (%d steps)" % step_count
		return
	var idx := scripted_indices[_scripted_cursor]
	_scripted_cursor += 1
	execute_index(idx)
