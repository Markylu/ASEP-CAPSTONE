@tool
extends Node3D
class_name TriggeredDoor

## One door leaf: a slab that seals a doorway or drops out of sight under the
## floor. It has no trigger of its own — a `TriggeredDoorBank` commands it, so
## that several doors change on one tick and one event describes all of them.
##
## The two rules it inherits from `TriggeredOccluder`:
##
## 1. The panel is ONE SIZE, `STANDARD_PANEL`, in every site. Which route is
##    open is then a property of which door moved, never of how big the doors
##    are, so two sites can be compared. The editor warns on an override.
## 2. Motion is counted in PHYSICS TICKS, never seconds of wall clock. A live
##    model run waits ~17 s per step for the decider; its replay waits not at
##    all. Anything paced by idle time would land in a different place in the
##    two, and `eval/replay.py` would stop agreeing with itself.

## Emitted on the tick the panel finishes moving. Deliberately NOT forwarded to
## the recorder — see the note in `_physics_process()`.
signal arrived(state: String, info: Dictionary)

## The cross-site standard, metres, as (x, y, z): a 2.4 x 3.2 m leaf, 0.5 m
## thick, sized to fill its doorway exactly rather than overhang it. Human door
## proportions are the point — a 4 x 5 m slab reads as a hangar shutter, and the
## agent has to recognise these as doors from the image.
const STANDARD_PANEL := Vector3(0.5, 3.2, 2.4)

enum State { OPEN, CLOSED }

## Where the panel sits when the doorway is sealed. The collider lives here from
## load and never moves; only the mesh travels.
@export var closed_position: Vector3 = Vector3(0.0, 1.85, 0.0):
	set = set_closed_position
## Where the panel sits when the doorway is clear. Default is under the floor.
@export var open_position: Vector3 = Vector3(0.0, -2.35, 0.0):
	set = set_open_position
## Size of the panel. Leave at STANDARD_PANEL unless a site has a written reason.
@export var panel_size: Vector3 = STANDARD_PANEL:
	set = set_panel_size
@export var panel_material: Material:
	set = set_panel_material
## State the door is in when the site loads.
@export var initial_state: State = State.CLOSED:
	set = set_initial_state
## Travel time. Converted to whole physics ticks; seconds never reach the motion.
@export var travel_seconds: float = 0.3:
	set = set_travel_seconds
@export_enum("LINEAR", "EASE_OUT", "SMOOTHSTEP") var easing: int = 2
## Hide the mesh once it is parked under the floor. Belt and braces.
@export var hide_when_open: bool = true

var state: State = State.CLOSED

var _travel_ticks: int = 18
var _tick: int = 0
var _moving: bool = false
var _from: Vector3 = Vector3.ZERO
var _to: Vector3 = Vector3.ZERO
var _command_tick: int = 0


func _ready() -> void:
	_apply_geometry()
	if Engine.is_editor_hint():
		return
	_recompute_ticks()
	state = initial_state
	_moving = false
	var visual := _visual()
	visual.position = _rest_position()
	visual.visible = not (state == State.OPEN and hide_when_open)
	_set_solid(state == State.CLOSED)
	set_physics_process(false)


# ------------------------------------------------------------------- commands

func open() -> void:
	_command(State.OPEN)


func close() -> void:
	_command(State.CLOSED)


func state_name() -> String:
	return "closed" if state == State.CLOSED else "open"


## The collider flips HERE, on the command tick, in both directions — never when
## the panel arrives.
##
## Step timing is not reproducible between a run and its replay: the live agent
## idles for seconds waiting on the model, the scripted one does not. Collider
## state tied to the command tick is a step function of the trajectory, which IS
## reproduced exactly. Tie it to the arrival tick instead and the door is shut
## long before the live agent moves but still rising in the replay, and
## `eval/replay.py` reports COLLISION DIFFERS.
##
## The cost either way is a sub-tenth-of-a-second window where what is drawn and
## what is solid disagree. Site geometry has to keep the agent further from the
## door than it can travel in `travel_seconds`; see the site README.
func _command(target: State) -> void:
	if state == target and not _moving:
		return
	state = target
	_command_tick = Engine.get_physics_frames()
	_tick = 0
	_from = _visual().position
	_to = _rest_position()
	_moving = true
	_visual().visible = true
	_set_solid(state == State.CLOSED)
	set_physics_process(true)


func _physics_process(_delta: float) -> void:
	# `_delta` is deliberately unused. Position is a function of whole ticks
	# elapsed, so it is identical in a live run, a headless replay and a movie
	# render, none of which share a frame cadence.
	if not _moving:
		return
	_tick += 1
	var u := clampf(float(_tick) / float(_travel_ticks), 0.0, 1.0)
	_visual().position = _from.lerp(_to, _ease(u))
	if _tick < _travel_ticks:
		return
	_moving = false
	set_physics_process(false)
	if state == State.OPEN and hide_when_open:
		_visual().visible = false
	# Signalled, but deliberately NOT sent to the recorder.
	#
	# Which step this lands in depends on how long the model took to answer the
	# step before: the panel moves on a fixed 18-tick schedule while the agent
	# idles for seconds in a live run and not at all in its replay, so the same
	# movement lands in step 4 of one and step 5 of the other. Recording it would
	# make every replay report EVENTS DIFFER over a difference that is not in the
	# trajectory. The bank's switch event carries `trigger_tick` and
	# `travel_ticks`, so the arrival tick is recoverable exactly.
	arrived.emit(state_name(), {
		"door": name,
		"state": state_name(),
		"command_tick": _command_tick,
		"physics_tick": Engine.get_physics_frames(),
		"travel_ticks": _travel_ticks,
	})


func _rest_position() -> Vector3:
	return closed_position if state == State.CLOSED else open_position


func _ease(u: float) -> float:
	match easing:
		0:
			return u
		1:
			return 1.0 - pow(1.0 - u, 3.0)
		_:
			return smoothstep(0.0, 1.0, u)


# ---------------------------------------------------------------------- geometry

## `panel_size` is the only source of truth: the mesh and the collider are both
## written from the exports, so nothing can drift out of step with what
## `site.json` claims the site contains.
func _apply_geometry() -> void:
	var visual := _visual()
	if visual != null:
		var mesh := visual.mesh as BoxMesh
		if mesh != null:
			mesh.size = panel_size
		if panel_material != null:
			visual.material_override = panel_material
		# The leaf artwork lives on two quads rather than on the box: a BoxMesh
		# splits its UVs across the faces, so a door drawn on it would be sliced.
		# A quad owns the full 0..1 UV square, which is what the SVG is drawn for.
		for leaf_name in ["LeafFront", "LeafBack"]:
			var leaf := visual.get_node_or_null(leaf_name) as MeshInstance3D
			if leaf == null:
				continue
			var quad := leaf.mesh as QuadMesh
			if quad != null:
				quad.size = Vector2(panel_size.z, panel_size.y)
			# Just proud of the box face, so it never z-fights with it.
			var offset := panel_size.x * 0.5 + 0.001
			leaf.position.x = offset if leaf_name == "LeafFront" else -offset
		# The editor previews the door in its starting state — that is the
		# placement a site is designed against.
		if Engine.is_editor_hint():
			visual.position = closed_position if initial_state == State.CLOSED else open_position
	var body := _body()
	if body != null:
		body.position = closed_position
		var shape := _shape()
		if shape != null and shape.shape is BoxShape3D:
			(shape.shape as BoxShape3D).size = panel_size
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


# ----------------------------------------------------------------------- setters

func set_closed_position(value: Vector3) -> void:
	closed_position = value
	_apply_geometry()


func set_open_position(value: Vector3) -> void:
	open_position = value
	_apply_geometry()


func set_panel_size(value: Vector3) -> void:
	panel_size = value
	_apply_geometry()


func set_panel_material(value: Material) -> void:
	panel_material = value
	_apply_geometry()


func set_initial_state(value: State) -> void:
	initial_state = value
	_apply_geometry()


## Also the hook `--speed` reaches, via the bank: a watch-mode replay slows the
## agent down, and a door that still slams in 0.3 s would read wrong on the
## recording.
func set_travel_seconds(value: float) -> void:
	travel_seconds = maxf(value, 0.0)
	_recompute_ticks()


func _get_configuration_warnings() -> PackedStringArray:
	var warnings := PackedStringArray()
	if not panel_size.is_equal_approx(STANDARD_PANEL):
		warnings.append(
			"panel_size %s deviates from STANDARD_PANEL %s. Which route is open is meant to be a"
			% [panel_size, STANDARD_PANEL]
			+ " property of which door moved, not of panel size — sites are not comparable unless"
			+ " this is deliberate and written into site.json.")
	if _visual() == null or _body() == null:
		warnings.append("Expected children Visual (MeshInstance3D) and Body/Shape (CollisionShape3D).")
	elif _visual().get_node_or_null("LeafFront") == null or _visual().get_node_or_null("LeafBack") == null:
		warnings.append("Visual has no LeafFront/LeafBack quads — the door would render as a blank"
			+ " slab, and the agent is meant to recognise it as a door from the image.")
	return warnings
