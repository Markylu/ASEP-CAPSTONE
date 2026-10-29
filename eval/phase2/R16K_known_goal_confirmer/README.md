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

Flown 2026-10-29 04:25–05:00 UTC beside R16, 4 lanes, 18/18 valid. **10/18**: `initial` 5/6 (s03
failed), `final` 2/6 (s01, s02va), `dynamic` 3/6 (s01, s02c, s02va; best `dynamic` of Phase 2).
R15 9/18, R15N 10/18, R11 11/18. One above R15: within one seed's spread; below R11, so not
the best agent.

- Confirmer in flight: genuine reports kept 139/151 (92%), false refused 11/17.
- "Goal in view" hand-backs 4 (R15 7); detours reached 27, closed 9, too long 4.
- Per run: [manipulation.txt](manipulation.txt); median `blocked_near` 15%, turn-arounds 7.5, max
  distance from start 22.1 m.

The confirmer stays in the known-goal line (R17K, R18K, R19K carry it): it costs one call on
steps with a goal report and did no visible harm.
