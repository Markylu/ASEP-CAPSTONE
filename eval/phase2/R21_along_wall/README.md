# R21: R20 with along-the-wall detours

**Agent:** `a40` (`fd6123bdf057`) · **Prompt:** `p17` (`cb3578251cfe`) · **Strategist:** `q08`
(`8cf2790c7220`) · **Status:** pre-registered 2026-10-29, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Built overnight without the operator
(operator, 2026-10-28: "mantain a prefrence for subagents over hard coded tasks": code offers the
two ways along the wall, the strategist chooses).

Second agent at the same SHA: **R21K**, `a41` (`ca6f816e9c32`) = `a40` + goal confirmer `c01`
([R21K](../R21K_along_wall_goal_confirmer/README.md)). `a39` (`ce386ea8aa4e`) is the same change on
`a35` without `d01`, registered and not flown.

## Change

One against `a37` (R20): along-the-wall detours, in two parts.

- **Items (code, `planner.along_wall`).** On every detour call (walled, blocked or stall) two items
  go first on the menu: "along the wall, left (right) of the way to the goal, up to N m". The
  wall's direction is the main axis of the map's wall cells within 3 m toward the goal (square to
  the goal with fewer than 3); each item ends where the map shows a wall, at most 5 m on; a side
  with under 1.5 m of room is left off and the other says so. Each says how often its side was
  chosen before. Parameters and wording: `agent.ALONG_WALL_A39`, in the features, so the sha.
- **Strategist `q08`** (q03 with the closing advice replaced): a wall usually stands between the
  drone and the goal and the way round is along it; follow one side until it ends, then the other;
  start on the side worded nearer the goal; doorways and unexplored ground only when no
  along-the-wall item is listed.
- **Hand-back.** An along-the-wall detour also ends when, after 2 steps on it, the way toward the
  goal is open with the goal within 60° of the heading (`along_way_open`); otherwise it holds until
  reached, stalled (a33) or 12 steps, as every detour.

## Evidence

- R15/R15N failure analysis ([failure_analysis.md](../R15_known_goal_reach/failure_analysis.md),
  mode B, Q4 change 2): no along-wall search at a blocking wall was primary in 7 of 17 failures,
  about 368 steps; 148 failed-run steps within 2.5 m of closed door B; walled calls ended in
  `explore` 28/61 and 29/72 times. R11's wins came from a long-held goal-side phantom that slid the
  drone along the wall (R11 spans 9.9 steps, R15 4.2).
- Items, no model (`eval/r21_along_probe.py items`, rebuilt memory at every recorded detour call,
  scored on R11's `analysis/geo.py`):

  | | calls | 2 / 1 / 0 items | item end free, clear line | at the divider: along it | toward an open door |
  |---|---|---|---|---|---|
  | R15 | 96 | 51 / 37 / 8 | 80% | 84% | 48% |
  | R15N | 97 | 54 / 35 / 8 | 76% | 89% | 52% |
  | R16K | 76 | 41 / 30 / 5 | 84% | 78% | 43% |

  One side of two leads to the open door, so about half is what the items can give; which side is
  the strategist's choice.
- Strategist, live (`eval/r21_along_probe.py run`/`score`, q08 on the recorded calls of R15, R15N
  and R16K with the items added and the situation worded again, text only):
  [probe/q08_score.txt](probe/q08_score.txt). 267 of 269 calls answered. An along item was
  picked on **245 of 246** calls that listed one (the rest: unexplored ground 14, doorway 7,
  explore 1). At the divider the side picked led toward the open door 73 of 139 times (53%): the
  first side is a coin flip, so what pays is following it to its end and then turning back
  ("followed N times" wording), which a replay of single calls cannot show. **Gate passed.**
- Smoke (`eval/r12_probe.py` `smoke_run`, stub strategist picks the first item, R15's 827
  manifests): `a39`, `a40`, `a41` 0 failed steps; 86 of 93 detour calls list an along item. A first
  version handed an along detour back whenever `goal_way` read open, which counts a goal off to the
  side as open: 77 hand-backs after 2 steps. Now only with the goal within 60° of the heading: 20.

## Hypothesis

Following the wall that stopped the drone finds the open door at the s02 divider, and the tines
past the s03 crossbar, where reachable frontiers and false doorways did not: R21 scores above R20.

## Predictions

| Arm | Baseline (R20, `a37`) | Predicted |
|---|---|---|
| initial | R20's | same (± 1) |
| final | R20's | + 1 or more (s02 final runs) |
| dynamic | R20's | + 1 |

Total ≥ R20 + 1. Steps within 2.5 m of closed door B in failed s02 runs: under half of R20's.

## Manipulation check

Along-the-wall items picked on at least half the detour calls that list one; mean span of a
non-goal target ≥ 6 steps (R15: 4.2).

## Drop criterion

Not carried forward if the total does not beat R20.

## Probe gate

Not a perception change. Set before the live probe: q08 picks an along item on ≥ 60% of calls
that list one.

## Builds on

R20 (`a37`: `a35` + doorway confirmer `d01`).

## Outcome

Flown 2026-10-29, lanes 1–4 beside R21K: 18/18 valid. **11/18** (initial 5, final 2, dynamic 4)
against R20's 11/18: **total not beaten, hypothesis not held**; the arms moved apart.

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | . | . |
| s02c | 1 | 1 | 1 |
| s02va | 1 | . | 1 |
| s02vc | 1 | . | 1 |
| s03 | . | . | . |

- `dynamic` 4/6 (R20 1/6; the best dynamic arm in Phase 2): s02va and s02vc `dynamic` solved for
  the first time in any round.
- `final` 2/6 (R20 4/6): s02a `final` ended 12.9 m away (R20 reached it in 42 steps); s03 0/3
  (R20 2/3), s03 `final` 27.3 m away.
- Manipulation took: an along item picked on 79 of the 84 calls that listed one. Not the span:
  mean non-goal target span 3.4 steps (R20 3.1; predicted ≥ 6). Stalled-detour hand-backs 28
  (R20 10): along items stall, the drone does not slide along the wall as far as the item lies.
- [manipulation.txt](manipulation.txt).
