# R53: a89 with goal reports off the line to the goal dropped, contested cells

**Agent:** `a93` (`8cc0bfc63d4e`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A89` ·
**Navigator notes:** `NAVIGATOR_A78` · **Goal check:** `GOAL_CHECK_A93` ·
**Status:** laid out 2026-11-06 by Claude on the operator's instruction ("do one more cycle of
the loop"); every decision here is Claude's, with its reason; shakedown flown 2026-11-06
(four of four solved; two gate rows not met as written, neither the change's doing; flown on);
**flown 2026-11-06, 24/30, a draw with the bar, not the new bar**

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R45 (`a85`, 23/30, the bar) and R49 (`a89`, 23/30, the agent this
changes), no control lane.

## Change

One stage against `a89`, code only (`orchestrator.check_goal`, `agent.GOAL_CHECK_A93`): **a goal
report from the perceiver is dropped when its strip lies more than 26° off the bearing to where
the goal is, the goal 4 m or more away.** The report is kept in the record as `goal_reported`
and the step's `goal_check` says why; the map, the planner and the navigator read "not
visible", as they do after `a27`'s confirmer says no. No new prompt, no extra call. The
planner side already knows the goal's position (`goal_truth: planner`, as `a66` and the agents
built on it); the navigator still never sees it, and loses a tag, not gains one.

## Evidence

`eval/probes/a93_goal_check.py` on the 210 runs of R44 to R52 (`eval/phase2/_probes/a93/`):

- **The perceiver names the goal where it cannot be seen.** 1579 goal reports; 249 (16%) on
  steps with no line of sight to the goal. Every one raised a goal tag, and the navigator took
  it on 247: `p17`'s first rule is a move with "goal this way".
- **What the rule removes:** 108 of the 249 (43%), and 13 of the 1330 made with a line of sight
  (1.0%). The other 141 lie within 26° of the true bearing: wrong about seeing, right about
  the way. Inside 4 m six real reports lay off the line (1.1 to 2.4 m: the sphere is wider
  than a strip), hence the 4 m.
- **Where it costs runs: the s03 lobby.** Traced, R52 s03 `dynamic` seed 1: at step 2 the drone
  is at (17.6, 0.3) facing the stem, the goal 29.6 m ahead and 3° left behind the fork. The
  perceiver reports it "far right, far"; the move tagged "toward your target" is the slight
  right, the sharp right gets "goal this way (seen now, far off)" and is taken; at step 3 a
  move is stopped at the stem's jamb, the route no longer runs through the mouth, and the
  first step in a tine is at 53. The same report at step 2 is in 12 of the 14 seed-1 s03
  runs of the seven flights; 4 of the 12 were won.
- **By run:** of the 42 s03 runs, 18 took a tag the rule drops by step 4 and 6 of them were
  won (33%); the other 24 won 15 (63%). In s02 no such tag comes before step 7; 51 runs took
  one later and won 22, the 117 without won 93, but a lost run flies longer and looks around
  more, so that gap is not the rule's to claim.

The 26° and the 4 m were chosen on these same runs: a fit, not a test (`sweep.txt`: 20° drops
3.0% of the real reports, 35° drops 38% of the blind ones).

## Hypothesis

With the off-line reports dropped, the seed-1 s03 runs fly on down the stem at step 2 as seeds
2 and 3 do, s03 is 3 of 6 or better (`a89`: 2), s02 stays at 19 of 24 or better, and `a93`
scores at least 23/30.

## Predictions

| Cell group | R45 (`a85`) | R49 (`a89`) | Predicted `a93` |
|---|---|---|---|
| s03 `final` | 3/3 | 1/3 | 2–3 |
| s03 `dynamic` | 1/3 | 1/3 | 1–2 |
| the eight s02 cells | 19/24 | 21/24 | 19–22 |
| **total** | **23/30** | **23/30** | **22–27** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule). Near-identical agents scored 23, 19
and 20 within two hours on 2026-11-06, and s03 alone ranged from 1 to 5 of 6 on code that did
not differ there. R54 flies the same `a93` at the same time (on H100 frames), so this agent
has 60 runs by the end of the hour.

## Manipulation check

From `decisions.jsonl` (`goal_check` on the step; `eval/probes/a93_goal_check.py`,
`eval/probes/a79_check.py`, `eval/probes/a80_check.py`):
- A report dropped at step 4 or before in both seed-1 s03 runs, and the drone in the stem
  (x < 15, |y| ≤ 1.5) by step 6 in both.
- The first step in a tine by step 25 in at least 5 of the 6 s03 runs (`a89`: 4, with 32 and 33).
- No goal tag on any step whose report was dropped.
- Of the reports made with a line of sight, at most 3% dropped (on the record: 1.0%).
- Unbroken: the survey starts in at least 19 of the 24 s02 runs by step 8 (`a89`: 21); a route
  on at least 95% of steps; walls in flight within 4 points of R49's.

## Drop criterion

Not carried forward below 21/30, or with s02 under 18/24. The new bar at 26/30 or more (the
bar's 23 plus 3). Between, a draw with `a85` and `a89`: read with R54's 30.

## Probe gate

**No model probe: the change adds no call and puts no new words before the model.** A step with
a dropped report reads to the navigator as any step with no goal in view.

**Gate 1, the rule on the record** (above): drops at least 40% of the reports made with no line
of sight and at most 2% of those made with one. **Read: 43% and 1.0%. Passed**, in sample.

**Gate 2:** `python -m pytest server/decider/tests -q` (82 pass, one on the check);
`VLM_AGENT=a93 python eval/probes/a63_smoke.py` (627/627). Earlier agents keep their shas
(`a66` `de7f23d07186`, `a85` `a43435111dff`, `a89` `85cda76df25b`, `a92` `8e5bcc8a5c74`).

**Shakedown gate** (on-policy, seed 1, lavapipe, two lanes on `:8004`, unscored, in a checkout of
its own): s03 `final`, s03 `dynamic`, s02c `dynamic`, s02a `final`. Passes if a report is
dropped by step 4 in both s03 runs and both are in the stem by step 6, no report made with a
line of sight from 4 m or more is dropped in the s02 runs' first 20 steps more than once, the
survey starts in both s02 runs by step 8, and a route is on at least 95% of steps in every
run. Wins are not required.

**Shakedown outcome** (2026-11-06, 18:34–18:42 UTC, `b8ef443`, two lanes alone on `:8004`,
checkouts `~/asep-r53-shake-a`, `-b`; unscored, not part of the round):

| run | result | reports dropped (step, strip, off the line) | in the stem | first tine step | survey from | route |
|---|---|---|---|---|---|---|
| s03 `final` 1 | goal at 34 | none (no goal report before step 5) | step 4 | 16 | — | 34/34 |
| s03 `dynamic` 1 | goal at 51 | 2 far right 40°; 37 far right 28° | step 4 | 13 | — | 51/51 |
| s02c `dynamic` 1 | goal at 29 | none | — | — | step 4 | 29/29 |
| s02a `final` 1 | goal at 32 | 21 far right 85° | — | — | never | 32/32 |

All four dropped reports had no line of sight; none of the 26 made with one was dropped; no
goal tag stood on a step whose report was dropped. **Two rows not met as written.** In s03
`final` no report was dropped by step 4 because the perceiver made none there this time; the
drone was in the stem at step 4 all the same. In s02a `final` the survey never started; it
did not in R49 either (`a89`, same cell and seed, lost there, won here at 32), so it is not
this change's doing. s03 `dynamic` seed 1 had been lost in six of the seven flights of
2026-11-05 and 06. **Flown on**: nothing here says the check breaks s02, which is what the
gate is for.

## Host

**The first round flown on two vLLM instances at once** (operator, 2026-11-06: flights may be
spread over the GPUs). Eight lanes, `~/asep-r53-l1..8`: lanes 1–4 on `:8004`, lanes 5–8 on a
copy on GPU 3 (`:8006`, `eval/docker/vllm_copy.sh`: same image, weights and flags). Four lanes
to an instance, as the rounds of 2026-11-05 flew, so a call's batch neighbours are what they
were. Godot under lavapipe, as every round: the change here hangs on how one frame is read
(s03 seed 1, step 2), and H100 frames differ from lavapipe's on thin edges. R54 flies beside
it on a third instance (`:8007`) and asks what the renderer does.

## Builds on

`a89` (R49, 23/30: the best s02 of 2026-11-06 and every planner fix of that night). Branch
`phase2/r53-goal-check` from `phase2/host-gpu-render` (`738a6c3`: R52's tip plus the lane and
render scripts).

## Notes for the operator

- **Readouts (no model):** `python eval/probes/a93_goal_check.py [--sweep]`; on a flown round,
  `--folders R53_goal_check` counts what was reported (dropped reports included, from
  `goal_reported`).
- **Preflight:** `python -m server.decider --profile remote --agent a93`; `/health` should
  report `8cc0bfc63d4e`.
- **Goal truth.** The check reads the goal's position on the planner side and removes a false
  report; no text carries the position. If you would rather the navigator's inputs never
  depend on it at all, this round is the one to strike.

## Outcome

**Flown 2026-11-06, 24/30** (s02 20/24, s03 4/6): the hypothesis held as written (at least 23,
s03 at least 3, s02 at least 19), and 24 against the bar's 23 is a draw by the rule. Every s03 run
was in the stem by step 5, s03 `final` 3/3; the check dropped 14 of 32 blind reports and 5 of 214
made with a line of sight. [summary.md](summary.md).
