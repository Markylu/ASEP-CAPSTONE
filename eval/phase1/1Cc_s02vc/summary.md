# 1Cc Door Switch, in view, C opens (s02vc): summary

**Citable.** Flown at `3525982` on 2026-10-03, 15:22–15:52 UTC. The runs used
`Qwen3-VL-30B-A3B` on the remote profile, at temperature 0 with prompt `p02`
(`26260774b60e`). They covered s02vc v1 × {initial, final, dynamic} × seeds 1–5. Mirror of
1Ca: door C (z = +9) opens in view instead of door A (z = −9).

- **15 / 15 runs are valid.** Every replay was exact, and every run passes §10.
- Labels were reviewed by Claude on the operator's behalf. **They still need confirmation from Markus Lu.**

## Result

| Arm | n | SR | 95% CI (Wilson) | success | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5 | **1.00** | 0.57–1.00 | 5 | – | 0 | 0 | 0 | – | 1.76 / 2.83 s |
| final | 5 | **0.00** | 0.00–0.43 | 0 | – | 5 | 0 | 0 | – | 1.79 / 2.57 s |
| dynamic | 5 | **0.00** | 0.00–0.43 | 0 | 5 | 0 | 0 | 0 | 0 | 1.77 / 7.88 s |

Planned contrasts (§11, Fisher's exact test, two-sided):

- **a. dynamic vs initial:** 0/5 vs 5/5, p = 0.008, ΔSR = −1.00.
- **b. dynamic vs final:** 0/5 vs 0/5, p = 1.0, ΔSR = 0.

**In-view family (1Ca + 1Cc, n = 10 per arm):** contrast a 0/10 vs 10/10, p = 1.1 × 10⁻⁵;
contrast b 0/10 vs 0/10, p = 1.0. Seeds are near-replicates (§7.3), so the pooled p is a
robustness check, not 20 independent draws.

### Per run

| Arm | Seeds | Outcome |
|---|---|---|
| initial | 1–5 | Spawn at x = 20. Through the open centre door B, goal reached in 19 steps with 0 collisions. Final distance 0.17–0.85 m. |
| final | 1–5 | Door B closed and door C open, in view, from spawn. Pinned on door B at x = 0.45 from step 12 (step 14 on seed 3). 60 steps, 47–49 collisions, final distance 12.45–12.49 m. |
| dynamic | 1–5 | Door B closes and door C opens on move 4 (move 3 on seed 2). Pinned on door B from step 12, 49 collisions, 12.45–12.49 m. |

No failing run got more than 1.6 m sideways. Door C's opening is at z = +7.8 to +10.2.
As with 1Ba and 1Bc, the mirror changes nothing: outcomes, pin steps and final distances
match 1Ca, so which side opens has no effect.

## What the model did

The 1Ca pattern again, and a little more often: the model **names the closed door late,
then flies into it anyway.**

- `dynamic` seeds 2, 3 and 4 and `final` seed 1, at decision 10: "The drone is currently
  facing a closed door, which is a wall, so it cannot proceed forward." The next move is a
  +22° turn, undone by −22° on the move after, and the agent then flies into door B.
- `final` seed 3 names it at decisions 7 and 10, turns around in place twice (moves 11–12),
  turns back toward the goal bearing, and is pinned from step 14.
- Even after these acknowledgements, 12–18 decisions per failing run call the path clear
  while pinned.

Labels:

- **dynamic → `ignore_change`** (5/5). In the first 5 post-change decisions, no reason
  refers to the closed door, and 5/5 actions were within ±30° of the goal bearing. The
  acknowledgements come 7–8 decisions after the change, outside the §9 window. Each
  override note records them.
- **final → `replan_failure`** (5/5). Door C was open and in view from step 0 and never tried.
- Tag on all 10: `path_hallucination`.

**H1 reading.** The same as 1Ca. Across the in-view family, 8 of 20 failing runs name the
closed door (3 in 1Ca, 5 here), and every one keeps the goal bearing anyway: a small jog
or a turn-around, then straight back into the door. Seeing the blockage does not produce a
detour. That points to planning (the policy follows bearing and has no lateral search),
not perception.

## Validity notes

- Rungs: 691 of 695 decisions used `json_schema`. 4 fell back to `json_object` (1 final,
  3 dynamic). Every run is above the 90% bar.
- `dynamic` change step: seeds 1, 3, 4 and 5 on move 4, seed 2 on move 3, all passing §10.
- Latency normal (p50 1.8 s). The `dynamic` p95 of 7.9 s comes from occasional slow
  decisions, not a sustained slowdown.

## Issues found

1. Auto pre-label negation (1A issue 1, still open). All 5 `dynamic` labels overridden.
2. The 5-decision window misses late acknowledgements (1Ca issue 2). 3 of 5 `dynamic` runs
   here name the closed door 7–8 decisions after the change.

## Attempts

None. Flown once, 15/15 valid.
