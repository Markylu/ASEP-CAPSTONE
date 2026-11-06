# R46: a85 with the route-behind sentence always and the latch off the survey's ground, contested cells

**Agent:** `a86` (`cd6b8de756ab`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A86` ·
**Navigator notes:** `NAVIGATOR_A86` ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) while R44 was landing and R45 taking off; shakedown and
flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30), R44 (`a84`) and R45 (`a85`). The bundle is
R43's (the wall survey for s02, the dead-end latch for s03).

## Change

Against `a85` (R45), three things, each from a run of tonight:

| Part | Setting | `a85` | `a86` | Why |
|---|---|---|---|---|
| Navigator | `NAVIGATOR_A86.always` | "The next point on your route is behind you: the turn around is the move toward it." said only inside a latched corridor | said on every step where "toward your target" sits on the turn-around (`a70`'s sentence, no critic) | the navigator took 63–68% of such turn-arounds in s02 and 68–92% in s03 (Round F, R32P, R39); in tonight's s03 runs that spent 36–53 steps before the tine it took 17 of 28. R39 s03 `final` seed 1: at the divider's face it flew back up the stem into the lobby against six such tags and never came back. `a70` took 46 of 46 with the sentence (R30's shakedown) |
| Latch | `confined.off_line_m`, `after_survey` | any straight run turned into can be latched | not a lane along the direct line from the spawn to the goal (within 2.5 m of it), and no new latch while the survey runs | R44 s02va `dynamic` seed 2: a sidestep at x = 10 made the rest of the approach to the shut door "a run turned into"; the latch shut the hall in front of the door at step 15 and the drone was out of it at 28 |
| Survey | `through_adv_m` off, `relook_steps` 4 | 5 m past its last read with nothing in the way, the drone is through | no such rule; a look taken up again after a lost doorway ends after four steps with no wall met and no doorway read | R45's shakedown: a door read from far leaves the drone 5 m on and still in the hall; the survey ended at steps 7 and 10 in two runs of four |

This is the first of tonight's rounds to change what the navigator is told. The sentence is
`a70`'s, word for word, and already flown by `a78` to `a85` inside a latched corridor.

## Evidence

- The table's runs. Counts of declined turn-arounds: a one-off over `decisions.jsonl` of Round
  F, R32P, R39 and tonight's shakedowns (tag on the turn-around against the pick), quoted in
  the night log.
- **`a70`** (`eval/phase2/R30_pathfinder/README.md`, shakedown): 46 of 46 turn-arounds taken
  with the sentence, and the lobby left in 11 steps where `a63`, `a67` and `a68` spent 18. It
  then oscillated 30 steps in the shut tine, the route flipping between the shut door and the
  way out; that is what the latch is for.
- **The latch's trigger with the direct-line rule** (`eval/probes/confined_trigger.py --agent
  a86`): s03 unchanged (10 of 11 s03 `dynamic` runs on Round F, R32P and R35; 3 of 4 on R30
  and R32; 3 of 3 on R39), one fewer won s02 run latched on each set (3 of 53, 3 of 17).

## Hypothesis

Told when its route is behind it, the drone stops flying away from the turn-arounds the route
asks for: fewer steps before the s03 tine, and a survey whose first move from the wall is
taken. `a86` scores at least as well as `a85`, and at least 18/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a86` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 8–10 |
| s02 `dynamic` ×4 | 6/12 | 8–10 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 1–2 |
| **total** | **15/30** | **18–24** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

- The sentence on every step with "toward your target" on the turn-around (`route_behind` in
  the record), and the turn-around taken on at least 85% of them (R39: 66% in s02, 68% in s03).
- s03: the first step in a tine at 25 or before in at least 5 of the 6 runs.
- No latch whose lane lies within 2.5 m of the direct line; none dated while a survey was
  running.
- R44's and R45's survey rows (`eval/probes/a80_check.py`); a route on at least 95% of steps;
  walls in flight within 4 points of Round F's.

## Drop criterion

Not carried forward below 15/30, or 3 or more under the better of `a84` and `a85`. Carried as
the base of the next round at 18/30 or more and no worse than the better of the two.

## Probe gate

**No model probe run.** The change does touch what the navigator is told, on the steps the
sentence is said; the sentence is `a70`'s and `a78`'s, and its effect was measured in flight
(46 of 46). The gate for it is the shakedown, on-policy.

- **Closed loop, no model** (`eval/probes/a80_sim.py --agent a86 --far 20`,
  `eval/phase2/_probes/a86/`): truthful perceiver 32/32 on the change arms; misread doorways
  and walls with 20% random moves 69/96 (`a85` 67, `a84` 59, `a66` 48). Passed. (The simulated
  navigator does not read the sentence.)
- `python -m pytest server/decider/tests -q`: 75 pass. `VLM_AGENT=a86 python
  eval/probes/a63_smoke.py`: 627/627. Earlier agents keep their shas (`a85` `a43435111dff`).

**Shakedown gate** (on-policy, seed 1 and one seed 2, slot 5 as a fifth client beside R45's
lanes): s03 `dynamic` (the run that spent 37–53 steps before the tine in three shakedowns),
s03 `final`, s02c `dynamic`, s02va `dynamic` seed 2 (the hall latch). Passes if the
turn-around is taken on at least 80% of the steps the sentence is said, the s03 runs are in a
tine by step 25, no latch lies on the direct line, and a route is on at least 95% of steps.

## Builds on

`a85` (R45). Branch `phase2/r46-behind-always` from `phase2/r45-survey-lineup` (`ca01a4a`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a86`; `/health` should
  report `cd6b8de756ab`.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
