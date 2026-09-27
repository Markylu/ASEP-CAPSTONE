# VLMnav action interface — player controller

A controller whose entire input surface is the VLMnav action space. No WASD.
Each step the frame carries a fan of numbered annotations; you take one by
pressing its number, clicking the annotation, or clicking it in the selection
panel. The agent turns by that action's angle, moves its distance, and offers a
new fan.

Zero-shot: the fan is fixed geometry. No depth model, no navigability estimate,
no extra sensor — VLMnav's `navigability_mode: none`. Whether an action is a
good idea is the decision-maker's problem, which is the thing being tested.

Reference: Goetting, Singh, Loquercio, *End-to-End Navigation with Vision
Language Models* (arXiv 2411.05755).

## Files

| File | Role |
|---|---|
| `vlmnav_config.gd` | FOV, how many actions, how far, fan spread, speeds |
| `polar_action.gd` | One action: `(r, θ)` and its number |
| `action_overlay.gd` | Draws the annotations; click one to take it |
| `action_panel.gd` | Selection panel — one button per action on the frame |
| `goal_marker.gd` / `.tscn` | The movable target: beacon, distance and bearing helpers |
| `vlmnav_controller.gd` | State machine, execution, the public API |
| `vlmnav_controller.tscn` | The instanceable controller |
| `decision_client.gd` | Asks an external decider which action to take |
| `run_session.gd` | Reads the command line, pins the frame, ends the run |
| `rig.gd` / `vlmnav_rig.tscn` | Controller + client + session as one node; snaps to the site's `Spawn` |
| `../site_manifest.gd` | Loads the `site.json` beside the running scene |
| `../props/triggered_occluder.gd` | A box that rises out of the floor when the agent crosses a line |
| `tests/smoke_test.tscn` | Headless self-check |

## Use

Instance `vlmnav_controller.tscn` and place it at cruise height — it holds the
altitude it spawns at. Already in `main.tscn`, and its camera is `current`, so
it is the only way to move in the scene.

| Input | Effect |
|---|---|
| `0`–`9` | Take that action. `0` is turn around. |
| Click an annotation | Same. |
| Panel button | Same. |
| `Tab` | Show/hide the panel. |
| `H` | Show/hide the status line. |

All four go through `execute_index()`, and so does a model calling
`submit_action()`. Nothing can express a move that was not on the frame — which
is what makes a human run and a model run on the same site comparable.

`decision_source`: `MANUAL` (you), `EXTERNAL` (`decision_requested` fires with
the manifest, something answers with `submit_action`), `SCRIPTED` (replays
`scripted_indices`).

## Running a model

`decision_client.gd` and `run_session.gd` sit as children of the controller in
`main.tscn` and do nothing until the command line says otherwise — opening the
scene in the editor is still a manual baseline run. With a decider URL they take
the controller into `EXTERNAL` and fly it.

```bash
godot --path first-project -- \
    --run-id=run_2026-09-14_1830 \
    --decider-url=http://127.0.0.1:8000 \
    --max-steps=30
```

| Flag | Meaning |
|---|---|
| `--run-id=` | Names the run directory the decider writes |
| `--decider-url=` | Base URL of the decider. Absent = manual run. |
| `--max-steps=` | Hard ceiling, default 30 |
| `--max-collisions=` | Run is called off past this, default 3, -1 for no limit |
| `--stop-on-goal=` | End on REACHED, default true |
| `--frame-size=WxH` | Window is pinned to this, default 768x768 |
| `--scripted-indices=` | Replay a recorded index list; no model is called |
| `--speed=` | Turn/move speed multiplier, for watching. 1.0 is recorded speed. |
| `--freeze-world=` | Pause the world while waiting on `/decide`, default true |

`--frame-size` is not cosmetic. `fov_deg` is the *horizontal* FOV
(`KEEP_WIDTH`), so a different window shape is a different vertical FOV and a
different image — two runs at different window sizes are not comparable.

`--freeze-world` is on by default and pauses the SceneTree for each `/decide`
round trip, so site props (doors, occluders) do not move while the model
thinks. Without it, how far the world advances between two actions depends on
model latency and a slow model flies a different world from a fast one. The
choice is recorded in `/run/start`; runs with and without it do not compare.
Step records carry `sim_tick` (ticks actually simulated) next to `tick`
(engine physics frames, which keep counting while paused).

The run ends here, not at the model's discretion: max steps, arrival, the
collision budget, a wall-clock limit, or a decision error. A decision error —
timeout, unreachable decider, or an index that was not on the frame — fails the
run rather than substituting a default action, because a run with a substituted
step cannot be cited.

See `server/README.md` for the decider itself and `eval/replay.py` for
reproducing a recorded trajectory.

### Watching a replay

A run flies at 8 m/s, so nine steps are over in about two seconds. `--speed`
slows it down; no decider is needed, since a scripted run calls no model.

```bash
godot --path first-project -- \
    --scripted-indices=2,1,2,4,2,4,3,3,2 \
    --speed=0.15 --frame-size=1280x720
```

`--speed` is watch-only. Measured drift against a 1.0 run is 2.4e-5 m over nine
steps — inside `eval/replay.py`'s tolerance, but nonzero and accumulating, so a
run whose numbers are being cited should fly at 1.0.

## What the model is shown

`capture_decision_frame()` is the image a decision is made from: annotations,
and nothing else. The HUD and the panel are hidden for the capture because both
print world-frame truth — the agent's own position and yaw, the goal's world
coordinates and its exact bearing. Left visible, a model could read its way to
the goal instead of looking at the room, which is the thing under test.

Capturing has to wait two `frame_post_draw`: `decision_requested` is emitted
from inside `_physics_process`, before the overlay's `queue_redraw()` has been
serviced, so capturing immediately returns the *previous* step's annotations.

## Action space

`num_actions` headings evenly spaced across `fan_spread` of the FOV, each at
`action_dist` metres, numbered left to right, plus `0` for turn-around. With
`fan_spread = 1.0` the outermost actions sit on the exact left and right edges
of what the camera sees, so the fan spans the full frame width.

Three settings decide that, and they interact:

- `camera.keep_aspect` is forced to `KEEP_WIDTH`, so `fov_deg` means the
  *horizontal* FOV. Under Godot's default it means vertical, and the fan
  overshoots or undershoots the frame depending on window shape.
- `camera_pitch` must stay at 0 for a full-width fan. Tilting down squeezes
  ground annotations toward the centre, because a tilted camera reads a near
  ground point as further ahead than it is. VLMnav's -0.45 is a ground robot
  looking at the floor by its feet.
- `annotation_distance` (6 m) is where the disc is drawn along the heading,
  separate from `action_dist` (1.7 m) which is how far the agent actually goes.
  A level camera at altitude sees the real endpoint as nearly straight below it,
  which piles the discs into the bottom corners. Set it to 0 to draw each disc
  at its true endpoint.

Annotations are clamped inside the frame by `clamp_to_frame` so an action at the
very edge of the FOV is still fully drawn and still clickable. The image, the
panel and the manifest always list the same set.

## Goal

Drop `goal_marker.tscn` into a scene and drag it anywhere — the controller picks
it up by group (`vlmnav_goal`), no wiring needed; set `goal_path` only if a
scene has more than one. The panel shows its world coordinates, planar distance
and signed bearing, updated every frame so the readout tracks the marker while
you drag it. `arrival_radius` is reported as REACHED on the panel, in metres.

It is a marker, not a trigger: nothing about the action space changes near it,
and reaching it is the decision-maker's problem. Altitude is excluded from the
distance, since no action can close a height difference.

`get_manifest()` returns the step, the pose, and exactly the actions drawn on
the current frame, plus a `goal` block when one is in the scene, with
`config.to_dict()` attached so a decision can cite the action space that
produced it. Pair it with `capture_decision_frame()` for the image a model
should see, `capture_annotated_frame()` for the raw viewport including the HUD,
or `capture_clean_frame()` for the frame without annotations.

## Sites

A site is a folder under `first-project/sites/`: `site.tscn`, a `site.json`
manifest and a README (notes/PLAN.md §5). Instance `vlmnav_rig.tscn` under
`Rig`, mark one `Marker3D` with the group `vlmnav_spawn`, and the rig moves
itself onto that marker before the controller reads its cruise altitude — the
marker is the authority on the start pose.

Launch one by passing the scene positionally, before the `--`:

```bash
godot --path first-project res://sites/s01_occluder_dropin/site.tscn -- \
    --run-id=run_2026-09-17_1830 --decider-url=http://127.0.0.1:8000 --max-steps=30
```

There is no `--site` flag and no launcher scene, and `run/main_scene` still
points at `main.tscn`, so a bare launch and editor F5 are unchanged. Replays
need no flag either: `run.json` records `scene`, and `eval/replay.py` re-flies
whatever the run used.

`run_session.gd` reads `site.json` from beside the running scene and reports
`site_id` and `site_version` at `/run/start`, so a run says which geometry it
flew (`s01@v1`). A scene with no manifest beside it — `main.tscn` — records
null, which reads as "flown on the unmigrated sandbox".

## Props that change the world mid-run

`common/props/triggered_occluder.tscn` is an `Area3D` trigger plus a box that
rises out of the floor when the agent crosses it, blocking the view and the
path. Two rules make its runs citable, and they apply to any prop added later:

- **One size everywhere.** `STANDARD_SIZE` is 8 × 8 × 8 m, so occlusion strength
  is a property of where a box is, not how big it is. The editor warns if a
  scene overrides `box_size`.
- **Pace everything in physics ticks, never seconds.** A live model run idles
  ~17 s per step waiting on the decider; its replay idles not at all, so
  anything paced by elapsed time lands in a different step in the two and
  `eval/replay.py` reports `EVENTS DIFFER` or `COLLISION DIFFERS`. The box is
  solid from the *trigger* tick — the collider never moves, only the mesh does.

A prop joins the `vlmnav_event_source` group and emits
`event_fired(name, data)`. `run_session.gd` connects every member without
knowing what it is, so the event reaches `pose["events"]`, `events.jsonl` via
`POST /event`, and `metrics.json` as `occlusion_step` /
`goal_first_hidden_step` / `steps_to_reacquire`.

`goal.line_of_sight` in the manifest is an engine raycast from the camera to the
orb — ground truth for reading a run back, **not** something the agent senses.
`server/decider/prompt.py` does not read it, so adding it left `prompt_sha()`
and every earlier run comparable.

## Headless check

```bash
godot --headless --path first-project res://common/vlmnav/tests/smoke_test.tscn
```

Exit 0 on pass. Asserts the fan is offered every step, indices are unique and
inside the FOV, distances match `action_dist`, and every chosen action executes.
Add `-- --capture-dir=/abs/path` to a windowed run to save each step's frame.

## Not done yet

- No stop action: the model cannot declare arrival, so `run_session.gd` ends the
  run instead. Whether a model *knows* it has arrived is therefore not yet a
  measurable quantity.
- Collisions are recorded per step and counted in `metrics.json`, but nothing
  scores them against ground truth yet.
- The controller does not read a site manifest; the config it reports is its own.
- Godot's `--headless` does not render, so a model run needs a window.
