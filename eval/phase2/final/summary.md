# F: a66 on the full design, 90 runs: summary

**64/90 (71%): `initial` 30/30, `final` 17/30, `dynamic` 17/30. Phase 1 (`a00`): 25/90,
`initial` 25/30, `final` 0/30, `dynamic` 0/30.** The README predicted 59–68 and the round landed
64: `initial` 30 (predicted 28–30), `final` 17 (18–21, one under), `dynamic` 17 (13–17, at the
top). The stretch goal, at least 50% on every layout, holds on all six: s01 15/15, s02a 9/15,
s02c 8/15, s02va 13/15, s02vc 10/15, s03 9/15. Citable: 90 runs, one SHA, seeds 1–5, order
`random.Random("phase2-F")`, 90/90 valid.

| cell | Phase 1 (`a00`) | F (`a66`), steps to the goal |
|---|---|---|
| s01 `initial` | 5/5 | 5/5 (14, 14, 14, 14, 14) |
| s01 `final` | 0/5 | 5/5 (26, 48, 30, 28, 20) |
| s01 `dynamic` | 0/5 | 5/5 (21, 24, 22, 20, 17) |
| s02a `initial` | 5/5 | 5/5 (14, 14, 14, 14, 14) |
| s02a `final` | 0/5 | 1/5 (—, —, 40, —, —) |
| s02a `dynamic` | 0/5 | 3/5 (—, 39, 41, —, 55) |
| s02c `initial` | 5/5 | 5/5 (14, 14, 14, 14, 14) |
| s02c `final` | 0/5 | 2/5 (47, —, —, 27, —) |
| s02c `dynamic` | 0/5 | 1/5 (—, —, 32, —, —) |
| s02va `initial` | 5/5 | 5/5 (19, 19, 19, 19, 19) |
| s02va `final` | 0/5 | 4/5 (28, —, 30, 29, 28) |
| s02va `dynamic` | 0/5 | 4/5 (26, —, 31, 39, 46) |
| s02vc `initial` | 5/5 | 5/5 (19, 19, 19, 19, 20) |
| s02vc `final` | 0/5 | 1/5 (—, —, —, 44, —) |
| s02vc `dynamic` | 0/5 | 4/5 (48, 52, —, 48, 37) |
| s03 `initial` | 0/5 | 5/5 (35, 25, 26, 35, 38) |
| s03 `final` | 0/5 | 4/5 (—, 26, 51, 55, 29) |
| s03 `dynamic` | 0/5 | 0/5 |
| **total** | **25/90** | **64/90** |

Mean steps on a solved run: `initial` 18.7, `final` 34.5, `dynamic` 35.2. The §11 tables and the
planned contrasts are in [results/results.md](../results/results.md#final-round-f-agent-a66).

What the runs say:
- **The change arms moved from 0 to 17 of 30 each.** `dynamic` vs `initial`, all sites: 17/30 vs
  30/30, Fisher p = 4.6e-05; `dynamic` vs `final`: 17/30 vs 17/30, p = 1. The agent handles a
  door that switched before the flight and one that switches during it at the same rate.
- **s01 is solved on every arm** (15/15); so is every `initial` cell, s03 `initial` included
  (5/5, Phase 1 0/5): the planner takes the open tine from the lobby in 25–38 steps.
- **s03 `final` 4/5.** Seeds 2 and 4 (door R shut) solved at 26 and 55 steps, seeds 3 and 5
  (door L shut) at 51 and 29. Seed 1 lost: 36 steps in the shut tine after the closed read, open
  tine 0, 9.3 m from the goal at 60. `a66`'s first s03 `final` loss in Phase 2 (R30 1/1, R32P 3/3).
- **s03 `dynamic` stays unsolved**, 0/5 here and 0/52 across Phase 2: 40, 37, 41 and 30 steps in
  the shut tine after the closed read on seeds 1, 3, 4, 5, open tine 0 in every run; seed 2
  reached neither tine. `dynamic` vs `final` on s03: 0/5 vs 4/5, p = 0.048, the one site where the
  arms differ. The oscillation R30 described is intact; the lobby cost 4 steps in each run.
- **s02: the divider decides.** In-view (L2b) 13/20 on the change arms against out-of-view (L2a)
  7/20 (`dynamic` 8/10 vs 4/10, p = 0.17). `dynamic` beat `final` on s02a (3/5 vs 1/5) and s02vc
  (4/5 vs 1/5); s02c `dynamic` 1/5 is the weakest change cell after s03 `dynamic`. The 20 s02
  failures: 18 never through (min x ≥ 0.45, 12.9–20.4 m from the goal at 60 steps) and 2
  timeouts through late (s02a `dynamic` seed 1 crossed the gap at step 56, 9.8 m short; s02c
  `dynamic` seed 1 reached x = −0.88 and spun, streak 9 from step 46). The 12 s02 change-arm wins
  crossed the true gap at steps 16–46 on "toward your target".
- **Walls in flight** (`eval/r28_flight.py`): missed 16.7% (350/2099), phantom 12.4%
  (1582/12791), s03 phantom 15.9% (R30 18.5 / 11.1 / —; R32P 21.2 / 11.2 / 15.0): inside the
  4-point window. Longest turn-around streak 13 (s03 `dynamic` seed 3).
- **Labels** (`labels.csv`, Claude review): 64 success, 24 replan_failure, 2 timeout. Tags:
  `spin_failure` on s02c `dynamic` 1, s02c `final` 5, s02vc `final` 5, s03 `dynamic` 3;
  `failed_goal_identification` on s02vc `dynamic` 3 (five phantom goal reads, three true). No
  ignore, collision or pre-change failures.

**Manipulation check.** Every `run.json` carries `a66`, `de7f23d07186`, git `8d50901`; s03
`final` has `final_closed` BranchL on seeds 1, 3, 5 and BranchR on seeds 2, 4; walls within the
window. A `planner` route on 100% of steps in 89 runs and 95% in one (s02c `final` seed 2).
"Toward your target" was taken on ≥ 70% of forward offers in 75 of 90 runs; the 15 below the line
are all solved runs, 11 of them `initial` or s01 runs of 14–30 steps where the offer count is small
(`eval/r30_check.py`, 23 of 90 outside its limits in all: the 15 above, 2 turn-offer rates, and the
s03 tine counts of the 7 s03 change-arm losses and near-losses). Held: the check that failed is a
rate on short solved runs, not an engagement or identity failure.

**Citable.** Flown at `8d50901` on 2026-11-04, 17:48–19:02 UTC, on the operator's instruction
("Fly the final"): sctsvr6, eight lanes (`~/asep-final-l1..8`) on one vLLM (`Qwen3-VL-30B-A3B`,
remote profile, temperature 0), about 8 min per run under the shared load. **90/90 valid.**
Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.

**Phase 2's reading.** The hypothesis held in part: `a66` closed 57% of Phase 1's gap on `final`
and 57% on `dynamic`, and met the stretch goal on every layout. What it did not do: s03
`dynamic` (0/52 in Phase 2) and the out-of-view divider on s02a/s02c `final` (3/10). Both are
perception at 2–4 m, not planning: R31's probe gate showed no map or planner variant routes
through the true s02 gap from the lobby, and the s03 oscillation is the closed read arriving
after the tine is entered ([r30 analysis](../../../docs/research/r30-analysis-and-proposals.md)).
