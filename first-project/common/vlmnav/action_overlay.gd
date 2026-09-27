extends Control
class_name VLMNavOverlay

## Draws the action set on the camera frame and lets you press it: an arrow per
## action, a numbered disc at each endpoint, action 0 as a badge. Click a disc
## to take that action.
##
## The annotated frame IS the prompt. Anything not drawn here cannot be chosen,
## by you or by a model, which is why `compute_projection()` is also what the
## manifest is built from.

signal action_pressed(index: int)

@export var draw_hud: bool = true
## Draw endpoints on the floor plane rather than at the agent's altitude, the
## way VLMnav's arrows lie on the ground.
@export var project_to_ground: bool = true
## Pull discs that land on or past the frame border back inside it. An action at
## the very edge of the FOV projects exactly onto the image border, so without
## this the two outermost actions are half-clipped and then dropped. The arrow
## still points along the true heading; only the disc moves.
@export var clamp_to_frame: bool = true

var cfg: VLMNavConfig
var actions: Array[PolarAction] = []
var agent_xform: Transform3D = Transform3D.IDENTITY
var selected_index: int = -1
var status_text: String = ""
## Second HUD line: the agent's own pose, refreshed every frame so it is still
## live while an action executes and the annotations are hidden.
var pose_text: String = ""
## Annotations are hidden while an action executes: they describe a choice made
## at a pose the agent has already left, and a fan sliding across the frame
## mid-move reads as if it were still selectable.
var annotations_visible: bool = true: set = set_annotations_visible

var _camera: Camera3D
var _font: Font
var _projectable: Dictionary = {}  # index -> screen position
var _hovered: int = -1

const ARROW_COLOR := Color(0.15, 0.85, 1.0, 0.95)
const SELECTED_COLOR := Color(0.25, 1.0, 0.35, 1.0)
const HOVER_COLOR := Color(1.0, 0.78, 0.2, 1.0)
const TURN_AROUND_COLOR := Color(1.0, 0.55, 0.85, 1.0)
const DISC_RADIUS := 19.0
const HUD_STATUS_SIZE := 16
## The pose line is read at a glance while the agent is moving, so it is set
## larger than the status line above it.
const HUD_POSE_SIZE := 24


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_PASS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_font = ThemeDB.fallback_font


func set_annotations_visible(value: bool) -> void:
	if annotations_visible == value:
		return
	annotations_visible = value
	if not value:
		_hovered = -1
	queue_redraw()


func bind_camera(cam: Camera3D) -> void:
	_camera = cam


func set_actions(new_actions: Array[PolarAction], xform: Transform3D) -> void:
	actions = new_actions
	agent_xform = xform
	selected_index = -1
	queue_redraw()


func projectable_indices() -> Array:
	return _projectable.keys()


## Fills `_projectable` without drawing, so the manifest is correct even in a
## headless run where `_draw` never fires.
func compute_projection() -> void:
	_projectable.clear()
	if _camera == null:
		return
	for a in actions:
		if a.is_turn_around:
			# Top centre: it is the one action with no heading to point at, and
			# the bottom of the frame is where every arrow converges.
			_projectable[0] = Vector2(size.x * 0.5, 76.0)
			continue
		var world := _endpoint(a)
		if _camera.is_position_behind(world):
			continue
		var p := _project(world)
		if clamp_to_frame:
			p = _clamp_to_frame(p)
		elif not _can_project(p):
			continue
		_projectable[a.index] = p


# ---------------------------------------------------------------------- input

func _gui_input(event: InputEvent) -> void:
	if not annotations_visible:
		return
	if event is InputEventMouseMotion:
		var hit := _hit_test((event as InputEventMouseMotion).position)
		if hit != _hovered:
			_hovered = hit
			queue_redraw()
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			var hit := _hit_test(mb.position)
			if hit >= 0:
				action_pressed.emit(hit)
				accept_event()


func _hit_test(p: Vector2) -> int:
	for index in _projectable:
		if p.distance_to(_projectable[index]) <= DISC_RADIUS + 4.0:
			return int(index)
	return -1


# ---------------------------------------------------------------------- draw

func _draw() -> void:
	if _camera == null or actions.is_empty():
		return
	if not annotations_visible:
		if draw_hud:
			_draw_hud()
		return
	compute_projection()

	# Arrows start at the bottom centre of the frame: the agent's own position
	# is at or behind the camera and does not project.
	var origin_screen := Vector2(size.x * 0.5, size.y)
	for a in actions:
		if not _projectable.has(a.index):
			continue
		var p: Vector2 = _projectable[a.index]
		var col := _color_for(a.index)
		if a.is_turn_around:
			if selected_index != 0 and _hovered != 0:
				col = TURN_AROUND_COLOR
			_draw_disc(p, 0, col)
			_draw_centered(p + Vector2(0.0, 40.0), "TURN AROUND", 16, col)
			continue
		_draw_arrow(origin_screen, p, col)
		_draw_disc(p, a.index, col)

	if draw_hud:
		_draw_hud()


func _color_for(index: int) -> Color:
	if index == selected_index:
		return SELECTED_COLOR
	if index == _hovered:
		return HOVER_COLOR
	return ARROW_COLOR


## Where the disc goes: along the action's heading, at `annotation_distance`,
## dropped onto the floor plane. The heading is exact; the distance is a drawing
## choice (see `annotation_distance`).
func _endpoint(a: PolarAction) -> Vector3:
	var drawn := a
	if cfg != null and cfg.annotation_distance > 0.0 and not a.is_turn_around:
		drawn = PolarAction.new(cfg.annotation_distance, a.theta)
	var world := drawn.endpoint_world(agent_xform)
	if project_to_ground and cfg != null:
		world.y -= cfg.draw_plane_offset
	return world


func _project(world: Vector3) -> Vector2:
	return _camera.unproject_position(world)


## Inset the frame by the disc radius, so an action sitting exactly on the edge
## of the FOV is drawn fully inside the image instead of straddling the border.
func _clamp_to_frame(p: Vector2) -> Vector2:
	var m := DISC_RADIUS + 4.0
	return Vector2(
		clampf(p.x, m, size.x - m),
		clampf(p.y, m, size.y - m)
	)


func _can_project(p: Vector2) -> bool:
	var edge: float = cfg.image_edge_threshold if cfg != null else 0.04
	var m := size * edge
	return p.x > m.x and p.x < size.x - m.x and p.y > m.y and p.y < size.y - m.y


func _draw_arrow(from: Vector2, to: Vector2, col: Color) -> void:
	var dir := to - from
	if dir.length() < 1.0:
		return
	draw_line(from, to - dir.normalized() * DISC_RADIUS, Color(col, 0.55), 3.0, true)


func _draw_disc(p: Vector2, number: int, col: Color) -> void:
	draw_circle(p, DISC_RADIUS, Color(0.0, 0.0, 0.0, 0.65))
	draw_arc(p, DISC_RADIUS, 0.0, TAU, 32, col, 3.0, true)
	_draw_centered(p + Vector2(0.0, 7.0), str(number), 20, col)


func _draw_centered(p: Vector2, text: String, font_size: int, col: Color) -> void:
	var w := _font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	draw_string(_font, p - Vector2(w * 0.5, 0.0), text, HORIZONTAL_ALIGNMENT_LEFT, -1,
		font_size, col)


func _draw_hud() -> void:
	var y := 24.0
	for entry in [[status_text, HUD_STATUS_SIZE], [pose_text, HUD_POSE_SIZE]]:
		var line: String = entry[0]
		var font_size: int = entry[1]
		if line == "":
			continue
		draw_string(_font, Vector2(16.0, y), line, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size,
			Color(1, 1, 1, 0.9))
		y += font_size + 12.0
