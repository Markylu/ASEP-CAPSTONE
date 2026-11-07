# R69: a102 with the goal check at 20 degrees, not 26, contested cells

**Agent:** `a104` (`df66b94d8c6a`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep), not flown

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R70, the reference lane
(`a102`) flown in the same batch on the same renderer.** The last batch of the night.

## Change

One parameter of `a93`'s goal check on `a102` (`GOAL_CHECK_A104`, `off_deg` 26 → 20): a goal report whose strip
lies more than 20 degrees off the bearing to where the goal truly is, the goal 4 m or more away, is dropped
before the map, the planner or the navigator read it. A strip is 17 degrees wide, so a report two strips off
the goal's strip is dropped; one in the next strip is kept. `a102` is otherwise unchanged.

## Evidence

- **On the record** (`python eval/probes/a93_goal_check.py --folders R49..R55 --sweep`, 1389 goal reports in 166
  runs): at 26 degrees the check drops 82 of the 210 reports made with no line of sight and 17 of the 1179 made
  with one; at 20 degrees, 93 and 43 (3.6%). The navigator took the tag on 188 of the 210 blind reports; the 11
  more it would drop at 20 are blind reports 20–26 degrees off.
- **R53 s02a `dynamic` seed 2, step 33** (scratch trace, 2026-11-07): the drone stood in front of the open door
  it had surveyed to, read the goal in the far-left strip, 25 degrees off its true bearing and behind the wall,
  took "goal this way" and left the door; lost. At 20 degrees that report is dropped.
- The 26 true reports more it drops (43 against 17 of 1179) lie two strips off the goal's true strip: wrong
  reports on their own terms, and the planner knows where the goal is in any case (`goal_truth: planner`).
- Offline: 82 tests pass; `VLM_AGENT=a104 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed.

## Hypothesis

Dropping the blind reports 20–26 degrees off costs no true sighting that matters and saves a run now and then:
`a104` scores at least as many runs as the reference lane in the same batch.

## Predictions

| | R70 (`a102`, reference, `:8004`) | Predicted R69 (`a104`, `:8007`) |
|---|---|---|
| total | its own flight | reference −1 to +2 |
| s02 | | within 2 of the reference |
| s03 | | within 1 of the reference |

## Manipulation check

- Every `run.json` carries `a104`, `df66b94d8c6a`, `:8007`; every `godot.log` names `NVIDIA H100 PCIe`.
- Reports dropped with no line of sight: at least 40% of those made (`a93`-family flights at 26 degrees: 23–51%);
  reports dropped with a line of sight: at most 6% of those made (`eval/probes/a93_goal_check.py --folders
  R69_goal_check_20`).
- No goal tag on a step whose report was dropped.
- `a102`'s rules unchanged: no station given up before its tenth step; the latch within 9 steps of a square read.
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps; walls within
  4 points of R70's.

## Drop criterion

Three or more below R70: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed: the check is code over the perceiver's existing report; the model is not asked anything new. The
offline sweep above is the gate (true reports dropped under 5% at 20 degrees: 3.6%).

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-b` on `:8006`, H100 frames: s03 `dynamic`, s02a `dynamic` (the blind
reports), s02c `final`, s02vc `final`. Scored by the manipulation check.

## Host

Lanes 9–12 of `~/asep-r68-l1..12` on `:8007` (a copy of `:8004` on GPU 4), beside R70 (`:8004`) and R68 (`:8006`);
Godot on GPU 5. `~/r68_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R66 (`a102`), R53 (`a93`'s check). Branch `phase2/r68-latch-inflate-20` (shared with R68 and R70).

## Outcome

Not flown yet.
