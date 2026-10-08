# R1: No goal hint

**Agent:** `a01` (`48f6b3973760`) · **Prompt:** `p03` (`e476e566cea2`) · **Status:** pre-registered, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

The prompt stops giving the model any numbers about where things are. `p02` stated the goal's
distance and bearing every step (`Goal: 24.0 m away, bearing +3 degrees (left)`), and listed each
action as `turn +22 degrees, then fly 1.7 m forward`. `p03` gives only the step number and the
marker numbers. It says the goal is a glowing red sphere with a tall red beam, and that the image
is the only information the model gets. The rules of the interface are the same as in `p02`.

Nothing else changes. The image was already free of pose data (`capture_decision_frame()`,
`first-project/common/vlmnav/README.md`, "What the model is shown"). The manifest still records
the true goal distance and bearing, so labels and metrics are computed as in Phase 1.

## Evidence

**1. The confound was logged before Phase 1 flew.** `notes/PLAN.md` §12.9 and the site READMEs
(for example `first-project/sites/s02a_doors_open_a/README.md`) warn that a model told the bearing
every step can ignore the image and steer by the number. A run then measures "obstacle handling
while being told the bearing", not replanning from vision. The proposed fix was
`--goal-hint=none`, which this round is.

**2. Every Phase 1 decision reasons from the bearing.** In [evidence.md](evidence.md)
(`python eval/agent_evidence.py eval/phase1`, all 90 citable runs, 4304 decisions):

| Arm | decisions | reason cites bearing | reason cites distance | nearest-bearing pick (chance 20%) | turn-around pick |
|---|---|---|---|---|---|
| initial | 704 | 100% | 100% | 74% | 0% |
| final | 1800 | 100% | 98% | 81% | 1% |
| dynamic | 1800 | 100% | 99% | 81% | 0% |

A typical reason opens with "The goal is 22.3 m away at a bearing of +3 degrees", then works
out which turn angle is closest (`eval/phase1/1A_s01/runs/s01/dynamic/seed1/decisions.jsonl`,
steps 0–7). It keeps doing this while pinned on the cube: "The goal is 14.2 m away at a bearing
of +1 degrees" at step 58.

**3. The failures follow the bearing into the obstacle.**
- s01 (cube): in all 10 `final`/`dynamic` runs, every action was within 22° of the goal bearing,
  no run turned around, and no run moved more than 1.3 m sideways. The cube's edges are at
  ±4 m (`eval/phase1/1A_s01/summary.md`).
- s02a/s02c (door switch, out of view): 4–5 of the first 5 post-change actions were within ±30°
  of the goal bearing (`eval/phase1/1Ba_s02a/summary.md`, `eval/phase1/1Bc_s02c/summary.md`).
- s02va/s02vc (door switch, in view): 8 of 20 failing runs name the closed door. "Every one keeps
  the goal bearing anyway: a small jog or a turn-around, then straight back into the door"
  (`eval/phase1/1Cc_s02vc/summary.md`). In s02va seed 3, "the goal bearing turns it straight
  back" (`eval/phase1/1Ca_s02va/summary.md`).
- s03 (fork): every run flies the 0° bearing into the divider and stays pinned
  (`eval/phase1/1D_s03/summary.md`).
- Labels: `dynamic` is 25/30 `ignore_change` (5/5 post-change actions toward the bearing in
  1A's overrides, `eval/phase1/1A_s01/labels.csv`). `final` is 30/30 `replan_failure`
  (`eval/phase1/results/results.md`).

**4. A rival explanation: the model does not see the walls.** Every failing Phase 1 run is
tagged `path_hallucination`. Reasons call a blocked path clear: "no visible obstacles in the
path" while the cube fills the frame (1A, `dynamic` seed 1, step 4), and "The door is open, so
flying forward is safe" after it closed (1Ba, seed 2, step 4). In 900 s03 decisions, only one
reason says the path is blocked (`eval/phase1/1D_s03/summary.md`). If the failures are caused
by perception, removing the bearing will not fix them. This round is meant to separate the two
explanations.

**Caveat on the nearest-bearing column.** At spawn the goal is dead ahead (bearing 0°), so flying
straight also counts as following the bearing. The P2.0 fake decider, which always flies
straight, scores 100% on it in `final` and `dynamic`. Read the column together with the
"reason cites bearing" column, never alone.

## Hypothesis

The Phase 1 agent fails after the change because it steers by the stated bearing rather than by
the image. If the prompt carries no goal or motion numbers, the agent will leave the
bearing-locked line and find routes around the obstacle on at least some `final`/`dynamic` runs
where the goal or an opening is visible.

## Predictions

R0 is the Phase 1 seed-1 runs (`eval/phase2/results/results.md`).

| Arm | Baseline (R0) | Predicted |
|---|---|---|
| initial | 5/6 (s03 fails) | 4–5/6. The beam is in view at spawn on s01/s02*, so these hold or drop by one. s03 stays failed: the goal is never visible before the fork. |
| final | 0/6 | ≥1/6, from s01 or s02va/s02vc, where the side gap or the open door is in the frame. |
| dynamic | 0/6 | ≥1/6 by the same sites. Fewer `ignore_change` labels than R0's 5/6 non-s03 cells. |

By site: s02a/s02c `final` and `dynamic` are the least likely to improve, because the open door is
out of view and nothing tells the agent the goal is behind it. A success there would be pure
exploration.

## Manipulation check

Run `python eval/agent_evidence.py eval/phase2/R1_no_goal_hint` after labelling and compare it
with [evidence.md](evidence.md):
- "reason cites bearing" and "reason cites distance" fall from ~100% to ~0%. A non-zero value
  means the model is inventing numbers. Read those reasons.
- The turn-around and lateral picks rise above Phase 1's 0–1%.
- In `final`/`dynamic`, the nearest-bearing pick falls from ~81% toward chance (20%).

If the check passes and success does not move, the bearing was not what held the agent on
the line.

## Drop criterion

Drop `a01` (do not build on it) if either:
- `final` and `dynamic` stay 0/12 while the manipulation check passes. That rules out the
  bearing as the cause and points to perception (Evidence 4). Record it as a finding, not a
  failed round.
- `initial` falls to 3/6 or worse. The goal hint was doing real work on the solvable layout.

## Builds on

R0 / `a00` (`p02`, sha `fb65adbe3317`), the Phase 1 agent.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
