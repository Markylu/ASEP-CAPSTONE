# s01 — Occluder Drop-In

**Hypothesis:** A VLM agent flying a clear line of sight to the goal will keep
committing to that heading after the goal is occluded, rather than replanning
around the obstacle that replaced it.

**Class:** geometry · **Status:** draft · **Version:** 1

## The condition

The agent spawns at `(12, 1.75, 0)` facing −X with the goal 24.0 m away at
bearing 0° — dead centre of the first frame, nothing between them. Crossing
`x = 6.5` (partway through step 3) fires an `Area3D` that raises an 8 m cube out
of the floor at `x = -2`, taking the sightline and the straight path with it.

- First occluded frame: **4**
- A straight-line policy collides during **step 6** (near face `x = +2`)
- Side gaps: **7.75 m** either side of the cube, so the task stays solvable
- The goal only reappears once the agent clears the cube's far face at `x = -6`

## Why the cube is 8 m

The goal's 6 m beam, not its 0.25 m orb, is what makes a 24 m sightline legible
(~125 px vs ~10 px at 768 px / 87°). Blocking the orb is not enough. Solving
"ray from camera at `y = 1.75` to beam top at `y = 7`, evaluated at the cube's
far face, must stay below the cube top" from the worst position in the room
(backed against the far wall at `x = 23.75`) gives a minimum side of **5.70 m**.
The standard 8 m cube clears it by 2.13 m from anywhere in the room, including
while backing up.

`TriggeredOccluder.STANDARD_SIZE` is 8 × 8 × 8 in every site, so occlusion
strength is a property of *where* the box is, never of how big it is. The editor
warns if a scene overrides `box_size`.

## Determinism

The box is solid from the **trigger tick**, not from the tick it finishes
rising, and its motion is counted in whole physics ticks rather than seconds. A
live model run idles ~17 s per step waiting on the decider; its replay idles not
at all, so anything paced by elapsed time would put the box in a different place
in the two and `eval/replay.py` would report `COLLISION DIFFERS`. See the
comments on `_deploy()` in `common/props/triggered_occluder.gd`.

This leaves a 0.3 s window where an invisible collider exists. The agent is
4.5 m from the near face when the trigger fires — 0.56 s at full speed, a 1.9×
margin.

## Verified behaviour

Scripted straight-ahead run (`--scripted-indices=3,3,3,3,3,3`), and a fake-model
run flown the same way. Designed vs recorded:

| | Designed | Measured |
|---|---|---|
| Goal at step 0 | 24.0 m, bearing 0° | 24.0 m, bearing 0° |
| Trigger | during step 3 | `occluder_deployed` step 3, tick 46 |
| Last clear frame | step 3 | `line_of_sight: true` steps 1–3 |
| First blocked frame | step 4 | `line_of_sight: false` from step 4 |
| Straight-line collision | step 6, `x = 2.2` | step 6, `x = 2.20` |

`metrics.json`: `occlusion_step: 3`, `goal_visible_steps: 3`,
`goal_first_hidden_step: 4`, `steps_to_reacquire: null`.

Replay reproduces it at `0.00000` m / `0.00000` rad drift on every step, with
collisions, `line_of_sight` and the deploy step all matching.

Screenshots (site overviews + the two decision frames either side of the
occlusion): `notes/screenshots/s01_occluder_dropin_2026-09-18_1321/`.

## Build log

- v1 2026-09-17 — initial greybox. Room geometry copied verbatim from
  `main.tscn` so this site differs from the sandbox by exactly one thing: the
  cube.
- v1 2026-09-18 — verified as above. No geometry change, so no version bump.

## Known issues

- **The prompt still hands the model the goal's exact distance and bearing,
  every step, including after the box is up** (`server/decider/prompt.py`,
  prompt version `p01`). A model that ignores the image and steers by that
  bearing will fly into the cube and keep steering by bearing. So a `p01` run on
  this site measures *how the VLM handles an obstacle while being told the
  bearing*, **not** *whether it replanned from vision*. Do not cite a number
  from this site as visual replanning until `--goal-hint` / prompt `p02` lands
  (notes/PLAN.md §12).
- `goal.line_of_sight` in `steps.jsonl` is an engine raycast — ground truth per
  notes/PLAN.md §8.2, not something the agent senses. `prompt.py` does not read
  it.
- **The cube fills almost the whole frame from step 4 onward.** At `x = 5.2` the
  agent is 3.2 m from the near face of an 8 m cube, which subtends roughly 102°
  against an 87° FOV — so the frame is wall, and the agent gets almost no visual
  cue which way to go around. Moving the cube toward the goal (centre `x = -6`)
  would leave it subtending ~58° with the side gaps visible, make the occlusion
  *stronger* from every position, and push the straight-line collision from step
  6 to step 9. It would also make re-acquiring the goal harder still. Undecided;
  see `05_agent_eye_occluded.png` in the screenshot folder before choosing.
- `status` stays `draft` until a baseline run with a **real** model is recorded
  and logged here (notes/PLAN.md §7). The runs above used the fake backend,
  which does not look at the image.

## Results referencing this site

- `fake_s01` / `fake_s01_replay` — plumbing and determinism only. The fake
  backend picks the straightest action without looking at the image, so these
  say nothing about navigation. Kept as the reference for what a clean replay
  looks like on this site.
- _(no model run yet)_
