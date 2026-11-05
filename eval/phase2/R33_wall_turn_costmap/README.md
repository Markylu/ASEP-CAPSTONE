# R33: a66 with the wall-turn rule and the Round F cost map, contested cells

**Agent:** `a73` (`7ce95fcbea92`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17i` · **Planner:** `PATHFINDER_A73` · **Status:**
laid out 2026-11-04 from Round F's 90 recorded runs; offline readouts measured (below); shakedown flown 2026-11-05, s03 lost to the cost map ([Outcome](#outcome)); **round not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Analysis of Round F:
[docs/research/round-f-analysis.md](../../../docs/research/round-f-analysis.md). A bundle of two
changes on the operator's decision ("Yes, build a73"), credited to the bundle. Design: the ten
contested cells, seeds 1–3, 30 runs, read against R32P (`a66`, 15/30) as R32 read `a49`.

## Change

Two changes against `a66` (R30, R32P 15/30, F 64/90), both code only; `g05`, `d01`, `p17`, goal
truth on the planner side and the turn rule are `a66`'s.

- **Wall-turn rule (memory `a17i`, `spatial.SpatialConfig.wall_turn`).** The step after a
  turn-around taken with every strip reading `blocked_near` (the drone faced a wall, now has its
  back to it), "toward your target" never sits on the turn-around: it goes to the open move
  nearest the target's bearing, so the turn rule (`no_repeat_when_open`) hides the turn-around
  and the drone moves along the wall. On that step a move onto ground the drone has stood on is
  open whatever this look says (the memory's own rule, a visit beats a wall mark): no "wall
  close", blocked or stopped-short note on it. Recorded per step in `spatial.nose_on` (the
  frames every strip read blocked) and `hidden`.
- **Cost map (`agent.PATHFINDER_A73`, memory `a17g`'s weak far floor).** Unknown cells cost 4
  per metre (was 2), floor seen only beyond 2.5 m along a ray 3 (`a17g`: a prior, sealable),
  suspects 6; a wall cell seals its eight neighbours, not four (`seal_diagonal`); A* takes no
  diagonal past an impassable cell (`strict_corners`). `a17i` = `a17g` + `wall_turn`, so firm
  walls and near walls are `a66`'s.

## Evidence

Round F, 90 runs, `eval/phase2/final/runs/*/decisions.jsonl` (analysis doc §3):

- **373 frames read every strip `blocked_near`** (11% of 3304 steps); the navigator turned
  around after 332 of them. 61 back-to-back turn-around pairs. s03 `dynamic` seed 3 s35–s47: 13
  turn-arounds in place, the cost map and route identical on every one (the turn-around carried
  "toward your target" each time the route lay behind; the a17 hide rule exempts a turn-around
  that alone carries it). The five s03 `dynamic` losses spent 13–21 steps on such frames.
- **10 of 20 s02 change-arm losses stood within 2 m of the open door's centre and left**
  (s02a `final` seed 2 s29: at (0.6, −9.6) inside door A's span, facing along the wall, frame
  all wall, waypoint through the divider at z −8.1). The route crossed the divider beside the
  door, not through it.
- **The route crosses walls through floor the perceiver painted.** On a73's own replayed map,
  of 1634 s02 near-side route crossings of x = 0, 1106 go through strong floor cells, 397
  through unknown, and 1192 cross six metres or more from the open door (along the goal line
  through shut door B). In s03, 205 of 223 shut-tine routes leave the tine through strong-floor
  cells of the divider, outer wall or exit wall.
- `d01` in the s02 change arms: 253 "open" verdicts on the real open door, 336 on blank wall or
  a closed door; at 3–6 m, 40 against 72. Not changed here (R31: the map's phantom floor comes
  from ordinary `open_far` rays, not doorway rays).

## Hypothesis

With the wall-turn rule, `a73` spends fewer steps turning in place at walls than `a66`, and
with far floor weak and the diagonal gaps sealed its route crosses the s02 divider through the
real door more often; it scores at least 15/30 on the contested cells.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a73` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 6–7 |
| s02 `dynamic` ×4 | 6/12 | 6–8 (s02c `dynamic` seed 1, s02vc `final` seed 5 type losses: steps given back) |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 0–1 (the recovery needs the route to leave the tine; the replay says it still rarely does) |
| **total** | **15/30** | **15–18** |

**Noise.** Three seeds per cell; the `a17b` family's spread is ±1.4 per 18. A gap under 3 on 30
runs is a draw (R32's rule).

## Manipulation check

Code only, from `decisions.jsonl` (`eval/r30_check.py`, `eval/r28_flight.py`, and the `hidden`
and `spatial.nose_on` records):
- Repeat turn-arounds after a wall turn (a turn-around on a frame with every strip blocked,
  then a turn-around on the next step): in Round F 41 of 327 such steps (12.5%). `a73` ≤ 4%.
- `hidden` carries the turn-around on ≥ 60% of steps after a wall turn where some forward move
  is open.
- A route on ≥ 95% of steps; no turn-around streak of 10 or more; walls in flight within 4
  points of Round F's (missed 16.7%, phantom 12.4%); "toward your target" taken on ≥ 70% of
  forward offers in runs with ≥ 20 offers.

## Drop criterion

Not carried forward below 15/30, or if repeat turn-arounds after a wall turn are not under half
of Round F's rate in flight (the rule did not do the one thing it was built for).

## Probe gate

Offline, no model, on Round F's 90 recorded runs (`eval/probes/a73_replay.py`, write-up
[_probes/a73](../_probes/a73/README.md)). **The readouts were measured while the agent was
being built, before this section was written; they are a record, not a pre-registration.**
The gates named in the analysis doc (§5, written before the replay) were:

| Readout | Gate (analysis doc) | `a66` | `a73` | Met |
|---|---|---|---|---|
| Repeat turn-arounds after a wall turn hidden | about all 61 pairs | 0 of 41 | **30 of 41** (73%); "toward" moved off the turn-around on 24 of 33 | partly |
| s02 near-side routes crossing the divider inside the open door's gap | ≥ 50% | 85/1638 (5%) | 134/1638 (8%) | **no** |
| s03 shut-tine routes leaving by the crossbar after the closed read | ≥ 80% | 0/223 (0%) | 4/223 (2%) | **no** |

Variants tried on the same steps (unknown cost 6, far floor 4, near floor 1.5 m): s02 8% in
each, s03 2–5%. The cost map is not the lever for the crossings: the floor the route crosses on
is strong floor from perceiver rays, which no cost change touches (a17g's weak floor moves 3
points). The wall-turn rule does what it was built for on three quarters of the loops; the
11 it leaves are frames that read every strip blocked facing both ways on ground the drone had
not stood on. Open loop understates the rule: a hidden turn-around changes where the drone goes
next, which the recording cannot show.

By the test plan's rule the cost-map change does not fly on this probe; the wall-turn rule
alone would. Whether to fly `a73` as the bundle, split it (`a66` + `a17i`'s rule only), or stop,
is the operator's call. If flown: a shakedown first, s03 `dynamic` and s02c `dynamic` seed 1,
alone on `:8004`, scored by the manipulation check above.

## Builds on

Round F (`a66`, 64/90). Branch `phase2/r33-deadlock-costmap` from `phase2/final` (`c0af776`).

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (23 pass);
  `VLM_AGENT=a73 python eval/probes/a63_smoke.py` (R25D's 627 recorded steps).
- **Replay:** `python eval/probes/a73_replay.py` (Round F, about 50 s) rewrites
  `eval/phase2/_probes/a73/replay.txt`.
- **Preflight, if flown:** `python -m server.decider --profile remote --agent a73`; `/health`
  should report `7ce95fcbea92`. Earlier agents keep their shas (`a66` `de7f23d07186`, `a67`
  `c6b3e9877438`, `a72` `135da10673e9`): the a17i code paths run only for `wall_turn`
  memories, the cost-map flags only when set.

## Outcome

Round not flown. **Shakedown (2026-11-05, 01:03–01:12 UTC, operator: "a73 first"): two unscored
`dynamic` runs, one lane alone on `:8004`, sctsvr6 `~/asep-r33-shake` at `17eb5a8`; runs kept
on the host as `~/r33_shake_a73_runs`, log `~/r33_shake_a73.log`. Both valid.**

| Cell | Result | Wall turns | Turned again | Turn-around hidden | No route |
|---|---|---|---|---|---|
| s02c `dynamic` seed 1 | **solved, 30 steps** (Round F: lost, spin streak 9 from s46) | 2 | 0 | 2 | 0 |
| s03 `dynamic` seed 1 | **lost in the lobby**, 60 steps, 27.3 m from the goal (Round F: lost in the shut tine, 15.1 m) | 8 | 0 | 8 | 0 |

- **The wall-turn rule did what it was built for:** 10 turn-arounds taken facing a wall, the
  turn-around hidden on all 10 next steps, no repeat turn (Round F: 41 of 327, 12.5%).
- **The cost map lost s03.** The drone never entered the stem. s02 a pick off the route
  (far-left strip read blocked), s04–s09 along the lobby wall with "toward your target" on the
  turn-around not taken (the R11 marker-0 pattern; a70's fix is not in `a73`), s23 at the stem
  mouth's edge (13.9, 1.3) a frame read every strip blocked, and from s24 the stem was
  impassable on the map: route 32 m → 51 m, the rest of the run spent searching the lobby.
  Replaying the flown records (`eval/probes/a73_replay.py`'s chain) the stem is passable on
  25 of 60 steps as flown, **60 of 60 with `seal_diagonal` off**, 60 of 60 on `a66`'s map with
  the wall-turn rule alone. A wall cell sealing its eight neighbours closes a 3 m corridor
  (3.5 cells) from one nose-on read at its mouth: a71's stem-mouth failure, made by the planner
  this time.
- **Drop criterion:** met for the bundle by the shakedown rule (s03 lost to the change itself).
  `a73` is not carried to the 30 runs. The wall-turn rule alone, on `a66`'s map and planner, is
  the candidate the shakedown supports.
