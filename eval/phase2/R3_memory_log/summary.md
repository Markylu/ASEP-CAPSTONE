# R3 Memory log, code-written: summary

**Hypothesis not tested; round failed (screening).** Success fell from 8/18 in R1 to **0/18**:
`initial` 5/6 → 0/6, and `final` + `dynamic` 3/12 → 0/12. The log was delivered on every decision
and the model read it. The R2 lock-in did not return. But the agent stopped seeing the goal. On the
same frames at steps 0–2, R1's reasons see the goal 30 times out of 30 and R3 reports it 0 times out
of 30. The log is still empty at step 0, so the loss comes from the rest of the change: the `goal`
field answered before the reason, or `p05`'s new text. The data cannot separate the two. Because of
this, the log never recorded a goal sighting in 13 of 18 runs, and the hypothesis about using the
record was never put to the test. Two of the three drop conditions are met. `a03` is dropped, and
`a01` remains the best agent. This is one seed per cell, so it is a screen, not an effect size
(`docs/phase2-test-plan.md` §3). Pre-registration: [README.md](README.md).

**Not citable.** Flown at `53998a3` on 2026-10-12. The round opened at 22:38 UTC, and the 18 valid
runs flew 23:13–23:56 UTC. The runs used `Qwen3-VL-30B-A3B` on the remote profile at temperature 0,
with agent `a03` (`bec48dc3ef3b`) and prompt `p05` (`dda9d66652d5`). Labels were reviewed by Claude
and confirmed by the operator on 2026-10-13.

- **18 / 18 runs valid.** Every replay was exact, every `run.json` has `git_dirty: false`, and the
  agent sha matches the round lock.
- s02a `dynamic` needed a second attempt: `a01` hit the 15-minute wall-clock limit (end reason
  `wall_clock_limit`), and `a02` is the valid run (§10). Two interrupted starts are also kept in
  `_attempts/`.
- Spawn jitter for seed 1 is the same as in R0–R2. Steps 0–2 have the same pose as R1 in every cell.

## Result

| Arm | R0 | R1 | R2 | R3 | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | 1/6 | **0/6** | – | 0 | 0 | 6 | – | 1.56 / 1.98 s |
| final | 0/6 | 2/6 | 0/6 | **0/6** | – | 5 | 0 | 1 | – | 1.60 / 1.97 s |
| dynamic | 0/6 | 1/6 | 0/6 | **0/6** | 0 | 2 | 0 | 3 | 1 | 1.61 / 2.02 s |

Collisions over all 18 runs: **41** (R1: 31, R2: 596, R0: 675). At step 60 the prompt is 1,853
tokens (median), against R1's flat 922 and R2's 8.8k.

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial R1 → R3 | final R1 → R3 | dynamic R1 → R3 |
|---|---|---|---|
| s01 | **✓ 14 → ✗ timeout** | ✗ timeout → ✗ replan | ✗ replan → ✗ replan |
| s02a | **✓ 14 → ✗ timeout** | ✗ timeout → ✗ replan | **✓ 60 → ✗ timeout** |
| s02c | **✓ 14 → ✗ timeout** | **✓ 34 → ✗ replan** | ✗ timeout → ✗ timeout |
| s02va | **✓ 55 → ✗ timeout** | ✗ replan → ✗ replan | ✗ timeout → ✗ replan |
| s02vc | **✓ 55 → ✗ timeout** | **✓ 24 → ✗ timeout** | ✗ timeout → ✗ timeout |
| s03 | ✗ replan → ✗ timeout | ✗ replan → ✗ replan | ✗ replan → ✗ pre-change |

All six `initial` runs got through, came within 2.3–3.5 m of the goal (arrival radius 1.0 m), and
then turned away. s03 `initial` left the fork for the first time in Phase 2 (R0–R2:
`replan_failure`) and got within 2.5 m.

## Manipulation check

`python eval/agent_evidence.py eval/phase2/R3_memory_log`, saved as
[manipulation_check.md](manipulation_check.md), against R1's numbers in [evidence.md](evidence.md):

| Measure | R1 | R3 (initial / final / dynamic) | Pre-registered expectation |
|---|---|---|---|
| `memory_steps` = number of earlier decisions | – | **1080 / 1080** | delivery: passed |
| valid `goal` field | – | **1080 / 1080** | delivery: passed |
| `prompt_tokens` per log line | flat 922 | **~13**; rises every step except one (s02va `dynamic` step 27, −142) | ~12: passed |
| goal seen when visible, pooled | – | **20%** (40 / 198): 25% / 0% / 0% | ≥ 50%: **failed** |
| goal report agrees with ground truth | – | 58% / 99% / 91%, against majority class 56% / 99% / 91% | above majority: **failed** |
| same pick as the step before | 77% / 56% / 53% | **54% / 46% / 45%** | < 90%: passed |
| reason copied word for word | 0% | **0%** | < 10%: passed |
| turn-around pick | 8% / 8% / 12% | **38% / 29% / 29%** | picked again: passed, overshot |
| revisit, `final` / `dynamic` | 28% / 33% | **30% / 40%** | below R1: **failed**, it rose |
| reason cites memory | 2% / 1% / 1% | 45% / 36% / 35% | reported, not judged |

Delivery passes, and so does the absence of lock-in. Perception fails, and the README named the
case: the record is delivered and nothing improves. But this record is not a correct one. It says
"Goal: not visible" at almost every step.

## What the model did

**It stops seeing the goal, from the first frame.** Steps 0–2 of all 18 cells have the same pose in
R1 and R3, at temperature 0. In the 30 of these decisions where the goal is in view, R1's reasons
see it every time: s01 step 0, "visible in the distance straight ahead". R3 reports `not_visible`
every time: "The goal, a glowing red sphere with a tall red beam, is not visible in the current
image". The log is empty at step 0. What differs is the `goal` field, which the schema puts before
`reason`, and `p05`'s text ("First say where the goal is in this image ..."). The reason then
follows the field. All 1,040 `not_visible` reports open with a sentence saying the goal is not
visible, and the other 40 do not.

- **Over the whole run the field is cautious, not noisy.** It never reports a goal that is not in
  view (0 / 882). It misses one that is in view 80% of the time.
- **Misses grow with distance.** The goal is reported in 0 / 50 decisions at 20 m or more, 13 / 74
  at 10–20 m, 20 / 60 at 5–10 m and 7 / 14 under 5 m.
- **It turns away close up.** Within 2–4 m the beam leaves the top of the frame, and the reasons
  rule out the sphere they can see. s03 `initial`, step 47: "a red sphere on the floor, but it does
  not have a tall red beam". Step 48, 2.5 m out: "The red sphere is on the floor directly in front
  of the drone". It turns around. s02a `initial` at 2.3 m (step 19) and s01 `initial` at 7.0 m
  (step 32) do the same.
- **The field and the reason can disagree.** s01 `initial`, steps 32–47: the reasons place "a red
  sphere and beam located to the left". The field says `not_visible`, and the pick is a turn-around
  16 times in a row.

**The log never held a sighting where it mattered.** 13 of 18 runs never report the goal once:
every `final` and `dynamic` run, and s03 `initial`. Their log reads "Goal: not visible" on every
line, so the part of the hypothesis about remembering where the goal was last seen had nothing to
work with. Where a sighting was logged, the model used it. s01 `initial`, step 50: "The drone has
previously reported the goal as 'ahead' in step 49, and the current image confirms this."

**It turns around far too often.** 345 of 1,080 picks are the turn-around (32%; R1 8–12%, R2 0%).
145 of them come straight after another turn-around and undo it, so 13% of all decisions move the
drone nowhere. Turn-around and straight alternate in place 17 times (`0 3 0 3`). s01 `dynamic`
shuttles between x 5.2 and 6.9 for steps 14–23. The reasons justify it from the log: "the drone has
already turned around multiple times ... the most logical action is to turn around and retrace the
path". With the goal never reported, the agent is always exploring, and `p05` names turning around
as a normal move.

**The R2 lock-in is gone, and it reads the frame for obstacles.** No reason is copied, same pick is
at or below R1's level, and there are no `ignore_change` or `collision` labels. In `dynamic` the
change is acknowledged at s01 step 14 (the cube, "a wall directly ahead ... blocked"), s02a and s02c
step 4 ("a closed door"), s02va step 22 and s02vc step 29: "one on the left is open and leads to a
lit area, while two in the center are closed". s02a, s02c and s02vc `dynamic` cross the wall
through the new door, which no R2 `dynamic` run did, but late (steps 49–50) and never within 12 m of
the goal.

**Identical runs.** s02a and s02c `initial` are identical, and so are s02va and s02vc `initial`.
s02a and s02c `dynamic` are identical to step 8. R3 holds fewer than 18 independent observations,
though more than R2.

**Cost.** Latency p50 / p95 is ~1.6 / 2.0 s (R1: ~1.4 / 1.8 s; R2: 1.5 / 2.4 s). The log adds ~13
tokens per step, and `p05` adds ~170 tokens at step 0 (1,090 against R1's 922). The 18 valid runs
took 43 min (R1: 31, R2: 36), because every run used all 60 steps.

## Against the predictions

| Prediction (README) | Outcome |
|---|---|
| `initial` 5/6, s03 stays failed | **Wrong**: 0/6. All five R1 successes now time out close to the goal |
| `final` ≥ 2/6, keeps s02c and s02vc | **Wrong**: 0/6. Lost both |
| `dynamic` ≥ 2/6, keeps s02a | **Wrong**: 0/6. Lost s02a (crossed at step 49, never closer than 12.9 m) |
| Fewer than R1's 5 `timeout` | **Wrong**: 10 |
| No turn to `collision` or `ignore_change` (R2's failure) | **Held**: 0 and 0 |
| s03 failed on all arms | **Held** on success; `initial` left the fork for the first time |
| s02va `final` does not move | **Held**: `replan_failure` |

**Drop criterion: met on two of three.** `final` + `dynamic` is 0/12 (≤ 3/12) while the log is
delivered, and `initial` is 0/6 (≤ 3/6). The lock-in did not return (same pick ≤ 54%). `a03` is not
carried forward.

## For the next round

R3 did not test what it set out to test. The log was compact, factual and read. It did not bring
back R2's lock-in or copied history, so that part of the design works. But the `goal` field, placed
first, changed perception before the log had any content, and a log of "Goal: not visible" lines
cannot carry a sighting forward. The open question from R2 is still open: does a record of where
the goal was last seen help?

Options, for the operator to choose:

1. **Keep the log, move the goal report after the reason** (recommended). This is `a03` with the
   field order changed and `p05`'s "First say where the goal is" line removed, so the model
   describes the frame before it commits. One change, cheap, and it separates the field from the
   log. Check: goal seen when visible returns toward R1's level (R1's reasons saw the goal in
   30 / 30 early frames), and step-0 picks match R1.
2. **Log moves only, no goal field.** This is the smallest test of the log alone, but it gives up
   the sighting record the hypothesis is about.
3. **Back to `a01` plus collision feedback**, the README's next candidate. This leaves the memory
   question for later.

The goal description may also need a line saying the beam can be out of frame when the goal is
close. Three `initial` runs turned away from a sphere at 2.3–7 m because they could not see a beam.
That would be a separate change, not part of option 1.

## Validity notes

- The auto-labeller's acknowledgement detector again gave false positives on `dynamic`: s02a step
  3 ("a doorway ... clear path forward"), s02va step 4 ("a dark wall to the left") and s02vc step 3
  ("The central doorway is open"). Manual review moved `ack_step` to the first real
  acknowledgement (`labels.csv` notes). No label changed: no `dynamic` run had ≥ 3 / 5 moves toward
  the goal, so `ignore_change` could not apply. The rubric and thresholds are unchanged.
- Static-arm `ack_step` values are cleared, as in R1 and R2. s03 `dynamic` has no change and its
  `ack_step` 0 is cleared.
- [evidence.md](evidence.md) holds R1's numbers on purpose (the README's baseline). R3's are in
  [manipulation_check.md](manipulation_check.md).
- "Goal seen when visible" uses ground truth from the manifest: line of sight to the sphere, and
  |bearing| ≤ 43.5° (half the camera's field of view).
- The step 0–2 comparison with R1 is matched on pose, not on the image file. Same seed, same
  spawn, same pose, temperature 0.
