extends Node3D

## Throwaway: hosts a site under a cinematic camera so a scripted replay can be
## filmed from outside the agent's head. Not part of the harness — the numbers
## come from the site scene flown directly, exactly as before. See
## notes/broll/README.md.
##
##   godot --path first-project res://tools/broll.tscn \
##       --write-movie out.avi --fixed-fps 30 -- \
##       --site=res://sites/s01_occluder_dropin/site.tscn \
##       --cam=reveal --scripted-indices=3,3,3 --speed=0.3 --stop-on-goal=false
##
## The site is instanced as a child rather than being the root, which changes
## nothing for the run: VLMNavRunSession and VLMNavDecisionClient read
## OS.get_cmdline_user_args() directly, not their position in the tree, so
## --scripted-indices / --speed / --max-steps arrive the same way.

## Room half-extents to keep the camera inside, so it never films a wall's back.
const ROOM_X := 23.0
const ROOM_Z := 11.0

var _site_path: String = ""
var _mode: String = "reveal"
var _fov: float = 62.0
var _still: String = ""
var _subs_path: String = ""
var _subs: Dictionary = {}
var _head_label: Label
var _step_label: Label
var _reason_label: Label
var _caption: Control
var _agent: VLMNavController
var _camera: Camera3D
var _spawn: Vector3 = Vector3.ZERO
var _goal: Vector3 = Vector3.ZERO
var _reveal_done: bool = false
## The viewport size the shot was framed for, sampled once the run has settled.
var _pinned_size: Vector2i = Vector2i.ZERO
var _orbit_angle: float = 0.0
var _chase: Transform3D
var _chase_primed: bool = false


func _ready() -> void:
	_parse_args()
	_pin_window()
	if _site_path == "":
		push_error("broll: --site=res://sites/<id>/site.tscn is required")
		get_tree().quit(2)
		return

	var site: Node = (load(_site_path) as PackedScene).instantiate()
	add_child(site)

	_agent = _find_controller(site)
	if _agent == null:
		push_error("broll: no VLMNavController under " + _site_path)
		get_tree().quit(2)
		return

	_collect_landmarks()

	if _mode == "fpv":
		_setup_fpv()
	else:
		# The agent's HUD is a CanvasLayer and would sit on top of the shot.
		var ui := _agent.get_node_or_null("UI")
		if ui != null:
			ui.visible = false
		# The controller has a collider and a camera but no mesh, so in third
		# person there is nothing to look at. Give it a body for the shoot.
		_add_avatar(_agent)
		_camera = Camera3D.new()
		_camera.fov = _fov
		_camera.near = 0.05
		_camera.far = 500.0
		add_child(_camera)

	_agent.action_started.connect(_on_action_started)
	_build_caption()

	# One frame so the site's own camera has claimed `current`, then take it.
	# In fpv mode that camera IS the shot, so it is left alone.
	await get_tree().process_frame
	if _mode != "fpv":
		_camera.current = true
		_place_camera(0.0)

	print("BROLL CAM %s  fov %.0f  site %s" % [_mode, _fov, _site_path])

	if _still != "":
		await _shoot_still()


func _process(delta: float) -> void:
	_check_window()
	if _mode == "fpv":
		return
	if _camera != null and _agent != null and is_instance_valid(_agent):
		_place_camera(delta)


func _on_action_started(_a) -> void:
	# Engine time is deterministic under --fixed-fps, so frame/fps is the exact
	# video timestamp of this step — worth logging even though the caption is
	# drawn in-engine and needs no external timing.
	var number := _agent.current_step_number()
	print("BROLL STEP %d FRAME %d" % [number, Engine.get_frames_drawn()])
	_show_caption(number - 1)
	if _mode == "fpv":
		# The controller hides the fan the instant a move starts: live, a fan
		# sliding across the frame would read as if it were still selectable.
		# On a recording of a decision already made, the opposite is true —
		# the discs are world positions frozen at the proposing pose, so they
		# stay pinned to the floor and the agent is seen flying to the one it
		# picked, drawn green by `selected_index`.
		_agent.overlay.annotations_visible = true


# -------------------------------------------------------------------- caption

## The model's own words, drawn in-engine rather than burned on afterwards.
## ffmpeg is not guaranteed to have libass — this machine's build has no `ass`,
## `subtitles` or `drawtext` filter at all — and drawing here is frame-exact
## anyway: the caption changes on the tick the step starts.
func _build_caption() -> void:
	if _subs_path == "":
		return
	var text := FileAccess.get_file_as_string(_subs_path)
	if text == "":
		push_warning("broll: no subtitles at " + _subs_path)
		return
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("broll: subtitles are not a JSON object")
		return
	_subs = parsed

	var layer := CanvasLayer.new()
	layer.layer = 10
	add_child(layer)

	_head_label = Label.new()
	_head_label.text = str(_subs.get("header", ""))
	_head_label.add_theme_font_size_override("font_size", 19)
	_head_label.add_theme_color_override("font_color", Color(1.0, 0.75, 0.47))
	_head_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.85))
	_head_label.add_theme_constant_override("shadow_offset_x", 2)
	_head_label.add_theme_constant_override("shadow_offset_y", 2)
	_head_label.position = Vector2(30.0, 22.0)
	layer.add_child(_head_label)

	# A translucent band, so a long reason stays legible over a bright floor.
	_caption = Control.new()
	_caption.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_caption.offset_top = -132.0
	_caption.visible = false
	layer.add_child(_caption)

	var band := ColorRect.new()
	band.color = Color(0.04, 0.05, 0.07, 0.72)
	band.set_anchors_preset(Control.PRESET_FULL_RECT)
	_caption.add_child(band)

	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side in ["margin_left", "margin_right"]:
		margin.add_theme_constant_override(side, 34)
	margin.add_theme_constant_override("margin_top", 14)
	margin.add_theme_constant_override("margin_bottom", 14)
	_caption.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 6)
	margin.add_child(column)

	_step_label = Label.new()
	_step_label.add_theme_font_size_override("font_size", 22)
	_step_label.add_theme_color_override("font_color", Color(0.47, 0.75, 1.0))
	column.add_child(_step_label)

	_reason_label = Label.new()
	_reason_label.add_theme_font_size_override("font_size", 19)
	_reason_label.add_theme_color_override("font_color", Color(0.86, 0.89, 0.93))
	_reason_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_reason_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_reason_label.clip_text = true
	column.add_child(_reason_label)


func _show_caption(step: int) -> void:
	if _caption == null:
		return
	var entry = (_subs.get("steps", {}) as Dictionary).get(str(step))
	if typeof(entry) != TYPE_DICTIONARY:
		_caption.visible = false
		return
	_step_label.text = "step %d  —  %s" % [step, str(entry.get("action", "?"))]
	_reason_label.text = str(entry.get("reason", ""))
	_caption.visible = true


# ------------------------------------------------------------------- window

## Stop the window manager from re-tiling the window mid-shot.
##
## yabai (and any tiling WM) grabs a new window about a second after it opens
## and resizes it to a tile. The stretch mode is `canvas_items` with aspect
## `expand`, so a taller window means a taller VIEWPORT, and with the camera on
## KEEP_WIDTH that means a wider vertical field of view part-way through the
## recording — which reads exactly like a zoom, because the framing genuinely
## changes. Marking the window non-resizable is enough: tiling managers leave
## non-resizable windows floating.
##
## The re-assert in `_check_window` is the belt to that braces: if something
## resizes it anyway, the shot is put back rather than silently reframed.
func _pin_window() -> void:
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_RESIZE_DISABLED, true)


func _check_window() -> void:
	var vs := get_viewport().get_visible_rect().size
	if _pinned_size == Vector2i.ZERO:
		_pinned_size = Vector2i(vs)
		return
	if Vector2i(vs) == _pinned_size:
		return
	push_warning("broll: viewport moved from %s to %s mid-shot — putting it back"
		% [_pinned_size, vs])
	DisplayServer.window_set_size(_pinned_size)


# ------------------------------------------------------------------ launch args

func _parse_args() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--site="):
			_site_path = arg.trim_prefix("--site=")
		elif arg.begins_with("--cam="):
			_mode = arg.trim_prefix("--cam=")
		elif arg.begins_with("--cam-fov="):
			_fov = float(arg.trim_prefix("--cam-fov="))
		elif arg.begins_with("--still="):
			_still = arg.trim_prefix("--still=")
		elif arg.begins_with("--subs="):
			_subs_path = arg.trim_prefix("--subs=")


# --------------------------------------------------------------------- fpv

## Keep the agent's own camera and HUD, but stop the recording from cropping
## the view.
##
## The agent flies with `KEEP_WIDTH`, so `fov` is the HORIZONTAL field of view
## and the vertical one falls out of the window aspect. That is right for the
## square frames the model is sent and wrong for a 16:9 recording: Movie Maker
## captures at the project viewport whatever the window was resized to, and at
## 1152x648 the same 87 degrees across the width leaves only 56 down the
## height. The picture looks zoomed in because it is — the top and bottom of
## what the model saw are simply gone.
##
## `KEEP_HEIGHT` with the same number makes 87 the VERTICAL field of view, so
## every pixel the model was sent is present, with extra periphery either side
## instead of a crop. `_mask_model_frame` then marks where the model's frame
## actually ended, so the wider view cannot be mistaken for what it saw.
func _setup_fpv() -> void:
	_camera = _agent.camera
	_camera.keep_aspect = Camera3D.KEEP_HEIGHT
	_mask_model_frame()


## Dim the periphery outside the square the model was actually sent.
##
## With `KEEP_HEIGHT` the vertical half-angle fills half the frame height, and
## the model's horizontal half-angle is the same 87/2 — so its frame is exactly
## a centred square of side = viewport height. No trigonometry needed: the
## square is as wide as the picture is tall.
func _mask_model_frame() -> void:
	var view := get_viewport().get_visible_rect().size
	var bar := maxf((view.x - view.y) * 0.5, 0.0)
	if bar <= 1.0:
		return  # already square: nothing was cropped, nothing to mark

	var layer := CanvasLayer.new()
	layer.layer = 0  # under the agent's HUD, which stays crisp
	add_child(layer)

	for left in [true, false]:
		var shade := ColorRect.new()
		shade.color = Color(0.0, 0.0, 0.0, 0.5)
		shade.position = Vector2(0.0 if left else view.x - bar, 0.0)
		shade.size = Vector2(bar, view.y)
		layer.add_child(shade)

		var edge := ColorRect.new()
		edge.color = Color(1.0, 0.75, 0.47, 0.55)
		edge.position = Vector2(bar - 2.0 if left else view.x - bar, 0.0)
		edge.size = Vector2(2.0, view.y)
		layer.add_child(edge)

	# Not "what the model saw": `clamp_to_frame` pulls the outermost discs back
	# inside the square when the frame really is 1:1, so on this wider view
	# actions 1 and 5 sit outside the box they would have been clamped into.
	var note := Label.new()
	note.text = "model's frame (1:1) — edge actions are clamped to it"
	note.add_theme_font_size_override("font_size", 15)
	note.add_theme_color_override("font_color", Color(1.0, 0.75, 0.47, 0.85))
	note.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	note.add_theme_constant_override("shadow_offset_x", 2)
	note.add_theme_constant_override("shadow_offset_y", 2)
	note.position = Vector2(bar + 10.0, view.y - 26.0)
	layer.add_child(note)


# ------------------------------------------------------------------ scene setup

func _find_controller(node: Node) -> VLMNavController:
	if node is VLMNavController:
		return node
	for child in node.get_children():
		var found := _find_controller(child)
		if found != null:
			return found
	return null


## A bright capsule with a nose cone, so the agent reads as a thing with a
## heading at 15 m. -Z is forward, matching the controller's own convention.
func _add_avatar(agent: Node3D) -> void:
	var body := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.38
	sphere.height = 0.76
	body.mesh = sphere
	body.material_override = _emissive(Color(1.0, 0.45, 0.15), 2.2)
	agent.add_child(body)

	var nose := MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.0
	cone.bottom_radius = 0.24
	cone.height = 0.7
	nose.mesh = cone
	nose.material_override = _emissive(Color(1.0, 0.85, 0.4), 3.0)
	# Cylinders point +Y; rotate so the tip leads along -Z.
	nose.rotation = Vector3(-PI / 2.0, 0.0, 0.0)
	nose.position = Vector3(0.0, 0.0, -0.55)
	agent.add_child(nose)

	var lamp := OmniLight3D.new()
	lamp.light_color = Color(1.0, 0.6, 0.3)
	lamp.light_energy = 2.0
	lamp.omni_range = 7.0
	agent.add_child(lamp)


func _emissive(colour: Color, energy: float) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = colour
	mat.emission_enabled = true
	mat.emission = colour
	mat.emission_energy_multiplier = energy
	return mat


## The two ends of the task. Every shot is framed off the line between them,
## because that is the line the prop interrupts.
func _collect_landmarks() -> void:
	_spawn = _agent.global_position
	var goal := get_tree().get_first_node_in_group(VLMNavGoal.GROUP) as Node3D
	_goal = goal.global_position if goal != null else _spawn - Vector3(24.0, 0.0, 0.0)


# --------------------------------------------------------------------- cameras

func _place_camera(delta: float) -> void:
	match _mode:
		"chase":
			_cam_chase(delta)
		"orbit":
			_cam_orbit(delta)
		"dolly":
			_cam_dolly(delta)
		_:
			_cam_reveal()


## Static wide, parked over the agent's shoulder on the spawn side and aimed
## down the hall at the prop. The agent flies away from the lens into the thing
## that changes, so the change happens in the middle of frame — the shot the
## FPV recording cannot give.
##
## Deliberately NOT on the goal side: s02's dividing wall is 12 m tall, so a
## camera behind the goal cannot see the agent at all until it is through a
## doorway, which in these runs never happens.
func _cam_reveal() -> void:
	if _reveal_done:
		return  # static: solved once, then left alone
	var axis := (_spawn - _goal)
	axis.y = 0.0
	axis = axis.normalized()
	var lateral := axis.cross(Vector3.UP).normalized()
	var pos := _spawn + axis * 5.0 + lateral * 9.0 + Vector3(0.0, 7.0, 0.0)
	pos.x = clampf(pos.x, -ROOM_X, ROOM_X)
	pos.z = clampf(pos.z, -ROOM_Z, ROOM_Z)
	_camera.global_position = pos
	_camera.look_at((_spawn + _goal) * 0.5 + Vector3(0.0, 2.0, 0.0), Vector3.UP)
	_reveal_done = true


## Smoothed follow, behind and above, looking where the agent is going.
func _cam_chase(delta: float) -> void:
	var back := _agent.global_transform.basis.z  # +Z is behind: forward is -Z
	var want := _agent.global_position + back * 5.5 + Vector3(0.0, 3.2, 0.0)
	want.y = clampf(want.y, 1.5, 11.0)
	want.x = clampf(want.x, -ROOM_X, ROOM_X)
	want.z = clampf(want.z, -ROOM_Z, ROOM_Z)
	var target := _agent.global_position - back * 4.0 + Vector3(0.0, 0.6, 0.0)
	if not _chase_primed:
		_camera.global_position = want
		_chase_primed = true
	else:
		# Frame-rate independent smoothing, so the shot looks the same whatever
		# --fixed-fps the recording used.
		_camera.global_position = _camera.global_position.lerp(
			want, 1.0 - pow(0.0025, delta))
	_camera.look_at(target, Vector3.UP)


## Slow orbit around the agent — the establishing shot.
func _cam_orbit(delta: float) -> void:
	_orbit_angle += delta * 0.32
	var centre := _agent.global_position
	var radius := 11.0
	var pos := centre + Vector3(cos(_orbit_angle) * radius, 6.5,
		sin(_orbit_angle) * radius)
	pos.x = clampf(pos.x, -ROOM_X, ROOM_X)
	pos.z = clampf(pos.z, -ROOM_Z, ROOM_Z)
	_camera.global_position = pos
	_camera.look_at(centre + Vector3(0.0, 0.8, 0.0), Vector3.UP)


## Lateral track past the wall, agent-tracking pan. Locked to the near side so
## the changing prop stays between the camera and the goal.
func _cam_dolly(delta: float) -> void:
	_orbit_angle += delta * 1.6
	var z := ROOM_Z - 1.5
	var x := clampf(8.0 - _orbit_angle, -14.0, 14.0)
	_camera.global_position = Vector3(x, 4.5, z)
	_camera.look_at(_agent.global_position + Vector3(0.0, 0.8, 0.0), Vector3.UP)


# ------------------------------------------------------------ still-frame mode

## Render one PNG and quit, for tuning a camera without waiting on a recording.
func _shoot_still() -> void:
	for i in 4:
		await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_still)
	print("BROLL STILL ", _still)
	get_tree().quit(0)
