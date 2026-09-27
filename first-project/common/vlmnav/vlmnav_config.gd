extends Resource
class_name VLMNavConfig

## Parameters for the VLMnav action interface, zero-shot configuration: a fixed
## fan of numbered actions projected on the frame, no navigability estimate and
## no depth model. This is VLMnav's `navigability_mode: none` setting — the
## action space is the prompt, and the VLM (or you) is the only thing filtering
## it.

@export_group("Camera")
## Horizontal FOV of the drone camera, degrees.
@export var fov_deg: float = 87.0
## Downward camera pitch, radians. Negative looks down. Keep this at 0 if the
## fan should span the full frame width: pitching down squeezes ground-plane
## annotations toward the centre, because a tilted camera sees a near ground
## point as further "ahead" than it is. VLMnav's -0.45 is a ground robot
## looking at the floor in front of its feet.
@export var camera_pitch: float = 0.0

@export_group("Action space")
## Numbered actions drawn across the FOV, excluding turn-around.
@export_range(2, 9) var num_actions: int = 5
## Distance travelled by any numbered action, metres.
@export var action_dist: float = 1.7
## Fraction of the half-FOV the fan spans. 1.0 puts the outermost actions at the
## exact edges of what the camera sees, which is the full action space the frame
## can justify; the overlay keeps those discs on-screen (see `clamp_to_frame`).
@export_range(0.1, 1.0) var fan_spread: float = 1.0
## Offer action 0, turn around 180 degrees in place.
@export var include_turn_around: bool = true
## Actions projecting within this fraction of the image edge are not drawn, and
## therefore cannot be chosen.
@export var image_edge_threshold: float = 0.04
## Metres below the agent that annotations are drawn on. Visual only: it puts
## them on the floor, where a person would point.
@export var draw_plane_offset: float = 1.5
## Distance along each heading at which the disc is drawn, metres. 0 draws it at
## the action's own endpoint. A level camera at altitude sees a point 1.7 m out
## and 1.5 m down as almost straight below it, which piles the discs into the
## bottom corners; drawing them further out lifts them into the frame while the
## arrow still points along the exact heading the action takes. Every action
## travels `action_dist` regardless — the panel and the manifest say so.
@export var annotation_distance: float = 6.0

@export_group("Execution")
## Yaw rate, rad/s. 0 snaps instantly.
@export var turn_speed: float = 6.0
## Translation speed, m/s. Fast on purpose: the step is the unit of interest,
## not the travel, so the agent should be at the next decision quickly.
@export var move_speed: float = 8.0


func fov_rad() -> float:
	return deg_to_rad(fov_deg)


## Flat dictionary for a run manifest, so a decision can cite the action space
## that produced it.
func to_dict() -> Dictionary:
	var out := {}
	for prop in get_property_list():
		if prop.usage & PROPERTY_USAGE_SCRIPT_VARIABLE and prop.name != "script":
			out[prop.name] = get(prop.name)
	return out
