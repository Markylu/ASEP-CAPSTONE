extends RefCounted
class_name PolarAction

## One element of the action space: turn by `theta`, then translate `r`.
##
## Godot frame: the agent faces -Z, +X is its right. `theta` is a yaw offset in
## radians, positive to the LEFT, which is what `rotate_y` already does.

var r: float = 0.0
var theta: float = 0.0
## The number shown on the frame. 0 is reserved for turn-around.
var index: int = -1
var is_turn_around: bool = false


func _init(distance: float = 0.0, angle: float = 0.0) -> void:
	r = distance
	theta = angle


static func turn_around() -> PolarAction:
	var a := PolarAction.new(0.0, PI)
	a.index = 0
	a.is_turn_around = true
	return a


## Endpoint in the agent's own frame.
func endpoint_local() -> Vector3:
	return Vector3(-sin(theta) * r, 0.0, -cos(theta) * r)


func endpoint_world(agent_transform: Transform3D) -> Vector3:
	return agent_transform * endpoint_local()


func to_dict() -> Dictionary:
	return {
		"index": index,
		"r": r,
		"theta": theta,
		"theta_deg": rad_to_deg(theta),
		"turn_around": is_turn_around,
	}


func label() -> String:
	if is_turn_around:
		return "turn around"
	return "%.1f m  %+.0f°" % [r, rad_to_deg(theta)]


func _to_string() -> String:
	return "[%d] %s" % [index, label()]
