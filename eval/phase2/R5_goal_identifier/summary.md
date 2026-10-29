# R5 Goal identifier on the clean frame, sighting age: summary

**The hypothesis held for perception and failed for success; `a06` dropped (screening).** R5 has
8/18 successes:
- `initial`: **6/6**, the first perfect arm in Phase 2 (R1 5/6, R4 2/6);
- `final` + `dynamic`: 2/12 (R1 3/12, R4 3/12). `dynamic` is 0/6.

The goal identifier did what it was built for:
- It saw the goal in 114 / 114 in-view decisions.
- It never reported a goal that was not in the frame. Its 10 out-of-view reports are the sphere at
  the frame edge (6) or a ground-truth timing artefact (4), see Validity notes.
- The navigator's reasons placed the goal around the drone in 11 / 696 out-of-view decisions
  (1.6%; R4 20% under the same measure).
- No failed run carries `failed_goal_identification` (R4: 9 / 13).

The phantom goal of R4 is gone. What is left is a new failure. After a change, or in a post-change
layout, the drone turns around in place, again and again: in 70% of `dynamic` decisions and 41%
of `final` ones (R1 12% / 8%), in streaks of up to 36. Every failure acknowledged the closed route
(where it said anything), and none got through. Two of the three drop conditions are met.
`initial` shows the change can help, so the identifier is worth keeping. One seed per cell: a
screen, not an effect size (`docs/phase2-test-plan.md` §3). Pre-registration:
[README.md](README.md). Probe: [probe/probe.md](probe/probe.md). Reasoning analysis:
[reasoning_analysis.md](reasoning_analysis.md).

**Not citable.** R5 flew agent `a06` (`9cc1e3f9a121`), with prompts `p07` (`fc7175f7b803`) and
`g02` (`bf175c973dfb`), on `Qwen3-VL-30B-A3B`, remote profile, temperature 0. It was flown at
`d883714` after the probe gate passed, in two sittings:
- maps 1–12 on 2026-10-15, 16:24–17:03 UTC;
- maps 13–18 on 2026-10-16, 16:55–17:08 UTC, after a pause the operator asked for.

The flying took 51 min. Labels were reviewed by Claude and confirmed by the operator on
2026-10-16.
- **18 / 18 valid on the first attempt.** Every replay was exact, and every `run.json` matches
  the round lock.
- Map 13 (s01 `final`) was stopped before Godot started. The runner set its empty folder aside as
  an interrupted attempt and flew it fresh on resume.
- The round moved from `a05` to `a06` before flying, after `a05` failed its probe (README,
  "Before flying").

## Result

| Arm | R0 | R1 | R4 | R5 | replan_failure | latency p50 / p95 (per step, both calls) |
|---|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | 2/6 | **6/6** | 0 | 2.44 / 3.27 s |
| final | 0/6 | 2/6 | 2/6 | **2/6** | 4 | 2.64 / 3.25 s |
| dynamic | 0/6 | 1/6 | 1/6 | **0/6** | 6 | 2.73 / 3.30 s |

- All 10 failures are `replan_failure`: never through the new or available route. None is
  `ignore_change`, `collision` or `timeout`.
- **9 of the 10 carry the new tag `spin_failure`** (see below). The exception is s02c `final`,
  which grinds into a doorway instead (longest streak 3).
- Collisions over all 18 runs: **38** (R1 31, R4 101). 23 of them are s02c `final`, in a
  doorway.
- The navigator's prompt is 1,165 tokens at step 0 and 1,666 at step 59 (median); the
  identifier's is 705. Per call, the identifier takes 1.00 s and the navigator 1.65 s (p50).

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial R1 → R4 → R5 | final R1 → R4 → R5 | dynamic R1 → R4 → R5 |
|---|---|---|---|
| s01 | ✓ 14 → ✗ timeout → **✓ 14** | ✗ timeout → ✗ replan → ✗ replan | ✗ replan → ✗ replan → ✗ replan |
| s02a | ✓ 14 → ✗ timeout → **✓ 14** | ✗ timeout → ✓ 36 → ✗ replan | ✓ 60 → ✗ replan → ✗ replan |
| s02c | ✓ 14 → ✗ timeout → **✓ 14** | ✓ 34 → ✗ timeout → ✗ replan | ✗ timeout → ✗ replan → ✗ replan |
| s02va | ✓ 55 → ✓ 39 → **✓ 19** | ✗ replan → ✓ 28 → **✓ 35** | ✗ timeout → ✓ 40 → ✗ replan |
| s02vc | ✓ 55 → ✓ 37 → **✓ 19** | ✓ 24 → ✗ timeout → ✗ replan | ✗ timeout → ✗ timeout → ✗ replan |
| s03 | ✗ replan → ✗ replan → **✓ 41** | ✗ replan → ✗ replan → **✓ 54** | ✗ replan → ✗ pre-change → ✗ replan |

**Gains:**
- R1's three 14-step `initial` successes, which R4 lost to phantom goals, are back.
- s02va and s02vc `initial` take 19 steps (R1 55, R4 37–39).
- s03 succeeds for the first time in Phase 2, twice: `initial` (41) and `final` (54).
- s03 `dynamic` reaches the trigger for the first time since R1 (R2–R4: `pre_change_failure`).

**Losses:**
- s02a `final` and s02va `dynamic` (both R4 successes);
- s02a `dynamic` (R1's only `dynamic` success);
- s02c and s02vc `final` (R1 successes).

**Fewer independent observations than cells.** s01, s02a and s02c `initial` fly the same 14 picks
and end 0.645 m from the goal. s02va and s02vc `initial` fly the same 19 picks and end 0.282 m
out. They share their opening geometry. `initial` 6/6 holds about 3 independent observations, and
the round about 15.

## Manipulation check

`python eval/agent_evidence.py eval/phase2/R5_goal_identifier`, saved as
[manipulation_check.md](manipulation_check.md), against R1's numbers in
[evidence.md](evidence.md) and R4's [manipulation check](../R4_goal_after_reason/manipulation_check.md):

| Measure | R1 | R4 | R5 (initial / final / dynamic) | Pre-registered expectation |
|---|---|---|---|---|
| delivery: `goal_identifier`, clean frame, `memory_steps`, no navigator `goal` field | – | – | **810 / 810** each | every decision: passed |
| identifier: goal seen when visible, pooled | – | 98% | **114 / 114** | ≥ 90%: passed |
| identifier: goal reported when not in view | – | 44% | **10 / 696 (1.4%)** | ≤ 10%: passed |
| identifier agrees with ground truth | – | 50% / 88% / 43% | 95% / 98% / 99%, against majority class 31% / 95% / 96% | above majority: passed (narrowly on `final` and `dynamic`) |
| navigator reason places the goal now, out of view | – | 155 / 781 (20%) | **11 / 696 (1.6%)** | ≤ 10%: passed |
| step-0 pick = R1's | – | 16 / 18 | 14 / 18 | most: passed |
| same pick as the step before | 77% / 56% / 53% | 61% / 49% / 51% | 61% / 46% / 67% | < 90%: passed |
| reason copied word for word | 0% | 0% | 0% | < 10%: passed |
| **turn-around pick** | 8% / 8% / 12% | 21% / 23% / 27% | **7% / 41% / 70%** | reported |
| **two turn-arounds in a row** | 0% / 0% / 1% | 9% / 10% / 15% | **1% / 26% / 58%** | – |
| revisit | 48% / 28% / 33% | 30% / 19% / 34% | 2% / 41% / 57% | reported |
| reason cites memory | 2% / 1% / 1% | 36% / 48% / 54% | 61% / 52% / 87% | reported, not judged |

Every pre-registered check passes. The change took effect as intended, and the failure has
moved from what the agent sees to what it does.

## What the model did

The reasoning analysis ([reasoning_analysis.md](reasoning_analysis.md)) was written by a subagent
from all 810 decisions. Its headline numbers were spot-checked against the data for this summary:
- the 10 identifier out-of-view reports;
- the "goal is behind" turn-arounds (74 / 82 here, 83 / 92 under its broader match);
- the double-turn-around rates;
- 0 turn-arounds with the goal in view.

Figures below are from this summary's own counts unless marked as the analysis's.

**It sees the goal and follows the identifier.**
- Out of view, the identifier and the navigator agree that the goal is not there.
- With the goal in view, R5 never turns around (0 / 114), and the navigator steers to the
  identifier's side. The analysis counts 115 / 124 such decisions; the rest are marker-number
  slips such as "[1], which corresponds to flying straight".
- R1, by the analysis, turned around 3.4 m from the goal on s02va `initial`, which is most of why
  R5 is three times faster there.

**After a change, it turns around in place.** The same two arguments alternate, and both end in
`[0]`:
- facing the old heading: "a closed door directly ahead, which blocks the path ... turn around"
  (s02a `dynamic`, step 4);
- facing away: "since then the drone has turned around (step 4), so it is now facing the opposite
  direction. The goal is not visible ... which means it is behind the drone ... the most direct way
  to reorient toward the goal is to turn around again" (s01 `dynamic`, step 5).

The sighting line carries the second argument. Its arithmetic is right: the analysis finds the
inferred direction correct 76 / 77 times. But in `dynamic` the goal's direction runs through the
closed door or the cube, and a reason that says the goal is behind ends in a turn-around 74 / 82
times. Three examples:
- s02a `dynamic` turns around on every step from 24 to 59: 36 in a row, with the drone not
  moving.
- s02va `dynamic` names the open doorway at step 5 ("an open doorway to the right (marker 5) and
  a closed door in the center (marker 3)") and takes it. At step 6 it turns back.
- s02vc `dynamic` turns around at step 4, where R1 and R4 went for the doorway that had just
  opened.

The sighting line is the goal-bearing hint of Phase 1 by another route (`results.md`: 0 / 30 on
`dynamic` with the bearing given). The model flies at the goal's direction, and the route that
direction points down is closed.

**The loop also runs without a sighting.**
- s01, s02a and s02vc `final` never see the goal, and still turn around 15, 9 and 12 times in a
  row.
- The stated reason is the wall ahead: "facing a wall ... turning around is the safest option to
  reorient".
- In the analysis, 54% of the wall-justified turn-arounds had at least 5 m of free floor ahead,
  and 183 of 217 reasons that note the repeated turning pick a turn-around again.

**Stuck at an open doorway.** In three runs the drone finds the open route and does not take it:
- s02c `final` spends 49 steps near door C and grinds 23 collisions into the frame. After
  collisions its reasons say it "has been moving forward": the log records the command, not the
  outcome.
- s02a `final` and s02va `dynamic` spend about 32 steps each within 3 m of the doorway, turning
  in place.

**What made s03 work.** The move log, not the sighting line. At the T-junction (s03 `initial`,
step 14) it reasons that "turning around ... would retrace the path already taken" and turns left
into the unexplored tine, where R1 shuttled along the entry corridor. s03 `final` had no sighting
until step 47.

## Against the predictions

| Prediction (README) | Outcome |
|---|---|
| `initial` 5/6, s03 stays failed | **Exceeded**: 6/6, s03 succeeds in 41 |
| `final` ≥ 2/6 | **Held**: 2/6 (s03 and s02va) |
| `dynamic` ≥ 2/6 | **Wrong**: 0/6 |
| `final` + `dynamic` ≥ 4/12 | **Wrong**: 2/12 |
| Phantom facet in ≤ 2 failed runs | **Held**: 0 |
| Collisions below R4's 101 | **Held**: 38 |
| s03 stays failed on all arms | **Wrong**: two successes |
| Close-range losses may remain | **Did not occur**: every run that came within 3 m arrived |

**Drop criterion: met on two of three.**
- `final` + `dynamic` is 2/12 (≤ 3/12) with the identifier delivered.
- `initial` is 6/6 (> 3/6), so that condition does not fire.
- Same pick stays below 90% on both arms (46% and 67%); the turn-around streaks are a lock-in of
  one action that this measure does not see.

`a06` is not carried forward as is. Its identifier is. Every option below keeps it.

## For the next round

The open problem moves from perception to replanning. The drone knows where the goal is and that
the route is closed, and it cannot leave the spot. The analysis ranks five single changes
([reasoning_analysis.md](reasoning_analysis.md) §8). In short:

1. **Do not offer turn-around on the step after a turn-around.** This targets the loop in 9 / 10
   failures, in both arms. It changes the action list, which the phase lock fixes (`config`:
   `include_turn_around`). It needs the operator's ruling on whether an agent may filter actions.
   Check: two turn-arounds in a row → 0; `final` + `dynamic` ≥ 4/12.
2. **Remove the sighting line**, and keep the identifier's answer for the current image and the
   move-only log. This removes the "goal is behind, turn around" argument. It does not touch the
   `final` loop. Check: `dynamic` turn-around ≤ 30%, `dynamic` ≥ 2/6, `initial` holds.
3. **Log outcomes, not commands** ("flew straight: hit a wall, did not move"; "turned around 3
   times in place"). The model can then see the loop and the grinding in its own record. Check:
   collisions ≤ 15, s02c `final` through door C.
4. **Name the marker directions in the action list** ([1] sharp left … [5] sharp right), against
   the marker-number slips. An efficiency fix only.
5. **Reword the turn-around guidance.** The least certain: R4 had the same sentence and turned
   around half as often.

Option 2 is the smallest step and a clean test of the sighting line. Option 1 attacks the
behaviour directly, if the lock allows it. Probe either one with the replay set first. The replay
set needs a measure for repeated turn-arounds, as it measures phantom claims now.

**Rubric.** The operator added the secondary tag `spin_failure` in this round (next section).
Still open:
- a tag for stalling at an open doorway, which `replan_failure` also hides;
- the step-3 ground-truth timing (Validity notes), to fix before the next labelling pass.

## New failure tag: `spin_failure`

R5 brought out a failure the rubric had no name for: the agent turns around in place, again and
again, and the run's steps run out with the drone standing still. The operator added it as a
secondary tag (`docs/phase2-test-plan.md` §5), not a terminal label, so the six labels and the
frozen thresholds are unchanged. `eval/phase1_label.py` computes it into `auto_labels.json`
(`spin`).

**Rule:** a failed run with **≥ 5 consecutive turn-around picks**. No successful run in R1–R5 has
a streak over 4 (R5 s03 `final`).

| R5 failed run | longest streak | from step | turn-arounds in the run |
|---|---|---|---|
| s02a `dynamic` | 36 | 24 | 48 / 60 |
| s01 `dynamic` | 26 | 34 | 50 / 60 |
| s02vc `dynamic` | 22 | 25 | 36 / 60 |
| s02va `dynamic` | 21 | 39 | 40 / 60 |
| s03 `dynamic` | 18 | 28 | 37 / 60 |
| s01 `final` | 15 | 30 | 35 / 60 |
| s02vc `final` | 12 | 33 | 31 / 60 |
| s02a `final` | 9 | 35 | 28 / 60 |
| s02c `dynamic` | 7 | 25 | 40 / 60 |
| s02c `final` (not tagged) | 3 | 25 | 21 / 60 |

By the operator's decision, R1–R4 keep their labels as reviewed, and the tag's first appearance
in R5 records when this failure was recognised. By the rule, 9 of R3's 18 failures and 6 of R4's
13 would have met it. R1's longest streak in any run is 4. The loop grew as the memory did.

## Validity notes

- **Line-of-sight timing at the change step.** At step 3 of the four s02 `dynamic` runs, the
  manifest records no line of sight (bearing 3°), but the clean frame shows the sphere. The doors
  switch after the frame is captured and before ground truth is sampled. This is R4's s01 note in
  another site. It accounts for 4 of the identifier's 10 out-of-view reports and for the
  labeller's `phantom: 1` on those runs. It is not a model error.
- **Frame-edge reports.** The other 6 out-of-view reports have the sphere at bearing −44° to −53°
  with line of sight, just outside the 43.5° half field of view that `true_goal()` uses: the
  sphere's edge is in the frame.
- **Auto-labeller acknowledgement corrections** (`labels.csv`):
  - s01 `dynamic` step 4: cleared, because the cube is never named;
  - s02a `dynamic` 3 → 4;
  - s02vc `dynamic` 3 → 9.

  No label changed: no `dynamic` run had ≥ 3/5 moves toward the goal, and none got through.
- **s01 `dynamic` is `replan_failure` without an acknowledgement**, as in R4: §9 labels any run
  that never gets through as `replan_failure`.
- **s02c `final`** collided on 23 of 56 post-change steps (41%). That is under the 50% collision
  threshold, and the run never got through, so it is `replan_failure`.
- **The round was flown in two sittings**, a day apart, at the same SHA and against the same
  decider process. The tunnel reconnected in between (autossh), and latency was within the probe's
  range in both sittings.
- **The calibration of the replay probe passed at its floor** (`a04` 10 / 40 against ≥ 25%). The
  in-flight result (1.6% against R4's 20%) supports what the probe found.
- Static-arm `ack_step` values are cleared, as in R1–R4.
