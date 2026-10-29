# Probe

`python eval/goal_probe.py report eval/phase2/R6_pose_log/probe`. No single-frame probe in this round.

## Replay with the log in place

60 recorded decisions where the goal was seen 5-20 steps earlier and is now out of view, plus in-view controls (`replay_set.jsonl`). `a04` gets its recorded log; an agent with a goal identifier gets a log of ground-truth goal reports and its identifier's live answer. *Places the goal now*: a sentence of the reason says the goal is in view or in a direction now (`claims_goal()`, eval/agent_evidence.py).

| Measure | `a07` | `a08` |
|---|---|---|
| frames answered | 60 / 60 | 60 / 60 |
| **reason places the goal now**, out of view, pooled | 1/40 (2%) | 0/40 (0%) |
| reason places the goal now, stale, turned < 90° | 0/20 (0%) | 0/20 (0%) |
| reason places the goal now, stale, turned ≥ 90° | 1/20 (5%) | 0/20 (0%) |
| goal reported seen, out of view, pooled | 0/40 (0%) | 0/40 (0%) |
| reason places the goal now, in view (control) | 20/20 (100%) | 20/20 (100%) |
| goal reported seen, in view (control) | 20/20 (100%) | 20/20 (100%) |

## Spin replay

Recorded R5 decisions with the log in place (`spin_set.jsonl`): `spin`, the move before was a turn-around (`final`/`dynamic`); `moving`, the move before took the drone ≥ 1 m and flight did not turn around; `visible`, the goal in view and flight did not turn around.

| Measure | `a06` | `a07` | `a08` |
|---|---|---|---|
| **turn-around**, spin | 34/40 (85%) | 17/40 (42%) | 6/40 (15%) |
| same pick as in flight, spin | 39/40 (98%) | 20/40 (50%) | 7/40 (18%) |
| **turn-around**, moving | 0/20 (0%) | 2/20 (10%) | 2/20 (10%) |
| same pick as in flight, moving | 20/20 (100%) | 11/20 (55%) | 14/20 (70%) |
| **turn-around**, visible | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) |
| same pick as in flight, visible | 19/20 (95%) | 18/20 (90%) | 17/20 (85%) |

## Gate (R6): **PASS, fly `a08`**

| Check | Result | |
|---|---|---|
| Calibration: `a06` spin replay turns around ≥ 60% | 34/40 (85%) | pass |
| `a07` spin: turn-around ≤ 50% of the calibration's | 17/40 (42%) | pass |
| `a07` visible: turn-around ≤ 5% | 0/20 (0%) | pass |
| `a07` replay, reason places the goal now ≤ 10% | 1/40 (2%) | pass |
| `a08` spin: turn-around ≤ 50% of the calibration's | 6/40 (15%) | pass |
| `a08` visible: turn-around ≤ 5% | 0/20 (0%) | pass |
| `a08` replay, reason places the goal now ≤ 10% | 0/40 (0%) | pass |
