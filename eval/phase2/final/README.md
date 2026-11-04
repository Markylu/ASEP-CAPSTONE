# F: Final round, a66 on the full design

**Agent:** `a66` (`de7f23d07186`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `planner.pathfind`
(`PATHFINDER_A65`) · **Status:** laid out 2026-11-04 on the operator's instruction ("Fly the
final"), not flown

Written before flying. Spec: `docs/phase2-test-plan.md` §6 and P1 §5–§7. **Citable.**

## Change

None. The agent chosen by the screening rounds, frozen: `a66`, R30's agent (R25D's `a49` with a
code route planner in place of the goal-way test and the detour strategist; memory `a17f`).
Chosen by R32's decision rule, written before R32 flew: on the ten contested cells with three
seeds each, `a66` 15/30 against `a49` 11/30, a gap of 4 at the rule's threshold of 3
([R32 summary](../R32_repeat_a49/summary.md)).

The design is Phase 1's (P1 §5–§7): six sites × three arms × seeds 1–5 = 90 runs, one SHA,
order `random.Random("phase2-F")`, validity P1 §10, rubric P1 §9 with Phase 2's tags. Phase 2's
lock (§2) plus the agent fields. s03 `final`: the shut exit is tine L on odd seeds, tine R on even.

## Evidence

- Phase 1 (`a00`, `p02`): 25/90, `initial` 25/30, `final` 0/30, `dynamic` 0/30
  (`eval/phase1/results/results.md`).
- Screening, seed 1: R25D (`a49`) and R30 (`a66`) 14/18; the `a17b` family 11.3 ± 1.4
  ([why_14](../R25D_door_confirmer_open_near_unwalled/why_14.md), [R30](../R30_pathfinder/summary.md)).
- Repeat screen R32/R32P: `a66` 15/30 on the contested cells, s03 `final` 3/3 (the open tine
  taken every time, seed 2 with the shut door on R), s03 `dynamic` 0/3, s02 12/24
  ([summary](../R32_repeat_a49/summary.md)). The eight settled cells were solved in 14 of the
  last 14 screening rounds; s03 `initial` in 11 of 14.

## Hypothesis

`a66` closes most of Phase 1's gap on `final` and part of it on `dynamic`, and reaches the
proposal's stretch goal, at least 50% on every layout, on all three.

## Predictions

From R32P's cell rates (contested cells) and the screening record (settled cells):

| Arm | Phase 1 (`a00`) | Predicted `a66` | Where it comes from |
|---|---|---|---|
| initial | 25/30 | 28–30 | s01, s02 ×4 solved every round; s03 `initial` about 4 of 5 |
| final | 0/30 | 18–21 | s01 5; s02 ×4 about half (R32P 6/12); s03 4–5 of 5 (R32P 3/3) |
| dynamic | 0/30 | 13–17 | s01 5; s02 ×4 about half (R32P 6/12); s03 0 (0/47 in Phase 2) |
| total | 25/90 | **59–68** | |

Per layout (15 runs each): s01 15; s02a, s02c, s02va, s02vc 9–11 each (60–73%); s03 8–10 (53–67%).
The stretch goal holds on every layout if s03 `final` repeats R32P's rate; it fails on s03 if
s03 `final` drops to R19–R30's 5/14.

## Manipulation check

- Every `run.json` carries `agent_version` a66, `agent_sha` `de7f23d07186`, one `git_sha`.
- `planner` record with a route on ≥ 95% of steps; "toward your target" taken on ≥ 70% of
  forward offers (`eval/r30_check.py`); walls in flight within 4 points of R30's 18.5% / 11.1%
  (`eval/r28_flight.py`).
- s03 `final` seeds 2 and 4: `final_closed` BranchR; seeds 1, 3, 5: BranchL.

## Drop criterion

None: the final is the measurement. Its results are the Phase 2 results, whatever they are.

## Probe gate

Not needed: no change to the agent.

## Builds on

R30 (`a66`), chosen over R25D (`a49`) by R32. Branch `phase2/final` from `phase2/r31-two-pose-commit`
(`988036a`); PR against it, never merged; tip tagged `phase2-complete` after the round.

## Notes for the operator

- **Host.** 90 runs, eight lanes on `:8004`, one round: `sh ~/round_lane.sh k 8 ~/asep-final-lk a66
  de7f23d07186 F final`, k = 1..8. About 8 min per run under eight lavapipe Godots: 90–100 min.
- **Preflight.** Clean tree at the flight SHA, `python eval/phase2.py init` says nothing, every lane's
  `/health` reports `de7f23d07186`, tunnel the operator's.
- **After.** Validity on all 90; `python eval/phase1_label.py --round F`; labels; `summary.md`;
  `python eval/phase2.py results` (§11 tables, contrasts, Phase 1 vs Phase 2 per cell);
  `phase.json` complete; tag `phase2-complete`.

## Outcome

Not flown.
