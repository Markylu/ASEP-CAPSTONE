# R8 probe

Run on sctsvr6 (Docker image `asep-phase1:latest`, vLLM at 127.0.0.1:8004) from `~/r8_probe_scratch` at `8c616a6`; log: [r8_probe.log](r8_probe.log). Regenerate with `eval/goal_probe.py report-step0 | report-r7 | report-spin`. The spin set is R6's `spin_set.jsonl` (identical bytes), not copied here.

## R8 probe: step-0 picks

9 frames, 18 cells (cells that share a start frame share a row). Reference: `a10`. Flight: the pick recorded at step 0 in the source round.

| agent | answered | same pick as a10 | same pick as flight | turn-around |
|---|---|---|---|---|
| a10 | 18 / 18 | 18/18 (100%) | 18/18 (100%) | 2/18 (11%) |
| a11 | 18 / 18 | 12/18 (67%) | 12/18 (67%) | 1/18 (6%) |
| a12 | 18 / 18 | 15/18 (83%) | 15/18 (83%) | 3/18 (17%) |

Cells where a pick differs from `a10` (pick, turn-around marked T):

| cell | flight | a10 | a11 | a12 |
|---|---|---|---|---|
| s02a/final/seed1 | 0 T | 0 T | 1 | 0 T |
| s02c/final/seed1 | 0 T | 0 T | 1 | 3 |
| s02va/final/seed1 | 3 | 3 | 3 | 0 T |
| s02vc/final/seed1 | 3 | 3 | 0 T | 0 T |
| s03/dynamic/seed1 | 3 | 3 | 5 | 3 |
| s03/final/seed1 | 3 | 3 | 5 | 3 |
| s03/initial/seed1 | 3 | 3 | 5 | 3 |

## R7 probe: lost and off-centre frames

| agent | group | answered | errors | turn-around | goal claimed around | same pick |
|---|---|---|---|---|---|---|
| a10 | lost | 25 / 25 | 0 | 3/25 (12%) | 0/25 (0%) | 16/25 (64%) |
| a10 | offcentre | 25 / 25 | 0 | 3/25 (12%) | 25/25 (100%) | 21/25 (84%) |
| a11 | lost | 25 / 25 | 0 | 5/25 (20%) | 0/25 (0%) | 13/25 (52%) |
| a11 | offcentre | 25 / 25 | 0 | 1/25 (4%) | 24/25 (96%) | 17/25 (68%) |
| a12 | lost | 25 / 25 | 0 | 4/25 (16%) | 0/25 (0%) | 12/25 (48%) |
| a12 | offcentre | 25 / 25 | 0 | 1/25 (4%) | 25/25 (100%) | 16/25 (64%) |

## R8 probe: spin replay

| agent | spin: turn-around | moving: turn-around | visible: turn-around | answered | same pick as a10 |
|---|---|---|---|---|---|
| a10 | 5/40 | 1/20 | 0/20 | 80 / 80 | 80 / 80 |
| a10r | 5/40 | 1/20 | 0/20 | 80 / 80 | 80 / 80 |
| a11 | 8/40 | 4/20 | 0/20 | 80 / 80 | 44 / 80 |
| a12 | 7/40 | 1/20 | 1/20 | 80 / 80 | 45 / 80 |
