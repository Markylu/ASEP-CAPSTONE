# Goal-detection probe

`python eval/goal_probe.py report eval/phase2/R5_goal_identifier/probe`. Each frame is sent as step 0 with an empty log; the reply's `goal` report is scored against the manifest's ground truth (`true_goal()`, eval/agent_evidence.py). Seen = any report other than `not_visible`. Early and step-0 rows count recorded decisions; every other row counts distinct frames.

| Measure | `a04` | `a05` | `a06` |
|---|---|---|---|
| frames answered | 173 / 173 | 173 / 173 | 173 / 173 |
| model | Qwen3-VL-30B-A3B | Qwen3-VL-30B-A3B | Qwen3-VL-30B-A3B |
| no valid report | 0 | 0 | 0 |
| **early** (first round, steps 0-2, goal visible) | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) |
| **seen when visible**, pooled | 107/107 (100%) | 107/107 (100%) | 107/107 (100%) |
| seen when visible, <5 m | 26/26 (100%) | 26/26 (100%) | 26/26 (100%) |
| seen when visible, 5-10 m | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) |
| seen when visible, 10-20 m | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) |
| seen when visible, >=20 m | 21/21 (100%) | 21/21 (100%) | 21/21 (100%) |
| **false positive**, not visible | 1/66 (2%) | 3/66 (5%) | 1/66 (2%) |
| false positive, not visible under 5 m | 1/30 (3%) | 1/30 (3%) | 1/30 (3%) |
| direction right, of seen | 73/107 (68%) | 88/107 (82%) | 89/107 (83%) |
| step-0 pick = first round's pick | 17/18 (94%) | 14/18 (78%) | 14/18 (78%) |
| latency p50 / p95 (s) | 1.25 / 1.57 | 2.91 / 4.57 | 1.04 / 1.35 |

## Replay with the log in place

60 recorded decisions where the goal was seen 5-20 steps earlier and is now out of view, plus in-view controls (`replay_set.jsonl`). `a04` gets its recorded log; an agent with a goal identifier gets a log of ground-truth goal reports and its identifier's live answer. *Places the goal now*: a sentence of the reason says the goal is in view or in a direction now (`claims_goal()`, eval/agent_evidence.py).

| Measure | `a04` | `a05` | `a06` |
|---|---|---|---|
| frames answered | 60 / 60 | 60 / 60 | 60 / 60 |
| **reason places the goal now**, out of view, pooled | 10/40 (25%) | 5/40 (12%) | 0/40 (0%) |
| reason places the goal now, stale, turned < 90° | 7/20 (35%) | 3/20 (15%) | 0/20 (0%) |
| reason places the goal now, stale, turned ≥ 90° | 3/20 (15%) | 2/20 (10%) | 0/20 (0%) |
| goal reported seen, out of view, pooled | 31/40 (78%) | 5/40 (12%) | 0/40 (0%) |
| reason places the goal now, in view (control) | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |
| goal reported seen, in view (control) | 19/20 (95%) | 20/20 (100%) | 20/20 (100%) |

## Gate (R5): **PASS, fly**

| Check | Result | |
|---|---|---|
| `a06` early ≥ 27 | 30/30 (100%) | pass |
| `a06` seen when visible, pooled ≥ 90% | 107/107 (100%) | pass |
| `a06` seen when visible, under 5 m ≥ 90% | 26/26 (100%) | pass |
| `a06` false positives ≤ 5% | 1/66 (2%) | pass |
| Calibration: `a04` replay, reason places the goal now ≥ 25% | 10/40 (25%) | pass |
| `a06` replay, reason places the goal now ≤ 10% | 0/40 (0%) | pass |
