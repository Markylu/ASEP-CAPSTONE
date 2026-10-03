# 1Ca Door Switch, in view, A opens (s02va): summary

**Citable.** Flown at `b352189` on 2026-10-02, 21:47–22:18 UTC. The runs used
`Qwen3-VL-30B-A3B` on the remote profile, at temperature 0 with prompt `p02`
(`26260774b60e`). They covered s02va v1 × {initial, final, dynamic} × seeds 1–5.

- **15 / 15 runs are valid.** Every replay was exact, and every run passes §10.
- Labels were reviewed by Claude on the operator's behalf. **They still need confirmation from Markus Lu.**

Site hypothesis (`site.json`): when the open route closes and a new one opens *inside* the
field of view, the agent will turn toward the visible new opening. **Not supported:** 0/10
runs tried door A.

## Result

| Arm | n | SR | 95% CI (Wilson) | success | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5 | **1.00** | 0.57–1.00 | 5 | – | 0 | 0 | 0 | – | 1.63 / 2.35 s |
| final | 5 | **0.00** | 0.00–0.43 | 0 | – | 5 | 0 | 0 | – | 1.81 / 7.13 s |
| dynamic | 5 | **0.00** | 0.00–0.43 | 0 | 5 | 0 | 0 | 0 | 0 | 1.82 / 7.54 s |

Planned contrasts (§11, Fisher's exact test, two-sided):

- **a. dynamic vs initial:** 0/5 vs 5/5, p = 0.008, ΔSR = −1.00.
- **b. dynamic vs final:** 0/5 vs 0/5, p = 1.0, ΔSR = 0.

### Per run

| Arm | Seeds | Outcome |
|---|---|---|
| initial | 1–5 | Spawn at x = 20. Through the open centre door B, goal reached in 19 steps with 0 collisions. Final distance 0.17–0.85 m. |
| final | 1–5 | Door B closed and door A (z = −9) open from spawn. Pinned on door B at x = 0.45 from step 12–16. 60 steps, 45–49 collisions, final distance 12.45 m. |
| dynamic | 1–5 | Door B closes and door A opens on move 4 (move 3 on seed 2), with door A in view. Then the same as `final`: pinned on door B from step 12–16, 45–49 collisions, 12.45 m. |

No failing run got more than 1.8 m sideways. Door A's opening is at z = −10.2 to −7.8.

## What the model did

For the first time in Phase 1, the model **sometimes names the closed door**, but late,
and it never acts on it.

- **`dynamic` seed 3 and `final` seed 3** (identical trajectories): at x = 3.2, before
  touching anything, steps 10, 12 and 14 say "The drone is currently facing a closed door,
  which blocks the path". The agent then turns around in place four times (moves 11–14).
  Each turn puts the goal behind it, so the next decision turns back toward the goal
  bearing. It then flies into door B and stays pinned. It never turns toward door A.
- `final` seed 1 mentions a closed door once (step 10). `final` seed 4 turns around twice
  (moves 11–12) without naming the door. Neither changes the outcome.
- Every other failing run: no reason refers to the closed door. Reasons call it "the open
  door" or "the only clear path forward", and while pinned, 12–22 decisions per run call
  the path clear.

Labels:

- **dynamic → `ignore_change`** (5/5). In the first 5 post-change decisions, no reason
  refers to the closed door, and 5/5 actions are within ±30° of the goal bearing. Seed 3's
  acknowledgement comes at decision 7 after the change, outside the fixed 5-decision window
  (§9), so the label stands. The override note records it.
- **final → `replan_failure`** (5/5). Door A was open and in view from step 0 and never tried.
- Tag on all 10: `path_hallucination`.

**H1 reading.** Same as 1Ba and s01: contrast a is total and contrast b is null. s02va was
the site meant to separate a change-specific cost from "the final layout is hard", and it
cannot, because `final` fails just as completely. The late acknowledgement in seed 3 shows
the model *can* register the closed door when close enough. But its only response is to
turn around, and the goal bearing turns it straight back. That looks like a planning
failure (no notion of a lateral detour) rather than a perception failure.

## Validity notes

- Rungs: 685 of 695 decisions used `json_schema`. 10 fell back to `json_object` (5 final,
  5 dynamic). Every run is above the 90% bar.
- `dynamic` change step: seeds 1, 3, 4 and 5 fired on move 4, seed 2 on move 3, all passing §10.
- Latency normal (p50 1.6–1.8 s). The p95 of about 7 s in `final` and `dynamic` comes from
  occasional slow decisions, not a sustained slowdown like 1Bc's.

## Issues found

1. Auto pre-label negation (1A issue 1, still open). All 15 runs got an `ack_step`, and all
   5 `dynamic` labels needed an override.
2. **The 5-decision window misses late acknowledgements.** Seed 3 is labelled
   `ignore_change` although it names the closed door 7 decisions after the change. Correct
   under §9, but worth a sentence in the paper. Changing the window now would mean
   relabelling every mini-phase (§9).

## Attempts

None. Flown once, 15/15 valid.
