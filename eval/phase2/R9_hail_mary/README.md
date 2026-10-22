# R9: Orchestrated agent with a spatial memory (bundle round)

**Agent:** `a13` (`3de550e110e7`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) · **Perceiver:**
`g03` (`3531e4d9ade9`) · **Strategist:** `q01` (`40fb0fbc3285`) · **Spatial memory:**
`spatial.wording_sha()` `eceb875a68a3` · **Status:** pre-registered, probe passed, not flown

Written before the probe and before flying. Spec: `docs/phase2-test-plan.md` (§1 and §8,
2026-10-22: bundle rounds). The shas above are re-checked against `config.lock.json` before the
round flies. R9 flies beside a control, **R9C**, on the same host (Control).

## Change

**A bundle, by the operator's decision (2026-10-22).** Seven rounds of one change each moved
`initial` but never took `final` + `dynamic` above 3/12. R9 changes the agent's structure in one
round: code does every spatial comparison, and each model call gets one job.

One step of `a13` (`server/decider/orchestrator.py`):

| Part | Who | Sees | Answers |
|---|---|---|---|
| Perceiver `g03` | model | the clean frame only (no log, no step, as `g02`) | goal strip (5 vertical strips or not visible), goal distance class, per strip: open floor far / near / wall close, and doorway yes/no |
| Mapper | code | pose of every decision, every perceiver report | the map: visited ground, blocked and short moves, seen floor and walls, goal rays and a goal estimate, doorways (open, passed, closed), unexplored edges, a loop score |
| Strategist `q01` | model, text only, on a trigger | a description in words written from the map, and a list of targets code built | a mode (approach / explore / backtrack / escape) and one listed target |
| Projector | code | map, perceiver report, target | up to three notes per action ("blocked here before (step 21)", "toward your target", "new ground", "wall close (seen now)", ...) |
| Navigator `p14` | model | the annotated frame, the target, the perceiver's line, the last three moves in words, the notes | `{reason, action}` |
| Critic | code, then the model once | the pick against the map | when the pick was blocked from here, is a third turn-around in four steps, or goes back to ground covered 3+ times in 10 steps while another action is new ground or toward the target: one more ask with the reason; the second answer stands; no action is ever hidden |

What the model is **no longer shown**: coordinates, headings in degrees, the pose log. What the
memory is **built from**: the drone's pose (accepted in R6) and the perceiver's reports. Not from
`site.json`, depth, raycasts, the sim's `collided` flag or the goal's ground truth (operator,
2026-10-22). The map is rebuilt from `decisions.jsonl` every step, so every run replays to the
map its model was shown (`eval/spatial_replay.py`).

The strategist is asked at step 0, after a blocked move, when the goal comes into view or has
been out of view for three steps, when a new doorway is seen, when its target is reached or
closed, when the loop score reaches 0.5, and otherwise every 8 steps (`spatial.trigger`). All
calls are the frozen model at temperature 0.

Example: R6 s03 `dynamic`, step 22, the corner at (15.2, −11.5) where R6 pinned. Map only (no
perceiver report exists for a recorded R6 frame). R6's `a08` picked [3] here, into the wall it
had hit at step 21; the critic would have asked again.

```
Planner: no fixed target; explore where the image shows open floor.
Perceiver, this image: no answer this step.
Your last moves: step 19 flew straight, moved 1.7 m; step 20 flew straight, stopped short
(blocked); step 21 flew sharp left, did not move (blocked).

Available actions this step:
  [0] turn around in place: behind you is new ground
  [1] sharp left: new ground
  [2] slight left: new ground
  [3] straight: blocked here before (step 21)
  [4] slight right: new ground
  [5] sharp right: stopped short here before (step 20)
```

`a00`–`a12` and `p02`–`p13`, `g01`, `g02` keep their shas: all 15,714 `p08`–`p13` renders of
the recorded R6, R7 and R7C decisions are byte-identical before and after the change.

## Evidence

- **The model does not compare positions or headings.** R6: it quotes its pose and still claims
  progress after 65% of blocked moves (143 collisions). R6/R7: heading arithmetic ("221 + 180")
  turns it away from a goal it can see (s02va/s02vc `initial`, step 12).
- **Verdicts written by code work; raw memory does not.** R7's comparison lines cut progress
  claims after a block 62% → 20% and collisions 100 → 60 (R7C → R7). R2's verbatim memory locked
  in (97% same pick).
- **A separate call with one job works.** R5's identifier on the clean frame: 114/114 goals seen.
- **What is left is replanning.** `replan_failure` is 9 of R7's 12 failures. s03 has 0/3 on R6,
  R7 and R7C: the drone circles the lobby (x 15–24) and never enters the stem at y ≈ 0
  (`spatial_replay.py draw` of R7 s03 `final`). On 255 recorded R5/R6 steps where the drone stood
  where it had been blocked, the recorded pick went into the blocked heading again 92 times (36%,
  `eval/r9_probe.py sample-trap`).

## Hypothesis

With spatial comparison moved into code and shown as notes on the actions, and a target chosen
from a map, the agent stops repeating blocked moves and leaves traps, and `final` + `dynamic`
rises.

## Predictions

| Measure | Prediction |
|---|---|
| `initial` | ≥ 5/6 |
| `final` + `dynamic` | ≥ 5/12, and above R9C by more than R8N's measured noise floor |
| s03 (any arm) | ≥ 1/3 |
| collisions | below R7's 60 |
| `spin_failure` runs | 0 |
| picks carrying "blocked here before" | < 5% of decisions |
| revisit rate | below R7's ~19% |

## Attribution rule

R9 is read against R9C only. A difference of 2 runs or fewer, or within R8N's noise floor
against R7, is not a result. If R9 wins, an ablation round follows before the final: `a13` with
the map and notes but without strategist and critic, so the parts can be told apart. Whatever
R9 shows is credited to the bundle.

## Control

**R9C** flies the agent R8 carries forward (`a11` if R8 keeps it, otherwise `a10`) on the same
host at the same SHA. Fixed when R8 is read, before R9's probe; added to `ROUNDS` then.

## Manipulation check

From `python eval/spatial_replay.py manip eval/phase2/R9_hail_mary/runs`:
- notes delivered on every decided step;
- picks carrying "blocked here before" (< 5%);
- critic calls and how often the second answer changed the pick;
- strategist calls by trigger and the mix of modes;
- perceiver in flight: goal strip within one of the truth when in view, phantom reports;
- goal-estimate error at the last step (ground truth, evaluation only);
- revisit rate; mean step latency.

## Drop criterion

`a13` is dropped if two or more hold:
- `final` + `dynamic` below 3/12;
- `initial` below 4/6;
- any run invalid on the wall clock (900 s);
- `spin_failure` on 2 or more runs.

## Probe gate

`eval/r9_probe.py`, on recorded R5 and R6 clean frames (the R6 worktree holds them), against the
live model, before flying. R9 does not fly if any line fails.

| Check | Set | Threshold |
|---|---|---|
| goal strip within one of truth, goal in view | perceiver set (158 frames: in view, out of view, blocked and completed moves) | ≥ 90% |
| phantom: goal reported, not in view | same | ≤ 5% |
| left/ahead/right from `g03` against `g02`'s in-flight answer, both scored on truth | frames with a `g02` answer | not lower by more than 5 points |
| false wall: completed move whose strip was called "wall close" | completed moves | ≤ 20% |
| trap repeat: a13 picks the known-blocked heading again | trap set (255 steps, recorded 36%) | ≤ 25% |

**Result: gate passed.** [probe/probe_r9.md](probe/probe_r9.md), run 2026-10-22 on the Mac at
`8b6056f`. Goal strip within one 47/47, phantom 4/111 (3.6%), left/ahead/right 96.2% against
g02's 96.2%, false wall 6/100, trap repeat 1/255 (0.4%; recorded agents 36.1%). Not gated: a13
turns around on 71% of trap steps (on 177 of 181, every forward move was marked blocked or wall);
the critic changed 2 of 40 picks; targets were not exercised (replayed maps have no perceiver
history); perceiver mean 1.96 s, whole step 5.1 s.

## Shakedown

One run per site on the flight host, not counted, before the round: every decision record
carries the perceiver, the map snapshot and the notes; `/health` reports `a13`'s sha; no run
passes 700 s.

## Host

sctsvr6 headless (Docker, Mesa lavapipe), as R7 and R8, with R9C there too. The final round, if
any, is flown on the Mac.

## Builds on

R5 (separate perceiver on the clean frame), R6 (ground-truth pose), R7 (blocked / short
thresholds, reused in `spatial.py`), R8 (control on the same host, noise floor).

## Outcome

Not flown.
