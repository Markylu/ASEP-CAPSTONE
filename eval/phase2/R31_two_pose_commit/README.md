# R31: a66 with one-look-is-soft memory (a17h) and route commitment

**Agent:** `a72` (`135da10673e9`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17h` · **Planner:** `PATHFINDER_A72` · **Status:**
laid out 2026-11-04 on the operator's instruction ("Build a72"); offline gate on R30's records
failed as registered; **not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Design and evidence:
[docs/research/r30-analysis-and-proposals.md](../../../docs/research/r30-analysis-and-proposals.md),
proposals P1 and P2. A bundle of two changes on the operator's decision, credited to the bundle.

## Change

Two changes against `a66` (R30, 14/18, equal to R25D's `a49`), both code only; the perceiver
`g05`, the door confirmer `d01`, the navigator `p17`, the tags, the turn rule and goal truth on
the planner side are `a66`'s.

- **Memory `a17h`: one look is soft** (`spatial.SpatialConfig.two_pose`, `PARAMS_A17H`,
  built on `a17e`: side-strip near walls, no firm walls from one look).
  1. An open doorway `d01` confirmed writes **soft** floor through its gap (`soft_door`: passable
     at unknown cost, never sealed, seals nothing, pops suspects and near walls only) until the
     opening has been seen open from two poses at least `confirm_m` (1 m) apart; then its rays
     are strong, as `a17d` wrote them from the first look.
  2. A nose-on wall run (three or more adjacent `no_floor` strips) and a closed-door wall are
     perceiver walls (seen floor pops them, as `a17b`) until read again from a pose 1 m away
     within a cell of the first read; then **firm** (`firm_wall`, a visit alone erases). `a17f`
     made them firm from one read.
  3. A strong close (a `d01` `closed` at the opening, or a nose-on wall run whose cells come
     within `veto_m` 1.5 m of it) closes the opening and erases its soft floor; two strong closes
     from poses 1 m apart kill it (`dead`): a later open sighting at that spot is a misread and
     writes nothing.
- **Route commitment** (`planner.committed_route`, `PATHFINDER_A72["commit"]`): the previous
  step's route is kept, from the nearest route cell on, unless the drone has left it by more
  than `leave_cells` (2), the rest is impassable on this step's map, or a fresh search is at
  least `gain` (25%) cheaper. Recorded per step as `planner.kept` and `planner.fresh_m`.

## Evidence

- a70 and a71 (R30 shakedown) lost s02c, s02a and s02va to a doorway `g05` reported and `d01`
  confirmed in the divider where there is none; `spatial._observe_a17d` wrote 6 m of strong floor
  through it from that one look, the route went there, and the next look re-opened it
  ([R30 README](../R30_pathfinder/README.md), shakedown a70, a71).
- a71 lost s03 `dynamic` in the lobby: one nose-on `no_floor` read down the stem at s4, made a
  firm wall by `a17f`, erased only by a visit the wall forbade (R30 README, a71).
- R30 s03 `dynamic` and a70's: at the shut door the route alternated every two or three steps
  between the door and the 40 m way out as single cells sealed; `planner.astar` replans from
  scratch each step ([labels.csv](../R30_pathfinder/labels.csv), R30 summary).
- R30 s02vc `final`: 48 steps within 4 m of the divider as the route hopped between unsealed
  divider cells.

## Hypothesis

With doorway floor and firm walls granted only from two poses, and the route kept between
steps, `a72` crosses the s02 divider through the real door more often than `a66` and does not
oscillate at the s03 shut door, and scores at least 14/18.

## Predictions

| Arm | Baseline (R30, `a66`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 4 | 4 or 5 (s02vc `final` back; s02va `final` the family-hard cell) |
| dynamic | 4 | 4 or 5 (s02a `dynamic` back; s03 `dynamic` needs the recovery to start at once) |

Total ≥ 14/18. **Noise.** The `a17b` family expects 11.3 ± 1.4; one seed-1 round cannot
resolve ±1–2 runs (why_14).

## Manipulation check

Code only, from `decisions.jsonl` (`eval/r30_check.py`, `eval/r28_flight.py`, and the `planner`
and `spatial` records):
- `planner.kept` on ≥ 60% of steps with a previous route; route flips (waypoint bearing turned
  > 90° between consecutive steps) in s03 `dynamic` and s02vc `final` at most half of R30's.
- Openings confirmed (`spatial.openings[].confirmed`) only where a door is; a phantom opening
  reaches `dead` within 10 steps of its first close.
- s03 `final`/`dynamic`: steps in the shut tine after the first confirmed closed door ≤ 8; steps
  in the open tine > 0; lobby ≤ 12 in every arm.
- A route on ≥ 95% of steps; no turn-around streak of 10 or more; walls in flight within 4 points
  of R30's (missed 18.5%, phantom 11.1%).

## Drop criterion

Not carried forward below 14/18, or if the route still crosses the s02 divider through phantom
floor on more than three quarters of the near-side steps of the failed runs.

## Probe gate

Offline, no model, on R30's 18 recorded runs (`eval/probes/a72_replay.py`, `a72_replay2.py`,
`a72_replay3.py`; write-up [_probes/a72](../_probes/a72/README.md)), thresholds written before
the run:
- (a) phantom free cells in the s02 divider (truly wall, claimed as floor by a look and passable)
  under `a17h` at most half of `a17f`'s on the same steps;
- (b) the true open door's gap no less passable than under `a17f`;
- (c) route flips in R30 s03 `dynamic` and s02vc `final` halved with commitment;
- (d) R30's solved runs keep their routes on ≥ 95% of steps.

**Outcome (2026-11-04): failed as registered.**
- (a) **fails**: 7.24 against 7.39 cells per step. It holds on the door-ray part alone (1.66
  against 4.40): the doorway rule does what it was built to do and the floor stays, because the
  divider's phantom floor is painted by ordinary `open_far` rays from 3–4 m out and a wall is
  written only within 1 m. Under `a66`'s memory every free cell is strong.
- (b) holds: 84% against 85%.
- (c) **fails**: s03 `dynamic` 8 → 7, s02vc `final` 5 → 7; over all 626 steps 34 → 35 (the memory
  change alone raised it to 44). Open loop understates commitment (the drone leaves a kept route
  it did not fly) and cannot say by how much.
- (d) not scored.
- Two poses do not separate phantom doorways from real ones: 20 phantom openings confirmed, 4
  real. Where the route crosses the divider on the 305 near-side s02 `final`/`dynamic` steps: `a66`
  through the true gap 10%, `a72` 7%, `a72` on weak far floor 7%, `a17g` alone 12%; a 5-cell wall
  halo 19% at double the flips and the real door sealed on 26% of steps (`a72_replay4.py`).

By the rule above `a72` is not carried to a flight on this probe. What the probe says instead:
the s02 divider is unknown to the map until the drone is within 1 m of it, and no memory or
planner rule tried routes through the real door while the map holds about seven phantom floor
cells per step on the wall. The lever is the reading at 2–4 m (the R30 verdict), not the map.
The stem-mouth case (a71) could not be tested: those runs are on the host only.

## Builds on

R30 (`a66`). Branch `phase2/r31-two-pose-commit` from `phase2/r30-pathfinder`.

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (19 pass);
  `VLM_AGENT=a72 python eval/probes/a63_smoke.py` (R25D's 627 recorded steps: 0 failed, a route
  on 627/627, fallbacks none 626 / soft 1, as `a66`).
- **Preflight, if flown against the gate:** `python -m server.decider --profile remote --agent a72`;
  `/health` should report `135da10673e9`. A shakedown first (one `dynamic` run per site, s03
  first, alone on `:8004`), scored by `eval/r30_check.py` and `eval/r28_flight.py`, plus the
  `kept` and `confirmed`/`dead` counts above.
- Earlier agents keep their shas (`a49` `83f7a6a19b01`, `a66` `de7f23d07186`, `a70`
  `cf82ad60b931`): the a17h code paths run only for `two_pose` memories.

## Outcome

Not flown: the offline gate failed (Probe gate). The best agent is still `a49` (R25D) or `a66`
(R30), both 14/18.
