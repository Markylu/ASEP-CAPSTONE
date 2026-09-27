extends Node3D
class_name VLMNavGoal

## The target the agent is trying to reach. Drag it anywhere in the scene; the
## controller finds it by group, reads its position every frame, and reports it
## on the HUD and in the manifest.
##
## It is a marker, not a trigger: nothing about the action space changes when
## the agent gets close. Reaching it is the decision-maker's job, which is the
## whole thing being tested.

const GROUP := "vlmnav_goal"

## Radius, metres, at which the agent counts as having arrived. Reported on the
## HUD; nothing enforces it yet.
@export var arrival_radius: float = 1.0
## Beacon colour.
@export var color: Color = Color(1.0, 0.35, 0.35):
	set = set_color

@onready var _orb: MeshInstance3D = $Orb
@onready var _beam: MeshInstance3D = $Beam


func _ready() -> void:
	add_to_group(GROUP)
	set_color(color)


func set_color(value: Color) -> void:
	color = value
	if not is_node_ready():
		return
	for mesh in [_orb, _beam]:
		var mi := mesh as MeshInstance3D
		var mat := mi.get_active_material(0)
		if mat is StandardMaterial3D:
			var m := (mat as StandardMaterial3D).duplicate() as StandardMaterial3D
			m.albedo_color = Color(value, m.albedo_color.a)
			m.emission = value
			mi.material_override = m


## Planar distance from `from`, ignoring altitude: the agent flies level, so a
## height difference is not something any action can close.
func planar_distance(from: Vector3) -> float:
	var d := global_position - from
	return Vector2(d.x, d.z).length()


## Is there an unobstructed line from `origin` to the orb?
##
## Ground truth, in the sense of notes/PLAN.md §8.2 — an engine raycast, not
## anything the agent can sense. It is recorded so a run can be read back as
## "the goal was visible for 4 steps, then hidden", and it is deliberately NOT
## put in the prompt: `server/decider/prompt.py` never reads this key.
##
## The orb is the target, not the beam: the beam is a 6 m column and a ray to
## its top clears most obstacles, which would report visibility long after the
## marker itself went behind something.
func visible_from(origin: Vector3, world: World3D, exclude: Array = []) -> bool:
	if world == null:
		return true
	var query := PhysicsRayQueryParameters3D.create(origin, global_position)
	query.exclude = exclude
	query.collide_with_areas = false
	query.collide_with_bodies = true
	return world.direct_space_state.intersect_ray(query).is_empty()


## Signed bearing from `basis`'s forward axis, radians. Positive is to the left,
## the same convention as PolarAction.theta.
func bearing_from(from: Vector3, basis: Basis) -> float:
	var local := basis.inverse() * (global_position - from)
	return atan2(-local.x, -local.z)
