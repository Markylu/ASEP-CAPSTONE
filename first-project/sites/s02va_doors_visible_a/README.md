# s02va_doors_visible_a — Three Doors, A Opens In View ("map 2.5")

**Hypothesis:** When the open route closes and a new one opens *inside* the
field of view, a VLM agent will turn toward the visible new opening rather than
keep pressing toward the closed route.

**Class:** geometry · **Status:** draft · **Version:** 1 · **Paired with:**
`s02vc_doors_visible_c` · **Contrast with:** `s02a_doors_open_a` / `s02c_doors_open_c`

## The condition

Same room, same three doors, same switch as s02a/s02c — **B slams shut and A
opens** on one physics tick — with one change: the agent spawns **8 m further
back**, at `(20, 1.75, 0)` facing −X, and the trigger slab moves with it to
`x = 14.5`. The goal is unchanged at `(-12, 1, 0)`, now 32.0 m away at bearing 0°.

Crossing `x = 15` (partway through step 3, same step as s02a/c) fires the
trigger.

- First changed frame: **4**, agent at `x = 13.2`
- **All three doors are in frame at the switch.** Door A's far architrave edge
  (`|z| = 10.45`, `x = 0.6`) sits at `atan2(10.45, 12.6) = 39.7°` against a
  **43.5° half-FOV**, so the whole doorway — frame, reveal and the now-empty
  opening — is on screen. Door A is on the agent's right (−z is right when facing −X).
- Flank doors at spawn sit at 24.2° (vs 36.9° in s02a/c)
- A straight-line policy collides during **step 12** (`x = 0.45`)
- Shortest path after the switch ≈ 17.4 + 15.0 = 32.4 m ≈ 19 steps; fly with
  `--max-steps=50`

## Why this map exists

In s02a/c the new opening is 56.3° off-axis at the first switched frame — the
agent has to *search*. A failure there can't separate "never saw the new door"
from "saw it and didn't replan". Here the new door is in the very frame where B
closes, so the only thing left to test is whether the agent acts on what it
sees. Read the two families together: s02va/vc − s02a/c ≈ the cost of search.

Why spawn moves rather than the trigger: from `x = 12` only the step-0 frame
shows all three doors (the far architrave needs the camera at `x ≥ ~11.6`), so
any switch after the first move is off-frame no matter where the trigger sits.

## How it is built

The room is `common/three_doors/room_far_spawn.tscn`, an *inherited* scene of
`room.tscn` that overrides only the `Spawn` marker — walls, openings, frames and
goal are literally the s02 geometry. The bank is the shared `bank.tscn` with
three overrides in `site.tscn`:

```
trigger_position = Vector3(14.5, 1.75, 0)
doors_to_open = Array[NodePath]([NodePath("DoorA")])
doors_to_close = Array[NodePath]([NodePath("DoorB")])
```

Door leaves, architraves, panel size, seal and determinism notes are all as in
`sites/s02a_doors_open_a/README.md` and are not repeated here. Closing margin is
larger than s02a's: the agent is 14.5 m from panel B's near face at the trigger.

## Verified behaviour

Scripted straight-ahead run (13 × index 3, `--max-steps=13`,
`--max-collisions=-1`, run `probe_s02va`). Designed vs recorded:

| | Designed | Measured |
|---|---|---|
| Goal after step 1 | 30.3 m, bearing 0° | 30.3 m, bearing 0° |
| Switch | during step 3 | `doors_switched` step 3, agent `x = 15.00` |
| Last clear frame | step 3 | `line_of_sight: true` steps 1–3 |
| First blocked frame | step 4 | `line_of_sight: false` from step 4 |
| Straight-line collision | step 12, `x = 0.45` | step 12, `x = 0.45` |
| Bank state after switch | `{A: open, B: closed, C: closed}` | `{A: open, B: closed, C: closed}` |

`metrics.json`: `occlusion_step: 3`, `goal_visible_steps: 3`,
`goal_first_hidden_step: 4`, `steps_to_reacquire: null`. `run.json` records
`site_id: s02va_doors_visible_a`, `site_version: 1`.

`fake_s02va` replays at `0.00000` m on every step with `events match:
doors_switched@3`.

In-view check: `tools/site_shots.gd --switched` (now shooting the agent's
768², 87° KEEP_WIDTH frame, poses taken from the spawn marker) —
`agent_eye_after_switch.png` at `x = 13.2` shows all three framed doorways with
A open.

## Known issues

- Spawn distance differs from s02a/c (32 m vs 24 m to goal, doors smaller in
  frame). That is the price of keeping the room identical; cite the contrast
  with it stated.
- `goal.line_of_sight` is an engine raycast, not something the agent senses.
- `status` stays `draft` until a deliberate baseline run with a real model is
  logged here (notes/PLAN.md §7).

## Build log

- v1 2026-09-27 — built from s02a/c: inherited room with spawn at `x = 20`,
  trigger at `x = 14.5`. No geometry change to the shared room or bank.

## Results referencing this site

- `probe_s02va` — scripted straight line, 13 steps. Plumbing and geometry
  check.
- `fake_s02va` / `fake_s02va_replay` — **mislabelled: not a fake-backend run.**
  The decider on port 8011 at the time was the `remote` profile, so this was
  flown by `Qwen3-VL-30B-A3B`, prompt `p02`, default collision budget. It went straight through the switch, jinked once (step 5–6), then flew into closed door B at step 12 and ended on `collision_budget` at step 15 — never turned toward the visible open door A.
  Unplanned run, not a baseline — useful as a first look only.
