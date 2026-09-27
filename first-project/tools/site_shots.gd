extends Node3D

## Throwaway: loads a site, parks a camera at a few poses, writes PNGs, quits.
## Not part of the harness — see notes/screenshots/<folder>/README.md.

var _out: String = ""
var _site: String = ""
var _switch_after: bool = false


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.trim_prefix("--out=")
		elif arg.begins_with("--site="):
			_site = arg.trim_prefix("--site=")
		elif arg == "--switched":
			_switch_after = true
	var packed: PackedScene = load(_site)
	var site := packed.instantiate()
	add_child(site)
	# Same frame the agent gets: 768 square, 87° horizontal (KEEP_WIDTH). The
	# default KEEP_HEIGHT on a wide window shows more than the agent can see.
	DisplayServer.window_set_size(Vector2i(768, 768))
	var camera := Camera3D.new()
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = 87.0
	camera.near = 0.05
	camera.far = 400.0
	add_child(camera)
	camera.current = true
	await get_tree().process_frame
	# The agent's HUD is a CanvasLayer and would sit on top of every shot.
	var ui := site.find_child("UI", true, false)
	if ui != null:
		ui.visible = false
	if _switch_after:
		var bank := site.find_child("ThreeDoorsBank", true, false)
		for child in bank.get_children():
			if child is TriggeredDoor:
				var door := child as TriggeredDoor
				if door.name == "DoorB":
					door.close()
				elif door.name == String(bank.doors_to_open[0]):
					door.open()
		# Let the panels finish travelling before anything is photographed.
		for i in 40:
			await get_tree().physics_frame

	var bank_for_z := site.find_child("ThreeDoorsBank", true, false)
	var z := -9.0 if String(bank_for_z.doors_to_open[0]) == "DoorA" else 9.0
	# Poses hang off the spawn marker, so s02a/c (x = 12) and s02va/vc (x = 20)
	# shoot the same views. First switched frame = 4 straight steps of 1.7 m.
	var spawn_x: float = (get_tree().get_first_node_in_group("vlmnav_spawn") as Node3D).global_position.x
	var shots := [
		["doors_from_spawn", Vector3(spawn_x + 2.0, 9.0, 0.0), Vector3(0.0, 2.5, 0.0)],
		["agent_eye_spawn", Vector3(spawn_x, 1.75, 0.0), Vector3(-12.0, 1.75, 0.0)],
		["agent_eye_after_switch", Vector3(spawn_x - 4.0 * 1.7, 1.75, 0.0), Vector3(-12.0, 1.75, 0.0)],
		["flank_door", Vector3(7.0, 3.5, z * 0.5), Vector3(0.0, 2.5, z)],
	]
	for shot in shots:
		camera.global_position = shot[1]
		camera.look_at(shot[2], Vector3.UP)
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		image.save_png("%s/%s.png" % [_out, shot[0]])
		print("shot ", shot[0])
	get_tree().quit()
