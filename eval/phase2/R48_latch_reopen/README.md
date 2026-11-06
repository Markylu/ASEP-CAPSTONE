# R48: a87 with the latched corridor reopened to a drone back inside it, contested cells

**Agent:** `a88` (`144756aca5a8`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A88` ·
**Navigator notes:** `NAVIGATOR_A86` ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R45's flight, while R46 was in the air and R47 queued
behind it; shakedown and flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R45 (`a85`, 23/30, the bar) and R46 and R47 as they land.

## Change

One setting against `a87` (R47): `dead_end_latch.reopen_m: 1.0` (`agent.PATHFINDER_A88`, read
in `planner.pathfind`). A latched corridor's lane is shut once the drone is out past the
mouth (`a78`'s plug, so the route never goes back in). With this setting, a drone that is
nevertheless back inside the rectangle, 1 m or more down it, has the lane opened again until
it is out. Everything else is `a87`'s.

## Evidence

- **R45 (`a85`), s03 `dynamic` seed 1**: door shut at step 21, latch at 28, out past the mouth
  at 36. The drone then flew back into the tine (the navigator's picks; the route pointed
  away). Inside a corridor now shut on every side, lane included, there was no route: the
  planner fell back on 21 of the last 24 steps and the run was lost in the shut tine (30
  steps in it after the latch). `a68` flew back into its sealed tine the same way in R30's
  shakedown.
- A unit test rebuilds the state (a latch that is out, the drone 4 m down the corridor):
  `a87` has no route, `a88` has one and its waypoint runs back down the lane
  (`server/decider/tests/test_pathfinder.py`).
- How often: in R39, R44 and R45, 14 s03 runs were latched and got out; one flew back in.

## Hypothesis

A drone that flies back into its latched corridor is led out again instead of being left
without a route; nothing else changes. `a88` scores at least as well as `a87`.

## Predictions

As `a87`'s (R47 README), with s03 `dynamic` no lower. No change expected in s02 beyond noise.

## Manipulation check

`eval/probes/a79_check.py`: no latched run with a route on fewer than 90% of its steps after
the latch; where a drone is back inside after being out, `latch.out` false again on the next
step and the drone out again within 8 steps.

## Drop criterion

Not carried forward if 3 or more under the best of R45, R46 and R47. As a rare-case fix it is
carried at a draw if no run shows it doing harm.

## Probe gate

**No model probe** (code only; nothing the model is told or asked changes).
`python -m pytest server/decider/tests -q`: 77 pass (one on this change, reproducing the
fault under `a87`). `VLM_AGENT=a88 python eval/probes/a63_smoke.py`: 627/627. Earlier agents
keep their shas (`a87` `aaf90e0ca54d`). The s02 simulation is not rerun: the setting acts
only on a latch that is out.

**Shakedown gate** (on-policy, slot 5 as a fifth client beside the flight in the air): s03
`dynamic` seeds 1, 2 and 3 and s03 `final` seed 1. Passes if a route is on at least 90% of
steps in every run and no run is lost inside a latched corridor it had left. Wins are not
required.

## Builds on

`a87` (R47). Branch `phase2/r48-latch-reopen` from `phase2/r47-station-guard` (`e68a3c2`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a88`; `/health` should
  report `144756aca5a8`.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
