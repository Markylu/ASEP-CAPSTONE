extends PanelContainer
class_name VLMNavPanel

## The selection panel: one button per action currently on the frame. Same
## signal as clicking the annotation itself, so the panel, the arrows and the
## number keys are three doors into one `execute_index()`.

signal action_pressed(index: int)

var _list: VBoxContainer
var _title: Label
var _goal: Label
var _separator: HSeparator
var _buttons: Dictionary = {}  # index -> Button
var _fixed: Array[Node] = []


func _ready() -> void:
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	add_child(margin)

	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 4)
	margin.add_child(_list)

	_title = Label.new()
	_title.text = "ACTIONS"
	_title.add_theme_font_size_override("font_size", 14)
	_title.modulate = Color(1, 1, 1, 0.6)
	_list.add_child(_title)

	_goal = Label.new()
	_goal.add_theme_font_size_override("font_size", 20)
	_goal.modulate = Color(1.0, 0.55, 0.55, 0.95)
	_list.add_child(_goal)

	_separator = HSeparator.new()
	_list.add_child(_separator)

	# Rebuilt every step: the buttons. Everything else stays put.
	_fixed = [_title, _goal, _separator]
	set_goal_info(null, 0.0, 0.0)


## `visible_indices` comes from the overlay, so the panel never offers a number
## that is not drawn on the frame.
func set_actions(actions: Array[PolarAction], visible_indices: Array) -> void:
	for child in _list.get_children():
		if not _fixed.has(child):
			child.queue_free()
	_buttons.clear()
	for a in actions:
		if not visible_indices.has(a.index):
			continue
		var b := Button.new()
		b.text = "%d   %s" % [a.index, a.label()]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(240, 0)
		b.pressed.connect(func(): action_pressed.emit(a.index))
		_list.add_child(b)
		_buttons[a.index] = b


func set_enabled(enabled: bool) -> void:
	for index in _buttons:
		(_buttons[index] as Button).disabled = not enabled


## Goal readout. `position` null means there is no goal in the scene.
func set_goal_info(position, distance: float, bearing_rad: float, reached: bool = false) -> void:
	if _goal == null:
		return
	if position == null:
		_goal.text = "goal: none in scene"
		_goal.modulate = Color(1, 1, 1, 0.4)
		return
	var p: Vector3 = position
	_goal.text = "goal  %+.1f  %+.1f  %+.1f\n%.1f m   %+.0f°%s" % [
		p.x, p.y, p.z, distance, rad_to_deg(bearing_rad), "   REACHED" if reached else "",
	]
	_goal.modulate = Color(0.4, 1.0, 0.5, 1.0) if reached else Color(1.0, 0.55, 0.55, 0.95)


func set_title(text: String) -> void:
	if _title != null:
		_title.text = text
