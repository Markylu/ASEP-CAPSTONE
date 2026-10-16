extends Node
class_name VLMNavDecisionClient

## Answers the controller's `decision_requested` by asking an external service
## which numbered action to take.
##
## The controller already defines the whole contract — `get_manifest()` lists
## exactly the actions drawn on the frame, `submit_action()` is the only way to
## move. This node is the transport and nothing else: it captures the frame the
## decision is made from, posts it with the manifest, and hands the returned
## index straight to `submit_action()`.
##
## It writes nothing to disk. The decider owns the run directory, because it is
## the side that knows the model tag, the prompt version and the git SHA.

signal decision_received(step: int, index: int, reason: String)
signal run_failed(reason: String)

## Base URL of the decider, no trailing slash. Empty disables the client.
@export var decider_url: String = ""
## Identifies the run directory the decider writes into.
@export var run_id: String = ""
## Seconds before a decision request is treated as a failed run.
@export var request_timeout: float = 120.0
## Frame is downscaled to this width before sending, 0 to send as rendered.
## A safety net only: `run_session.gd` pins the window so captures are already
## this size. Aspect is preserved.
@export var frame_width: int = 768
## Pause the SceneTree for the whole /decide round trip. Without it site props
## keep moving while the model thinks, so how far the world advanced between
## two actions depends on model latency — a slow model and a fast one would
## fly different worlds. A run records which mode it used; the two do not mix.
@export var freeze_world: bool = true

var agent: VLMNavController
var last_frame_size: Vector2i = Vector2i.ZERO
## Cleared by the session when the run is ending, so a `propose()` that lands
## after the last step does not start another decision.
var accepting: bool = true

var _busy: bool = false
var _run_opened: bool = true
## Set from the decider's /run/start reply: its agent wants the frame without
## annotations as well (a goal identifier, agent a06 on). Sent beside the
## annotated frame, which stays the one the decision is made from.
var send_clean_frame: bool = false
## Step reports still on the wire. The run must not be closed past them.
var _steps_in_flight: int = 0


func _ready() -> void:
	agent = get_parent() as VLMNavController
	if agent == null:
		push_error("VLMNavDecisionClient must be a child of a VLMNavController")
		return
	# Keeps this node and its per-call HTTPRequest children running while the
	# tree is paused for a decision; the reply could never land otherwise.
	process_mode = Node.PROCESS_MODE_ALWAYS

	# Connected unconditionally; both handlers no-op until a URL is set. The
	# sibling RunSession reads the command line in its own _ready, which runs
	# after this one, so nothing can be decided at this point.
	agent.decision_requested.connect(_on_decision_requested)
	agent.step_completed.connect(_on_step_completed)


## Called by the session once a decider URL is known. Hands the controller over
## to this client; without it the scene stays in whatever mode it was saved in,
## so opening main.tscn in the editor is still a manual baseline run.
func activate(url: String, id: String) -> void:
	decider_url = url.rstrip("/")
	run_id = id
	if enabled():
		agent.decision_source = VLMNavController.DecisionSource.EXTERNAL


func enabled() -> bool:
	return decider_url != "" and agent != null


# ------------------------------------------------------------------- lifecycle

func start_run(extra: Dictionary = {}) -> void:
	if not enabled():
		return
	var body := {
		"run_id": run_id,
		"scene": get_tree().current_scene.scene_file_path,
		"config": agent.config.to_dict(),
		"frame_size": [last_frame_size.x, last_frame_size.y],
		"godot_version": Engine.get_version_info()["string"],
		"freeze_world": freeze_world,
	}
	body.merge(extra, true)
	_run_opened = false
	var reply := await _post("/run/start", body, 30.0)
	send_clean_frame = bool(reply.get("clean_frame", false))
	_run_opened = true


func end_run(reason: String) -> void:
	if not enabled():
		return
	# The last step's report and this call are started from the same frame, and
	# /run/end is the smaller request, so it used to win: the decider computed
	# metrics.json from a steps.jsonl that was one line short. Every count in
	# metrics came out low — a collision on the final step read as zero
	# collisions, and the run looked cleaner than it flew.
	while _steps_in_flight > 0:
		await get_tree().process_frame
	await _post("/run/end", {
		"run_id": run_id,
		"reason": reason,
		"steps": agent.step_count,
	}, 30.0)


# -------------------------------------------------------------------- decision

func _on_decision_requested(manifest: Dictionary) -> void:
	if not enabled() or _busy or not accepting:
		return
	_busy = true
	# Paused here rather than in the controller's `propose()`: a run that is
	# ending clears `accepting` from `step_completed`, which fires before
	# `propose()`, so the guard above keeps a finished run from pausing.
	if freeze_world:
		get_tree().paused = true
	# The first fan is proposed one process frame after launch, which is sooner
	# than /run/start can round-trip. Waiting keeps the decision inside a run
	# directory that already knows the model tag and the prompt hash.
	while not _run_opened:
		await get_tree().process_frame

	# Clean first, inside the paused window, so both frames show the same pose.
	var clean_png := PackedByteArray()
	if send_clean_frame:
		clean_png = _fit(await agent.capture_clean_frame()).save_png_to_buffer()
	var frame := await _capture_current_frame()
	var png := frame.save_png_to_buffer()
	var body := {
		"run_id": run_id,
		"step": manifest.get("step", agent.step_count),
		"manifest": manifest,
		"frame_png_b64": Marshalls.raw_to_base64(png),
		"frame_size": [frame.get_width(), frame.get_height()],
	}
	if send_clean_frame:
		body["clean_frame_png_b64"] = Marshalls.raw_to_base64(clean_png)
	var response := await _post("/decide", body, request_timeout)
	_busy = false

	if response.is_empty():
		_fail("decider unreachable or timed out at step %d" % agent.step_count)
		return
	if response.has("error"):
		_fail("decider error at step %d: %s" % [agent.step_count, response["error"]])
		return

	var index := int(response.get("index", -1))
	var reason := str(response.get("reason", ""))
	# A run whose action was silently substituted cannot be cited, so an index
	# the frame never offered ends the run rather than falling back to one.
	_resume()
	if not agent.submit_action(index):
		_fail("decider returned index %d, which is not an action on step %d's frame"
			% [index, agent.step_count])
		return
	decision_received.emit(agent.step_count, index, reason)


## The annotated frame the decision is made from, HUD and panel excluded.
##
## `capture_decision_frame()` waits two `frame_post_draw` for a reason worth
## keeping: `decision_requested` is emitted from `propose()`, which runs inside
## `_physics_process` via `_finish()`. At that moment `overlay.set_actions()`
## has run but its `queue_redraw()` has not been serviced, so capturing
## immediately returns the PREVIOUS step's annotations — the same reason
## `tests/smoke_test.gd` waits twice. Waiting is safe: the controller sits in
## AWAITING_DECISION until `submit_action()` lands.
func _capture_current_frame() -> Image:
	var img: Image = await agent.capture_decision_frame()
	last_frame_size = Vector2i(img.get_width(), img.get_height())
	return _fit(img)


## Downscale to `frame_width` if the capture came out wider. Both frames go
## through it, so the clean one always matches the annotated one in size.
func _fit(img: Image) -> Image:
	if frame_width > 0 and img.get_width() != frame_width:
		var h := int(round(float(img.get_height()) * float(frame_width) / float(img.get_width())))
		img.resize(frame_width, max(h, 1), Image.INTERPOLATE_LANCZOS)
	return img


func _on_step_completed(pose: Dictionary) -> void:
	if not enabled():
		return
	# The goal rides along so steps.jsonl stands on its own. A scripted run or a
	# replay has no decisions.jsonl to read arrival out of, and its metrics
	# should still say whether it got there.
	var body := {"run_id": run_id, "pose": pose}
	var goal: Variant = agent.get_manifest().get("goal")
	if goal != null:
		body["goal"] = goal
	_steps_in_flight += 1
	await _post("/step", body, 30.0)
	_steps_in_flight -= 1


## A timeline event from a site prop: the box deployed, a door opened. Recorded
## next to the steps rather than inside them so the run reads chronologically
## even when nothing moved, and so a prop that fires between steps is not lost.
func post_event(name: String, step: int, data: Dictionary = {}) -> void:
	if not enabled():
		return
	await _post("/event", {
		"run_id": run_id,
		"name": name,
		"step": step,
		"data": data,
	}, 30.0)


func _resume() -> void:
	get_tree().paused = false


func _fail(reason: String) -> void:
	_resume()
	printerr("VLMNAV RUN FAILED: " + reason)
	run_failed.emit(reason)


# ------------------------------------------------------------------- transport

## Returns the parsed response, or an empty Dictionary on any transport failure.
##
## One HTTPRequest per call, because several are legitimately in flight at once:
## `step_completed` and `decision_requested` are both emitted from `_finish()`,
## so an outcome report and the next decision overlap, and the end of a run
## overlaps the last report. A shared node refuses the second of any such pair.
func _post(path: String, body: Dictionary, timeout: float) -> Dictionary:
	var http := HTTPRequest.new()
	http.timeout = timeout
	add_child(http)
	var response := await _perform(http, path, body)
	http.queue_free()
	return response


func _perform(http: HTTPRequest, path: String, body: Dictionary) -> Dictionary:
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err := http.request(decider_url + path, headers, HTTPClient.METHOD_POST,
		JSON.stringify(body))
	if err != OK:
		printerr("POST %s failed to start: %d" % [path, err])
		return {}
	var result: Array = await http.request_completed
	var code: int = result[1]
	var text := (result[3] as PackedByteArray).get_string_from_utf8()
	if result[0] != HTTPRequest.RESULT_SUCCESS:
		printerr("POST %s transport error %d" % [path, result[0]])
		return {}
	if code < 200 or code >= 300:
		printerr("POST %s returned HTTP %d: %s" % [path, code, text])
		return {"error": "http %d" % code}
	var parsed: Variant = JSON.parse_string(text)
	return parsed if parsed is Dictionary else {}
