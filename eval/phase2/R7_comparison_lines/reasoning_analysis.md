# R7 (a10) reasoning analysis: comparison lines in the log

Written by Claude. Every one of the 1,725 decisions in R7 (858) and R7C (867) went through
scripts; R6's 894 went through the same scripts for comparison. What was read by eye is listed
in §7. Scripts work on the poses recorded in each decision's manifest:
- a forward move is **blocked** if the drone moved < 0.85 m (half a step), as in R6's analysis;
- R7 = `a10` (`p11`), R7C = `a08` (`p09`) flown on the same host (sctsvr6, lavapipe), R6 = `a08`
  on the Mac. R7 against R7C is the prompt change alone.

Step numbers are the decision's step.

## 0. Headline

**The comparison lines changed how the model reacts to a blocked move, a lot. They did not
change whether it finds the goal, and the success counts cannot be credited to them.**
- After a blocked move `a10` repeats the same pick 8% of the time (R7C 33%, R6 42%), turns around
  65% of the time (R7C 24%), and cites the line in 39 of 40 reasons.
- Blocking at an already-blocked spot fell from 41 (R6) and 21 (R7C) to 3. Collisions: 143, 100, 60.
- Success is 6/18 against R7C's 8/18, and `final` went 3/6 to 0/6. All three `final` cells that
  changed diverge at **step 0**, before any line exists (§3).
- The goal-in-view turn-around survived (§4): three in R7, one of them s02vc `initial`, step 12,
  goal 12 m away, as in R6.

## 1. The flagged runs

| Run | Auto label | Verdict | What happened |
|---|---|---|---|
| R7 s02vc `final` | `timeout` + `failed_goal_identification` (close_range) | agree | At step 44 the goal was reported ahead at 1.4 m; the pick was sharp left. At 1.3 m it read "not visible" and the drone flew straight away for 7 steps (1.3 m to 12.7 m) on "exploration is needed". It found the goal again at step 54 and ran out of steps at 2.9 m. One 1.7 m move can pass the arrival radius, so this is overshoot; the identifier said "not visible" at 1.3 m. The tag's close-range facet fits. |
| R7 s02c `dynamic` | `timeout` | agree | Goal ahead through the door at steps 0–3. The world changed; at steps 12 and 13 the drone turned around twice in a row (the second with the goal reported left at 15.6 m), then spent steps 4–50 in the east (x up to 23.5), blocked and turning. It re-found the goal at step 53 and ended at 2.0 m, out of steps. |
| R7 s03 `dynamic` | `pre_change_failure` | agree | Never reached the trigger. It returned to the corner at (23.5, 11.5) five times (steps 21, 33–34, 52–59), each time reading "did not move, wall ahead", then going back. |
| R7 s02vc `initial` | `replan_failure` | agree | Goal ahead for 11 steps. At step 11 the goal swung left then right as the drone passed the doorway, and at step 12 (12.0 m) it turned around. Same step, site and cause as R6. It then travelled to the north-east corner and back, and ended at 22 m. |
| R7C s02c `dynamic` | `timeout` | agree | Goal ahead at steps 0–3, door closed at step 5, wandered east, re-found the goal at step 56, ended at 12.1 m. |
| R7C s02va `dynamic` | `timeout` | agree | Reached 9.3 m at step 20, turned away ("nearly directly backward"), and ended 35 m away at (22, 7). The R6 lost-goal pattern. |

No auto label needs changing. The one auto tag (`failed_goal_identification`, R7 s02vc `final`)
stands; its facet is lost-at-close-range, not a missed or phantom goal.

## 2. The lines worked as designed

| After a blocked forward move | R6 `a08` | R7C `a08` | R7 `a10` |
|---|---|---|---|
| blocked forward moves | 123 | 91 | **40** |
| same pick again | 52 (42%) | 30 (33%) | **3 (8%)** |
| turn-around next | 29 (24%) | 22 (24%) | **26 (65%)** |
| reason claims progress | 68% | 62% | **20%** |
| reason notes no movement | 29% | 18% | 48% |
| blocked at an already-blocked spot | 41 | 21 | **3** |
| stationary steps (moved < 0.85 m) | 191 | 139 | **114** |
| collisions | 143 | 100 | **60** |
| s03 collisions | 48 | 48 | **17** |

- The line reached the model after all 40 blocked moves (re-rendered from the logs).
- 39 of the 40 reasons that follow cite "stopped short" or "did not move"; the one that does not
  is s02va `dynamic`, step 57, which lists "previously explored" areas and carries on.
- s01 `dynamic`, step 15: "the last move (Step 14) stopped short, indicating a wall or obstacle
  directly ahead." This is the sentence R6 almost never wrote.
- The cost: the model now answers a block with a turn-around two times out of three. Revisit
  stays at 19% (R7C 19%, R6 18%), and mean path is 69 m (R7C 67 m).

## 3. Why the success counts cannot be read as an effect

R7 against R7C, cell by cell (6 sites × 3 arms):
- Identical to the end: 2 cells (s02a and s02c `initial`, which fly the same 14 steps).
- First different pick at step 0: 5 cells (every `final` cell except s03). The log is empty then,
  so no comparison line exists. The positions are identical. Only the system prompt wording
  differs.
- First different pick at step 4: 5 cells (every `dynamic` cell except s03). Steps 0–3 are
  straight moves, so the log has no blocked move yet and no line.
- At step 1: s03 `initial`, `final`, `dynamic`.
- Later: s01 `initial` (14), s02va `initial` (7), s02vc `initial` (10).

Six cells changed outcome. Five of them diverge at step 0 or 4: `final` s02a, s02c, s02vc (control
succeeded, `a10` did not) and `dynamic` s01, s02vc (`a10` succeeded, control did not). The sixth
is `initial` s02vc, the step-12 turn-around. At step 0 in s02a the control flew straight ("the
path appears unobstructed") and `a10` turned around ("facing a wall").

So the change in success comes from differences that appear before any line is shown. Whether
that is the extra system-prompt paragraph or run-to-run noise, this data cannot say. The 3 → 0
on `final` and 0 → 2 on `dynamic` are not evidence for or against the lines. The independent
evidence is smaller than 18 runs: 2 cells are identical and 8 more start the same until step 4 or
later.

## 4. Failures the lines do not touch

1. **Goal in view, turn-around.** Goal-in-view turn-arounds: R6 3, R7C **0**, R7 3. R7's are s01
   `dynamic` step 20 (11 m), s02c `dynamic` step 13 (16 m) and s02vc `initial` step 12 (12 m,
   again). R7C had none, so the host or noise matters here. Reasons with arithmetic ("287 +
   180"): 8 (R6), 9 (R7C), 11 (R7). Not read: s01 `dynamic` step 20.
2. **Corner traps.** s03 pins in the north-east corner (23.5, 11.5) in `a10`, at x = 15.2 in R6.
   Collisions fell (48 → 17), but s03 is 0/3 in all three rounds.
3. **Close-range overshoot.** s02vc `final`: one move is longer than the arrival radius, and the
   drone flew past a goal it was 1.3 m from.
4. **Lost goal after being seen.** Failed runs that came within 14 m and ended more than 8 m
   further away: R6 3, R7C 4, R7 2. R7 does not target this.
5. **Not getting near.** Failed runs that never came within 14 m: R6 9, R7C 5, R7 **8**.

## 5. Label review

All 36 auto labels stand. 12 `a10` and 10 `a08` runs are failures; none needs a different
terminal label. R7 s02vc `final` takes `failed_goal_identification` (close-range facet). There is
no `spin_failure` tag in either round. By the memory rule, tags apply from the round they appear
in; nothing earlier is touched. The operator still confirms.

## 6. For R8

1. The step-0 sensitivity is the largest source of variance seen so far: a prompt that adds one
   paragraph moved 5 of 18 cells from step 0. Before the next change, measure it: run a no-op
   prompt edit (an extra sentence) through the same 18 cells, so the next result has a noise
   floor.
2. Heading: the goal-in-view turn-around survives. Candidates: heading as a word ("facing west"),
   or dropping the degrees. Test it on the 11 `offcentre` probe frames first.
3. The turn-around-after-a-block reflex (65%) may be too strong for corner traps: the line says
   "blocked" and the model has one answer. A line that names an untried direction is a bigger
   step.
4. More seeds. At 18 runs, a 2-run difference is not a result.

## 7. What was read by eye

- All six runs in §1, step by step (compact view: every blocked move, turn-around, goal report
  and the last ten steps). The first dump of s02vc `final` was read in full.
- The first different pick of every R7 / R7C cell pair, and the reasons at the divergences in
  s02a, s02c and s02vc `final` and s01, s02a and s02vc `dynamic`.
- 6 reasons after blocked moves, to check the line is being cited.
- The rest of the 1,725 decisions were counted by script (blocked moves, picks, revisits,
  claims, arithmetic), not read one by one. The progress-claim and no-movement classifiers are
  regexes calibrated on R6 (84 claims where R6's analysis reported 80).
