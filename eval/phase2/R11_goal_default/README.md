# R11: Goal by default, detours on demand (bundle round)

**Agent:** `a15` (not yet built) · **Navigator prompt:** `p14` (as `a14`) · **Perceiver:** `g03`
(as `a14`) · **Strategist:** `q03` (new, detour only) · **Spatial memory:** new `SpatialConfig`
for `a15`; `a13`/`a14` keep theirs · **Status:** **draft design, not built, not probed, not flown**

Draft written 2026-10-25 from [evidence.md](evidence.md), before any R11 code. Nothing here is
pre-registered until the operator confirms the design; the shas are filled in when `a15` exists
and are re-checked against `config.lock.json` before the round flies. R11 flies beside a control,
**R11C** (`a14` unchanged), on the same host at the same SHA.

## Goal truth (operator, 2026-10-26)

**Planner-side code may use the goal's true position; no navigator or perceiver text may carry
it.** R10 gave it to the strategist's prompt only. The route planner and the progress monitor
below read it in code (marked "truth"), and `q03`'s targets are worded with how much nearer the
goal they lie. The navigator still gets the goal only as "toward your target", with no distance
or direction, and the perceiver gets the clean frame alone (evidence §3, O2 and O7).

## Change

**A bundle on `a14`.** Credited to the bundle, not to any part.

| Part | `a14` (R10) | `a15` |
|---|---|---|
| Who sets the target | `q02` on nine triggers (30% of steps) | **route planner** (code, truth): the goal is the standing target unless the move toward it carries a wall, blocked or stopped-short note, or a move toward it was blocked in the last 3 steps; then **`q03`** chooses a detour |
| Progress monitor | none (critic off) | code, truth: no gain in goal distance over 6 steps → ask `q03` |
| Strategist text | goal visibility line; "within 2 m of this spot" line; targets in distance and direction | **`q03`**: asked only for a detour; both lines dropped; each target also worded with how much nearer the goal it lies ("about 4 m nearer the goal than you") |
| Doorways | enter the menu and the trigger on one sighting; struck when passed or seen closed | **doorway gate**: enter on the second sighting; leave after 10 steps without one |
| Block memory | stored at the move's start pose; matched within 0.85 m and 15° | also stored where the move ended; matched on the landing cell; the adjacent fan actions get the note too |
| "toward your target" | on the action nearest the target's bearing, walls or not | **wall-aware**: never on an action with a wall, blocked or stopped-short note; the next open action within ~55° instead, or none |
| Navigator | `p14` | `p14` unchanged; it sees only the notes change |
| Turn rule | [0] not offered after a turn-around while a move ahead is open | unchanged (kept so R11 does not confound it; the unhidden variant is a later ablation) |
| Critic | off | off |

Code structure (evidence §4) is built with `a15`: stages, role views with an allowlist,
`SpatialConfig`, `TargetPolicy`, ordered note rules. It ships only if every R9, R10 and R10C
decision re-renders byte for byte and `a13`/`a14` keep their shas.

## Evidence

[evidence.md](evidence.md), from `python eval/spatial_replay.py audit` on R10, R10C and R9:
- **The strategist leaves the goal it was told about.** It chose the goal on 70 of 229 calls; 157
  of the other 159 reasons cite a wall, a block or the goal not being visible. Standing on the goal
  or a doorway gains about 0.9 m a step toward the goal; unexplored ground +0.14, backtrack −0.34,
  explore −0.42. 352 of 755 steps (47%) stood on those three.
- **It is asked by doorways.** "A new doorway is in view" is 81 of 229 calls (35%); 162 target
  changes in 755 steps; doorway entries 4 steps old at the median, up to 54.
- **The collision after a collision is never warned about.** 36 of 37 near-repeat collisions in
  R9, R10C and R10 carried no blocked or stopped-short note (block stored at the start pose,
  0.85 m / 15° match).
- **"toward your target" sat on a walled action 36 times** in R10; picked 12, stopped short 4.
- **What the memory does well stays:** blocked and stopped-short notes are never picked (0 of 23),
  "been there" lift 0.51, loop-score steps 16 (R10C 108).

## Hypothesis

With the goal as the standing target unless the way toward it is shut, detours chosen only then,
and notes that warn about the next collision and never point "toward" a wall, the agent spends
more of its steps closing on the goal, and `final` + `dynamic` rises above R11C.

## Predictions (draft)

| Measure | R10 | Prediction |
|---|---|---|
| `initial` | 5/6 | ≥ 5/6 |
| `final` + `dynamic` | 6/12 | above R11C |
| cells changed against R11C | | more than the floor (below), more gained than lost |
| steps with the goal as standing target | 232/755 (31%) | ≥ 50% |
| steps standing on unexplored ground, backtrack or none | 352 (47%) | ≤ 25% |
| strategist calls | 229 (30% of steps) | ≤ 15% of steps |
| "toward your target" on an action with a wall, blocked or stopped-short note | 36 | 0 |
| near-repeat collisions with no blocked or stopped-short note | 9 of 9 | ≤ 2 |
| collisions | 36 | at most R11C's |
| `spin_failure` runs | 0 | 0 |

## Attribution rule

As R10, with a floor measured for `a14` itself (R10 summary, "For the next round" 1). R11 is read
against R11C. A success change is credited to the bundle only if R11 changes **more than F of 18**
outcomes against R11C **and** gains more cells than it loses, where F = max(6, the number of
outcomes R11C changes against R10). R11C against R10 is reported as `a14`'s run-to-run floor.

## Control

**R11C flies `a14`** (`63ad006476b6`), R10's agent, unchanged, on the R11 host at R11's SHA, right
after R11. [R11C README](../R11C_a14_control/README.md).

## Manipulation check

From `python eval/spatial_replay.py manip` and `audit` on R11 and R11C:
- standing-target kinds per step; strategist calls by trigger; target changes;
- route planner hand-overs to `q03`, each with its reason (walled, blocked, no progress);
- "toward your target" on an action with a not-open note (must be 0);
- near-repeat collisions with and without a note;
- doorway entries: sightings before entering the menu, age at the median and max;
- the role-view leak scan: no navigator or perceiver text carries the goal's distance or direction;
  no `q03` text carries "the goal is not in the current image" or "within 2 m of this spot";
- `hidden` on every step where the turn rule applies, never otherwise; collisions, revisit rate,
  mean step latency.

## Drop criterion

`a15` is dropped if two or more hold (as R10):
- `final` + `dynamic` below 3/12;
- `initial` below 4/6;
- any run invalid on the wall clock (900 s);
- `spin_failure` on 2 or more runs.

## Probe gate (draft)

`eval/r11_probe.py` (to be written), on R10's recorded runs, before flying. R11 does not fly if any
line fails.

| Check | Set | Threshold |
|---|---|---|
| block memory warns about near-repeat collisions | R9, R10C, R10's 37 near-repeat collisions, rebuilt with `a15`'s memory (code only) | note on ≥ 30 |
| route planner keeps the goal | R10's 755 steps, `a15`'s planner on R10's records (code only) | goal standing on ≥ 50% |
| navigator with the wall-aware note | R10's steps where "toward" shared an action with a not-open note and some forward move was open, re-tagged as `a15` tags them, R10's annotated frame, `p14`, live model (frames on sctsvr6) | pick carries no not-open note on ≥ 80% |
| `q03` detours | R10's strategist calls where `a15` would hand over, rebuilt as `a15` words them, live model, text only | target ≥ 3 m nearer the goal on ≥ 60%; explore ≤ 10% |

The strategist and navigator sets keep R10's history, so they test how `a15`'s parts choose in
R10's situations, not how an `a15` run unfolds (as R10's probe).

## Shakedown

One unscored `dynamic` run per site on the flight host: every record carries the perceiver, the
map snapshot, the notes, the route planner's state and, where it applies, `hidden` and `q03`'s
call; `/health` reports `a15`'s sha; no run passes 700 s.

## Host

sctsvr6 headless (Docker, Mesa lavapipe), as R7–R10, with R11C there too. The tunnel is the
operator's.

## Builds on

R10 (`a14`: goal known to the planner, turn rule, no critic); R9 (`a13`: perceiver, map, notes,
strategist, navigator); R10C (re-fly noise of a multi-call agent); R2 (a model's own history makes
it repeat itself).

## Outcome

Not flown.
