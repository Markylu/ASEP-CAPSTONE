# F2: a102 on the full design, lavapipe, 90 runs: summary

**76/90 (84%): `initial` 30/30, `final` 23/30, `dynamic` 23/30. Round F (`a66`): 64/90, 30/17/17.
Phase 1 (`a00`): 25/90, 25/0/0.** The README predicted 72–83 and the round landed 76: `initial` 30
(predicted 28–30), `final` 23 (24–28, one under), `dynamic` 23 (20–25). Per layout: s01 15/15
(predicted 15), s02a 13/15 (11–13), s02c 12/15 (11–13), s02va 12/15 (14–15, under), s02vc 11/15
(12–14, under), s03 13/15 (8–10, over). At least 50% on every layout. Citable: 90 runs, one SHA
(`00e8b2bf`, agent `a102` `e405aeb4a004`), seeds 1–5, order `random.Random("phase2-F2")`, 90/90
valid, Godot under lavapipe (llvmpipe named in all 90 `godot.log`), eight lanes on `:8004` as Round F.

| cell | Phase 1 (`a00`) | F (`a66`) | F2 (`a102`), steps to the goal |
|---|---|---|---|
| s01 `initial` | 5/5 | 5/5 | 5/5 (14, 14, 14, 14, 14) |
| s01 `final` | 0/5 | 5/5 | 5/5 (33, 24, 21, 37, 31) |
| s01 `dynamic` | 0/5 | 5/5 | 5/5 (23, 21, 19, 28, 22) |
| s02a `initial` | 5/5 | 5/5 | 5/5 (14, 14, 14, 14, 14) |
| s02a `final` | 0/5 | 1/5 | **4/5 (35, 18, —, 25, 18)** |
| s02a `dynamic` | 0/5 | 3/5 | **4/5 (—, 40, 37, 45, 58)** |
| s02c `initial` | 5/5 | 5/5 | 5/5 (14, 14, 14, 14, 14) |
| s02c `final` | 0/5 | 2/5 | **3/5 (—, —, 23, 27, 26)** |
| s02c `dynamic` | 0/5 | 1/5 | **4/5 (35, —, 23, 29, 23)** |
| s02va `initial` | 5/5 | 5/5 | 5/5 (19, 19, 19, 19, 19) |
| s02va `final` | 0/5 | 4/5 | 3/5 (29, 25, 30, —, —) |
| s02va `dynamic` | 0/5 | 4/5 | 4/5 (53, 22, 23, —, 27) |
| s02vc `initial` | 5/5 | 5/5 | 5/5 (19, 19, 19, 19, 19) |
| s02vc `final` | 0/5 | 1/5 | **4/5 (—, 42, 47, 28, 32)** |
| s02vc `dynamic` | 0/5 | 4/5 | 2/5 (—, —, —, 27, 25) |
| s03 `initial` | 0/5 | 5/5 | 5/5 (30, 29, 37, 37, 33) |
| s03 `final` | 0/5 | 4/5 | 4/5 (56, 31, —, 39, 25) |
| s03 `dynamic` | 0/5 | 0/5 | **4/5 (46, 48, —, 51, 46)** |
| **total** | **25/90** | **64/90** | **76/90** |

Bold: above Round F. Mean steps on a solved run: `initial` 18.9, `final` 30.5, `dynamic` 33.5
(F: 18.7, 34.5, 35.2). The §11 tables and the planned contrasts are in
[results/results.md](../results/results.md#final-round-f2-agent-a102-final-design-a102-on-the-full-design-lavapipe).

What the runs say:
- **Twelve runs over Round F, all on the change arms** (F2 vs F, Fisher two-sided: 76/90 vs
  64/90, p = 0.048). The eight settled cells held, 40/40. Per site against F: s01 0, s02a +4,
  s02c +4, s02va −1, s02vc +1, s03 +4.
- **s02 out of view is where the gain is.** s02a and s02c change arms 15/20 against F's 7/20
  (p = 0.025); in view (s02va, s02vc) 13/20 against 13/20. All s02 change arms 28/40 against
  20/40 (p = 0.110). The twelve s02 losses: nine never through (min x 0.06–0.80, 12.9–20.4 m
  from the goal at 60 steps) and three timeouts through late, at steps 54–55, 4.5–6.6 m short
  (s02c `final` 2, s02va `final` 4, s02vc `final` 1). s02vc `dynamic` 2/5 (F 4/5) is the weakest
  change cell: seeds 1–3 never through; seed 2 (`ignore_change`) reached the divider 2.6 m from
  door C at step 13, collided, left on a survey excursion back to the lobby (x = 21 at step 29) and
  came back to shut door B at step 54. The one other lobby return of the round was one step in
  s02a `dynamic` seed 5, a win at 58.
- **s03 `dynamic` 4/5, Phase 2's first wins on the cell** (F 0/5, 0/52 across Phase 2 up to R32;
  p = 0.048 against F). In all four wins the door shut at step 17–18, the closed read came the
  same step or the next, a94's latch fired four to six steps after it (steps 22–24), the drone left
  the shut tine, crossed the exit wall at steps 42–48 and reached the goal at 46–51
  (`eval/probes/a94_latch_check.py --agent a94 --folders final_a102 --runs`). The loss, seed 3,
  never entered a tine, so the switch never fired (`pre_change_failure`): at step 9 a frame at the
  stem mouth read blocked on every strip, the drone turned back and spent the remaining 50 steps
  in the lobby and stem, five collisions, 26 m from the goal at 60. The lobby stall of R70 s03
  `dynamic` seed 3 again; a99 and a101's stop walls were aimed at it and never met it in flight.
- **s03 `final` 4/5.** Seeds 2, 4 and 5 took the open tine from the lobby (28, 35 and 21 steps to
  the exit wall) without a latch. Seed 1 entered the shut tine, closed read at 22, latch at 27,
  goal at 56. Seed 3 (door L shut) entered tine L at 26, closed read 26, latch 33, crossed the
  exit wall at step 58 and ended 1.7 m from the goal: a timeout through, the budget not the route.
- **The 60-step budget took four runs through the last door**: the three s02 timeouts and s03
  `final` seed 3 crossed at steps 54–58. None of Round F's wins crossed later than step 46.
- **Lavapipe did not lift a102 over its H100 flights.** On the thirty contested cells it flew on
  H100 frames (s02 and s03, `final` and `dynamic`, seeds 1–3), this round scored 19/30 against 23
  (R66) and 21 (R70); seeds 4–5 of the same cells 17/20. Three flights 19–23: the a93 lavapipe
  flight (R53 24/30 against 16–21 on H100) was one flight, not a renderer effect.
- **Walls in flight** (`eval/r28_flight.py`): missed 16.2% (186/1151), phantom 10.0%
  (1162/11599), s03 phantom 10.7% (281/2626); Round F 16.7 / 12.4 / 15.9. Longest turn-around
  streak 4 (s01 `final` 4; Round F 13). Decision latency p50, median over runs, 2.03 s (F 2.14 s).
- **Manipulation check held**: one agent, agent sha and git sha on all 90 `run.json`; llvmpipe on
  all 90 `godot.log`, no H100; s03 `final` `final_closed` BranchL / R / L / R / L on seeds 1–5;
  survey stations in the planner record on every s02 change-arm run; the latch fired within seven
  steps of the closed read on all six s03 runs that read a shut door in a tine.
- **Labels** (`labels.csv`, Claude review, not yet confirmed by the operator): 76 success, 8
  replan_failure, 4 timeout, 1 ignore_change (s02vc `dynamic` 2), 1 pre_change_failure (s03
  `dynamic` 3). No tags. Both non-standard labels are the auto labels, checked step by step
  (notes in the csv).

Flown 2026-11-07 16:01–17:04 UTC on eight sctsvr6 lanes (`asep-r68-l1..8`), shared vLLM `:8004`,
Godot under lavapipe, 90/90 valid, 0 attempts beyond the first. No vLLM copy ran. Lane logs are not
in the repo.
