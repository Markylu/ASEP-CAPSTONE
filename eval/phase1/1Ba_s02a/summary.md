# 1Ba Door Switch, out of view, A opens (s02a): summary

**Citable.** Flown at `21b103f` on 2026-10-02, 17:25–17:52 UTC. The runs used
`Qwen3-VL-30B-A3B` on the remote profile, at temperature 0 with prompt `p02`
(`26260774b60e`). They covered s02a v2 × {initial, final, dynamic} × seeds 1–5.

- **15 / 15 runs are valid.** Every replay was exact, and every run passes §10.
- Labels were reviewed by Claude on the operator's behalf and confirmed by Markus Lu on 2026-10-07, unchanged.

## Result

| Arm | n | SR | 95% CI (Wilson) | success | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5 | **1.00** | 0.57–1.00 | 5 | – | 0 | 0 | 0 | – | 1.77 / 2.23 s |
| final | 5 | **0.00** | 0.00–0.43 | 0 | – | 5 | 0 | 0 | – | 1.77 / 2.47 s |
| dynamic | 5 | **0.00** | 0.00–0.43 | 0 | 5 | 0 | 0 | 0 | 0 | 1.78 / 2.70 s |

Planned contrasts (§11, Fisher's exact test, two-sided):

- **a. dynamic vs initial:** 0/5 vs 5/5, p = 0.008, ΔSR = −1.00.
- **b. dynamic vs final:** 0/5 vs 0/5, p = 1.0, ΔSR = 0.

Pooled with its mirror 1Bc (L2 family, n = 10 per arm), contrast a is 0/10 vs 10/10,
p = 1.1 × 10⁻⁵. See `1Bc_s02c/summary.md`.

### Per run

| Arm | Seeds | Outcome |
|---|---|---|
| initial | 1–5 | Through the open centre door B, goal reached in 14–15 steps with 0 collisions. Final distance 0.66–0.98 m. |
| final | 1–5 | Door B is closed and door A (z = −9) open from spawn. Flies straight at door B, pinned on it at x = 0.45 from step 7 (step 8 on seed 2). 60 steps, 53–54 collisions, final distance 12.45 m. |
| dynamic | 1–5 | Door B closes and door A opens on move 4 (move 3 on seed 4). After that the run is identical to `final`: pinned on door B from step 7–8, 53–54 collisions, 12.45 m. |

No failing run ever got more than 1.25 m sideways (|z| ≤ 1.25 m). Door A's opening is at
z = −10.2 to −7.8, so the agent never moved even a sixth of the way toward it.

## What the model did

The model **never registered that door B closed.** No `reason` in any run says the door is
closed, shut or blocked. In the `dynamic` window right after the switch, several reasons say
the opposite: "The door is open, so flying forward is safe" (seed 2, step 4), "facing directly
toward the open doorway" (seed 4, step 3). While pinned, 13–26 decisions per failing run
still call the path clear.

- **dynamic → `ignore_change`** (5/5). No reason refers to the closed door or a blocked
  route, and 4–5 of the first 5 post-change actions were within ±30° of the goal bearing
  (threshold 3). Seed 3 mentions "the wall on the left" at step 6, but only as a turning
  hazard, not the closed route.
- **final → `replan_failure`** (5/5). Door A was open from step 0 and never tried. Seed 4,
  step 6 says "facing a wall, and the open path is to the right", but the agent never turns
  toward it.
- Tag on all 10: `path_hallucination`.

**H1 reading.** Same shape as 1A. The change costs everything (contrast a), but the
post-change layout alone is just as fatal (contrast b). The model does not search for the
side door whether it opened mid-run or was open all along.

## Validity notes

- Rungs: 664 of 671 decisions used `json_schema`. 7 fell back to `json_object` (1 initial,
  1 final, 5 dynamic). Every run is above the 90% bar.
- `dynamic` change step: seeds 1, 2, 3 and 5 fired on move 4, seed 4 on move 3, all passing §10.
- Network was normal: decision latency 1.6–2.7 s throughout.

## Issues found

1. **The auto pre-label still cannot handle negation** (1A issue 1, still open). Every run,
   including all 5 `initial` runs, got an `ack_step` from "no visible obstacles" or
   "closing the distance". All 10 `dynamic` labels needed an override from `replan_failure`
   to `ignore_change`. Manual review caught all of it.
2. **On s02a, `dynamic` cannot be separated from `final`**, as on s01. s02va/s02vc (new door
   in view, 1Ca/1Cc) are the sites where contrast b can show a change-specific cost.

## Attempts

The first start at `80a0a2d` stopped after 2 runs. `dynamic` seed 5 a01 was marked invalid
because two same-tick steps were logged out of order and `replay.py` compared by line. The
replay itself was exact. Fixed in `21b103f`; the earlier runs are kept in `_attempts/`. See
`phase.json` and §15.
