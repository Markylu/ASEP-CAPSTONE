# R35 a75 (a66 with the wall-turn rule alone) on the ten contested cells, seeds 1-3: summary

**a75 13/30, a66 15/30 (R32P): gap −2, under the rule's threshold of 3, a draw; and under this
round's drop criterion of 15. The wall-turn rule did what it was built for and did not move the
score. `a75` is not carried forward.**

| cell | `a66` (R32P) | `a75` (R35), steps to the goal | `a66` (F, 5 seeds) |
|---|---|---|---|
| s02a `final` | 2/3 | **3/3** (24, 22, 21) | 1/5 |
| s02a `dynamic` | 2/3 | **3/3** (24, 37, 40) | 3/5 |
| s02c `final` | 1/3 | 1/3 (—, —, 27) | 2/5 |
| s02c `dynamic` | 0/3 | 0/3 | 1/5 |
| s02va `final` | 2/3 | 1/3 (—, —, 48) | 4/5 |
| s02va `dynamic` | 2/3 | 2/3 (29, —, 37) | 4/5 |
| s02vc `final` | 1/3 | 0/3 | 1/5 |
| s02vc `dynamic` | 2/3 | 1/3 (—, —, 30) | 4/5 |
| s03 `final` | 3/3 | 2/3 (—, 26, 31) | 4/5 |
| s03 `dynamic` | 0/3 | 0/3 | 0/5 |
| **total** | **15/30** | **13/30** | 24/50 |
| s02 | 12/24 | 11/24 | |
| s03 | 3/6 | 2/6 | |

Against the predictions (README): 15–18 predicted, 13 landed, two under. s02a 6/6 (predicted
about 3–4), every other s02 site at or under `a66`'s count.

What the runs say:
- **The manipulation held completely.** 148 steps followed a turn-around taken facing a wall;
  the turn-around was hidden on all 148 and none was repeated (R32P `a66`: 8 of 146, 5.5%;
  Round F: 39 of 297 in these cells, 13.1%). Longest turn-around streak 2 (R32P 5, F 13). A
  route on 1415 of 1416 steps.
- **It bought no steps that mattered.** Turn-arounds per step 0.144 (R32P 0.138), frames with
  every strip blocked 12.6% (R32P 11.2%): the drone meets the wall as often and turns as often;
  only the second turn of a pair is gone, and `a66` under four lanes already repeated on just
  5.5% of wall turns (Round F's 13.1% was under eight lanes). The 17 losses are all
  `replan_failure`, never through, as `a66`'s.
- **s03 unchanged.** `dynamic` 0/3 with 35, 24 and 28 steps in the shut tine after the closed read
  and the open tine 0; `final` 2/3, seed 1 lost in the shut tine
  (32 steps), the loss `a66` took in Round F at the same seed.
- **s02a 6/6 is the one cell group above `a66`** (R32P 4/6, F 4/10). One site, three seeds per
  arm: by R32's rule a draw until repeated; the six runs crossed the divider at steps 10–31, four of them
  on "toward your target", after 0–3 wall turns each.
- **Shakedown against round.** The shakedown's seed-1 wins did not all repeat under four lanes:
  s02c `dynamic` seed 1 (solved at 29 alone) and s03 `final` seed 1 (solved at 26 alone) were
  lost here. A run is a fresh draw from step 0 (why_14, R30).
- **Walls in flight** (`eval/r28_flight.py`): missed 18.1%, phantom 11.3%, s03 phantom 14.6%
  (R32P 21.2 / 11.2 / 15.0; F 16.7 / 12.4 / 15.9): inside the window.
- **Labels** (`labels.csv`, Claude review): 13 success, 17 replan_failure; no spin or
  goal-identification tags.

**Manipulation check.** Every `run.json` carries `a75`, `81d682c1424b`, git `155ce17`. Repeat
turn-arounds after a wall turn 0% (limit 4%); hidden 100% (limit 60%); no streak of 5; route
99.9%; walls within 4 points. `eval/r30_check.py`: 9 of 30 outside its limits, the s03 shut-tine
counts and short-run "toward" rates, as for `a66`. Held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r35-l1..4`) alone on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0);
R32P flew four lanes beside R32's four. Flown at `155ce17` on 2026-11-05, 12:23–13:07 UTC, on
the operator's instruction ("Fly R35"). **30/30 valid**, no attempt beyond the first. Labels:
Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** The turn-around loop was real in the records and is closed; it was a symptom, not
the cause of the losses. The drone that no longer spins at the wall still has no route through
it: the losses are decided by where the route crosses (analysis §3.2–3.4), which `a75` does not
touch. The best agent is still `a66` (F 64/90).
