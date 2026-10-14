# R4: Memory log, goal reported last

**Agent:** `a04` (`a90e249c14a1`) · **Prompt:** `p06` (`d9059847942e`) · **Status:** pre-registered, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

R4 is `a03` with two edits. The operator chose option 1 from the
[R3 summary](../R3_memory_log/summary.md) and added the second edit:

1. **The goal report comes after the reason.** The reply order is now `reason`, `goal`, `action`
   (R3: `goal`, `reason`, `action`), with the feature `goal_order: after_reason` and
   `schema.action_schema(..., goal_after_reason=True)`. On the text rung the lines come in the
   order REASON, GOAL, ACTION. The last prompt line changes from "First say where the goal is in
   this image, then give your reasoning, then the number." to "Give your reasoning first, then
   say where the goal is, then the number."
2. **The goal is "a glowing red sphere".** `p05`'s "with a tall red beam of light rising above
   it" is gone from the prompt, and the field's description no longer mentions a beam.

Everything else is `a03`: the code-written log (move plus goal report, no marker numbers, no
reasons), the log paragraph, and one model call per step. `a03`'s schema output is
byte-identical, and `a00`–`a03` and `p02`–`p05` keep their shas.

**These are two changes in one round, by the operator's choice.** The probe (below) measures their
joint effect on perception before flying. It cannot split their effect on flight.

## Evidence

From the [R3 summary](../R3_memory_log/summary.md) and its
[manipulation_check.md](../R3_memory_log/manipulation_check.md):

**1. The goal report put first stopped the model seeing the goal.**
- R1 and R3 have the same pose at steps 0–2 in all 18 cells, at temperature 0. In the 30
  decisions where the goal is in view, R1's reasons see it 30 times and R3 reports it 0 times.
  The log is still empty at step 0, so what differs is the field order and `p05`'s last line.
- All 1,040 `not_visible` reports open with a sentence saying the goal is not visible. The reason
  follows the field.
- Pooled, the goal is seen when visible in 20% of decisions (40 / 198, against a pre-registered
  ≥ 50%). It is never reported when it is not in view (0 / 882).

**2. The beam rules out a sphere up close.**
- Within 2–4 m the beam leaves the top of the frame. s03 `initial`, step 47: "a red sphere on
  the floor, but it does not have a tall red beam". At 2.5 m it turns around.
- s02a `initial` (2.3 m, step 19) and s01 `initial` (7.0 m, step 32) do the same.
- All six R3 `initial` runs came within 2.3–3.5 m of the goal (arrival radius 1.0 m), then
  turned away.

**3. The log works as a mechanism.** No lock-in (same pick 54% / 46% / 45%), no copied reasons
(0%), and the turn-around is used again. Where a sighting was logged, the model used it (s01
`initial`, step 50). What failed is what went into the log: "Goal: not visible" on every line in
13 of 18 runs.

**4. Baseline.** [evidence.md](evidence.md) is
`python eval/agent_evidence.py eval/phase2/R1_no_goal_hint`, the same table R3 cites.

| Measure, R1 (`a01`) | initial | final | dynamic |
|---|---|---|---|
| same pick | 77% | 56% | 53% |
| turn-around pick | 8% | 8% | 12% |
| revisit | 48% | 28% | 33% |
| goal visible (ground truth) | 55% | 6% | 9% |

## Hypothesis

If the goal report comes after the reason and the goal is described without a beam, the model
sees the goal at R1's rate. The log then carries real sightings, and the agent keeps R1's
successes and turns some of R1's `timeout` cells into successes.

## Predictions

Baseline: R0 (`a00`), with R1 (`a01`), the best round so far, alongside. R2 and R3 are shown for
reference.

| Arm | R0 | R1 | R2 | R3 | Predicted |
|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | 1/6 | 0/6 | 5/6. s03 stays failed. |
| final | 0/6 | 2/6 | 0/6 | 0/6 | ≥ 2/6. Keeps s02c and s02vc. |
| dynamic | 0/6 | 1/6 | 0/6 | 0/6 | ≥ 2/6. Keeps s02a. |

So `final` + `dynamic` ≥ 4/12, against R1's 3/12.
- The R3 close-range turn-aways (2.3–7 m) do not recur.
- There are fewer than R1's 5 `timeout` labels, and they do not turn into `collision` or
  `ignore_change` (R2's failure).
- s03 stays failed on all three arms (perception before the fork, `path_hallucination`).
- s02va `final` is unlikely to move.

## Manipulation check

Run `python eval/agent_evidence.py eval/phase2/R4_goal_after_reason` and compare it with
[evidence.md](evidence.md) (R1) and R3's
[manipulation_check.md](../R3_memory_log/manipulation_check.md).

- **Delivery:** every decision has `memory_steps` equal to the number of earlier valid decisions
  and carries a `goal` field. `prompt_tokens` rises by about 13 per step.
- **Perception:**
  - Goal seen when visible is ≥ 50%, pooled over all arms (R3: 20%).
  - Goal report agreement is above each arm's majority-class rate.
  - On the 30 early decisions matched on pose with R1, the goal is reported in ≥ 27.
- **Step 0 matches R1:** most of the 18 step-0 picks equal R1's (same pose, same frame,
  temperature 0). Option 1 named this check.
- **No lock-in:** same pick below 90% on every arm. Copied reason < 10%.
- **Use:** in runs that log a sighting, read whether later reasons use it, as R3 did at s01
  `initial` step 50. "Reason cites memory" is reported, not judged.

## Drop criterion

Drop `a04` (do not build on it) if any of these holds:
- `final` + `dynamic` ≤ 3/12 (no better than R1) while the log is delivered.
- `initial` ≤ 3/6.
- The lock-in returns: same pick ≥ 90% on `final` or `dynamic`.

Cost is recorded but is not a drop criterion: latency p50 / p95 (R1: ~1.4 / 1.8 s; R3: ~1.6 /
2.0 s) and `prompt_tokens` at step 60.

If perception passes and success does not move, the record is correct and the model does not act
on it. The next candidate is then collision feedback in the log (R3 README).

## Probe gate

The probe is required here, because R4 changes what the model is asked to perceive and report
(`docs/phase2-test-plan.md` §4 step 2). It runs before any flight, on `eval/goal_probe.py`.

**The frame set** is [probe/probe_set.jsonl](probe/probe_set.jsonl), committed with this write-up.
It holds 173 distinct frames out of 1,595 recorded in R1 and R3. The sample is deduplicated by
PNG hash and stratified with seed 0:

| Group | Frames |
|---|---|
| goal visible, under 5 m (every one there is) | 26 |
| goal visible, 5–10 m | 30 |
| goal visible, 10–20 m | 30 |
| goal visible, 20 m or more (every one there is) | 21 |
| goal not visible, 30 of them under 5 m | 66 |

The set also holds two forced subsets:
- the 30 `early` decisions, R1 steps 0–2 with the goal in view, which are the R3 summary's
  30 / 30 against 0 / 30;
- the 18 `step0` frames, which are byte-identical in R1 and R3.

Each frame goes in as step 0 with an empty log.

**Agents probed:**
- `a03`, the calibration. Its in-flight failure is known. If the probe gives it high
  detection, the probe does not reflect flight, and its result for `a04` means nothing.
- `a04`, the candidate.

| Check | Pass |
|---|---|
| Calibration: `a03`, `early` | ≤ 6 / 30 (R3 in flight: 0 / 30). Otherwise stop and look at the probe |
| `a04`, `early` | ≥ 27 / 30 (R1's reasons: 30 / 30) |
| `a04`, seen when visible, pooled | ≥ 50% (R3 in flight: 20%) |
| `a04`, seen when visible, under 5 m | ≥ 70% (R3 in flight: 7 / 14) |
| `a04`, false positives on not-visible frames | ≤ 10% (R3 in flight: 0%) |

Reported but not gated:
- `a03`'s step-0 report against R3's recorded step-0 report on the same frames (a replay check
  of the probe itself);
- `a04`'s step-0 pick against R1's;
- direction agreement among sightings;
- seen-when-visible by distance band;
- latency.

If every check passes, R4 flies. If any check fails, R4 does not fly: the Outcome records the
probe, and the next wording is a new prompt version, probed the same way.

## Builds on

`a03` (`p05`, sha `bec48dc3ef3b`) for the log plumbing (`Run.memory()`, `memory_steps`, the
`goal` field). `a01` (sha `48f6b3973760`), the best agent so far, is the baseline. `a03` itself
was dropped.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
