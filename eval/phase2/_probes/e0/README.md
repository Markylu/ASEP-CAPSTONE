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

Run 2026-10-29 on sctsvr6 (`b2d262f`): 72 s02 `dynamic` runs with a switch, R15–R26N, of which
56 were offered a door-ward action after it. Full output: [score.txt](score.txt), per run:
[runs.jsonl](runs.jsonl).

| Readout | Result |
|---|---|
| Runs with a stale note on a door-ward action | **17/56 = 30% → gate: holds, exactly on the threshold** |
| Door-ward calls with a stale note | 34/219 (pre-switch block notes 0, "searched" notes 46) |
| Solved, with vs without stale notes | 9/17 = 53% vs 16/39 = 41% |
| Wall cell within 1 m of the new door after the switch | 18/72 = 25% of runs |
| Open doorway still listed at shut door B, > 3 steps after the switch | **23/72 = 32% of runs** |

**Reading.** The belief holds as registered, but weakly:
- It sits exactly on the 30% line.
- Every stale note is "searched already this way", and the definition counts every such note on a
  door-ward action, including ones built from cells seen after the switch. So 30% is an upper
  bound.
- No pre-switch block note ever appeared.
- Runs with stale notes solved *more* often (53% vs 41%), the opposite of harm.

The stronger finding is the secondary one, and it runs the other way: **in a third of runs, the
memory still offers door B as an open doorway after it has shut.** Doorways update newest-first,
but only when looked at again. The drone usually does not look back, so the stale "open" survives.
Any follow-up should start there (expiring openings at doors a switch can close, or re-checking
before a detour to one), not with expiring "searched" cells.
