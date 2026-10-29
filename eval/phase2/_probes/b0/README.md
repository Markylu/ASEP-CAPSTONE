# Probe B0: can code tell that the s03 dead end is used up? (no model)

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), section B. Script:
`eval/probes/b0.py`.

## Belief

When the model keeps ignoring a listed way out (25 of 33 calls, 0 picks;
`R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md`), code should detect that the pocket
is used up and move the target itself. That is the frontier-exploration pattern (VLFM, 3D-Mem;
CogEval's loops). The belief fails if no rule built from our own memory can spot the dead end in
time without firing on runs that were going to succeed.

## Method

Every recorded run, R15–R26N, all sites and arms. At each decision the memory is rebuilt as the
run's agent had it (`spatial.rebuild` with the agent's own config). The recorded `planner.way`
gives the goal way. Three rules are checked, each a pure function of the record:

| Rule | Fires when |
|---|---|
| R-pocket | the last 10 decision poses all lie within 3.0 m of their centroid, and `way` is not `open` |
| R-blacklist | `way` is `walled`, and the top 3 `search_frontiers` (no blacklist) are all within 1.5 m of a failed detour (`planner.failed_detours`), or none exist |
| R-stall | straight-line distance to the goal shrank by under 1.0 m over the last 12 decisions, and `way` is not `open` |

**Target on firing.** The first of `search_frontiers(here, blacklist=failed, limit=10)` whose point
is more than 6.0 m from the centroid of the last 10 poses. If there is none, the fire has no target
and does not count as useful.

**Scoring (geo, ground truth):**

- **Shut-tine failures.** s03 `final` and `dynamic` runs that were not solved and came within
  2.0 m of the shut tine's exit wall (x ≤ −4.0 inside that tine). The shut side is L in `final`,
  and the tine the drone was in at the switch in `dynamic`. The six named in the plan are in this
  set when the index finds them.
- **Hit.** The rule's first fire in the run lies between the step the drone entered the shut tine
  and 5 steps after it first came within 2.0 m of the exit wall.
- **Useful target.** At that fire, the target is on the crossbar or in the other tine, and
  `step + (frontier path m + geo path from the target to the goal) / 1.7 ≤ 60`.
- **Harm.** In a solved run, the rule's first fire comes before the step the goal was reached.

## Gate (set before the first run)

A rule passes only if all three hold:

| Readout | Threshold |
|---|---|
| Hits | ≥ 80% of shut-tine failures |
| Useful target | ≥ 80% of those hits |
| Harm | ≤ 10% of solved runs |

Fires in `initial` are reported, not gated.

- **Any rule passes:** belief B holds. The next step is a round in which that rule moves the target.
- **No rule passes:** belief B is refuted for our memory, and B is dropped. The gap lies in what the
  memory records, not in the prompt.

## Result

Run 2026-10-29 on sctsvr6 (`b2d262f`): 324 runs, R15–R26N, with 17 shut-tine failures (all six
named in the plan among them). Full output: [score.txt](score.txt), per-run fires:
[fires.jsonl](fires.jsonl).

| Rule | Hits | Useful (of hits) | Harm | `initial` fired | Gate |
|---|---|---|---|---|---|
| R-pocket | 1/17 = 6% | 0/1 | 32/184 = 17% | 9 | fail |
| R-blacklist | 0/17 | — | 1/184 = 1% | 1 | fail |
| R-stall | 1/17 = 6% | 0/1 | 28/184 = 15% | 8 | fail |

**Belief B refuted for the three rules as registered. B is dropped.**

**Why they missed** (a diagnostic run after scoring; the gate stands as it is):
- The planner's `way` read **`open` on 376 of 485 decisions (78%)** made inside the shut tine
  (`walled` 68, `blocked` 41). Every rule requires `way` not to be open, so none could fire. In
  the shut tine, our memory says the way to the goal is open.
- The drone *was* confined. In 15 of 17 runs, its tightest 10-pose window spans at most 3.4 m.
  A pocket rule without the `way` condition would have had something to see.

This matches the gate's refutation clause: the gap is in what the memory and planner record
(`goal_way` reads open in a dead end), not in the prompt. A rule without the `way` condition is a
new probe with its own gate, not a retune of this one. It would also have to answer this probe's
harm numbers, since R-pocket already fires early in 17% of solved runs.
