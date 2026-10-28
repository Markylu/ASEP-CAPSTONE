# R12: Staged search with a coverage map, no goal truth (bundle round)

**Agent:** `a19` (`0da467a5c3ca`; `a17` `3001a0c0a0fb` and `a18` `39e2bad86238` failed line 7) ·
**Navigator prompt:** `p14` (`31a9f28eaf94`, as `a13`–`a16`) ·
**Perceiver:** `g05` (`133ed83db46b`, new; floor map in "Line 7, perceiver changes") · **Strategist:** `q04` (`f8fdf4b5946c`, new) ·
**Spatial memory:** `spatial.A17` (`spatial` `eceb875a68a3`, `spatial_a14` `0075a8a0e5c0`,
`spatial_a17` `63ccdaa218d9`) · **Stage machine:** `planner_a17` `6eb22517c3e0` ·
**Status:** flown 2026-10-28, complete: 5/18 (Outcome). Offline probe passed; line 7 failed for
`a17` (`g04`) and `a18`, passed for `a19` on R11C's held-out frames; shakedown 6/6 valid. Below, `a17` names the bundle's code, which `a19` runs unchanged with `g05`.

Draft written 2026-10-28 from R11's [failure analysis](../R11_goal_default/failure_analysis.md)
and the operator's direction the same day. The shas are re-checked against `config.lock.json`
before the round flies. Spec: `docs/phase2-test-plan.md`.

## R12C dropped (operator, 2026-10-28, before flying)

The operator's aim is the best-performing agent; hiding the goal's position is one of its tools,
not a variable under test. So R12 is read against the best round so far, **R11** (`a16`, 11/18),
not against an `a13` control, and **R12C is not flown**. Where the predictions below say R12C,
they are read against R10C (`a13`'s last flight, 7/18). The attribution rule changes with it
(below). R12 flies on 4 parallel lanes (own checkout, decider, Godot cache and X display each),
one SHA.

## Goal truth dropped (operator, 2026-10-28)

**No part of `a17` sees the goal's true position.** This reverses the 2026-10-26 decision
(planner-side code may read it), which R10 and R11 flew under.

- `orchestrator.decide` removes the manifest's `goal` block before any stage runs
  (`goal_truth: none`).
- The decision record still carries the full manifest, for evaluation only.
- The planner works from the agent's own sightings: the perceiver's goal strip on the clean frame.

The search is therefore a real search, and R12 is not comparable with R10 or R11 on outcomes. Its
control is the last agent that flew without goal truth, `a13` (Control below).

## Change

**A bundle on `a13`'s pipeline**, credited to the bundle, not to any part. It carries R11's
lessons, which `a14`–`a16` were built on.

| Part | `a13` (R9, R10C) | `a17` |
|---|---|---|
| **Who sets the target** | `q01` on nine triggers | **Stage machine** (code, `planner.staged`). In **explore** (the start), the target is a search target chosen by `q04`. In **goal**, entered on one goal sighting, the target is where the goal was seen (`goal_belief`; one sighting gives a bearing, steered 10 m along it). Back to explore when a look disproves the sighting (below). In goal, a walled or blocked way asks `q04` for a detour (a16's rule, on the belief instead of the truth). |
| **Coverage map** | free floor, 6 m rays down each strip's centre | **Each look's cone is searched.** 3 rays per strip, out to where the floor ends, cut at a stop wall. Ground under the cone with no goal reported in that strip is *searched*: it is never a target, but it can still be flown through. Floor that ends at a wall or a closed door writes a wall. |
| **Evaluator** | critic: one retry on a blocked, spin or loop pick | **Code, per step, recorded as `evaluator`**: `new_seen` (cells newly searched), `view_revisit` (share of the cone already searched, "seen this view before"), `target_gain_m`, `stopped_short`, `goal_sighted`. 4 unproductive steps in a row (`new_seen` < 3 and gain < 0.5 m) blacklist the target. If no unsearched ground is reachable ("exhausted"), only doorways and a way back are offered. No navigator retry, and no critic. |
| **Sighting check** | none | A belief is disproved when a look's cone covers it, or when a look faces it down an open strip with no known wall on the line, and no goal is reported in either case. One such look is enough: the rays are dropped and the stage is explore. |
| **Search targets** | frontier centres, largest first | **Reachable only.** Edges of unsearched ground that a path over known floor reaches, keeping one cell from walls. Each is offered one cell short on its path, ranked by edge cells ÷ (path + 2 m). Doorways are listed only if a path reaches them. |
| **Walls** | a visit or a newer look erases a wall | A move under 1.5 m writes a **stop wall** one cell ahead of where it stopped. No look erases it. |
| **Doorways** | passed within 1.5 m | passed only when a move runs through them (within 0.6 m); closed when `g04` says closed; a15's gate (second sighting, 10-step lifetime) kept |
| **Perceiver** | `g03` | **`g04`**: `open_far` splits into `wall_far` (a wall or door ends the floor at about 4–8 m) and `open_very_far` (no wall within about 8 m); doorway open, closed or none; "a surface with no floor line across it is blocked_near" |
| **Strategist** | `q01` | **`q04`**: places worded by unsearched ground and path length over known floor, never by nearness to the goal; "every place listed can be reached"; backtrack for dead ends |
| **Notes** | a13's | a16's wall-aware "toward", plus three changes. When nothing in the fan is within 55°, "toward" goes on the sharpest open move on the target's side. [0] is never hidden while it carries "toward". A move facing only searched ground reads "searched already this way" instead of "new ground". |
| Navigator | `p14` | `p14` unchanged; it sees only the notes and the plan line change |
| Turn rule | none | `a14`'s (no turn-around right after one while a move ahead is open), except as above |

Ranges, by floor class:

| Floor class | Reach | Note |
|---|---|---|
| `blocked_near` | 0.5 m | g03's 1.0 m: wall within 1 m on 378 of 606 R11 lane reads |
| `open_near` | 2.0 m | |
| `open_far` (g03, replay only) | 4.0 m | was 6 m |
| `wall_far` | 6.0 m | |
| `open_very_far` | 10.0 m | |

`eval/r12_probe.py` gives the R11-geometry counts behind each.

## Evidence

From R11's [failure analysis](../R11_goal_default/failure_analysis.md) and
[analysis/d_detect.py](analysis/d_detect.py) ([probe/d_detect.txt](probe/d_detect.txt)).

- **R11 lost to its map, not its model.**
  - 34 of 37 detour targets lay behind or inside a wall, and only 1 of 33 detours was reached.
  - 37 of 58 collisions came on those detours.
  - With a perfect perceiver, the top goal-side frontier would still be unreachable in 37 of 38
    calls.
  - The causes: collisions never wrote walls, newer looks erased walls, open floor ran a fixed 6 m,
    and no target was checked for a path.
- **g03 sees the goal whenever it is in line of sight, at any range.** Over R9–R11 it reported the
  goal 612 of 612 times in view, in every distance band out past 30 m. It reported a goal out of
  view on 123 of 3290 frames (3.7%). So a look that faces the goal with nothing in the way shows
  it: ground a look covers without the goal is empty, and only walls end the cone.
- **Its range class says nothing.** "near" covered 40 of 40 sightings at 30+ m, so a single
  sighting is a bearing.
- **False sightings drove R11's failures.** 10 of R11's 14 goal-in-view hand-backs were
  hallucinated, 7 of them in failed runs.
- **The navigator ignored a target behind it.** "toward" sat on [0], hidden or ignored, on 185
  steps, which flew +158 m away from the goal.
- **Doorways were struck as passed without being crossed.** The true door was listed at only 4 of
  the 14 calls where it was in memory.
- **A critic that only asks again does not change picks.** R9's critic changed 0 of 19.

## Hypothesis

With the goal unknown, an agent that searches only ground it has not yet looked over, goes only
where a known path leads, and drops sightings a later look disproves, finds and reaches the goal
more often than `a13`, which searches with the same model, perceiver map and navigator but no
coverage, stages or reachability. `final` + `dynamic` rises above R12C.

## Predictions

| Measure | R10C (`a13`) | Prediction (R12 against R12C) |
|---|---|---|
| `initial` | 5/6 | ≥ 5/6 |
| `final` + `dynamic` | 2/12 | above R12C |
| cells changed against R12C | | more than the floor (below), more gained than lost |
| collisions | 57 | below R12C |
| top search target inside a wall or not truly reachable (geometry, evaluation only) | | ≤ 10% of `q04` calls |
| steps whose look was ≥ 90% already searched (`view_revisit`) | | below R12C's, with R12C's records replayed through `a17`'s memory |
| `q04` calls | | ≤ 15% of steps (smoke on R11's manifests: 9%) |
| false sightings disproved within 3 steps, of those a later look faced (truth, evaluation only) | | ≥ 80% |
| "toward your target" on an action with a not-open note | | 0 |
| `spin_failure` runs | | 0 |

## Attribution rule

R12 is read against R11, the best round so far (R12C dropped, above).

- R12 is credited as better than R11 only if it changes **more than F of 18** outcomes against R11
  **and** gains more cells than it loses.
- F = 6: max(6, re-fly noise), with re-fly noise 2 of 18 (R11C against R10, `a14`) and 3 of 18
  (R10C against R9, `a13`).
- R12 against R10C (`a13`, the last agent without the goal's position) is reported too.

## Control

None flown (R12C dropped, above). Planned as `a13` (`3de550e110e7`) on the R12 host;
[R12C README](../R12C_a13_control/README.md).

- `a13` is the last agent with no goal truth. R10C flew it at 7/18: `initial` 5/6, `final` 1/6,
  `dynamic` 1/6.
- `a14` and `a16` read the goal's true position in code, so they are not a fair control.
- R11 (`a16`, 11/18) is reported beside R12 as the truth-informed reference. It does not enter the
  attribution rule.

## Manipulation check

From the decision records and `eval/r12_probe.py`, on R12 and R12C. Truth is used only to score.

- **Stages:** stage per step; entries to goal; returns to explore by kind (disproved, reached
  empty).
- **Evaluator:** `new_seen` and `view_revisit` distributions; blacklist events; exhausted menus.
- **`q04` calls:** count by trigger, and the picks by kind (frontier, doorway, backtrack, explore).
- **Sightings:** genuine and false, scored against line of sight and bearing, and how many of each
  were disproved.
- **Search targets:** the top target inside a wall or not reachable on the site geometry.
- **Coverage:** share of searched cells truly in line of sight (on `g04`'s reads); runs with goal
  ground searched before the goal was first reported.
- **No truth:** every record carries `stage` and `evaluator`; the `smoke` line repeated on R12's
  records (decisions with and without the goal block identical).
- **Notes and the turn rule:**
  - "toward" on a not-open action must be 0;
  - `hidden` must never fall on a turn-around tagged "toward".
- **Also:** collisions, revisit rate and mean step latency.

## Drop criterion

`a17` is dropped if two or more hold (as R11):
- `final` + `dynamic` below 3/12;
- `initial` below 4/6;
- any run invalid on the wall clock (900 s);
- `spin_failure` on 2 or more runs.

## Probe gate

`eval/r12_probe.py`. R12 does not fly if any line fails.
- **Offline lines** run on recorded runs (R10, R11C, R11) through `a17`'s code, with g03's recorded
  reports. They are scored against R11's 2D site model, `analysis/geo.py`, where s03's exit doors
  are taken as open.
- **Line 7** needs the model.

| # | Check | Set | Threshold | Result (2026-10-28) |
|---|---|---|---|---|
| 1 | Old agents unchanged | `spatial_replay.py rerender` on R10, R11C, R11; shas of `a13`, `a14`, `a16` | diffs as before the change, 0 in words; shas as locked | 7 / 6 / 0, the same as HEAD (strategist replay), 0 in words; `3de550e110e7`, `63ad006476b6`, `6d614e3c4450`, **pass** |
| 3 | No false "empty" | R10, R11C, R11, `a17` memory | goal ground searched before the goal was first reported in ≤ 2 runs per round | 0 / 0 / 0, **pass** |
| 4 | Reachable targets | R11's 38 `q03` situations | top search target inside a wall or not truly reachable ≤ 5 of 38 | 3 of 38 (R11's frontier 37 of 38), **pass** |
| 5 | Sightings checked | stage machine open-loop on R11 and R11C, `q04` stubbed | false sightings that a later look faced: ≥ 80% disproved; genuine sightings disproved with the goal in line of sight ≤ 5% | 39 of 46 (85%); 12 of 285 (4.2%), **pass** |
| 6 | No goal truth | `a17`'s real step (`smoke`) over R11's 706 manifests, stub replies, with and without the goal block | 0 decisions differ, 0 failed steps | 0, 0, **pass** |
| 7 | `g04` reads (live, sctsvr6) | R11 frames scored against geometry | searched cells in line of sight ≥ 90%; `blocked_near` read as open < 15% | 64.1%; 53.2% (g03 on the same steps: 82.6%; 32.7%), **FAIL**: g04 reads 69% of strips `open_very_far` and uses `open_near` on 1%. `a18`/`g05` (floor end placed in the image): 86.8%; 16.2%, **FAIL** (a perceiver with true distances: 94.6%; 0%). `a19` on R11C (held out): **93.1%; 7.3%, pass** |

[probe/offline.txt](probe/offline.txt), [probe/smoke.txt](probe/smoke.txt).

### Changed while building, before pre-registration (2026-10-28)

- **Line 3 is split.** On g03 the in-sight share is 87%, 88% and 83% (R10, R11C, R11), because
  g03 reads walls within 1 m as `open_far` a third of the time. `g04` is built to fix that, so the
  ≥ 90% line is gated live on `g04` (line 7). The false-"empty" count stays offline.
- **Line 5 is scored as follows.**
  - A sighting is genuine with line of sight and the goal ≤ 60° off-axis (its glow reaches past the
    frame's 43.5°).
  - The false-sighting share counts only the sightings a later look faced within 3 steps. The
    replay follows R11's recorded path, so it cannot turn the drone toward `a17`'s belief.
  - A genuine sighting counts as lost only while the goal is still in line of sight. 25 more were
    dropped after the goal went out of sight, mostly door B closing at step 4 in `dynamic`, which
    g03 reads as open floor.
- **The disproof rule gained "faces it down an open strip".** With the cone alone, 3 of 52 false
  sightings were disproved: a single sighting's point lies 10 m out, past g03's 4 m cone.
  `miss_looks` = 1, with this trade-off:

  | `miss_looks` | False sightings disproved | Genuine lost in sight |
  |---|---|---|
  | 1 | 39 of 46 | 12 of 285 |
  | 2 | 28 of 46 | 9 of 285 |

- **g03 reaches shortened** against R11's geometry (Change above).
- **Search targets are offered one cell short on their path.** At the edge cell itself, 10 of 38
  lay inside a wall slab.

### Line 7, perceiver changes (2026-10-28, live on sctsvr6)

Line 7 on R11's 706 frames, scored by `eval/r12_probe.py score-g04` against `geo.py`:

| Perceiver | Agent | In line of sight | Walls < 1 m read open | Cells searched |
|---|---|---|---|---|
| g03 (recorded) | | 82.6% | 32.7% | 12748 |
| g04 (metres, far split) | `a17` `3001a0c0a0fb` | 64.1% | 53.2% | 57209 |
| g05 (floor end in the image) | `a18` `39e2bad86238` | 86.8% | 16.2% | 9052 |
| g05, map one class nearer | `a19` `0da467a5c3ca` | 90.0% | 6.8% | 5765 |
| true distances (ceiling) | | 94.6% | 0% | 12345 |
| **g05, `a19`, R11C's 721 frames (held out, the gate)** | `a19` | **93.1%** | **7.3%** | 7950 |

`a19` passes line 7 on R11C ([probe/live_a19_r11c.txt](probe/live_a19_r11c.txt)).

- `g05` (`133ed83db46b`): the camera is level at 1.75 m with an 87° view, so no floor at a strip's
  bottom means an obstacle under 1.84 m, and a floor line at fraction v of the half-height below
  the centre lies 1.84 / v m away. `g05` asks `no_floor` / `bottom` / `lower` / `middle`; the
  agent's `floor_map` turns that into a floor class.
- `a19`'s map (`no_floor`, `bottom` → `blocked_near`; `lower` → `open_near`; `middle` →
  `open_far`) was chosen on R11's answers, so its R11 row does not count. **Pre-registered
  before it is run: line 7 for `a19` is scored on R11C's 18 runs (frames not used to choose the
  map), thresholds unchanged (≥ 90%; < 15%).** R12 flies `a19` only if that passes, then the
  shakedown.
- Known cost: `bottom` read on long views (653 of R11's strips over 8 m) now writes a wall
  0.75 m out until a later look clears it, so search covers less per look. The shakedown watches
  for `exhausted` menus.

```
python3 eval/phase2/R12_staged_search/analysis/d_detect.py
python3 eval/r12_probe.py offline
python3 eval/r12_probe.py smoke eval/phase2/R11_goal_default/runs
```

## Shakedown

One unscored `dynamic` run per site on the flight host:
- every record carries `perceiver` (g04 classes), `stage`, `evaluator`, `tags` and, where it
  applies, `hidden` and `q04`'s call;
- the decision manifest's goal block reaches no stage (the `smoke` check on the shakedown records);
- `/health` reports `a17`'s sha;
- no run passes 700 s.

## Host

sctsvr6 headless (Docker, Mesa lavapipe), as R7–R11, on 4 parallel lanes. The tunnel is the
operator's.

## Builds on

- R11: map fixes from its failure analysis, wall-aware "toward", the role-view leak check.
- R10: the turn rule.
- R9: perceiver, map, notes, strategist, navigator; the critic that changed no picks.
- R10C: re-fly noise of a multi-call agent.
- R2: a model's own history makes it repeat itself.

## Outcome

Flown 2026-10-28 on sctsvr6 at `09d11a0`, 4 parallel lanes merged into one round. 18/18 valid.
Ended by the operator without labels or a summary.

| Arm | R10C (`a13`) | R11 (`a16`) | R12 (`a19`) |
|---|---|---|---|
| `initial` | 5/6 | 6/6 | 5/6 |
| `final` | 1/6 | 4/6 | 0/6 |
| `dynamic` | 1/6 | 1/6 | 0/6 |
| total | 7/18 | 11/18 | **5/18** |

- **Against R11:** 6 outcomes lost (s03 `initial`, four `final`, s01 `dynamic`), none gained.
  Not better than R11.
- **Drop criterion:** `final` + `dynamic` 0/12 holds; `initial` 5/6 and the wall clock do not;
  `spin_failure` was not labelled. `a19` is not carried forward either way.
- **Why, from the records (evaluation uses geometry):**
  - In `final` the goal was never reported in 5 of 6 runs.
  - The drone flew 60–80 m a run but stayed within 6–18 m of its start (R11: 13–32 m), with
    12–35 turn-arounds a run (R11: 1–17).
  - `g05` under `a19`'s map read 39–67% of strips blocked (R11's `g03`: 8–36%). Walls written
    0.75 m out in most directions kept search targets near the start and put "wall close" on most
    moves. Line 7 checked that searched ground was in sight, not that the drone could still move.
  - In `dynamic` the goal was reported at step 0 in 5 of 6 runs, then disproved or lost within a
    few steps and not found again.
