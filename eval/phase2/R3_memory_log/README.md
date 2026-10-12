# R3: Memory log, code-written

**Agent:** `a03` (`bec48dc3ef3b`) · **Prompt:** `p05` (`dda9d66652d5`) · **Status:** pre-registered, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

R3 builds on `a01`, not `a02`. R2's verbatim memory is dropped
([R2 summary](../R2_text_memory/summary.md)). R3 keeps R2's idea of giving the agent a record of
the whole run, but changes what goes in it and who writes it. `a03` is `a01` plus three things,
which together are `p05` and one reply field:

1. **A log written by code.** The user message lists every earlier step of this run, oldest
   first, one line each:

   ```
   Log of your earlier steps (what happened, not a plan):
   Step 25: flew straight. Goal: not visible.
   Step 26: flew slight left. Goal: ahead.
   ```

   - The **move** is read from the chosen action's heading in the stored manifest: straight,
     slight left or right (±21.75°), sharp left or right (±43.5°), or turned around (`_move`,
     `server/decider/prompt.py`). It states the command that was executed, so the model cannot
     misreport it.
   - There are **no marker numbers**. A marker's meaning changes with every view.
   - There are **no reasons**, so there is no prose to copy forward.
2. **A goal report in the reply.** The reply schema gains `goal: ahead | left | right |
   not_visible`, declared before `reason`, so the model states what the current frame shows before
   it argues (`schema.action_schema(..., goal=True)`; text rung: a `GOAL:` line). The log shows
   this report, so the record carries where the goal was last seen. It is still the model's own
   claim and carries no ground truth. A missing or invalid report never fails a decision; the log
   then shows "not reported".
3. **One paragraph in the system prompt** says what the log is:
   - It is kept by the system and is a record, not a plan.
   - Its directions are relative to the heading at that step.
   - The current image outranks it.
   - A move should be repeated only while the image shows it still works.
   - Turning around is a normal move when the way ahead is blocked.
   - The log can be used to remember where the goal was last seen and to avoid covered ground.

   The last line becomes "First say where the goal is in this image, then give your reasoning,
   then the number."

Nothing else changes. There is no pose, no collision feedback, no goal bearing, and one model call
per step. Each decision records `memory_steps` (as in R2) and `goal`.

**Compute.** One log line is about 12 tokens, so at most about 700 tokens at step 60. A step-30
log from R1's s02va `dynamic` is 1,491 characters. That puts the prompt near R1's 922 tokens plus
the log, against R2's 8.8k median at step 60. The goal field adds about 5 output tokens.

**What the agent still cannot do.** The log is relative moves in the drone's own frame. The agent
has no coordinates, so "avoid covered ground" needs dead reckoning in the model's head. A pose
readout would be a separate round.

## Evidence

**1. R1's open failure is losing the goal after finding the route.** All five R1 `timeout` runs
got through and came within 8–13 m, then flew back out. Beam sightings in the reasons are 15–30
steps apart ([R2 README](../R2_text_memory/README.md), Evidence 1–2). This is the gap R2 targeted,
and it is still open.

**2. R2's memory form drove a lock-in, not its content.** From R2's
[manipulation_check.md](../R2_text_memory/manipulation_check.md) and summary:

- 97% of picks are the same as the step before (R1: 60%).
- 62% of reasons are copied word for word from the step before (R1: 0%).
- 0 turn-arounds in 1034 decisions (R1: 8–12%).
- 17 of 18 runs settle on one marker by step 9.

The reasons count streaks in marker numbers: s01 `dynamic` step 40, "using marker 3 for 38
consecutive steps". They also copy false history forward. s01 `final` repeats "turning left at
each step" from step 5 to step 59 while it picks `[3]`. s03 says "I have already explored the left
path extensively" after 4 left picks. Each of these needs a marker number or a free-text reason in
the record. `p05`'s log carries neither.

**3. The record overrode the frame.** In R1, s02va and s02vc `dynamic` read the door switch at
step 4. In R2 all four s02 `dynamic` runs fly `[3]` into the closed middle door, 49–54 collisions,
with reasons like "The environment has not changed" (s02va, step 20). 12 of 18 R2 runs are tagged
`path_hallucination` ([R2 labels](../R2_text_memory/labels.csv)). Hence the goal report comes
first and the prompt says the image outranks the log.

**4. Baseline for the new columns** ([evidence.md](evidence.md) is
`python eval/agent_evidence.py eval/phase2/R1_no_goal_hint`):

| Measure, R1 (`a01`) | initial | final | dynamic |
|---|---|---|---|
| same pick | 77% | 56% | 53% |
| copied reason | 0% | 0% | 0% |
| turn-around pick | 8% | 8% | 12% |
| revisit | 48% | 28% | 33% |
| goal visible (ground truth) | 55% | 6% | 9% |

On `final` and `dynamic` the goal is in view on fewer than 1 decision in 10. A report of
`not_visible` on every step would agree with ground truth 91–94% of the time. Agreement alone is
therefore a weak check, and seen-when-visible is the one that matters (below).

## Hypothesis

The model can use a record of its own moves and goal sightings when the record is factual,
compact and framed as history: it keeps R1's reading of the frame and gains the persistence R1
lacked, so some of R1's `timeout` cells become successes.

## Predictions

Baseline: R0 (`a00`), with R1 (`a01`), the best round so far, alongside
(`eval/phase2/results/results.md`). R2 is shown for reference.

| Arm | R0 | R1 | R2 | Predicted |
|---|---|---|---|---|
| initial | 5/6 | 5/6 | 1/6 | 5/6. s03 stays failed. |
| final | 0/6 | 2/6 | 0/6 | ≥ 2/6. Keeps s02c and s02vc. Gains come from R1's `timeout` cells (s01, s02a). |
| dynamic | 0/6 | 1/6 | 0/6 | ≥ 2/6. Keeps s02a. Gains come from R1's `timeout` cells (s02c, s02va, s02vc). |

So `final` + `dynamic` ≥ 4/12, against R1's 3/12. There are fewer than R1's 5 `timeout` labels,
and they do not turn into `collision` or `ignore_change` the way R2's did.

By site: s03 stays failed on all three arms (perception, `path_hallucination`; the goal is never
in line of sight before the fork). s02va `final` (never crossed the wall in R1) is unlikely to move.

## Manipulation check

Run `python eval/agent_evidence.py eval/phase2/R3_memory_log` and compare it with
[evidence.md](evidence.md) (R1) and R2's
[manipulation_check.md](../R2_text_memory/manipulation_check.md):

- **Delivery:** every decision has `memory_steps` equal to the number of earlier valid decisions
  and carries a `goal` field. `prompt_tokens` rises by about 12 per step, not R2's ~140.
- **Perception:** goal seen when visible ≥ 50%, pooled over all arms. Goal report agreement is
  above each arm's majority-class rate (1 − goal visible). This also gives Phase 2 its first
  direct measure of whether the model sees the goal.
- **No lock-in:** same pick stays near R1's 53–56% on `final`/`dynamic`, and below 90% on every
  arm. Copied reason < 10%.
- **Behaviour:** the turn-around is picked again (R1: 8–12%; R2: 0%). The revisit rate on
  `final`/`dynamic` falls below R1's 28% / 33%.
- **Use:** read the reasons in any run where revisits do not fall. "Reason cites memory" is raw
  keyword hits; in R2 most hits were streak counting, so it is reported, not judged.

If delivery and perception pass and success does not move, the model has a correct record and does
not act on it.

## Drop criterion

Drop `a03` (do not build on it) if any of:
- `final` + `dynamic` ≤ 3/12 (no better than R1) while the log is delivered.
- `initial` ≤ 3/6.
- The lock-in returns: same pick ≥ 90% on `final` or `dynamic`.

Cost is recorded but is not a drop criterion: latency p50/p95 (R1: ~1.4 / 1.8 s; R2: 1.5 / 2.4 s)
and `prompt_tokens` at step 60.

If R3 fails with the log in use, the next candidates, in order, are collision feedback ("hit
something" as a fact in the log) and a short buffer. Both build on `a01` or `a03`, depending on
what R3 shows.

## Builds on

R1 / `a01` (`p03`, sha `48f6b3973760`). Uses R2's memory plumbing (`Run.memory()`,
`memory_steps`); `a02` itself is dropped.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
