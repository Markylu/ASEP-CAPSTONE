# R20: R19 with the doorway confirmer

**Agent:** `a37` (`a07b58847180`) · **Prompt:** `p17` (`cb3578251cfe`) · **Doorway confirmer:**
`d01` (`95c80a5ef984`) · **Status:** pre-registered 2026-10-29, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Built overnight without the operator
(operator, 2026-10-28: "mantain a prefrence for subagents over hard coded tasks").

Second agent at the same SHA: **R20K**, `a38` (`5f54e18d45cb`) = `a37` + goal confirmer `c01`
([R20K](../R20K_door_confirmer_goal_confirmer/README.md)).

## Change

One against `a35` (R19): the doorway confirmer `d01`, a new subagent after the perceiver (and
after `c01` where an agent has it). When the perceiver reports an open doorway in one or more
strips, a second call on the same clean frame answers per reported strip: `open` (a gap the drone
could fly through, floor visible beyond), `closed` (a door fills it) or `none`. `closed` marks that
strip's doorway closed and `none` removes it (both keep `doorway_reported: open`) before the map
lists openings. A failed call keeps the reports. Recorded as `door_confirmer`.

## Evidence

- R15/R15N failure analysis ([failure_analysis.md](../R15_known_goal_reach/failure_analysis.md)):
  detour-menu doorway items were at a truly open door 4 of 54 (R15) and 5 of 52 (R15N) times; most
  s02 doorway items lay over 2.5 m from any door; the closed exit was picked as a detour in R15N
  s03/final.
- Doorway probe ([probe/d01_r15_score.txt](probe/d01_r15_score.txt), `eval/r20_door_probe.py`,
  live model on the flight host): every R15 step with an open-doorway report (252 steps, 428
  strip reports), each strip scored against the site model (R11's `analysis/geo.py`: a ray in the
  strip from the drone's pose passes through a door open at that step). 0 failed calls.

  | | genuine kept | false refused |
  |---|---|---|
  | all | **72/78 (92.3%)** | **215/350 (61.4%)** |
  | s01 (no doors) | – | 15/17 |
  | s02 | 63/69 | 191/318 |
  | s03 | 9/9 | 9/15 |

- Smoke (`eval/r12_probe.py` stub answering open/closed/none in turn, R15's 827 manifests): `a37`
  and `a38` 0 failed steps, 252 doorway-confirmer calls each.

## Hypothesis

With most false doorways off the map, detours stop sending the drone at closed doors and blank
walls, so R20 scores above R19.

## Predictions

| Arm | Baseline (R19, `a35`) | Predicted |
|---|---|---|
| initial | R19's | same (± 1) |
| final | R19's | + 1 |
| dynamic | R19's | + 1 |

Total ≥ R19 + 1.

## Manipulation check

`door_confirmer` recorded on every step with an open-doorway report; share of reported open
doorways that survive ≤ 60% (probe: 72 + 135 of 428 kept = 48%).

## Drop criterion

Not carried forward if the total does not beat R19.

## Probe gate

Set before the probe ran, as `c01`'s: genuine kept ≥ 90%, false refused ≥ 50%. **Passed**
(92.3%, 61.4%).

## Builds on

R19 (`a35`: `a26` + navigator `p17` + stalled-detour hand-back).

## Outcome

Flown 2026-10-29, lanes 1–4 beside R20K: 18/18 valid. **11/18** (initial 6, final 4, dynamic 1)
against R19's 10/18: **hypothesis held, by one**; level with R11. `final` + 2 as predicted,
`dynamic` − 1 (R19 2).

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | 1 | . |
| s02c | 1 | 1 | . |
| s02va | 1 | . | . |
| s02vc | 1 | . | . |
| s03 | 1 | 1 | . |

- `d01` asked on 238 steps, 0 failed calls. Doorways on the detour menus 20 (R19 50); picked 7
  (R19 17). Menu doorways within 2.5 m of an open s02 door 1 of 20 (R19 10 of 50): the confirmer
  removed most false ones and some real ones; the gain is the drone no longer sent to closed doors.
- Turn-arounds against a forward "toward" 14 (R19 25).
- R24's through-the-doorway items, built from R20's confirmed sightings, aimed at an open door 2 of
  11 times (`eval/r24_through_probe.py`): confirmed sightings are still too few and too scattered
  to place a gap.
- [manipulation.txt](manipulation.txt).
