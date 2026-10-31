extends Node3D

## Probe LD renderer: pre-renders the agent's camera at manifest poses under
## seven lighting conditions and writes PNGs plus a renders.jsonl index.
##
## Not part of the harness. Grown from site_shots.gd: same camera (768 square,
## 87 degrees KEEP_WIDTH, near 0.05), same two frame_post_draw waits per shot.
##
##   godot --path first-project res://tools/ld_render.tscn -- \
##       --manifest=/abs/manifest.jsonl --out=/abs/renders
##
## Manifest rows (JSON lines):
##   {"id", "set", "scene", "pos": [x,y,z], "yaw", "rig": {"d","angle_deg",
##    "material"} | null, "world": null | {"s02": "initial"|"final"} |
##    {"s03": "L"|"R"|null}, "lighting": "L0".."L6", "truth": {...}}
## Rows are grouped by (scene, world); one scene instance per group. Each row's
## PNG lands at <out>/<set>/<lighting>/<id>.png and the row plus "path" is
## appended to <out>/renders.jsonl. Rows whose PNG already exists are skipped,
## so a killed run resumes. Exit code is non-zero if any row failed.
##
## Lighting is camera-relative: the sun azimuth is the camera yaw ("behind")
## or yaw + 90 degrees ("side"), so every pose sees the same stimulus.

const WALL_TEXTURE := "res://addons/kenney_prototype-textures/Vector/texture_01.svg"
const SETTLE_PHYSICS_FRAMES := 5
const PROGRESS_EVERY := 25

var _manifest_path: String = ""
var _out: String = ""
var _camera: Camera3D
var _done: int = 0
var _skipped: int = 0
var _failed: int = 0


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--manifest="):
			_manifest_path = arg.trim_prefix("--manifest=")
		elif arg.begins_with("--out="):
			_out = arg.trim_prefix("--out=")
	if _manifest_path == "" or _out == "":
		push_error("usage: -- --manifest=<path.jsonl> --out=<dir>")
		get_tree().quit(2)
		return
	var rows := _read_manifest(_manifest_path)
	if rows.is_empty():
		push_error("ld_render: no rows in %s" % _manifest_path)
		get_tree().quit(2)
		return

	# Same frame the agent gets: 768 square, 87 degrees horizontal (KEEP_WIDTH).
	DisplayServer.window_set_size(Vector2i(768, 768))
	_camera = Camera3D.new()
	_camera.keep_aspect = Camera3D.KEEP_WIDTH
	_camera.fov = 87.0
	_camera.near = 0.05
	_camera.far = 400.0
	add_child(_camera)
	_camera.current = true
	await get_tree().process_frame
	await get_tree().process_frame

	DirAccess.make_dir_recursive_absolute(_out)
	var groups := _group_rows(rows)
	print("ld_render: %d rows in %d groups -> %s" % [rows.size(), groups.size(), _out])
	for key in groups:
		await _render_group(groups[key])
	print("ld_render: done %d, skipped %d, failed %d" % [_done, _skipped, _failed])
	get_tree().quit(1 if _failed > 0 else 0)


# ------------------------------------------------------------------ manifest

func _read_manifest(path: String) -> Array:
	var rows := []
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("ld_render: cannot open %s" % path)
		return rows
	while not f.eof_reached():
		var line := f.get_line().strip_edges()
		if line == "":
			continue
		var parsed = JSON.parse_string(line)
		if typeof(parsed) != TYPE_DICTIONARY:
			push_error("ld_render: bad manifest line: %s" % line.left(80))
			_failed += 1
			continue
		rows.append(parsed)
	return rows


## Group key is the scene path plus the world as JSON, in first-seen order.
func _group_rows(rows: Array) -> Dictionary:
	var groups := {}
	for row in rows:
		var key := "%s|%s" % [row.get("scene", ""), JSON.stringify(row.get("world"))]
		if not groups.has(key):
			groups[key] = []
		groups[key].append(row)
	return groups


# ------------------------------------------------------------------ one group

func _render_group(rows: Array) -> void:
	var first: Dictionary = rows[0]
	var scene_path: String = first.get("scene", "")
	var packed: PackedScene = load(scene_path)
	if packed == null:
		push_error("ld_render: cannot load %s" % scene_path)
		_failed += rows.size()
		return
	var scene: Node = packed.instantiate()
	# Sites instance VLMNavRig under `Rig`; pulling it out before the scene
	# enters the tree means no controller or run session ever runs _ready.
	var rig := scene.get_node_or_null("Rig")
	if rig != null and scene.name != "Rig":
		scene.remove_child(rig)
		rig.free()
	add_child(scene)
	var ui := scene.find_child("UI", true, false)
	if ui != null:
		ui.visible = false
	_apply_world(scene, first.get("world"))
	# Doors snap, but give the CSG and shadow maps a few ticks anyway.
	for i in SETTLE_PHYSICS_FRAMES:
		await get_tree().physics_frame

	var envs := scene.find_children("*", "WorldEnvironment", true, false)
	var lights := scene.find_children("*", "DirectionalLight3D", true, false)
	if envs.is_empty() or lights.is_empty():
		push_error("ld_render: %s has no WorldEnvironment or DirectionalLight3D" % scene_path)
		_failed += rows.size()
		scene.queue_free()
		return
	var env := envs[0] as WorldEnvironment
	var light := lights[0] as DirectionalLight3D
	# Never edit the shared sub-resource: keep a pristine copy and hand the
	# WorldEnvironment a fresh duplicate for every row.
	var pristine: Environment = env.environment.duplicate()
	env.environment = pristine.duplicate()
	var light_xform := light.transform
	var light_energy := light.light_energy
	var light_visible := light.visible

	var ceiling := _make_ceiling(scene)
	scene.add_child(ceiling)

	for row in rows:
		var rel := "%s/%s/%s.png" % [row.get("set", "X"), row.get("lighting", "L0"), row.get("id", "")]
		var png := _out.path_join(rel)
		if FileAccess.file_exists(png):
			_skipped += 1
			_tick()
			continue
		# Reset to the loaded state, then apply this row.
		env.environment = pristine.duplicate()
		light.transform = light_xform
		light.light_energy = light_energy
		light.visible = light_visible
		ceiling.visible = false

		var pos_arr: Array = row.get("pos", [])
		var yaw: float = float(row.get("yaw", 0.0))
		if pos_arr.size() != 3:
			push_error("ld_render: row %s has no pos" % row.get("id"))
			_failed += 1
			_tick()
			continue
		var pos := Vector3(float(pos_arr[0]), float(pos_arr[1]), float(pos_arr[2]))
		if not _apply_rig(scene, row.get("rig")):
			_failed += 1
			_tick()
			continue
		_apply_lighting(String(row.get("lighting", "L0")), env, light, ceiling, pos, yaw)
		_camera.global_position = pos
		_camera.rotation = Vector3(0.0, yaw, 0.0)
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		DirAccess.make_dir_recursive_absolute(png.get_base_dir())
		var err := image.save_png(png)
		if err != OK:
			push_error("ld_render: save_png %s failed: %s" % [png, error_string(err)])
			_failed += 1
			_tick()
			continue
		var record: Dictionary = row.duplicate(true)
		record["path"] = rel
		_append_record(record)
		_done += 1
		_tick()

	scene.queue_free()
	await get_tree().process_frame


func _tick() -> void:
	var n := _done + _skipped + _failed
	if n % PROGRESS_EVERY == 0:
		print("ld_render: %d rows (done %d, skipped %d, failed %d)" % [n, _done, _skipped, _failed])


func _append_record(record: Dictionary) -> void:
	var path := _out.path_join("renders.jsonl")
	var f: FileAccess
	if FileAccess.file_exists(path):
		f = FileAccess.open(path, FileAccess.READ_WRITE)
		if f != null:
			f.seek_end()
	else:
		f = FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("ld_render: cannot append to %s" % path)
		_failed += 1
		return
	f.store_line(JSON.stringify(record))
	f.close()


# ------------------------------------------------------------------ world

## Mirrors run_session.gd:_apply_world for the two site families the probe
## replays. s02: `final` puts the post-trigger layout in place, `initial`
## disarms the bank. s03: the branch whose name ends with `side` is closed,
## the other disarmed; side null disarms both.
func _apply_world(scene: Node, world) -> void:
	if world == null or typeof(world) != TYPE_DICTIONARY:
		return
	if world.has("s02"):
		var bank := scene.find_child("ThreeDoorsBank", true, false) as TriggeredDoorBank
		if bank == null:
			push_error("ld_render: world s02 but no ThreeDoorsBank in scene")
			return
		if String(world["s02"]) == "final":
			bank.apply_final_state()
		else:
			bank.disarm()
	elif world.has("s03"):
		var side = world["s03"]
		for bank_name in ["BranchL", "BranchR"]:
			var bank := scene.get_node_or_null("Props/" + bank_name) as TriggeredDoorBank
			if bank == null:
				push_error("ld_render: world s03 but no Props/%s in scene" % bank_name)
				continue
			if side != null and bank_name.ends_with(String(side)):
				bank.close_immediate()
			else:
				bank.disarm()


# ------------------------------------------------------------------ rig

func _apply_rig(scene: Node, rig) -> bool:
	if rig == null or typeof(rig) != TYPE_DICTIONARY:
		return true
	var pivot := scene.get_node_or_null("WallPivot") as Node3D
	var wall := scene.get_node_or_null("WallPivot/Wall") as CSGBox3D
	if pivot == null or wall == null:
		push_error("ld_render: rig row but scene has no WallPivot/Wall")
		return false
	pivot.rotation.y = deg_to_rad(float(rig.get("angle_deg", 0.0)))
	var mat_key := "wall_%s" % String(rig.get("material", "dark"))
	if not wall.has_meta(mat_key):
		push_error("ld_render: rig material '%s' not on Wall" % mat_key)
		return false
	wall.material = wall.get_meta(mat_key)
	return true


# ------------------------------------------------------------------ lighting

## The light shines along its local -Z, so rotation (-el, az, 0) is a sun at
## elevation `el` coming from azimuth `az`; az = camera yaw is behind the
## camera shining along the view, az = yaw + 90 degrees is from the side.
func _apply_lighting(lighting: String, env: WorldEnvironment, light: DirectionalLight3D,
		ceiling: CSGBox3D, pos: Vector3, yaw: float) -> void:
	match lighting:
		"L0":
			pass
		"L1":
			light.rotation = Vector3(-deg_to_rad(20.0), yaw, 0.0)
		"L2":
			light.rotation = Vector3(-deg_to_rad(20.0), yaw + PI / 2.0, 0.0)
		"L3":
			light.rotation = Vector3(-deg_to_rad(62.0), yaw, 0.0)
		"L4":
			light.rotation = Vector3(-deg_to_rad(85.0), yaw, 0.0)
		"L5":
			_ambient_only(env, light, 1.0)
		"L6":
			_ambient_only(env, light, 2.0)
			ceiling.global_position = Vector3(pos.x, 3.3, pos.z)
			ceiling.visible = true
		_:
			push_error("ld_render: unknown lighting %s, rendered as L0" % lighting)


func _ambient_only(env: WorldEnvironment, light: DirectionalLight3D, energy: float) -> void:
	light.visible = false
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color.WHITE
	env.environment.ambient_light_energy = energy


## L6's ceiling: a standalone CSG slab under the scene root (not inside a
## CSGCombiner3D, so it never unions with site geometry), hidden until a L6
## row centres it over the camera. Wall material: the rig's own, else the
## sites' wall material rebuilt from the same texture and triplanar settings.
func _make_ceiling(scene: Node) -> CSGBox3D:
	var box := CSGBox3D.new()
	box.name = "LDCeiling"
	box.size = Vector3(60.0, 0.1, 30.0)
	box.visible = false
	var wall := scene.get_node_or_null("WallPivot/Wall") as CSGBox3D
	if wall != null and wall.material != null:
		box.material = wall.material
	else:
		var mat := StandardMaterial3D.new()
		mat.albedo_texture = load(WALL_TEXTURE)
		mat.uv1_scale = Vector3(0.25, 0.25, 0.25)
		mat.uv1_triplanar = true
		mat.uv1_world_triplanar = true
		mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		box.material = mat
	return box
