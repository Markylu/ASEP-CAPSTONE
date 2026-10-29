# Probe E0: do old blocks and "searched" notes mislead after a door switch? (no model)

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), section E. Script:
`eval/probes/e0.py`.

## Belief

A map for a changing world has to forget (DynaMem; LiSoNav; EvoNav). Our doorways already update
with the newest reading winning. Blocks and seen cells never expire. So after the s02 switch opens
a door, notes made before the switch may still steer the drone away from the new way.

## Method

Every s02 `dynamic` run (s02a, s02c, s02va, s02vc), R15–R26N. The switch step comes from the
`doors_switched` event in `metrics.json`. The world changes from the next step on.

- **Door-ward action.** For each recorded navigator call after the switch, a forward action is
  door-ward when the switch opened its heading: the geo ray along it (12 m cap) is at least 1.0 m
  longer in the new world than in the old.
- **Stale note.** A door-ward action carries a stale note when its recorded tags (exactly what the
  navigator was shown) include:
  - "blocked here before (step s)" or "stopped short here before (step s)" with s at or before the
    switch, or
  - "searched already this way".
- **Secondary readouts** (memory rebuilt with the run's agent config):
  - a `wall` or `stop_wall` cell within 1.0 m of the newly opened door's centre, on calls after
    the switch;
  - a listed opening within 2.5 m of the now-shut door B, not marked closed, more than 3 steps
    after the switch.

**Unit:** the run. A run counts when at least one door-ward action was offered after the switch.

## Gate (set before the first run)

| Share of counted runs with at least one stale note on a door-ward action | Consequence |
|---|---|
| ≥ 30% | Belief E holds. Next step: an expiry rule (a later look that sees floor clears a block or seen cell), probed before any round |
| < 10% | E dropped |
| In between | Reported, no call |

Solved rates for runs with and without stale notes are reported. They are not part of the gate,
because the sample is small.

## Result

Pending.
