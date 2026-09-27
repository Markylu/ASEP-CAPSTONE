extends Node3D
class_name VLMNavRig

## Controller + decision client + run session, as one node a site can drop in.
##
## Before this existed, every scene hand-wired three nodes and every scene could
## get it subtly wrong. A site now instances this and places a `Spawn` marker;
## the rig moves itself onto the marker, so the marker is the single authority
## on the start pose and `site.json` can record it honestly.
##
## The snap happens in `_enter_tree`, which runs top-down and therefore BEFORE
## the controller child's `_ready` — which matters, because the controller reads
## its own `global_position.y` into `_hold_altitude` and treats it as the cruise
## height for the whole run. Snap any later and the agent flies at whatever
## altitude the rig happened to be saved at.

## Marker group the rig looks for. A site marks exactly one node with it.
const SPAWN_GROUP := "vlmnav_spawn"

## Leave empty to use the first node in `vlmnav_spawn`.
@export var spawn_path: NodePath
## Off if a site wants the rig to stay exactly where it was placed.
@export var snap_to_spawn: bool = true


func _enter_tree() -> void:
	if not snap_to_spawn:
		return
	var spawn := _resolve_spawn()
	if spawn == null:
		return
	global_transform = spawn.global_transform


func _resolve_spawn() -> Node3D:
	if spawn_path != NodePath():
		var explicit := get_node_or_null(spawn_path) as Node3D
		if explicit != null:
			return explicit
	return get_tree().get_first_node_in_group(SPAWN_GROUP) as Node3D
