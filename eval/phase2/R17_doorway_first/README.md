# R17: R15 (known goal) with detour strategist q07 (a31; R17K flies a32 beside it)

**Agent:** `a31` (`8caaa2c3e19a`) · **Navigator prompt:** `p14` · **Detour strategist:** `q07`
(`50850d92c4d1`, new) · everything else as `a25` (R15) · **Status:** pre-registered 2026-10-29,
built overnight without the operator (operator, 2026-10-28: "maintain a preference for subagents
over hard coded tasks").

Second agent at the same SHA: **R17K**, `a32` (`393510161353`) = `a28` (R16K: `a25` + goal
confirmer `c01`) with `q07`; [R17K's README](../R17K_doorway_first_confirmer/README.md). Laid out
before R15 and R16K were read: it is queued behind them.

## Change against `a25` (R15)

One: the detour strategist's prompt. `q07` is `q03` with its closing advice ("prefer a detour
that lies nearer the goal than the drone") replaced by:

- every detour listed is reachable; "nearer the goal" is straight-line distance and says nothing
  about the wall the drone has just been stopped by;
- a doorway is the way round the wall: take it even when it lies farther from the goal;
- with no doorway, more unexplored ground first, nearer only breaking a tie;
- blocked on several sides is a dead end: go back.

`q06` (the same advice without the straight-line sentence) and its agents `a29`/`a30` were built
and probed first; they are not flown.

## Evidence

- R11 failure analysis Q6 items 3 and 7 ([../R11_goal_default/failure_analysis.md](../R11_goal_default/failure_analysis.md)):
  a doorway was picked on 1 of the 19 menus that held one; backtrack never chosen (s03 dynamic,
  32 steps in a dead end). Its offline test: doorway picks ≥ 50%.
- Strategist replay ([probe/strategist_r11_score.txt](probe/strategist_r11_score.txt),
  `eval/r17_strategist_probe.py`, live model on the flight host): R11's 38 recorded q03 calls
  asked again, text only.

  | prompt | doorway when listed | way back in a dead end | pick worded nearer the goal |
  |---|---|---|---|
  | recorded `q03` | 1/19 | 0/2 | 38/38 |
  | `q03` again | 1/19 | 0/2 | 38/38 |
  | `q06` | 2/19 | 1/2 | 37/38 |
  | **`q07`** | **10/19** | 1/2 | 29/38 |

  R11's menus are `a16`'s (frontiers behind walls); `a25`'s menu lists reachable places only,
  so this measures the strategist's preference, not the outcome.
- The same replay on R15's 96 calls (`a25`'s own reachable menus, flown after this README was
  first written; [probe/strategist_r15_score.txt](probe/strategist_r15_score.txt)):

  | prompt | doorway when listed | `explore` (no target) | frontier | backtrack |
  |---|---|---|---|---|
  | recorded `q03` | 18/44 | 32 | 39 | 7 |
  | `q03` again | 17/44 | 31 | 44 | 4 |
  | **`q07`** | **37/44** | 3 | 52 | 4 |

  On `a25`'s menus `q03` already takes a doorway 41% of the time; `q07` doubles it and nearly
  stops choosing no target. Whether those doorways are the open ones is not scored.
- Smoke (stub replies, goal kept): `a31` and `a32` on R12's 862 manifests, 0 failed steps,
  102 and 98 strategist calls; `a32`'s 58 refusals all set the perceiver's goal to `not_visible`.

## Hypothesis

Taking doorways when the way toward the goal is shut gets the known-goal agent round the
divider in `final`/`dynamic` (R11: 6 of 7 failures were s02 `dynamic`/`final` and s03 `dynamic`).

## Predictions

| Measure | R15 (`a25`) | R17 |
|---|---|---|
| total | see R15's Outcome | ≥ R15 + 1 |
| doorway picks when one is listed | | ≥ 40% |
| s02 `final` + `dynamic` solved | | ≥ R15 + 1 |

## Drop criterion

Not carried forward if it does not beat R15.

## Outcome

Not flown.
