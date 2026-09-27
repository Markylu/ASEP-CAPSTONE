# s03 — Fork, Dead End

**Hypothesis:** After the corridor it committed to becomes a dead end, a VLM
agent will keep pressing against the closed exit rather than backing out and
taking the remaining branch.

**Class:** geometry · **Status:** draft · **Version:** 2

## The condition

Same room as s01 and s02 — the outer shell is copied node for node from
`common/three_doors/room.tscn` minus its divider — and the same goal
`(-12, 1, 0)`. The spawn moves back to `(21, 1.75, 0)` facing −X, 33.0 m from
the goal at bearing 0°, in an open lobby in front of the fork.

The walkable space is a **tuning fork** lying along −X, all walls 12 m tall:

```
   goal chamber            x = -7 … -24
 ══[DoorL]══════[DoorR]══  exit wall, x ∈ [-7, -6]
   ║ L  ║ divider ║ R  ║   tines,    x ∈ [-6, 5]
   ║    ║         ║    ║
   ╚════╩═╗     ╔═╩════╝   crossbar, x ∈ [5, 8], z ∈ [-6.5, 6.5]
          ║stem ║          stem,     x ∈ [8, 15], z ∈ [-1.5, 1.5]
 ═════════╝     ╚═══════
                           lobby,    x ∈ [15, 23.75], full room width
             ▲             spawn at x = 21
```

- **Lobby** — open, 8.75 × 23.5 m. The agent starts here facing the stem mouth
  in the middle of a flat wall.
- **Stem** (the handle) — 3 m wide, 7 m long. Looking down it, the agent sees
  only the divider face at the far end: a blank T-junction.
- **Crossbar** — 3 m deep, runs `z ∈ [-6.5, 6.5]`. The agent must turn left or
  right here before either tine exists in frame.
- **L** — `z ∈ [3.5, 6.5]`, the agent's **left** at spawn (+Z)
- **R** — `z ∈ [-6.5, -3.5]`, the agent's **right** at spawn (−Z)

Each tine ends in a 2.4 × 3.2 m doorway in an exit wall at `x ∈ [-7, -6]`,
ringed by the same orange architrave as s02 and fitted with the same door leaf.
**Both doors start open.** The goal chamber beyond is `x ∈ [-24, -7]`.

Halfway down each corridor (`x = 0`) is a trigger. **Whichever one the agent
crosses first slams that corridor's exit door shut** and disarms the other, so
the corridor the agent committed to becomes a dead end and the other one is the
only way through. The fork adapts to the agent's choice, so there is no variant
pair: every run tests "back out and switch branches".

- **Neither tine is visible at step 0** (v1 showed both mouths at ±30.3°). The
  stem walls cut every sightline from spawn into `|z| > 3.5`; the choice is
  made at the crossbar, blind, and each tine is only seen after turning into it
- The divider hides the goal from the stem and crossbar; `line_of_sight` is
  false at spawn
- Trigger to closed-door near face is 6.25 m, so the straight-line policy
  collides 4 steps after the switch

## Why the trigger is mid-corridor

At the mouth, "closing the door ahead" would be a choice the agent can undo in
one step. Five metres in, it has committed: backing out means ~4 steps back to
the crossbar, ~5 across it and ~7 down the other tine, which is what makes
`steps_to_reacquire` measure a real decision and not a wobble.

## The latch

The only code this site added is `latch_group` on `TriggeredDoorBank`
(`common/props/triggered_door_bank.gd`). Banks sharing a non-empty group are
mutually exclusive: the first to fire disarms every other bank in the group
on the same tick, and its `doors_switched` event carries `latch_group` and
`disarmed`. `BranchL` and `BranchR` share `s03_fork`. An empty group is the
old behaviour, so s02 is unchanged (regression-checked below).

The event keeps the name `doors_switched`, so the recorder's
`OCCLUSION_EVENTS` dates `occlusion_step` from it with no recorder change. The
`bank` field (`…/Props/BranchL` or `…/BranchR`) records which branch the agent
took.

## Determinism

Inherited from `TriggeredDoor`: the collider flips on the command tick, and
motion is counted in physics ticks. The agent is 6.25 m from the closing
door's near face when the trigger fires — 0.78 s at 8 m/s, the same **2.6×**
margin as s02.

## Verified behaviour

Scripted probes, designed vs recorded (v2; `L` = `3×8,1,1,5,5,3×6`):

| | Designed | Measured |
|---|---|---|
| Spawn view | stem + blank divider face, no tine in frame | confirmed by a camera render at `(21, 1.75, 0)` |
| Lobby + stem (`3×8`) | reach the T-junction | enters stem step 4, step 8 at `x = 7.40` in the crossbar |
| Left branch (`L`) | `BranchL` fires mid-tine | `doors_switched` step 14 at `x = -0.61` |
| Straight on after switch | collide at door | step 18, `x = -6.05` |
| Right branch (`L` with 1↔5 swapped) | `BranchR` fires | step 14; collide step 18, `x = -6.05` |
| Recovery (`L,0,3×6,1,1,3×3,1,1,3×7,1,2,3,2`, 43 steps) | turn round, crossbar, other tine, goal | R trigger crossed with **no second event**, through `DoorR` step 38, `goal_reached` step 43 |

Determinism: the recovery sequence flown twice gives identical positions,
yaw and collisions on all 43 steps.

v1 numbers (spawn at `x = 12`, switch step 8, collide step 12,
`steps_to_reacquire: 32`) are for the v1 geometry only and are not comparable.

## Known issues

- **The prompt still hands the model the goal's exact distance and bearing every
  step** (`server/decider/prompt.py`, prompt `p01`). Here the bearing points
  straight at the divider from the stem and at the closed door from inside the
  dead end, so a bearing-follower is pulled into walls. A `p01` run measures
  *how the VLM handles a dead end while being told the bearing*, **not**
  *whether it replanned from vision* (notes/PLAN.md §12).
- The goal is never visible before the switch: the doorway is off the
  corridor-centre → goal line, so no frame shows the beam through the open door.
  The dead end reads from the door slamming ahead, not from the goal
  disappearing. If an arm needs "goal seen, then lost", move the goal off
  `z = 0` toward one doorway, as a new version.
- Corridors are in shadow from the directional key and read as dark slits at
  spawn. Legible in the step-0 frame, but check the in-corridor frames with
  `tools/site_shots` before a real-model baseline.
- `status` stays `draft` until a baseline run with a **real** model is recorded
  (notes/PLAN.md §7).

## Build log

- v1 2026-09-24 — initial greybox. Outer shell copied from s01/s02; fork block,
  exit wall, two door banks sharing latch group `s03_fork`. Takes the `s03` ID
  previously reserved for the `main.tscn` migration, which moves to
  `s04_corridor_straight`.
- v2 2026-09-27 — **tuning-fork layout**. v1 let the agent see both corridor
  mouths from spawn, so the branch choice was made with both options in view.
  Now the agent spawns at `x = 21` in an open lobby, walks into a 7 m stem
  that runs into a T crossbar,
  and the two tines turn off it out of sight. Tines moved from `z = ±3.5` to
  `z = ±5` (doorways, doors, triggers with them); island + fill blocks replaced
  by stem fills, outer fills and a divider. Door, trigger and latch logic
  unchanged. Probes re-flown above; v1 probe/fake runs no longer match.

## Results referencing this site

- `probe_s03_L`, `probe_s03_R`, `probe_s03_recover`, `probe_s03_recover_b` —
  scripted, geometry/latch/determinism only. **v1 geometry.**
- `fake_s03` / `fake_s03_replay` — plumbing and replay only. **v1 geometry;
  will not replay against v2.**
- _(no model run yet)_

---

## Build checklist (notes/PLAN.md §7)

- [x] Hypothesis written **before** any geometry exists
- [x] Folder copied from `sites/_template/`
- [x] `site.json` filled; `id` and `scene` updated
- [x] Scene built to the notes/PLAN.md §5.2 skeleton, greybox only
- [x] Real-world scale verified (same shell as s01/s02; 2.4 × 3.2 m doors)
- [x] `Spawn` placed and oriented
- [x] Goal placed; line of sight from spawn checked deliberately (hidden)
- [ ] Manual walkthrough in the editor — no leaks, no z-fighting
- [x] Headless run clean end to end
- [x] Replay determinism verified
- [ ] Baseline run recorded and logged above
- [ ] `status: active`, version bumped, committed
