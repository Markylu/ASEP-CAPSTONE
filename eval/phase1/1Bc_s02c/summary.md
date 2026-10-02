# 1Bc Door Switch, out of view, C opens (s02c): summary

**Citable.** Flown at `21b103f` on 2026-10-02, 20:37–21:22 UTC. The runs used
`Qwen3-VL-30B-A3B` on the remote profile, at temperature 0 with prompt `p02`
(`26260774b60e`). They covered s02c v2 × {initial, final, dynamic} × seeds 1–5. Mirror of
1Ba: door C (z = +9) opens instead of door A (z = −9).

- **15 / 15 runs are valid.** Every replay was exact, and every run passes §10.
- Labels were reviewed by Claude on the operator's behalf. **They still need confirmation from Markus Lu.**

## Result

| Arm | n | SR | 95% CI (Wilson) | success | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5 | **1.00** | 0.57–1.00 | 5 | – | 0 | 0 | 0 | – | 2.59 / 68.9 s * |
| final | 5 | **0.00** | 0.00–0.43 | 0 | – | 5 | 0 | 0 | – | 1.77 / 2.50 s |
| dynamic | 5 | **0.00** | 0.00–0.43 | 0 | 5 | 0 | 0 | 0 | 0 | 1.74 / 2.64 s |

\* Inflated by server load, see Validity notes. Without the affected decisions (seeds 3, 4,
and seed 2 from step 3): 1.72 / 8.35 s.

Planned contrasts (§11, Fisher's exact test, two-sided):

- **a. dynamic vs initial:** 0/5 vs 5/5, p = 0.008, ΔSR = −1.00.
- **b. dynamic vs final:** 0/5 vs 0/5, p = 1.0, ΔSR = 0.

**L2 family (1Ba + 1Bc, n = 10 per arm):** contrast a 0/10 vs 10/10, p = 1.1 × 10⁻⁵;
contrast b 0/10 vs 0/10, p = 1.0. Seeds are near-replicates (§7.3), so read the pooled p as
a robustness check, not as 20 independent draws.

### Per run

| Arm | Seeds | Outcome |
|---|---|---|
| initial | 1–5 | Through the open centre door B, goal reached in 14–15 steps with 0 collisions. Final distance 0.67–0.88 m. |
| final | 1–5 | Door B is closed and door C (z = +9) open from spawn. Pinned on door B at x = 0.45 from step 7 (step 8 on seed 2). 60 steps, 53–54 collisions, final distance 12.45 m. |
| dynamic | 1–5 | Door B closes and door C opens on move 4 (move 3 on seed 4). Then identical to `final`: pinned on door B, 53–54 collisions, 12.45 m. |

**The mirror changes nothing.** Final distances match 1Ba's to the centimetre, and so do the
change moves and pin steps. No failing run got more than 1.25 m sideways in either
mini-phase. Whichever side door opens, the agent ends at the same spot on door B. Its
behaviour does not depend on where the new route is; a side bias would have shown up as a
difference between the two mini-phases.

## What the model did

As in 1Ba: no `reason` in any run says door B closed. Right after the switch, reasons
describe "the door, which is the only clear path forward" (seed 2, steps 4–5), and while
pinned, 17–26 decisions per failing run still call the path clear.

- **dynamic → `ignore_change`** (5/5). No reason refers to the closed door or a blocked
  route, and 4–5 of the first 5 post-change actions were within ±30° of the goal bearing.
- **final → `replan_failure`** (5/5). Door C was open from step 0 and never tried.
- Tag on all 10: `path_hallucination`.

## Validity notes

- **Server load during the first three runs.** `initial` seeds 1 and 5 took 8–10 min
  instead of about 2 min, and seed 2's first 2 decisions took 45 s and 21 s. Prefill took
  about 31 s per decision instead of about 0.2 s, while network time stayed at 0.26–0.29 s.
  So the cause was GPU contention on sctsvr6, which also serves the text models, not the
  tunnel. The trajectories are unaffected: the world freezes between moves and decoding is
  at temperature 0, and all three runs reached the goal in 14 steps like the other `initial`
  runs. Only the latency DV is affected. Use `compute_ms` / `network_ms` from
  `decisions.jsonl` when comparing latency across mini-phases. §10 has no latency
  validity rule, so the runs stand.
- Rungs: 662 of 671 decisions used `json_schema`. 9 fell back to `json_object` (2 initial,
  2 final, 5 dynamic). Every run is above the 90% bar.
- `dynamic` change step: seeds 1, 2, 3 and 5 on move 4, seed 4 on move 3, all passing §10.

## Issues found

1. Auto pre-label negation (1A issue 1, still open). Same overrides as 1Ba.
2. **Consider a latency validity rule** before the remaining mini-phases, e.g. flag a run
   whose median `prefill_ms` exceeds ten times the session median. Adding one is a spec change (§7.1).

## Attempts

None. Flown once, 15/15 valid.
