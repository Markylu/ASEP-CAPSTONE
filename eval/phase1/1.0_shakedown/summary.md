# 1.0 Shakedown: summary

**Not citable.** Flown at `d100948` on 2026-09-27, 21:23–21:27 UTC. The runs
used the fake decider: `server/decider/fake_litellm.py` with `FAKE_PICK=straight`,
which always picks the straight-ahead action (index 3). The decider ran on
:8010 with `--profile remote`, `VLM_MODEL=stub`, `VLM_STREAM=0` and `VLM_RTT_PROBE=0`.

The shakedown had one job: to prove that the flags, the run-dir layout, the validity
checks, the replay and the labeling all work end to end. They do.

## Result

- **18 / 18 runs valid on the first attempt.** Every replay reproduced its run
  with 0.0 m drift, and the events matched.
- Each `dynamic` arm on s01, s02a/c and s02va/vc logged its change event at
  step 3. No `initial` or `final` arm logged a change event.
- The spawn jitter for seed 1 was dz −0.170 m and dyaw −2.23°. It was
  identical on all 18 runs, as the paired design requires.
- Every run ended on `max_steps` after 60 steps.

| Site | Arm | Label | Collisions | Final dist (m) |
|---|---|---|---|---|
| s01 | dynamic | ignore_change | 55 | 14.23 |
| s01 | final | replan_failure | 55 | 14.23 |
| s01 | initial | collision | 39 | 12.18 |
| s02a | dynamic | ignore_change | 54 | 12.48 |
| s02a | final | replan_failure | 54 | 12.48 |
| s02a | initial | collision | 39 | 12.18 |
| s02c | dynamic | ignore_change | 54 | 12.48 |
| s02c | final | replan_failure | 54 | 12.48 |
| s02c | initial | collision | 39 | 12.18 |
| s02va | dynamic | ignore_change | 49 | 12.49 |
| s02va | final | replan_failure | 49 | 12.49 |
| s02va | initial | collision | 35 | 12.23 |
| s02vc | dynamic | ignore_change | 49 | 12.49 |
| s02vc | final | replan_failure | 49 | 12.49 |
| s02vc | initial | collision | 35 | 12.23 |
| s03 | dynamic | pre_change_failure | 51 | 17.23 |
| s03 | final | replan_failure | 51 | 17.23 |
| s03 | initial | replan_failure | 51 | 17.23 |

The labels describe the stub policy, not a VLM.

- The `initial` arms miss the goal because the stub flies dead ahead instead of
  along the goal bearing. The yaw jitter drifts it 1.1 m sideways, so it passes
  1.12 m from the goal, just outside the 1.0 m arrival radius. It then grinds
  against the far wall.
- s03 `dynamic` is `pre_change_failure` because a straight flyer never enters a
  tine.

## Findings for the spec (decide before 1A)

1. **Rubric order makes `collision` hard to reach (§9).** `replan_failure`
   (#3) is "acknowledged but never got through". It is checked before
   `collision` (#4). So a run that grinds against geometry without getting
   through is always labelled `replan_failure`, and `collision` only fires
   *after* a run got through. This happened here: the `initial` arms
   overshot, ground the far wall, and were labelled `collision` rather than
   `timeout`. One fix: test `collision` before `replan_failure`, or
   restrict `collision` to runs that did not get through.
2. **The keyword "door" will false-positive on s02/s02v.** The doors are in
   frame from spawn, so a real model will mention them before and after the
   change whether or not it noticed anything. Consider dropping "door" from
   the automatic pass, or requiring "closed"/"shut"/"open" near it.
3. **s03 `initial`/`final` have no split step if the agent never enters a
   tine.** The labeler then treats the whole run as post-change. §8 should say
   what the split is in that case.
4. **`git_dirty` has to ignore recorded data.** Otherwise every run after the
   first in a mini-phase counts as dirty, because the previous run's files
   are untracked. The decider and `phase1.py` now exclude `eval/runs/` and
   `eval/phase1/`. This is recorded in the §15 changelog.
5. **The fake decider needs `VLM_STREAM=0 VLM_RTT_PROBE=0`.** Its router
   predates streaming. With streaming on, every rung fails with
   `JSONDecodeError`.
6. **Port 8000 can be taken.** On the operator's machine it is held by an ssh
   tunnel, so `phase1.py run` takes `--decider-url`.

The §7.2 "one scripted straight-ahead probe per site" check was covered by the
stub runs. The stub *is* a straight-ahead probe. On the s01 and s02a checks
flown during setup, the collision steps matched §4: s01 collides at step 6 at
x = 2.2, and s02a at step 7 at x = 0.45. The change fired at step 3 on every
`dynamic` arm.
