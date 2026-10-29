# R19: R15N with "searched already" defined and stalled detours handed back (a35; R19K flies a36)

**Agent:** `a35` (`c003fd885a4a`) · **Navigator prompt:** `p17` (`cb3578251cfe`, new) ·
**Detour strategist:** `q03` · everything else as `a26` (R15N) · **Status:** pre-registered
2026-10-29, built overnight without the operator (operator, 2026-10-28: "fix any issues found in
probing, any loops any errors and whatnot, then fly the agent").

Second agent at the same SHA: **R19K**, `a36` (`1aee9212aeee`) = `a35` with the goal confirmer
`c01`; [R19K's README](../R19K_searched_defined_confirmer/README.md).

R19 flies in the slot queued for R18 (`a33`/`a34`: `q07` plus the stalled-detour hand-back).
R15's failure analysis found that the menu doorways `q07` prefers are real on 4 of 54 menus, so
R18 was taken off the queue unflown; its stalled-detour hand-back is carried here on `q03`.

## Change against `a26` (R15N)

1. **Navigator prompt `p17`** = `p16` with a17's coverage note defined and turning around limited:
   - '"searched already this way": the camera has looked that way before; the drone has not
     flown there. It is not a dead end and no reason to turn around.'
   - "Turn around only when 'toward your target' is on marker 0, or when every forward move is
     blocked before, stopped short or 'wall close'." (replaces "Turning around is also the move
     when every way ahead is blocked").
2. **Stalled detours handed back** (`a33`'s code, [R18's README](../R18_detour_stall/README.md)):
   4 moves on a detour gaining under 0.5 m hand it back; such detours are left off later menus.

## Evidence

- R15/R15N failure analysis ([../R15_known_goal_reach/failure_analysis.md](../R15_known_goal_reach/failure_analysis.md)):
  mode A, turning around against a forward "toward your target" while every forward move says
  "searched already this way": 50 a round (R11 3), primary in all 5 s03 failures and R15
  `s01/dynamic`; the navigator's reason reads the note as "explored, did not lead to the goal".
  Mode E (orbit) and part of C (detours that do not pay) are what the hand-back targets.
- Navigator probe ([probe/nav_score.txt](probe/nav_score.txt), `eval/r19_nav_probe.py`, live on the
  flight host, R15 and R15N's recorded steps with their frames, 480 calls, 0 failed):

  | set | p16 | **p17** | want |
  |---|---|---|---|
  | `ta`: recorded turn-around against a forward "toward" (100) | toward 23%, turned 72% | **toward 55%, turned 42%** | toward up |
  | `kept`: forward "toward" followed (80) | 94% | 99% | unchanged |
  | `back`: "toward" on marker 0 (60) | 72% | 77% | unchanged |

  Of the 100 `ta` steps about 21 had the toward move truly blocked within 2.2 m (failure
  analysis), so 55% is near the ceiling of what should change.
- Smoke (stub replies, recorded moves, R15's 827 manifests): `a35` and `a36` 0 failed steps;
  60 and 62 `detour_stalled` hand-backs; `a36` 143 confirmer calls.

## Hypothesis

With the drone no longer turning back from a forward "toward your target" on searched ground,
and detours that do not pay dropped, the known-goal agent beats R11 (11/18).

## Predictions

| Measure | R15N (`a26`) | R19 |
|---|---|---|
| total | 10/18 | ≥ 12/18 |
| turn-arounds against a forward "toward" | 50 | ≤ 25 |
| s03 solved (any arm) | 0/3 | ≥ 1/3 |
| steps on a stalled detour (`eval/r18_stalled_steps.py`) | 43 | ≤ 25 |

## Drop criterion

Not carried forward if it does not beat R15N. If it beats R11, it is the agent to build on.

## Outcome

Not flown.
