# R32 / R32P: a49 and a66 on the ten contested cells, three seeds each

**Agents:** R32 `a49` (`83f7a6a19b01`), R32P `a66` (`de7f23d07186`) · **Prompt:** `p17`
(`cb3578251cfe`) · **Status:** laid out 2026-11-04 on the operator's instruction ("Set up R32"),
not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Comes from
[docs/research/r30-analysis-and-proposals.md](../../../docs/research/r30-analysis-and-proposals.md),
P5. R32P's folder holds its runs, labels and summary; this README covers both, as R25's did for R25D.

## Change

No agent change. The protocol: which cells a screening round flies, and how often.

- **Cells.** The ten contested cells only: s02a, s02c, s02va, s02vc and s03, `final` and
  `dynamic` (`CONTESTED_SITES`, `CONTESTED_ARMS` in `eval/phase2.py`). The other eight (s01 ×3,
  s02 `initial` ×4, s03 `initial`) are left out.
- **Seeds 1, 2 and 3** per cell (`REPEAT_SEEDS`): 30 runs per agent, 60 in all. Seed 1 is the
  cell every round so far flew; seeds 2 and 3 are the design's own repeats (P1 §5, the final
  flies 1–5). In s03 `final` the closed exit is tine L on odd seeds and tine R on even, so the
  first-tine coin flip is tested both ways.
- **Two agents, same host, same time:** `a49` (R25D, 14/18) and `a66` (R30, 14/18), four lanes
  each on `:8004`, as R25 flew beside R25D. The runner takes `arms` and `seeds` per round;
  `results.md` reads a multi-seed cell as k/3 (`eval/phase2.py`, `cells()`).

## Evidence

- Over the last 14 rounds (R19–R30) eight cells were solved 14 of 14 times and s03 `initial`
  11 of 14; the ten contested cells were solved 50 of 140 (36%)
  ([r30-analysis-and-proposals.md](../../../docs/research/r30-analysis-and-proposals.md) §2).
  A round's total moves only on those ten.
- R25D and R30 both scored 14/18 on seed 1; the `a17b` family expects 11.3 ± 1.4 per 18, and
  P(≥ 14) is about 3% for one round ([why_14.md](../R25D_door_confirmer_open_near_unwalled/why_14.md)).
  The step-0 perceiver read differed between the two rounds in 16 of 18 cells on a lane alone
  (R30 README): each run is a fresh draw. Two 14s on one seed cannot say which agent is better.
- The planner's one structural win (R30 s03 `final`: tine R first after an early closed read of
  door L) and its two losses (s02a `dynamic`, s02vc `final`) are each one run.

## Hypothesis

One of `a49` and `a66` solves more of the 30 contested runs than the other by at least 3, the
difference the family's noise (±1.4 per 18, about ±1.8 per 30) does not reach.

## Predictions

From the per-cell rates of R19–R30 (wins of 14), both agents sit at 10–12 of 30. Where they
should differ:

| Cell | R19–R30 rate | `a49` (R32) | `a66` (R32P) | Why |
|---|---|---|---|---|
| s03 `final` ×3 | 5/14 | 1 | 2 | the route takes the open tine when d01 reads the shut door early; seed 2 puts the shut door on R |
| s03 `dynamic` ×3 | 0/14 | 0 | 0 or 1 | never solved; the recovery needs ~44 of 60 steps |
| s02a `dynamic` ×3 | 3/14 | 1 | 1 | both relearn door B badly |
| s02vc `final` ×3 | 5/14 | 1 | 1 | wrong side first is a coin flip for both |
| s02va `final` ×3 | 2/14 | 0 | 0 | family-hard |
| the other five cells ×3 | 7–10/14 | 7–9 | 7–9 | |

Totals: `a49` 10–12, `a66` 10–13. A gap of 3 or more either way is the result; under 3 the
two are the same agent for the final's purpose.

## Decision rule (written before flying)

The final 90 flies the agent with more solved runs of 30. On a tie or a gap under 3: `a66` if
it solved more s03 runs (the planner's cell, the one the final's s03 `final` seeds 2 and 4 will
test with the shut door on R), otherwise `a49` (fewer parts).

## Manipulation check

- Every `run.json` in R32 carries `agent_version` a49 and `agent_sha` `83f7a6a19b01`; in R32P
  a66 and `de7f23d07186`.
- Both rounds flown at the same time on the same instance, four lanes each, `phase.json` "lanes"
  filled in for both.
- s03 `final` seed 2: `final_closed` is BranchR in `run.json`.
- Walls in flight (`eval/r28_flight.py`) within 4 points of R25D's 17.3% / 12.7% for both.

## Drop criterion

Nothing is carried or dropped from an agent. The protocol change stands for any later screening
round that compares two agents.

## Probe gate

Not needed: no change to what the model is asked.

## Builds on

R30 (`a66`) and R25D (`a49`), unchanged. Branch `phase2/r31-two-pose-commit` (R31 laid out, not
flown; R32 follows it on the same branch).

## Notes for the operator

- **Host.** 60 runs, 8 lanes on `:8004`: about 40 min (R25 + R25D: 36 runs in 24 min on 8 lanes).
  Nothing else on the instance. GPU limit unchanged (one instance).
- **Lanes.** `sh ~/round_lane.sh k 4 ~/asep-r32-lk a49 83f7a6a19b01 R32 R32_repeat_a49` and
  `sh ~/round_lane.sh k 4 ~/asep-r32p-lk a66 de7f23d07186 R32P R32P_repeat_a66`, k = 1..4 each;
  every lane's `/health` reports its agent's sha.
- **Preflight.** Clean tree, `python eval/phase2.py init` says nothing, tunnel up (yours).
- **After.** Validity (§10) on all 60; `python eval/phase1_label.py --round R32` and `R32P`;
  labels; `eval/r28_flight.py`; one summary in this folder covering both rounds and the decision
  rule's outcome; `python eval/phase2.py results`.

## Outcome

Not flown.
