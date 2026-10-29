# R18: R17 with stalled detours handed back (a33; R18K flies a34 beside it)

**Agent:** `a33` (`f32d6cd48ceb`) · **Navigator prompt:** `p14` · **Detour strategist:** `q07` ·
everything else as `a31` (R17) · **Status:** pre-registered 2026-10-29, built overnight without the
operator (operator, 2026-10-28: "fix any issues found in probing, any loops any errors").

Second agent at the same SHA: **R18K**, `a34` (`335f604f2a75`) = `a32` (R17K) with the same change;
[R18K's README](../R18K_detour_stall_confirmer/README.md). Laid out while R15 flew, before R16 and
R17 were read.

## Change against `a31` (R17)

Code, in the planner (`planner.detour_stalled`, `planner.failed_detours`; feature
`detour_stall: {steps: 4, gain_m: 0.5}`):

1. A detour stands only while it pays: when the last 4 moves, all on it, brought the drone less
   than 0.5 m nearer it, it is handed back (`detour_stalled`) and the goal is the target again.
   Before: a detour stood until reached, closed, 12 steps, or the goal in view.
2. Detours handed back stalled or too long are left off later menus (`search_menu`'s blacklist,
   1.5 m), so the strategist cannot pick the same one again (R11 failure analysis Q6, fix 1d).

## Evidence

- R15 `s01/final` (`a25`, live): from step 12 the target was a frontier 3–4 m abeam; the navigator
  flew "sharp right: toward your target" for 12 steps and circled it at that distance until
  `detour_too_long` at step 25. The fan has no 90° turn, so a near target abeam is orbited.
- Steps on a standing detour that 4 moves brought under 0.5 m nearer, more than 1.5 m from it
  ([probe/stalled_steps.txt](probe/stalled_steps.txt), `eval/r18_stalled_steps.py`): R11 156/706,
  R12 181/862, R14 164/840, R15 (first 12 runs) 32/475. Mostly 4–8 m from the target.
- Smoke (stub replies, recorded moves): `a33`/`a34` on R15's first 12 runs (475 steps) and R12's 862
  manifests, 0 failed steps; 32 and 69 `detour_stalled` hand-backs, no `detour_too_long` left.

## Hypothesis

Steps that went into circling or pressing on a detour that does not pay go back to the goal or to
a different detour, so the known-goal agent reaches the goal more often in `final`/`dynamic`.

## Predictions

| Measure | R17 (`a31`) | R18 |
|---|---|---|
| total | see R17's Outcome | ≥ R17 + 1 |
| steps stalled on a detour (`eval/r18_stalled_steps.py`) | | ≤ 1/2 of R17's |

## Drop criterion

Not carried forward if it does not beat R17. A hand-back that fires on detours that would have
paid (round the end of a wall) would show as more strategist calls and no fewer stalled steps.

## Outcome

Not flown.
