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

Pending.
