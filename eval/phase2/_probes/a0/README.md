# Probe A0: position and left/right in recorded picks (no model)

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), section A. Script:
`eval/probes/a0.py`.

## Belief

The model picks partly by list position, not only by content, so menu order is a hidden lever
(Zheng et al., ICLR 2024; Pezeshkpour & Hruschka, 2024).

## Method

All recorded runs, R11–R26N, loaded through the lane index.

- **Strategist.** Every call with a menu. An item is *good* when its ground-truth path to the goal
  (geo, with the run's own door state, Dijkstra on a 0.25 m grid) is at least 1 m shorter than the
  drone's. Compare the pick rate of first-listed items with items listed 2nd or later, separately
  for good and not-good items.
- **Strategist, by kind.** Report the pick rate when listed. Backtrack items are also counted
  separately while the drone is in the s03 shut tine.
- **Navigator.** The slot order is set by angle, so only a lean can be read. Compare how often
  "toward your target" is followed on slot 1 against slot 5, and on slot 2 against slot 4. When
  mirrored slots carry identical notes and one of them is picked, report the share that went left.

## Gate (set before the full run)

| Readout | Threshold | Consequence |
|---|---|---|
| Position signal | first-listed minus later ≥ 15 pts, among good or among not-good items | A1 (permutation) goes first among the model probes |
| Content signal | good minus not-good ≥ 15 pts at both positions | Reported only |
| Left/right lean | \|lean\| ≥ 10 pts, or tie share outside 40–60% with n ≥ 50 | C1 (mirror) gets the lean as a primary readout |

A0 is descriptive and cannot refute belief A on its own. Position and content are confounded,
because code lists better items first. A1's permutation is the test that settles it.

**Disclosure.** Before this README was committed, the script ran once on R25 only (R25 and R25D),
to check that it ran without errors. That run printed a position effect of +16 pts among not-good
items and a lean of −37 pts. The thresholds above were already in the code before that run, and
they were not changed after it. The R25 output was overwritten by the full run.

## Result

Run 2026-10-29 on sctsvr6 (`~/asep-research-probes`, `b2d262f`), through the lane index:
2,679 strategist calls (10,749 menu items) and 19,178 navigator calls, R11–R26N. Full output:
[score.txt](score.txt).

| Readout | Result | Gate |
|---|---|---|
| Position | First-listed items picked 57% (good) and 49% (not good); later items 16% and 8%. Effect +41 and +42 pts | **YES** |
| Content | Good minus not-good: +8 pts first-listed, +9 pts later | no |
| Lean | "toward" followed 50% on slot 1 vs 81% on slot 5; 34% on slot 2 vs 67% on slot 4. Mean −32 pts (right favoured). Identical notes on mirrored slots: left picked 302/429 = 70% | **YES** |

**Reading.**
- Where an item sits in the list matters about five times more than whether it leads toward the
  goal. A not-good item listed first (49%) is picked three times as often as a good item listed
  later (16%). This is still confounded, because code lists its best-scored item first and geo's
  "good" is not code's score. A1 is the clean test, and it now goes first among the model probes.
- Backtrack items are almost never picked: 86/2,536 (3%) overall and 1/74 inside the s03 shut
  tine. That matches the "listed but ignored" pattern behind B.
- The lean points both ways. The navigator follows "toward" far more on the right, yet on ties it
  goes left 70% of the time. Site geometry may drive part of this: s03's shut tine is L in
  `final`, and s02a/s02c are mirror pairs. So this is a flag for C1, not a conclusion.
