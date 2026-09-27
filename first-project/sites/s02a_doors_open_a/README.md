# s02a — Three Doors, A Opens

**Hypothesis:** When the open route closes and a new one opens outside the field
of view, a VLM agent will keep pressing toward the closed route rather than
turning to search for the new opening.

**Class:** geometry · **Status:** draft · **Version:** 2 · **Paired with:**
`s02c_doors_open_c`

## The condition

A wall across the middle of the hall at `x = 0` is pierced by three doorways —
**A** at `z = -9`, **B** at `z = 0`, **C** at `z = +9`, each **2.4 m wide and
3.2 m tall**, ringed by an orange architrave and filled by a door leaf carrying
stiles, panels, hinges and a lever handle at 1.05 m. At spawn only **B** is
open, and it is dead ahead: the agent starts at
`(12, 1.75, 0)` facing −X with the goal 24.0 m away at bearing 0°, and the whole
6 m goal beam is visible through the doorway.

Crossing `x = 6.5` (partway through step 3) fires an `Area3D`. **B slams shut
and A opens**, on the same physics tick.

- First changed frame: **4**
- All three doors are in frame at step 0 — the flanking pair sits at 36.9°
  against a 43.5° half-FOV — so the agent can see that three doors exist before
  anything changes
- A straight-line policy collides during **step 7** (panel B's near face is
  `x = +0.25`, contact at `x = 0.45`)
- The goal is hidden from every point on the spawn side once B is shut, except
  from inside a flanking doorway — so `steps_to_reacquire` measures the agent
  actually working its way to the new opening, not a lucky sidestep

## Why the doors look like doors

The agent has to tell "three doors, one of them open" from a 768 px frame, and
a flat grey slab in a grey wall does not say that. Two things carry it:

- **The leaf** (`common/props/door_leaf.svg`) — an authored greybox door:
  stiles and rails around two recessed panels, three hinges on one edge, a lever
  handle at 1.05 m, a kickplate. It is drawn on two quads either side of the
  panel, not on the box itself: a `BoxMesh` splits its UVs across the faces and
  would slice the artwork. No colour coding and no letters — every door is
  identical, so nothing labels the route.
- **The architrave** (`common/props/door_frame.tres`, Kenney Orange) — a 0.25 m
  band standing 0.1 m proud around **every** opening, including the open one.
  Without it, door B at step 0 is an unmarked hole; with it, the step-0 frame
  shows three doorways, one of which happens to be empty.

Doors are 2.4 × 3.2 m, human proportions, for the same reason: at the original
4 × 5 m a leaf with a handle a fifth of the way up read as a hangar shutter.

## Why the new door is off-frame

Deliberate. At the first post-switch frame (`x ≈ 5.2`) the near edge of opening
A sits `atan2(7.8, 5.2) = 56.3°` off-axis against a **43.5° half-FOV** — none
of it is on screen. The agent has to turn and look. A policy that steers on the
goal bearing alone has no visual cue at all and flies into the closed door,
which is what makes the site diagnostic rather than decorative.

Shortest path after the switch is ≈ 26.5 m ≈ 16 steps; fly with
`--max-steps=40`.

## Why the seal is total

Panels are **0.5 × 3.2 × 2.4 m**, sized to their doorway exactly and set in the
middle of the 1 m wall, so a closed door fills its opening the way a real door
fills a reveal. Everything above `y = 3.45` is solid wall, so there is no
over-the-top sightline to defend against: the worst-case ray from the far wall
at `x = 23.75` to the goal beam's top crosses the wall plane at `y = 5.24`, well
inside the lintel. Earlier versions of this site used a 4 × 5 m opening, where
that ray passed 1 cm under the opening's top edge and the panel had to overhang
the lintel by a metre to stop it.

`TriggeredDoor.STANDARD_PANEL` is that size in every site, so which route is open
is a property of *which door moved*, never of how big the doors are. The editor
warns if a scene overrides `panel_size`.

## The variant pair

`s02a` and `s02c` are identical scenes down to the trigger tick — same room, same
bank, same spawn, same goal. The only difference is one line in `site.tscn`:

```
doors_to_open = Array[NodePath]([NodePath("DoorA")])
```

Running both is what separates "the agent searched and found the new opening"
from "the agent always drifts the same way". Neither arm means much cited alone,
which is why each manifest carries `paired_with`.

## Determinism

Door colliders flip on the **command tick**, not when the panel finishes moving,
in both directions. A live model run idles ~17 s per step waiting on the decider;
its replay idles not at all, so anything paced by elapsed time would put the
panel in a different place in the two and `eval/replay.py` would report
`COLLISION DIFFERS`. Motion itself is counted in whole physics ticks. See the
comments on `_command()` in `common/props/triggered_door.gd`.

This leaves two 0.3 s windows where what is drawn and what is solid disagree:

- **Closing:** an invisible-but-solid panel. The agent is 6.25 m from panel B's
  near face when the trigger fires — 0.78 s at 8 m/s, a **2.6×** margin (s01
  runs 1.9×).
- **Opening:** a visible-but-passable panel. The agent is ~12 m (1.5 s) from the
  flanking door at the trigger and cannot reach it.

Each door's arrival is signalled but not recorded, for the same reason
`occluder_in_place` is not: which step it lands in depends on the previous
model call's latency. `trigger_tick` + `travel_ticks` in the `doors_switched`
event recover it exactly.

## Verified behaviour

Scripted straight-ahead run (`--scripted-indices=3,3,3,3,3,3,3,3`,
`--max-steps=8`, run `probe_s02a`). Designed vs recorded:

| | Designed | Measured |
|---|---|---|
| Goal at step 0 | 24.0 m, bearing 0° | 24.0 m, bearing 0° |
| Switch | during step 3 | `doors_switched` step 3, agent `x = 7.00` |
| Last clear frame | step 3 | `line_of_sight: true` steps 1–3 |
| First blocked frame | step 4 | `line_of_sight: false` from step 4 |
| Straight-line collision | step 7, `x = 0.45` | step 7, `x = 0.45` |
| Bank state after switch | `{A: open, B: closed, C: closed}` | `{A: open, B: closed, C: closed}` |

`metrics.json`: `occlusion_step: 3`, `goal_visible_steps: 3`,
`goal_first_hidden_step: 4`, `steps_to_reacquire: null`.

Replay reproduces the fake-model run at `0.00035` m at two of twelve steps and `0.00000` elsewhere — the two are
where the agent is pressed against the closed door, and contact resolution is
sensitive to sub-tick timing. Inside the 1e-3 m tolerance, but not the exact
zero v1 reported before the leaves filled their openings, with collisions,
`line_of_sight` and the switch step all matching.
(`eval/replay.py` needed a fix to get here: it re-imposed the default collision
budget, so a replay of a run that grinds against a closed door ended early and
exited before the comparison ran. Replays now fly with `--max-collisions=-1`.)

Screenshots (both arms, before and after the switch, plus the two decision
frames either side of it):
`notes/screenshots/s02_three_doors_v2_2026-09-20_1130/`
(v1 shots kept at `notes/screenshots/s02_three_doors_2026-09-18_1436/`).

## Known issues

- **The prompt still hands the model the goal's exact distance and bearing every
  step** (`server/decider/prompt.py`, prompt version `p01`). On this site that
  confound bites harder than on s01: the true bearing points straight at the
  closed door for the entire detour, so a bearing-follower is actively pulled
  into the wall. A `p01` run here measures *how the VLM handles a route change
  while being told the bearing*, **not** *whether it replanned from vision*. Do
  not cite it as the latter until `--goal-hint` / prompt `p02` lands
  (notes/PLAN.md §12).
- `goal.line_of_sight` in `steps.jsonl` is an engine raycast — ground truth per
  notes/PLAN.md §8.2, not something the agent senses. `prompt.py` does not read
  it.
- The doors are deliberately unlabelled: same greybox material as the walls, so
  open vs closed is the only visual difference. A future arm could colour-code
  them, but the Crazyflie counterpart will not have that affordance.
- `status` stays `draft` until a baseline run with a **real** model is recorded
  and logged here (notes/PLAN.md §7). The runs above used the fake backend,
  which does not look at the image.

## Build log

- v1 2026-09-18 — initial greybox. Room geometry copied verbatim from `s01`, so
  this site differs from the occluder site by exactly one thing: the divider wall
  and its doors. Shared room and bank scenes live in `common/three_doors/`.
- v2 2026-09-20 — **geometry change, hence the bump.** Openings 4 × 5 m → 2.4 ×
  3.2 m, panels resized to fill them and recentred in the wall, orange
  architraves added around all three, authored door leaf on both faces. The
  agent could not tell these were doors at v1. Trigger, spawn, goal and the
  switch step are unchanged; the straight-line collision moves from `x = 1.2` to
  `x = 0.45`, still during step 7. Runs citing `@v1` are not comparable.

## Results referencing this site

- `probe_s02a` — scripted straight line, 8 steps. Plumbing and geometry check
  only.
- `fake_s02a` / `fake_s02a_replay` — 12 steps, determinism only. The fake backend picks
  the straightest action without looking at the image, so it says nothing about
  navigation.
- _(no model run yet)_
