# R4 Memory log, goal reported last: summary

**Hypothesis did not hold; `a04` dropped (screening).** R4 has 5/18 successes:
- `initial`: 2/6 (R1 5/6, R3 0/6);
- `final` + `dynamic`: 3/12, level with R1's 3/12.

Moving the goal report after the reason and dropping the beam from the description fixed R3's
perception failure, both in the pre-flight probe and in flight:
- In flight, the goal is reported in 175 of the 179 decisions where it is in view (R3: 40 / 198).
- The 30 early frames matched on pose with R1 give 30 / 30 (R3: 0 / 30).

But the log now carries the opposite error. Once one "Goal: ahead" is in it, the model keeps
reporting the goal as ahead after it has left the frame:
- 342 of the 781 decisions with the goal out of view report it anyway.
- 272 of those 342 reasons cite the log ("the goal consistently reported as ahead").
- The agent then flies away from the goal, or into a wall, on a goal it cannot see.

R3's log said "not visible" all the time, and R4's says "ahead" all the time. The record still
carries no correct sighting. Two of the three drop conditions are met. `a01` remains the best
agent. This is one seed per cell, so it is a screen, not an effect size
(`docs/phase2-test-plan.md` §3). Pre-registration: [README.md](README.md). Probe:
[probe/probe.md](probe/probe.md).

**Not citable.** Flown at `60118e8` on 2026-10-14, 14:43–15:22 UTC (39 min), after the probe
gate passed. The runs used `Qwen3-VL-30B-A3B` on the remote profile at temperature 0, with agent
`a04` (`a90e249c14a1`) and prompt `p06` (`d9059847942e`). Labels were reviewed by Claude and
confirmed by the operator on 2026-10-14.

- **18 / 18 valid on the first attempt.** Every replay was exact, every `run.json` has
  `git_dirty: false`, and the agent sha matches the round lock.
- **The step-0 pick equals R1's in 16 / 18 cells** (the probe gave 17 / 18 on the same frames).
  In the other two cells, the trajectories differ from R1 from step 1 on.

## Result

| Arm | R0 | R1 | R2 | R3 | R4 | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | 1/6 | 0/6 | **2/6** | – | 1 | 0 | 3 | – | 1.54 / 2.18 s |
| final | 0/6 | 2/6 | 0/6 | 0/6 | **2/6** | – | 2 | 0 | 2 | – | 1.57 / 2.10 s |
| dynamic | 0/6 | 1/6 | 0/6 | 0/6 | **1/6** | 0 | 3 | 0 | 1 | 1 | 1.56 / 2.09 s |

- Collisions over all 18 runs: **101** (R1: 31, R3: 41, R2: 596).
- At step 59 the prompt is 1,828 tokens (median of the 13 runs that got there). At step 0 it is
  1,076 (R3: 1,090).
- 9 of the 13 failed runs carry the new tag `failed_goal_identification` (see below).

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial R1 → R4 | final R1 → R4 | dynamic R1 → R4 |
|---|---|---|---|
| s01 | **✓ 14 → ✗ timeout** | ✗ timeout → ✗ replan | ✗ replan → ✗ replan |
| s02a | **✓ 14 → ✗ timeout** | ✗ timeout → **✓ 36** | **✓ 60 → ✗ replan** |
| s02c | **✓ 14 → ✗ timeout** | **✓ 34 → ✗ timeout** | ✗ timeout → ✗ replan |
| s02va | ✓ 55 → ✓ 39 | ✗ replan → **✓ 28** | ✗ timeout → **✓ 40** |
| s02vc | ✓ 55 → ✓ 37 | **✓ 24 → ✗ timeout** | ✗ timeout → ✗ timeout |
| s03 | ✗ replan → ✗ replan | ✗ replan → ✗ replan | ✗ replan → ✗ pre-change |

**Gains.** These three cells never succeeded in R1–R3:
- s02va `final` (✓ 28) and s02va `dynamic` (✓ 40), the first successes in those cells in
  Phase 2;
- s02a `final` (✓ 36).

s02va and s02vc `initial` held their R1 successes and got there faster (39 and 37 steps,
against 55).

**Losses:**
- the three 14-step R1 `initial` successes (s01, s02a, s02c);
- s02c and s02vc `final`;
- s02a `dynamic`.

## Probe against flight

The probe ([probe/probe.md](probe/probe.md)) sent 173 recorded frames to the model, each as step
0 with an empty log. Both in the probe and in flight, it predicted R3's failure and R4's
perception correctly. It missed R4's failure:

| Measure | probe `a04` | flight R4 |
|---|---|---|
| early frames (R1 steps 0–2, goal in view) | 30 / 30 | 30 / 30 |
| goal seen when in view | 107 / 107 | 175 / 179 (99% / 93% / 100%) |
| goal reported when not in view | 1 / 66 (2%) | **342 / 781 (44%)**: 143 / 204 `initial`, 12 / 263 `final`, 187 / 314 `dynamic` |
| step-0 pick = R1's | 17 / 18 | 16 / 18 |

The false reports need a log with a sighting in it, and every probe frame starts with an empty
log. A probe that only tests step 0 cannot see a failure that builds up through the log. The next
probe has to replay frames with a log already in place, including one that says "Goal: ahead"
while the goal is out of view.

## Manipulation check

`python eval/agent_evidence.py eval/phase2/R4_goal_after_reason`, saved as
[manipulation_check.md](manipulation_check.md), against R1's numbers in
[evidence.md](evidence.md):

| Measure | R1 | R3 | R4 (initial / final / dynamic) | Pre-registered expectation |
|---|---|---|---|---|
| valid `goal` field | – | 1080 / 1080 | **960 / 960** | delivery: passed |
| goal seen when visible, pooled | – | 20% | **98%** (175 / 179): 99% / 93% / 100% | ≥ 50%: passed |
| early frames matched on pose with R1 | 30 / 30 (reasons) | 0 / 30 | **30 / 30** | ≥ 27: passed |
| goal report agrees with ground truth | – | 58% / 99% / 91% | **50% / 88% / 43%**, against majority class 65% / 87% / 92% | above majority: **failed** on `initial` and `dynamic` |
| step-0 pick = R1's | – | – | 16 / 18 | most: passed |
| same pick as the step before | 77% / 56% / 53% | 54% / 46% / 45% | 61% / 49% / 51% | < 90%: passed |
| reason copied word for word | 0% | 0% | 0% | < 10%: passed |
| turn-around pick | 8% / 8% / 12% | 38% / 29% / 29% | 21% / 23% / 27% | reported |
| revisit | 48% / 28% / 33% | – / 30% / 40% | 30% / 19% / 34% | reported |
| reason cites memory | 2% / 1% / 1% | 45% / 36% / 35% | 36% / 48% / 54% | reported, not judged |

- Delivery, seeing the goal and no lock-in all pass.
- Agreement fails, and this time it fails on false reports, not misses.
- The README named this case: "If perception passes and success does not move, the record is
  correct and the model does not act on it." The record here is not correct either. The model
  acts on it, but it acts on stale sightings.

## What the model did

**It sees the goal again, from the first frame.** At steps 0–2 the reasons describe it and the
field reports it. s02c `final`, step 32: "The goal is a glowing red sphere, which is visible in
the image directly ahead of the drone". With no beam in the description, the R3 close-range
rejection ("it does not have a tall red beam") never recurs.

**Then the log keeps the goal "ahead" after it is gone.**
- Most phantom reports (272 / 342) argue from the log, not the image. s01 `dynamic`, step 31:
  "The drone has been moving forward in a straight line for multiple steps, with the goal
  consistently reported as ahead". At that point the goal is 168° behind the drone and out of
  line of sight.
- The field and the reason disagree again, now the other way round. s02a `initial`, step 11: "The
  goal is not visible in the current view", and the field says `ahead`.
- The log's directions are relative to the heading at each step. The model reads "Goal: ahead"
  as ahead of the current heading, even after a turn-around. s02a `initial` turns around 7.1 m
  from the goal at step 18, then flies east from step 19 with the goal behind it (bearing −171 to
  −176). s02vc `final`, step 55: "the log indicates it has been visible and ahead for several
  steps (from Step 44 onward)".

**It follows the phantom into walls.**
- s01 `dynamic`: 28 collisions against the east back wall at steps 22–49, while the reasons say
  "no visible obstacles ... the goal is still reported as ahead".
- s02vc `dynamic`: crosses the wall at step 41 and collides on all 19 remaining steps.
- s02vc `final`: 5 collisions at steps 55–59, also against a wall.
- These three are tagged `path_hallucination` as well.
- Collisions rise to 101, from R3's 41. They are below R2's 596 and are not a lock-in: same pick
  stays at 49–61%.

**It loses the goal at close range a different way.** Close up, R3 rejected the sphere. R4
oversteps or turns past it:
- s02c `final`, step 34: a sharp left at 2.6 m puts the goal at −63° and 1.4 m (arrival radius
  1.0 m). The goal leaves the frame, the report goes to `not_visible`, and it turns around.
- s02c `initial`, step 30: it passes 2.2 m from the goal, then flies 12 m away on the log. It
  comes back to 1.4 m at step 48 and overshoots again.
- The five successes came within 1.4–2.6 m before their last move.

**The changes are read, but late or wrongly.**
- The closed doors are acknowledged at step 4 or 5 in all four s02 `dynamic` runs (`ack_step`
  corrected in review).
- s01 `dynamic` never sees the cube. Its step-3 frame was captured before the cube rose, it turns
  around at that step, and it does not face west again until step 51.
- s02va `dynamic` reads the switch at step 5: "The leftmost doorway (marker 1) is closed, the
  middle doorway (marker 3) is closed, and the rightmost doorway (marker 5) is open". It is the
  only `dynamic` success.
- `ignore_change` does not occur. The model is never heading toward the goal bearing right after
  a change (0–2 of 5).

**Identical runs.** s03 `initial` and s03 `dynamic` are identical: the trigger is never reached.
No s02 pair is identical this round, unlike R3. R4 therefore holds about 17 independent
observations.

**Cost.** Latency p50 / p95 is ~1.56 / 2.1 s (R1: ~1.4 / 1.8 s; R3: ~1.6 / 2.0 s). The round
took 39 min, against R3's 43, because 5 runs ended early.

## Against the predictions

| Prediction (README) | Outcome |
|---|---|
| `initial` 5/6, s03 stays failed | **Wrong**: 2/6. s03 stays failed; s01, s02a and s02c time out after phantom sightings |
| `final` ≥ 2/6, keeps s02c and s02vc | **Partly**: 2/6, but from s02a and s02va. Lost both predicted cells |
| `dynamic` ≥ 2/6, keeps s02a | **Wrong**: 1/6 (s02va, new). Lost s02a (`replan_failure`) |
| `final` + `dynamic` ≥ 4/12 | **Wrong**: 3/12, level with R1 |
| R3's close-range turn-aways do not recur | **Held** for the beam rejection. Close-range losses remain in another form (s02c ×2) |
| Fewer than R1's 5 `timeout` | **Wrong**: 6 |
| No turn to `collision` or `ignore_change` | **Held**: 0 and 0 |
| s02va `final` unlikely to move | **Wrong**: ✓ 28, its first success in Phase 2 |

**Drop criterion: met on two of three.** `final` + `dynamic` is 3/12 (≤ 3/12) while the log is
delivered, and `initial` is 2/6 (≤ 3/6). The lock-in did not return (same pick ≤ 61%). `a04` is
not carried forward.

## New failure tag: `failed_goal_identification`

R4 brought out a failure the rubric had no name for: the agent fails to identify where the goal
is. This round it mostly comes as a phantom, and in R3 it came as a miss. The operator added it
as a secondary tag (`docs/phase2-test-plan.md` §5), not a terminal label, so the six labels and
the frozen thresholds are unchanged. `eval/phase1_label.py` computes it into
`auto_labels.json` (`goal_id`).

A failed run gets the tag if any of these holds:
- **phantom goal:** ≥ 5 reports of the goal while it is out of view;
- **missed goal:** ≥ 3 in-view decisions reported `not_visible`, and that is ≥ 50% of the in-view
  decisions;
- **lost at close range:** closest approach ≤ 3.0 m without arriving.

| Facet | R4 failed runs |
|---|---|
| phantom goal | 8: s01 `initial` (40) and `dynamic` (57), s02a `initial` (44) and `dynamic` (11), s02c `initial` (32) and `dynamic` (35), s02vc `final` (9) and `dynamic` (57) |
| missed goal | 0 |
| lost at close range | 2: s02c `final` (1.4 m), s02c `initial` (1.4 m, also phantom) |

The four untagged failures are s01 `final` and the three s03 runs. They never come near the
goal, and they fail on the route.

By the operator's decision, R1–R3 keep their labels as reviewed. The tag's first appearance in R4
records when this failure was recognised. By the numbers, 12 of R3's 18 failed runs would have
met "missed goal".

## For the next round

The open question is still R2's: does a record of where the goal was last seen help?
- R3's record never held a sighting.
- R4's record holds sightings and never lets go of them.
- Both rounds show the model takes the log's goal entries as fact over the image. The image-first
  sentence in `p05`/`p06` does not stop this.

Options, for the operator to choose:

1. **Log moves only, no goal entries** (R3 option 2). Keep `a04`'s reply order and wording,
   which see the goal, but leave the goal report out of the log, so no stale sighting can be
   copied. This tests whether the move log alone helps, and it is the smallest step back from
   R4. Check: phantom reports fall to near the probe's 2%, and `initial` returns toward 5/6.
2. **Log goal sightings with their age** (recommended if the record is to stay). Replace
   "Goal: ahead" on every line with one line written by code: "Last reported goal sighting: step
   N, ahead (K steps and M turns ago)". The entry then states its own staleness, and the
   relative-heading problem is spelled out. This is one change, and it still tests the
   hypothesis.
3. **Back to `a01` plus collision feedback**, the README's next candidate. This leaves the memory
   question for later.

Whichever is chosen, extend the probe first:
- add frames replayed with a log in place (a sighting 5–20 steps old, and a turn-around after
  it), so it can catch phantom reports before flying;
- gate on the phantom rate for those frames, not only on the empty-log ones.

## Validity notes

- **Frame-capture timing on s01 `dynamic`.** The cube rises in 0.3 s. The step-3 frame shows the
  goal at the end of the corridor, but the manifest already records no line of sight. The step-3
  report of `ahead` is counted as a phantom, but it is correct for the image. This affects at
  most 1 decision per s01 `dynamic` run. It is not a model error, and it is in the R1–R3 frames
  too.
- **Auto-labeller acknowledgement false positives** on `dynamic`:
  - s02c step 3 ("a clear path forward toward a doorway"), moved to step 4;
  - s02vc step 3 ("The central doorway is open and leads to a room where the glowing red sphere
    ... is visible"), moved to step 4;
  - s02va step 4 (no door state named), moved to step 5;
  - s01 step 3 (the end wall), cleared.
  No label changed: no `dynamic` run had ≥ 3 / 5 moves toward the goal, so `ignore_change` could
  not apply.
- **s01 `dynamic` is `replan_failure` without an acknowledgement.** The cube is never named. §9
  makes any run that never gets through `replan_failure`, whatever else holds.
- **s02vc `dynamic` collided on 19 of the 19 steps after crossing.** The rubric's collision share
  is over all post-change steps (22 / 57 = 39%), under 50%, so the label is `timeout`. The
  threshold is frozen and is not changed here.
- Static-arm `ack_step` values are cleared, as in R1–R3.
- [evidence.md](evidence.md) holds R1's numbers on purpose (the README's baseline). R4's are in
  [manipulation_check.md](manipulation_check.md).
- "Goal seen when visible" and the phantom counts use ground truth from the manifest: line of
  sight to the sphere, and |bearing| ≤ 43.5°.
