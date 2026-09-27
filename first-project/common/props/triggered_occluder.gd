@tool
extends Node3D
class_name TriggeredOccluder

## A box that is not there until the agent crosses a line, and then is.
##
## The agent starts with a clear view of the goal. Somewhere along the way it
## passes through `Trigger`, and this box rises out of the floor between the
## agent and the goal, taking both the sightline and the straight path with it.
## Whether the run recovers is the whole question the site is asking.
##
## Two rules make it safe to cite:
##
## 1. The box is ONE SIZE, `STANDARD_SIZE`, in every site. Occlusion strength is
##    then a property of where the box is, never of how big it is, so two sites
##    can be compared. The editor warns if a scene overrides `box_size`.
## 2. Motion is counted in PHYSICS TICKS, never seconds of wall clock. A live
##    model run waits ~17 s per step for the decider; its replay waits not at
##    all. Anything paced by idle time would land in a different place in the
##    two, and `eval/replay.py` would stop agreeing with itself.

## Emitted the moment the agent crosses the trigger.
signal deployed(info: Dictionary)
## Emitted on the tick the box finishes rising.
signal in_place(info: Dictionary)
## The generic channel `run_session.gd` listens for on every member of the
## `vlmnav_event_source` group. Any future prop — a door, a light, a subject —
## emits this and inherits the whole recording path for free.
signal event_fired(name: String, data: Dictionary)

## Alias of `SiteProp.EVENT_GROUP`, kept so existing scenes and scripts that
## reference `TriggeredOccluder.EVENT_GROUP` still resolve. New code should use
## `SiteProp.EVENT_GROUP` — the group is not the occluder's property.
const EVENT_GROUP := SiteProp.EVENT_GROUP
## The cross-site standard. Do not change per site: see rule 1 above.
const STANDARD_SIZE := Vector3(8.0, 8.0, 8.0)

enum State { PARKED, DEPLOYING, IN_PLACE }
enum CollisionMode {
	AT_TRIGGER,  ## solid from the trigger tick — deterministic, see below
	AT_ARRIVAL,  ## solid when the box finishes rising — physically honest, not replay-safe
}

## Where the box sits while it is not needed. Default is below the floor.
@export var park_position: Vector3 = Vector3(0.0, -9.0, 0.0):
	set = set_park_position
## Where the box ends up. The collider lives here from load; only the mesh moves.
@export var deployed_position: Vector3 = Vector3(0.0, 0.0, 0.0):
	set = set_deployed_position
## Size of the box. Leave at STANDARD_SIZE unless a site has a written reason.
@export var box_size: Vector3 = STANDARD_SIZE:
	set = set_box_size
@export var box_material: Material:
	set = set_box_material
## Rise time. Converted to whole physics ticks at _ready; seconds never reach
## the motion itself.
@export var travel_seconds: float = 0.3:
	set = set_travel_seconds
@export_enum("LINEAR", "EASE_OUT", "SMOOTHSTEP") var easing: int = 2
## When the box becomes solid. AT_TRIGGER is the replay-safe choice; see the
## note on `_deploy()`.
@export var collision_mode: CollisionMode = CollisionMode.AT_TRIGGER
## Hide the mesh while parked. Belt and braces — it is already under the floor.
@export var hidden_until_deploy: bool = true
@export var trigger_position: Vector3 = Vector3(0.0, 0.0, 0.0):
	set = set_trigger_position
@export var trigger_size: Vector3 = Vector3(1.0, 4.0, 23.0):
	set = set_trigger_size
## Fire once per run. Off lets the agent re-arm it by walking back through.
@export var trigger_once: bool = true
@export var event_name: String = "occluder_deployed"

var state: State = State.PARKED

var _travel_ticks: int = 18
var _tick: int = 0
var _trigger_tick: int = 0
var _trigger_step: int = 0
var _fired: bool = false


func _ready() -> void:
	_apply_geometry()
	if Engine.is_editor_hint():
		return
	add_to_group(EVENT_GROUP)
	_recompute_ticks()
	_set_solid(false)
	_visual().position = park_position
	if hidden_until_deploy:
		_visual().visible = false
	var trigger := _trigger()
	if trigger != null:
		trigger.body_entered.connect(_on_body_entered)
	set_physics_process(false)


# ------------------------------------------------------------------- deployment

func _on_body_entered(body: Node3D) -> void:
	if _fired and trigger_once:
		return
	if not (body is VLMNavController):
		return
	_deploy(body as VLMNavController)


## The box becomes solid HERE, on the trigger tick, not when the mesh arrives.
##
## Step timing is not reproducible between a run and its replay: the live agent
## idles for seconds waiting on the model, the scripted one does not. The world
## is paused during that wait by default (`freeze_world` on the decision
## client), but `--freeze-world=0` runs still idle unfrozen. Collider
## state tied to the trigger tick is a step function of the trajectory, which IS
## reproduced exactly — so a run and its replay collide in the same place. Tie
## it to the arrival tick instead and the box is up before the live agent moves
## but mid-rise in the replay, and `eval/replay.py` reports COLLISION DIFFERS.
##
## The cost is a sub-tenth-of-a-second window where an invisible collider
## exists. Site geometry has to keep the agent further from the box than it can
## travel in `travel_seconds`; s01 leaves a 1.9x margin.
func _deploy(agent: VLMNavController) -> void:
	_fired = true
	_tick = 0
	_trigger_tick = Engine.get_physics_frames()
	_trigger_step = agent.current_step_number()
	state = State.DEPLOYING
	_visual().visible = true
	if collision_mode == CollisionMode.AT_TRIGGER:
		_set_solid(true)
	set_physics_process(true)
	var info := _info(agent.global_position, "deploying")
	deployed.emit(info)
	event_fired.emit(event_name, info)


func _physics_process(_delta: float) -> void:
	# `_delta` is deliberately unused. Position is a function of whole ticks
	# elapsed, so it is identical in a live run, a headless replay and a movie
	# render, none of which share a frame cadence.
	if state != State.DEPLOYING:
		return
	_tick += 1
	var u := clampf(float(_tick) / float(_travel_ticks), 0.0, 1.0)
	_visual().position = park_position.lerp(deployed_position, _ease(u))
	if _tick < _travel_ticks:
		return
	state = State.IN_PLACE
	set_physics_process(false)
	if collision_mode == CollisionMode.AT_ARRIVAL:
		_set_solid(true)
	# Signalled, but deliberately NOT sent to the recorder over `event_fired`.
	#
	# Which step this lands in depends on how long the model took to answer the
	# step before: the box rises on a fixed 18-tick schedule while the agent
	# idles for seconds in a live run and not at all in its replay, so the same
	# rise lands in step 4 of one and step 5 of the other. Recording it would
	# make every replay report EVENTS DIFFER over a difference that is not in
	# the trajectory. The deploy event already carries `trigger_tick` and
	# `travel_ticks`, so the arrival tick is recoverable exactly.
	var info := _info(_visual().global_position, "in_place")
	in_place.emit(info)


func _ease(u: float) -> float:
	match easing:
		0:
			return u
		1:
			return 1.0 - pow(1.0 - u, 3.0)
		_:
			return smoothstep(0.0, 1.0, u)


func _info(agent_position: Vector3, phase: String) -> Dictionary:
	return {
		"occluder": String(get_path()),
		"step": _trigger_step,
		"physics_tick": Engine.get_physics_frames(),
		"trigger_tick": _trigger_tick,
		"travel_ticks": _travel_ticks,
		"travel_seconds": travel_seconds,
		"agent_position": [agent_position.x, agent_position.y, agent_position.z],
		"park": [park_position.x, park_position.y, park_position.z],
		"deployed": [deployed_position.x, deployed_position.y, deployed_position.z],
		"box_size": [box_size.x, box_size.y, box_size.z],
		"collision_mode": "at_trigger" if collision_mode == CollisionMode.AT_TRIGGER else "at_arrival",
		"state": phase,
	}


# ---------------------------------------------------------------------- geometry

## `box_size` is the only source of truth: the mesh, the collider and the
## trigger are all written from the exports, so nothing can drift out of step
## with what `site.json` claims the site contains.
func _apply_geometry() -> void:
	var visual := _visual()
	if visual != null:
		var mesh := visual.mesh as BoxMesh
		if mesh != null:
			mesh.size = box_size
		if box_material != null:
			visual.material_override = box_material
		# The editor previews the box where it ends up — that is the placement a
		# site is designed against. At runtime it starts parked and only the
		# deploy moves it.
		if Engine.is_editor_hint():
			visual.position = deployed_position
		elif state == State.PARKED:
			visual.position = park_position
	var body := _body()
	if body != null:
		body.position = deployed_position
		var shape := _shape()
		if shape != null and shape.shape is BoxShape3D:
			(shape.shape as BoxShape3D).size = box_size
	var trigger := _trigger()
	if trigger != null:
		trigger.position = trigger_position
		var ts := _trigger_shape()
		if ts != null and ts.shape is BoxShape3D:
			(ts.shape as BoxShape3D).size = trigger_size
	update_configuration_warnings()


func _set_solid(solid: bool) -> void:
	var shape := _shape()
	if shape != null:
		shape.disabled = not solid


func _recompute_ticks() -> void:
	_travel_ticks = maxi(1, int(round(travel_seconds * float(Engine.physics_ticks_per_second))))


func _visual() -> MeshInstance3D:
	return get_node_or_null("Visual") as MeshInstance3D


func _body() -> StaticBody3D:
	return get_node_or_null("Body") as StaticBody3D


func _shape() -> CollisionShape3D:
	return get_node_or_null("Body/Shape") as CollisionShape3D


func _trigger() -> Area3D:
	return get_node_or_null("Trigger") as Area3D


func _trigger_shape() -> CollisionShape3D:
	return get_node_or_null("Trigger/TriggerShape") as CollisionShape3D


# ----------------------------------------------------------------------- setters

func set_park_position(value: Vector3) -> void:
	park_position = value
	_apply_geometry()


func set_deployed_position(value: Vector3) -> void:
	deployed_position = value
	_apply_geometry()


func set_box_size(value: Vector3) -> void:
	box_size = value
	_apply_geometry()


func set_box_material(value: Material) -> void:
	box_material = value
	_apply_geometry()


## Also the hook `run_session.gd` uses for `--speed`: a watch-mode replay slows
## the agent down, and a box that still slams up in 0.3 s would look wrong and
## read wrong on the recording.
func set_travel_seconds(value: float) -> void:
	travel_seconds = maxf(value, 0.0)
	_recompute_ticks()


func set_trigger_position(value: Vector3) -> void:
	trigger_position = value
	_apply_geometry()


func set_trigger_size(value: Vector3) -> void:
	trigger_size = value
	_apply_geometry()


func _get_configuration_warnings() -> PackedStringArray:
	var warnings := PackedStringArray()
	if not box_size.is_equal_approx(STANDARD_SIZE):
		warnings.append(
			"box_size %s deviates from STANDARD_SIZE %s. Occlusion strength is meant to be a"
			% [box_size, STANDARD_SIZE]
			+ " property of placement, not of size — sites are not comparable unless this is"
			+ " deliberate and written into site.json.")
	if _visual() == null or _body() == null or _trigger() == null:
		warnings.append("Expected children Visual (MeshInstance3D), Body/Shape and Trigger/TriggerShape.")
	return warnings
