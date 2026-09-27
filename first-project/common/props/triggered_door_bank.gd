@tool
extends Node3D
class_name TriggeredDoorBank

## Several doors, one trigger, one event.
##
## The agent flies through an `Area3D` and the world rearranges itself: the door
## it was heading for shuts, another one opens. Whether it notices — and how
## many steps it spends before it looks somewhere else — is the whole question
## the site is asking.
##
## Everything lives on one node rather than one trigger per door so that the
## change is atomic: every listed door flips on the SAME physics tick, and one
## `doors_switched` event describes the whole new state of the bank. A reader of
## `events.jsonl` never has to stitch two events together and hope they were
## simultaneous.

## Emitted the moment the agent crosses the trigger.
signal switched(info: Dictionary)
## The generic channel `run_session.gd` listens for on every member of
## `SiteProp.EVENT_GROUP`.
signal event_fired(name: String, data: Dictionary)

## Doors made passable when the trigger fires.
@export var doors_to_open: Array[NodePath] = []
## Doors sealed when the trigger fires.
@export var doors_to_close: Array[NodePath] = []
@export var trigger_position: Vector3 = Vector3(0.0, 1.75, 0.0):
	set = set_trigger_position
@export var trigger_size: Vector3 = Vector3(1.0, 4.0, 23.0):
	set = set_trigger_size
## Fire once per run. Off lets the agent re-arm it by flying back through.
@export var trigger_once: bool = true
@export var event_name: String = "doors_switched"
## Travel time for every door in the bank. Writing it here keeps the arms of a
## variant pair in step and gives `--speed` a single hook.
@export var travel_seconds: float = 0.3:
	set = set_travel_seconds
## Banks sharing a non-empty latch group are mutually exclusive: the first one
## the agent trips fires, and every other bank in the group is disarmed for the
## rest of the run. This is what lets a fork close whichever branch the agent
## commits to. Empty = independent, the s02 behaviour.
@export var latch_group: StringName = &""

var _fired: bool = false
## Set when a peer in `latch_group` fired first. Separate from `_fired` so a
## disarmed bank stays dead even with `trigger_once` off.
var _disarmed: bool = false


func _ready() -> void:
	_apply_geometry()
	if Engine.is_editor_hint():
		return
	add_to_group(SiteProp.EVENT_GROUP)
	if latch_group != &"":
		add_to_group(latch_group)
	set_travel_seconds(travel_seconds)
	var trigger := _trigger()
	if trigger != null:
		trigger.body_entered.connect(_on_body_entered)


func _on_body_entered(body: Node3D) -> void:
	if _disarmed or (_fired and trigger_once):
		return
	if not (body is VLMNavController):
		return
	_switch(body as VLMNavController)


func _switch(agent: VLMNavController) -> void:
	_fired = true
	# Closed first, then opened: if a site ever lists the same door in both
	# arrays, sealing it and then clearing it is the reading that matches the
	# order the arrays are written in, and the recorded `states` says which won.
	var closed := _command(doors_to_close, false)
	var opened := _command(doors_to_open, true)
	var disarmed := _disarm_peers()
	var info := {
		"bank": String(get_path()),
		"step": agent.current_step_number(),
		"physics_tick": Engine.get_physics_frames(),
		"trigger_tick": Engine.get_physics_frames(),
		"travel_ticks": maxi(1, int(round(travel_seconds * float(Engine.physics_ticks_per_second)))),
		"travel_seconds": travel_seconds,
		"agent_position": [agent.global_position.x, agent.global_position.y, agent.global_position.z],
		"closed": closed,
		"opened": opened,
		# The after picture, so nothing downstream has to reconstruct it.
		"states": states(),
		"collision_mode": "at_trigger",
		"latch_group": String(latch_group),
		"disarmed": disarmed,
	}
	switched.emit(info)
	event_fired.emit(event_name, info)


## Disarm every other bank in `latch_group`, on this same tick. Returns their
## node names for the event record.
func _disarm_peers() -> Array:
	var names := []
	if latch_group == &"":
		return names
	for peer in get_tree().get_nodes_in_group(latch_group):
		if peer == self or not (peer is TriggeredDoorBank):
			continue
		(peer as TriggeredDoorBank)._disarmed = true
		names.append(String(peer.name))
	return names


func _command(paths: Array[NodePath], should_open: bool) -> Array:
	var names := []
	for path in paths:
		var door := get_node_or_null(path) as TriggeredDoor
		if door == null:
			push_warning("TriggeredDoorBank: no TriggeredDoor at '%s'" % path)
			continue
		if should_open:
			door.open()
		else:
			door.close()
		names.append(door.name)
	return names


## Every door in the bank and whether it is open or closed right now.
func states() -> Dictionary:
	var out := {}
	for child in get_children():
		if child is TriggeredDoor:
			out[String(child.name)] = (child as TriggeredDoor).state_name()
	return out


# ---------------------------------------------------------------------- geometry

func _apply_geometry() -> void:
	var trigger := _trigger()
	if trigger == null:
		update_configuration_warnings()
		return
	trigger.position = trigger_position
	var shape := _trigger_shape()
	if shape != null and shape.shape is BoxShape3D:
		(shape.shape as BoxShape3D).size = trigger_size
	update_configuration_warnings()


func _trigger() -> Area3D:
	return get_node_or_null("Trigger") as Area3D


func _trigger_shape() -> CollisionShape3D:
	return get_node_or_null("Trigger/TriggerShape") as CollisionShape3D


# ----------------------------------------------------------------------- setters

func set_trigger_position(value: Vector3) -> void:
	trigger_position = value
	_apply_geometry()


func set_trigger_size(value: Vector3) -> void:
	trigger_size = value
	_apply_geometry()


## `run_session.gd` calls this for `--speed`, and it has to reach the doors: they
## are what actually moves.
func set_travel_seconds(value: float) -> void:
	travel_seconds = maxf(value, 0.0)
	for child in get_children():
		if child is TriggeredDoor:
			(child as TriggeredDoor).travel_seconds = travel_seconds


func _get_configuration_warnings() -> PackedStringArray:
	var warnings := PackedStringArray()
	if _trigger() == null or _trigger_shape() == null:
		warnings.append("Expected a child Trigger (Area3D) with a TriggerShape (CollisionShape3D).")
	var doors := 0
	for child in get_children():
		if child is TriggeredDoor:
			doors += 1
	if doors == 0:
		warnings.append("No TriggeredDoor children — this bank switches nothing.")
	if doors_to_open.is_empty() and doors_to_close.is_empty():
		warnings.append("doors_to_open and doors_to_close are both empty — crossing the trigger"
			+ " would change nothing. A site that wants a static wall should not use a bank.")
	return warnings
