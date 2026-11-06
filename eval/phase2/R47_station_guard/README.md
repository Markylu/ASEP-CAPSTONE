# R47: a86 with the survey's stations shut only by walls the drone has met, contested cells

**Agent:** `a87` (`aaf90e0ca54d`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A87` ·
**Navigator notes:** `NAVIGATOR_A86` ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R44's flight, while R45 was in the air and R46 queued
behind it; shakedown flown 2026-11-06 (four of four s02c runs solved, gate passed); **flown
2026-11-06, 12/30, dropped**

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R44 (`a84`, 18/30, the bar since tonight), R32P (`a66`, 15/30) and
R45 and R46 as they land.

## Change

One setting against `a86` (R46): `station_guard: "hard"` (`agent.SURVEY_A87`, read in
`planner.survey_start`). When the survey starts, a station is shut only if a wall the drone
has met lies on the straight line to it: a stop wall, a nose-on wall, a shut door's wall.
`a80` to `a86` shut a station if any cell on that line was impassable on the route's cost
map, which includes the walls the perceiver reads through open floor and the unknown cells
sealed beside them. Everything else is `a86`'s.

## Evidence

- **R44 (`a84`), s02**: the survey started in 22 of 24 runs, and in 8 of them with one station
  only. In the six looked at cell by cell, five had a single cell sealed beside a perceiver
  wall on the line to the shut station and one a near-wall cell; none had a wall the drone had
  met. In four s02c runs (`final` 2 and 3, `dynamic` 2 and 3) the station shut was the one on
  the open door's side: the survey flew at the other side's wall and ended by step 11. Three
  of those four were lost or won only at steps 45 and 60 on the route. s02c was 3/6.
- **Open loop on R44's records**: at the step each survey started, both stations stand in 14
  of 22 runs under `a86`'s rule and in 22 of 22 under this one.
- The guard was written for corridors (in an s03 tine the side walls are on the map). Since
  `a82` the survey starts only on the drone's first way in along the direct line, which is
  never a tine, so the guard has nothing left to do there; a station that really is behind a
  wall is given up after six steps without coming nearer.

## Hypothesis

With both stations open to it, the survey goes to the open door's side in the s02c runs it now
abandons; `a87` scores at least as well as `a86` and at least 18/30.

## Predictions

| Cell group | R32P (`a66`) | R44 (`a84`) | Predicted `a87` |
|---|---|---|---|
| s02 `final` ×4 | 6/12 | 7/12 | 8–10 |
| s02 `dynamic` ×4 | 6/12 | 6/12 | 8–10 |
| s03 `final` | 3/3 | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 2/3 | 1–3 |
| **total** | **15/30** | **18/30** | **19–25** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

`eval/probes/a80_check.py`: the survey starts with both stations in at least 20 of the s02
runs it starts in (R44: 14 of 22); R46's rows otherwise.

## Drop criterion

Not carried forward below 18/30 (R44's score), or 3 or more under the best of R44, R45 and
R46. Carried at 3 or more above R44, or as the last agent of the night if it is the newest
version at or above the best.

## Probe gate

**No model probe** (code only against `a86`; nothing the model is told or asked changes).

- Open loop on R44 (above): 22 of 22. Closed loop, no model (`eval/probes/a80_sim.py --agent
  a87 --far 20`, `eval/phase2/_probes/a87/`): truthful perceiver 32/32; misreads and 20%
  random moves 70/96 (`a86` 69, `a84` 59, `a66` 48). Passed.
- `python -m pytest server/decider/tests -q`: 76 pass. Smoke 627/627. Earlier agents keep
  their shas (`a86` `cd6b8de756ab`).

**Shakedown gate** (on-policy, slot 5 as a fifth client beside the flight in the air): the
four s02c runs above (s02c `final` 2 and 3, `dynamic` 2 and 3). Passes if the survey starts
with both stations in at least three of the four, and a route is on at least 95% of steps.
Wins are not required.

## Builds on

`a86` (R46). Branch `phase2/r47-station-guard` from `phase2/r46-behind-always` (`071cc62`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a87`; `/health` should
  report `aaf90e0ca54d`.

## Outcome

**Flown 2026-11-06: 12/30 against `a86`'s 21/30 (R46) and `a85`'s 23/30 (R45); dropped.** The
hypothesis did not hold. s03 1/6 on code that is `a86`'s there (R46 5/6); s02 11/24: 7 of 7 surveys
that crossed from their first station won, 2 of 11 that went on to the second.
[summary.md](summary.md). Labels: Claude review, not yet confirmed by the operator.

**Shakedown (2026-11-06, 06:32–06:47 UTC): four unscored runs, slot 5 (port 8105) as a fifth
client beside R45's four lanes, sctsvr6 `~/asep-r33-shake` at `3ce00d1`, log
`~/r47_shake_a87.log`. All valid, all four solved. Gate passed.** (`eval/probes/a80_check.py`.)

| Cell (seed) | `a87` | R44 `a84`, same cell and seed | Survey | Crossed |
|---|---|---|---|---|
| s02c `final` (2) | solved, 36 | solved, 60 (one station) | did not start (no closed door read dead ahead on the way in); the route crossed, after a latch at 10 off the direct line | 28 |
| s02c `final` (3) | **solved, 26** | lost (one station) | both stations; the door flown at from step 7, through at 18 | 18 |
| s02c `dynamic` (2) | **solved, 25** | lost (one station) | both stations; station at 11, door flown at from 14, through at 17 | 17 |
| s02c `dynamic` (3) | solved, 22 | solved, 45 (one station) | both stations; door flown at from 11, through at 14 | 14 |

- **Gate:** the survey starts with both stations in at least three of the four: three (the
  fourth did not start). A route on every step. Passed.
- The three runs with a survey crossed at steps 14 to 18, on the survey; in R44 the same three
  had one station, on the wrong side, and crossed at 36 or never.
