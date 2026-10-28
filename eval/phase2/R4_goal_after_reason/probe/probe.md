# Goal-detection probe

`python eval/goal_probe.py report eval/phase2/R4_goal_after_reason/probe`. Each frame is sent as step 0 with an empty log; the reply's `goal` report is scored against the manifest's ground truth (`true_goal()`, eval/agent_evidence.py). Seen = any report other than `not_visible`. Early and step-0 rows count recorded decisions; every other row counts distinct frames.

| Measure | `a03` | `a04` |
|---|---|---|
| frames answered | 173 / 173 | 173 / 173 |
| model | Qwen3-VL-30B-A3B | Qwen3-VL-30B-A3B |
| no valid report | 0 | 0 |
| **early** (first round, steps 0-2, goal visible) | 0/30 (0%) | 30/30 (100%) |
| **seen when visible**, pooled | 65/107 (61%) | 107/107 (100%) |
| seen when visible, <5 m | 22/26 (85%) | 26/26 (100%) |
| seen when visible, 5-10 m | 23/30 (77%) | 30/30 (100%) |
| seen when visible, 10-20 m | 17/30 (57%) | 30/30 (100%) |
| seen when visible, >=20 m | 3/21 (14%) | 21/21 (100%) |
| **false positive**, not visible | 0/66 (0%) | 1/66 (2%) |
| false positive, not visible under 5 m | 0/30 (0%) | 1/30 (3%) |
| direction right, of seen | 27/65 (42%) | 73/107 (68%) |
| step-0 pick = first round's pick | 13/18 (72%) | 17/18 (94%) |
| latency p50 / p95 (s) | 1.20 / 1.65 | 1.25 / 1.57 |

## Gate: **PASS, fly**

| Check | Result | |
|---|---|---|
| Calibration: `a03` early ≤ 6 | 0/30 (0%) | pass |
| `a04` early ≥ 27 | 30/30 (100%) | pass |
| `a04` seen when visible, pooled ≥ 50% | 107/107 (100%) | pass |
| `a04` seen when visible, under 5 m ≥ 70% | 26/26 (100%) | pass |
| `a04` false positives ≤ 10% | 1/66 (2%) | pass |

Replay check (not gated): `a03`'s step-0 report equals the one R3_memory_log recorded at step 0 on the same frame in 18/18 (100%).
