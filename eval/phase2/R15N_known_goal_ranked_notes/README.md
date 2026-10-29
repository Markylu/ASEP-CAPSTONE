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
| `p14` | 47/228 (21%) | 36/48 (75%) |
| `p15` (one sentence changed) | 71/228 (31%) | 37/49 (76%) |
| `p16` | see probe/ | see probe/ |

With `a17`'s memory "toward" rarely sits on marker 0 (it goes on the sharpest open move on the
target's side), so the probe's `back` set overstates the change's reach; `ahead` checks it does
no harm.

## Outcome

Not flown. Read against R15 and R11; [R15's README](../R15_known_goal_reach/README.md).
