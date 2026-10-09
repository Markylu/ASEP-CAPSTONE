# R2: Text memory, full run

**Agent:** `a02` (`f53deb3d5b14`) · **Prompt:** `p04` (`d514fe7a2ded`) · **Status:** pre-registered, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

The agent now remembers the run. `a01` was stateless: every `/decide` sent one frame and the `p03`
text, and nothing from earlier steps reached the model (`server/decider/vlm.py`, `_messages`).
`a02` keeps `p03`'s wording and adds two things, together called `p04`:

- The user message lists every earlier step of this run, oldest first: `Step N: you picked [k]`
  (or `you turned around [0]`) followed by the reason the model gave at that step, verbatim. It is
  read back from the run's own `decisions.jsonl` (`Run.memory()`, `server/decider/recorder.py`),
  so the model sees exactly what was recorded. Failed decisions are skipped.
- One paragraph in the system prompt says the record is there, that marker numbers refer to the
  view at that step, and that the record can be used to avoid going back over covered ground and to
  remember where the goal was last seen.

Nothing else changes. The memory holds only text the model wrote itself. It carries no pose, goal
bearing or distance, and no collision feedback. Each decision records `memory_steps`, the number of
earlier steps it was shown.

**Why text and not images.** R1 showed that perception was not the gap on s01/s02. The model named
the cube, the closed door, the open door and the beam
([R1 summary](../R1_no_goal_hint/summary.md), "What the model did"). What it lacked was a record of
what it had already seen and done, and its reasons already contain that in words. An image costs
about 800 prompt tokens: R1's prompt was 922 tokens on every decision, image included. A reason
has a median of 139 completion tokens and a maximum of 379, so ten past frames cost about as much
as sixty past reasons. Past frames shown next to the current one also add a confound: the model
might act on a beam that is only in an old frame. A real drone link also favours text, because it
sends one frame per step and a text history is bytes, not megabytes.

**Why the whole run and not a buffer.** The horizons in R1 are long (Evidence 2), and the 60-step
limit keeps the full record bounded. The expected size at step 60 is about 60 × 139 ≈ 8k tokens,
and the worst case is about 23k. At step 31, s02va `dynamic`'s record is 17.6k characters. A
buffer, a summary, or past images can each be a later round, tested against this one.

## Evidence

**1. R1's open failure is losing the goal after finding the route.** All five R1 `timeout` runs
got through, came within 8–13 m of the goal, then flew back out the way they came. Two of them
ended further away than the 24 m they started at
([R1 summary](../R1_no_goal_hint/summary.md), "New failure"). The summary's "For the next round"
names memory of the route or of the last goal sighting as the candidate.

**2. The agent goes back over its own ground, on long horizons.** Read from
`eval/phase2/R1_no_goal_hint/runs/*/seed1/decisions.jsonl`:

| Run | steps where the reason says the beam is in view | closest → end distance |
|---|---|---|
| s01 `final` | 9, 25–26, 52–56 | 13.1 → 20.6 m |
| s02a `final` | 10 | 11.7 → 15.6 m |
| s02va `dynamic` | 26–27 | 12.8 → 26.4 m |
| s02vc `dynamic` | 17, 29–32 | 8.3 → 31.6 m |

Sightings are 15–30 steps apart. s02va `dynamic` crosses the same doorway three times between
steps 31 and 59. Each time it goes through, meets a wall, turns around (steps 40, 44, 49, 59) and
comes back. Its step-28 reason says it faces "a corner with no visible path forward", one step
after it "can see a tall red beam rising". A 5–10 step buffer would have dropped that sighting
before the loop began.

**3. Revisits, as a share of decisions.** [evidence.md](evidence.md) is
`python eval/agent_evidence.py eval/phase2/R1_no_goal_hint`. A decision counts as a revisit when
the drone is within 1 m of where it was at least 5 decisions earlier. R1's revisit rate is 28%
(`final`), 33% (`dynamic`) and 48% (`initial`). The `initial` figure is driven by s02va and s02vc
at 62% each: both succeed, but take 55 steps against R0's 19. Phase 1 scores 76–77% on
`final`/`dynamic`, but there the drone was pinned against an obstacle rather than wandering. Read
the column next to the collisions.

**4. The model does not refer back on its own.** "Reason cites memory" is 1–2% in R1
([evidence.md](evidence.md)). With no record in the prompt, it has nothing to refer back to.

## Hypothesis

R1's agent loses the goal and re-covers ground because it keeps nothing between steps. With its own
earlier picks and reasons for the whole run in the prompt, it will stop doubling back and keep
heading for where it last saw the goal, so some of R1's `timeout` cells become successes.

## Predictions

Baseline: R0 (`a00`), with R1 (`a01`), the best round so far, alongside
(`eval/phase2/results/results.md`).

| Arm | R0 | R1 | Predicted |
|---|---|---|---|
| initial | 5/6 | 5/6 | 5/6. s03 stays failed. s02va/s02vc reach the goal in fewer than R1's 55 steps. |
| final | 0/6 | 2/6 | ≥ 3/6. Keeps s02c and s02vc. Gains s01 or s02a, both `timeout` in R1. |
| dynamic | 0/6 | 1/6 | ≥ 2/6. Keeps s02a. Gains from s02c (most likely: it was 9.1 m out and closing when the step limit hit), s02va or s02vc. |

So `final` + `dynamic` ≥ 5/12, against R1's 3/12. Fewer than R1's 5 `timeout` labels.

By site: s03 stays failed on all three arms. Its failure includes `path_hallucination`, which is
perception, and the goal is never in line of sight before the fork, so there is no sighting to
remember. s02va `final` (`replan_failure`, never crossed the wall in R1) is unlikely to move.

## Manipulation check

Run `python eval/agent_evidence.py eval/phase2/R2_text_memory` and compare it with
[evidence.md](evidence.md):

- Delivery: on every decision, `memory_steps` equals the number of earlier valid decisions, and
  `prompt_tokens` rises with the step.
- Use: "reason cites memory" rises clearly above R1's 1–2% after the first few steps.
- Effect on behaviour: the revisit rate on `final`/`dynamic` falls below R1's 28% / 33%.
- Watch for perseveration: reasons copied word for word from earlier steps, or the same pick held
  because the record shows it. Read the reasons in any run where revisits do not fall.

If delivery and use pass and success does not move, the model has the record but does not act on
it.

## Drop criterion

Drop `a02` (do not build on it) if any of:
- `final` + `dynamic` ≤ 3/12 (no better than R1) while the manipulation check shows use.
- `initial` ≤ 3/6.
- The revisit rate on `final`/`dynamic` does not fall below R1's.

Cost is recorded but is not a drop criterion: latency p50/p95 (R1: 1.30–1.44 / 1.71–1.84 s) and
`prompt_tokens` at step 60.

## Preflight addition

Before flying, read the served context length (`max_model_len` from the provider's `/v1/models`,
through the operator's tunnel). It must be at least 32k tokens. If it is shorter, stop: a buffer or
a cap is a different agent.

## Builds on

R1 / `a01` (`p03`, sha `48f6b3973760`).

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to
[summary.md](summary.md).
