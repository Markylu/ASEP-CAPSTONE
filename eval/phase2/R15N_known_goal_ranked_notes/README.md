# R15N: R15 with the navigator's notes ranked (a26, p16)

**Agent:** `a26` (`a4434efe7cf4`) · **Navigator prompt:** `p16` (`9cae9e381fd6`) ·
everything else as `a25` (R15) · **Status:** pre-registered 2026-10-29, not flown.

`a26` is `a25` with one change: the navigator prompt. `p16` is `p14` with its closing advice
replaced by an order: a move with a goal note; then the move with "toward your target", marker 0
included ("your target is behind you: turn around, even when the way ahead looks open and new");
then new ground. `p14` said "prefer new ground" and "turning around is a normal move when every
way ahead is blocked", and marker 0 nearly always carries "behind you is ground you have covered".

## Probe (live, on R11's recorded steps; `eval/r15_nav_probe.py`)

Each recorded step with "toward your target" on a visible action asked again with its recorded
navigator text and annotated frame on the flight host, under each prompt's system text
([probe/](probe/)):

| prompt | "toward" on marker 0 followed | "toward" on a forward move followed |
|---|---|---|
| `p14` | 47/228 (21%) | 107/150 (71%) |
| `p15` (one sentence changed) | 71/228 (31%) | 115/150 (77%) |
| `p16` | **83/228 (36%)** | **115/150 (77%)** |

With `a17`'s memory "toward" rarely sits on marker 0 (it goes on the sharpest open move on the
target's side), so the probe's `back` set overstates the change's reach; `ahead` checks it does
no harm. The R13 failure analysis warns that in the no-truth agents (`a19`/`a20`) the navigator
already follows "toward" on marker 0 70–80% of the time (ping-pong on false walls), so `p16` is
flown only on the known-goal agent here.

## Outcome

Flown 2026-10-29 03:50–04:30 UTC beside R15, 4 lanes, 18/18 valid. **10/18**: `initial` 5/6 (s03
failed), `final` 3/6 (s01, s02c, s02va), `dynamic` 2/6 (s01, s02vc). R15 (same agent with `p14`)
9/18, R11 11/18. One run above R15, one below R11: within the spread of one seed. Strategist
doorway picks 17/37; steps on a stalled detour 43/786 (R15 68/827). Per run:
[manipulation.txt](manipulation.txt). Read with R15's [failure analysis](../R15_known_goal_reach/failure_analysis.md).
