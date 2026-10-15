# R5: Goal identifier, sighting age

**Agent:** `a05` (`7e9a54f898bc`) · **Prompt:** `p07` (`fc7175f7b803`) · **Identifier prompt:** `g01` (`46df663da25f`) · **Status:** pre-registered, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

R5 splits seeing the goal from navigating. The operator chose the goal identifier, and added option 2
from the [R4 summary](../R4_goal_after_reason/summary.md) as a second change:

1. **A goal identifier.** Each step makes a second model call before the navigator's, with
   prompt `g01`. It gets the current frame and nothing else: no log, no step number, no actions.
   Its only job is to say whether the goal (a glowing red sphere) is in the image, and where. It
   replies `reason`, then `goal` (`ahead | left | right | not_visible`), in the order that saw the
   goal in R4. The navigator (`p07`) is given that answer for this image and no longer reports the
   goal itself: its reply is `reason`, `action`, as in `a01`.
   - Code: `vlm.identify_goal()`, `schema.identifier_schema()`, feature `goal_identifier`.
   - The identifier's report is recorded as the decision's `goal`, so the log, the labeller's goal
     facets and `agent_evidence.py` read it where they read `a03`/`a04`'s field. The full reply is
     in `goal_identifier`.
2. **Sighting age in the log.** The log lists moves only. Instead of "Goal: X" on every line, one
   line written by code gives the last step the identifier saw the goal, the direction then, and
   the number of moves and the net turn since. The net turn comes from the executed commands,
   never from ground truth. For example: "Last goal sighting: step 12, ahead (relative to the way
   the drone faced then). Since then: 5 moves, net turn 180 degrees (now facing the opposite
   way)."

Everything else is `a04`: the move log, its "what happened, not a plan" framing, the sphere wording
and the reason-first navigator.
- `a00`–`a04` and `p02`–`p06` keep their shas.
- Their requests are byte-identical on all four rungs after the shared-ladder refactor in
  `vlm.py`.
- `agent_sha` also hashes `g01`'s sha, so the identifier's wording is part of the agent.

**These are two changes in one round, by the operator's choice.** The probe (below) measures each
one's precondition before flying, but cannot split their effect on flight.

**Cost:** two calls per step. Expect latency p50 near 2.8 s per step (R4: ~1.56 s) and a round
of about 55–60 min (R4: 39).

## Evidence

From the [R4 summary](../R4_goal_after_reason/summary.md), its
[manipulation_check.md](../R4_goal_after_reason/manipulation_check.md) and its
[probe/probe.md](../R4_goal_after_reason/probe/probe.md):

**1. Without a log, the model is close to a perfect goal detector.** On 173 recorded frames, each
sent as step 0 with an empty log, `a04` saw the goal in 107 / 107 frames where it was visible (all
four distance bands at 100%). It reported it in 1 / 66 frames where it was not. In flight, at
steps 0–2 (log empty or nearly so), it saw it in 30 / 30.

**2. With the log, the same model invents the goal.**
- In flight, `a04` reports the goal in 342 / 781 decisions with the goal out of view (44%):
  143 / 204 `initial`, 12 / 263 `final`, 187 / 314 `dynamic`.
- 272 of those 342 reasons cite the log ("the goal consistently reported as ahead", s01
  `dynamic`, step 31, with the goal 168° behind).
- Goal report agreement falls below the majority class on `initial` and `dynamic`.

The perception is there; the log overrides it. An identifier that never sees the log cannot be
overridden by it.

**3. "Goal: ahead" is read in the current heading.** Directions in the log are relative to the
heading at each step, and the model reads them as relative to now.
- s02a `initial` turns around 7.1 m from the goal at step 18, then flies east from step 19 with
  the goal behind it (bearing −171 to −176).
- s02vc `final`, step 55: "the log indicates it has been visible and ahead for several steps
  (from Step 44 onward)".

A line stating the sighting's age and the turn since spells this out.

**4. The phantom drives the failures.**
- 8 of R4's 13 failed runs carry the phantom facet of `failed_goal_identification`.
- Collisions rose to 101 (R3: 41), 28 of them in s01 `dynamic` against a wall while "the goal is
  still reported as ahead".

**5. The empty-log probe missed this.** It gave `a04` 1 / 66 false positives against flight's
44%. The R4 summary asks for a probe with the log in place. R5 adds one (Probe gate).

**6. Baseline.** [evidence.md](evidence.md) is `python eval/agent_evidence.py
eval/phase2/R1_no_goal_hint`, as in R3 and R4.

## Hypothesis

If the goal is reported by an identifier that sees only the current frame, and the log gives the
last sighting with its age and the turning since, the navigator no longer invents or misses the
goal. It keeps R1's `initial` successes and beats R1 on `final` + `dynamic`.

## Predictions

Baseline: R0 (`a00`). R1 (`a01`) is the best round so far and is shown alongside; R4 is the round
this one repairs.

| Arm | R0 | R1 | R4 | Predicted |
|---|---|---|---|---|
| initial | 5/6 | 5/6 | 2/6 | 5/6. s03 stays failed. Back on s01, s02a and s02c (lost to phantoms in R4). |
| final | 0/6 | 2/6 | 2/6 | ≥ 2/6 |
| dynamic | 0/6 | 1/6 | 1/6 | ≥ 2/6 |

So `final` + `dynamic` ≥ 4/12, against 3/12 for both R1 and R4.
- Phantom goal: the facet holds in at most 2 failed runs (R4: 8).
- Collisions fall below R4's 101.
- s03 stays failed on all three arms (perception before the fork, `path_hallucination`).
- Close-range losses (s02c in R4, closest approach 1.4 m) may remain. The identifier does not
  change how the drone moves near the goal.

## Manipulation check

Run `python eval/agent_evidence.py eval/phase2/R5_goal_identifier` and compare with
[evidence.md](evidence.md) (R1) and R4's
[manipulation_check.md](../R4_goal_after_reason/manipulation_check.md).

- **Delivery:**
  - every valid decision has a `goal_identifier` record and a valid `goal` (identifier failures
    are counted);
  - `memory_steps` equals the number of earlier valid decisions;
  - the navigator's reply has no `goal` field.
- **Identifier, in flight:**
  - goal seen when visible ≥ 90%, pooled;
  - goal reported when not in view ≤ 10% of out-of-view decisions (R4: 44%);
  - goal report agreement above each arm's majority-class rate (R4 failed this on `initial` and
    `dynamic`).
- **Navigator, in flight:** of out-of-view decisions, the share whose reason places the goal
  around the drone now (`claims_goal()`) is ≤ 10%. Under the same measure, R4 scores 155 / 781
  (20%).
- **Step 0 matches R1:** most of the 18 step-0 picks equal R1's.
- **No lock-in:** same pick below 90% on every arm. Copied reason < 10%.
- Reported, not judged:
  - reason cites memory;
  - turn-around pick;
  - revisit;
  - identifier latency against navigator latency.

## Drop criterion

Drop `a05` (do not build on it) if any of these holds:
- `final` + `dynamic` ≤ 3/12 (no better than R1) while the identifier is delivered.
- `initial` ≤ 3/6.
- The lock-in returns: same pick ≥ 90% on `final` or `dynamic`.

Cost is recorded but is not a drop criterion.

If the identifier passes its check and the navigator still places the goal where it is not, the
navigator is overriding a correct report, and moving perception out of the call did not help. If
both pass and success does not move, the record is correct and the model does not act on it. The
next candidate is then collision feedback in the log (R3 README).

## Probe gate

The probe is required, because R5 changes what the model is asked to perceive and report
(`docs/phase2-test-plan.md` §4 step 2). It has two parts, both in `eval/goal_probe.py`, and runs
before any flight.

**Part 1, the identifier on single frames.** The frame set is R4's
[probe_set.jsonl](probe/probe_set.jsonl), copied unchanged: 173 frames, with the `early` 30 and
the `step0` 18. The identifier never sees a log, so a single frame is exactly its in-flight
condition. That was not true of R4's navigator. `run --agent a05` scores `identify_goal()`'s
report and asks the navigator for the step-0 pick.
- [probe_a04.jsonl](probe/probe_a04.jsonl) is R4's answers, copied for comparison and not re-run.
- `a04`'s probe result matched its in-flight perception when the goal was in view (107 / 107
  against 175 / 179). It needs no calibration here.

**Part 2, the navigator with a log in place.** [replay_set.jsonl](probe/replay_set.jsonl) comes from
`sample-replay eval/phase2/R4_goal_after_reason`, seed 0. Each row is a recorded R4 decision with
the log that `a04` had at that step (`Run.memory()`). There are 60 frames:

| Group | Frames | Pool | R4's reasons placed the goal now, in flight |
|---|---|---|---|
| goal out of view, sighting 5–20 steps old, turned < 90° since | 20 | 84 | 7 / 20 (pool 31 / 84) |
| goal out of view, sighting 5–20 steps old, turned ≥ 90° since | 20 | 96 | 6 / 20 (pool 35 / 96) |
| goal in view, earlier sighting in the log (control) | 20 | 133 | 19 / 20 |

`run-replay` sends each frame at its recorded step:
- **`a04` (calibration)** gets its recorded log. If the replay does not reproduce its in-flight
  phantom claims, the replay does not reflect flight, and its result for `a05` means nothing.
- **`a05` (candidate)** gets a log whose goal entries are ground truth, which is what a perfect
  identifier would have written. Its identifier answers the current frame live, then the
  navigator answers.

Both are scored on the same instrument: does a sentence of the navigator's reason place the goal
in view or in a direction now (`claims_goal()`, `eval/agent_evidence.py`)?
- Negated, backward-looking and conditional sentences do not count.
- Checked on R4's recorded reasons, it flags 1 / 439 out-of-view decisions where the reason and
  the field both say not visible, and 155 / 179 in-view decisions.
- In a random 25 of the flagged out-of-view R4 decisions, read by hand, 23 placed the goal
  around the drone now, mostly "Since the goal is still reported as ahead … continue forward".
  The other 2 were conditionals, which are now excluded.

| Check | Pass |
|---|---|
| `a05` identifier, `early` | ≥ 27 / 30 (`a04` probe: 30 / 30) |
| `a05` identifier, seen when visible, pooled | ≥ 90% (`a04` probe: 100%) |
| `a05` identifier, seen when visible, under 5 m | ≥ 90% (`a04` probe: 26 / 26) |
| `a05` identifier, false positives on not-visible frames | ≤ 5% (`a04` probe: 1 / 66) |
| Calibration: `a04` replay, reason places the goal now, out of view | ≥ 25% (in flight on these 40: 13 / 40). Otherwise stop and look at the probe |
| `a05` replay, reason places the goal now, out of view | ≤ 10% |

Reported but not gated:
- identifier direction agreement;
- the navigator's step-0 pick against R1's;
- the replay split by turn since sighting;
- the in-view control;
- the latency of both calls.

`python eval/goal_probe.py report eval/phase2/R5_goal_identifier/probe --gate R5 --calibration
a04 --candidate a05`.

If every check passes, R5 flies. If any fails, R5 does not fly: the Outcome records the probe, and
the next wording is a new prompt version, probed the same way.

## Builds on

- `a04` (`p06`, sha `a90e249c14a1`): the move log, the sphere wording and the reason-before-goal
  order, now used by the identifier. `a04` itself was dropped.
- `a01` (sha `48f6b3973760`), the best agent so far, is the baseline.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
