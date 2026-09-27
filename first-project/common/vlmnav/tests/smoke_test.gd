extends Node3D

## Headless self-check of the action interface. Drives the controller through a
## fixed index list and asserts the invariants: the fan is offered every step,
## indices are unique and inside the FOV, and every chosen action executes.
##
##   godot --headless --path first-project res://common/vlmnav/tests/smoke_test.tscn
##
## Exit code 0 = pass.

@onready var agent: VLMNavController = $VLMNavController

## Set with `--capture-dir=<abs path>`: saves the annotated frame each step, so
## a windowed run leaves behind the images a decision-maker would have seen.
var capture_dir: String = ""

var steps := 0
var failures: Array[String] = []
const MAX_STEPS := 6


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			capture_dir = arg.trim_prefix("--capture-dir=")
	agent.actions_proposed.connect(_on_actions_proposed)
	agent.action_finished.connect(_on_action_finished)
	get_tree().create_timer(30.0).timeout.connect(_timeout)
	if capture_dir != "":
		# The opening frame, before anything has moved.
		get_tree().create_timer(1.0).timeout.connect(func(): _capture())


func _on_actions_proposed(proposed: Array) -> void:
	var expected: int = agent.config.num_actions + (1 if agent.config.include_turn_around else 0)
	if proposed.size() != expected:
		failures.append("step %d: %d actions, expected %d" % [steps, proposed.size(), expected])
	var seen := {}
	var line := "step %d:" % steps
	for a in proposed:
		line += " " + str(a)
		if seen.has(a.index):
			failures.append("step %d: duplicate index %d" % [steps, a.index])
		seen[a.index] = true
		if a.is_turn_around:
			continue
		if absf(a.theta) > agent.config.fov_rad() * 0.5 + 0.001:
			failures.append("step %d: action %d outside FOV" % [steps, a.index])
		if not is_equal_approx(a.r, agent.config.action_dist):
			failures.append("step %d: action %d has r %.2f" % [steps, a.index, a.r])
	print(line)


func _on_action_finished(action: PolarAction, collided: bool) -> void:
	steps += 1
	print("  executed %s -> %s yaw %+.0f deg%s" % [
		str(action), agent.global_position, rad_to_deg(agent.rotation.y),
		"  COLLIDED" if collided else "",
	])
	if capture_dir != "" and DisplayServer.get_name() != "headless":
		await _capture()
	if steps >= MAX_STEPS:
		_report()


func _capture() -> void:
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(capture_dir)
	agent.capture_annotated_frame().save_png("%s/step_%02d.png" % [capture_dir, steps])


func _timeout() -> void:
	failures.append("timed out after %d steps" % steps)
	_report()


func _report() -> void:
	if failures.is_empty():
		print("VLMNAV SMOKE TEST: PASS (%d steps)" % steps)
		get_tree().quit(0)
	else:
		for f in failures:
			printerr("FAIL: " + f)
		print("VLMNAV SMOKE TEST: FAIL (%d issues)" % failures.size())
		get_tree().quit(1)
