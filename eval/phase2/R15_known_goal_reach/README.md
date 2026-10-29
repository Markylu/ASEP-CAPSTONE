# R15: Known goal, reachable detours (a25; R15N flies a26 beside it)

**Agent:** `a25` (`b46c2c06c890`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) ·
**Perceiver:** `g05` (floor map as `a22`) · **Detour strategist:** `q03` · **Memory:** `spatial.A17` ·
**Status:** pre-registered 2026-10-29, built overnight without the operator (operator, 2026-10-28:
"iterate and improve this project as much as possible ... DO NOT WAIT FOR MY APPROVAL").

Second agent at the same SHA: **R15N**, `a26` (`a4434efe7cf4`) = `a25` with navigator prompt `p16`;
[R15N's README](../R15N_known_goal_ranked_notes/README.md).

## Why this round

The operator's aim is the best agent; the goal's position is a tool, not a variable (operator,
2026-10-28, when R12C was dropped). The best round so far is R11 (`a16`, 11/18), which kept the
goal's true position in the planner. Its failure analysis found one mechanism behind most of its
losses, and R12 built the fix for it, but R12 also removed goal truth and changed the perceiver at
the same time, so the fix was never flown with the goal known.

## Change against `a16` (R11)

| | `a16` (R11) | `a25` |
|---|---|---|
| target | the goal's true position; detour asked when walled, blocked, or 6 steps no nearer (`planner.route`) | same |
| detour menu | `a16` frontier at its cell nearest the goal (`spatial.targets`) | `a17`'s `search_menu`: reachable edges of unsearched ground, reachable doorways, the way back (`goal_reach_detour`) |
| memory | `a16` | `a17` (cone coverage, stop walls, reachable targets; "toward" on the sharpest open move on the target's side when nothing in the fan points at it) |
| perceiver | `g03` | `g05`, read with `a22`'s floor map (R14) |
| strategist | `q03`, each place worded nearer/farther the goal | same |

## Evidence

- R11 failure analysis §0 ([../R11_goal_default/failure_analysis.md](../R11_goal_default/failure_analysis.md)):
  34 of 37 detour picks lay behind or inside a wall; 51% of R11's steps stood on such a target,
  with 37 of 58 collisions. Counterfactual with a perfect perceiver: still 37 of 38. "A better
  perceiver does not fix this. Reachability does."
- R12 probe line 4: `a17`'s top search target is reachable at R11's q03 calls.
- R11 Q2: 185 steps with "toward" on marker 0 not followed, +158.5 m away from the goal; `a17`'s
  projector puts "toward" on the sharpest open move on the target's side instead.
- R14 so far (8 of 36 runs): `a22`'s floor map reads 0–24% of strips blocked (R13: 39–68%).

## Hypothesis

With the goal known and every detour reachable, `final` returns to R11's level or above and
`dynamic` rises above R11's 1/6.

## Predictions

| Arm | R11 (`a16`) | R15 / R15N |
|---|---|---|
| `initial` | 6/6 | ≥ 5/6 |
| `final` | 4/6 | ≥ 4/6 |
| `dynamic` | 1/6 | ≥ 2/6 |
| total | 11/18 | ≥ 12/18 |
| detour picks behind or inside a wall | 34/37 | ≤ 5 |

## Drop criterion

Not carried forward unless it beats R11's 11/18.

## Probe gate

1. Smoke on R12's 862 recorded manifests with stub replies (`eval/r12_probe.smoke_run`, `a25`):
   0 failed steps; 102 strategist calls (94 walled, 6 stall, 2 blocked); every menu item from
   `search_menu`; "toward" never on a not-open action.
2. Navigator (R15N only): [R15N's README](../R15N_known_goal_ranked_notes/README.md).

## Host

sctsvr6, 8 lanes (4 per agent), all model calls to the existing vLLM on :8004 (one H100; the
operator's limit is 4). The tunnel is the operator's.

## Outcome

Not flown.
