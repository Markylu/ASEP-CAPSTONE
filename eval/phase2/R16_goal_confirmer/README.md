# R16: R14 with a goal confirmer (a27; R16K flies a28 beside it)

**Agent:** `a27` (`fb202659aeaf`) · **Navigator prompt:** `p14` · **Perceiver:** `g05` (map as
`a22`) · **Goal confirmer:** `c01` (`5b3eb45ce241`, new subagent) · **Strategist:** `q04` ·
**Status:** pre-registered 2026-10-29, built overnight without the operator (operator,
2026-10-28: "maintain a preference for subagents over hard coded tasks").

Second agent at the same SHA: **R16K**, `a28` (`8128af346342`) = `a25` (R15, known goal) with `c01`;
[R16K's README](../R16K_known_goal_confirmer/README.md). R16 was laid out while R14 flew and R16K
while R15 was queued: each line moves on before its previous round is read.

## Change against `a22` (R14)

1. **Goal confirmer `c01`**, a new subagent. When the perceiver reports the goal in a strip, a
   second call looks at the same clean frame with one question: is a glowing red sphere in that
   strip (or next to it)? It is told such reports are often wrong and what is not the goal (red
   marks, labels, door frames, reflections, flat things). A "no" removes the report
   (`goal: not_visible`, kept as `goal_reported`) before the map, the stages, the projector and
   the navigator read it; a failed call keeps it. Recorded as `confirmer`.
2. **Verify's check look** counts within 2.6 m of the vantage (`verify_budget.check_within_m`),
   not 1.5 m.

## Evidence

- R13 failure analysis ([../R13_verify/failure_analysis.md](../R13_verify/failure_analysis.md)):
  of 26 losses of sight in R13/R13G, 21 rested on hallucinated goal reports and 4 on a stale
  frame at a door switch; 1 was genuine. 5 of 8 verify timeouts reached the vantage but could not
  face the seen bearing inside 1.5 m (facing it takes a 1.7 m move).
- R11 failure analysis §0: 10 of 14 "goal in view" hand-backs were hallucinated.
- Confirmer probe (gate 1 below, [probe/score.txt](probe/score.txt)): of 527 recorded goal
  reports in R11–R13G, 454 genuine and 73 false by the site model; `c01` kept 433/454 genuine
  (95.4%) and refused 53/73 false (72.6%), 0 failed calls. **Gate passed.**

## Hypothesis

With most false goal reports refused, the drone stops chasing and verifying goals that are not
there, so `final`/`dynamic` rise above R14.

## Predictions

| Measure | R14 (`a22`) | R16 |
|---|---|---|
| total | see R14's Outcome | ≥ R14 + 1 |
| goal reports refused that were genuine (scored by `in_view`) | | ≤ 5% |
| verify episodes from false reports | | ≤ 1/3 of R14's |
| verify timeouts at the vantage without a check | | 0 |

## Drop criterion

Not carried forward if it does not beat R14. The confirmer is carried forward on its own if the
probe and the flight both keep ≥ 95% of genuine reports.

## Probe gate

1. **Confirmer, live** (`eval/r16_confirm_probe.py`, on the flight host): `c01` on every recorded
   goal report of R11, R12, R13 and R13G (527), scored against the site model (`r12_probe.in_view`).
   Gate: genuine kept ≥ 90%, false refused ≥ 50%.
2. **Smoke** (stub replies, the confirmer refusing every other report): `a27` on R13's 881
   manifests and `a28` on R12's 862: 0 failed steps; every refusal sets the perceiver's goal to
   `not_visible`.
3. `eval/r13_probe.py transitions`: PASS (verify unchanged without `check_within_m`).

## Host

sctsvr6, 8 lanes, the existing vLLM on :8004 (one H100). The confirmer adds one call on steps with
a goal report only.

## Outcome

Not flown.
