# R16K: R15 (known goal) with a goal confirmer (a28)

**Agent:** `a28` (`8128af346342`) · **Navigator prompt:** `p14` · **Strategist:** `q03` ·
**Goal confirmer:** `c01` (`5b3eb45ce241`) · everything else as `a25` (R15) · **Status:**
pre-registered 2026-10-29, not flown.

Flies beside R16 (`a27`); [R16's README](../R16_goal_confirmer/README.md) has the confirmer, its
evidence and the probe.

## Change against `a25` (R15)

One: the goal confirmer `c01` after the perceiver. A goal report it refuses becomes
`not_visible` before the planner reads it, so the known-goal agent no longer hands control to
"goal in view" on a hallucinated sighting.

## Evidence

- R11 failure analysis §0: 10 of 14 "goal in view" hand-backs were hallucinated; with the goal's
  position known the planner then steers at a goal that is not in the frame.
- Confirmer probe (R16's [probe/](../R16_goal_confirmer/probe/)): genuine reports kept 95.4%,
  false refused 72.6% (527 reports, gate passed).

## Hypothesis

Fewer false hand-backs to "goal in view" raise `a25`'s success, most in `final` and `dynamic`
where the goal starts out of sight.

## Predictions

| Measure | R15 (`a25`) | R16K |
|---|---|---|
| total | see R15's Outcome | ≥ R15 + 1 |
| steps in "goal in view" with the goal not in view (`in_view`) | | ≤ 1/2 of R15's |

## Drop criterion

Not carried forward if it does not beat R15 and R11 (11/18).

## Probe gate

As R16: confirmer probe and smoke (`a28` on R12's 862 manifests, 0 failed steps).

## Outcome

Not flown. Read against R15 and R11.
