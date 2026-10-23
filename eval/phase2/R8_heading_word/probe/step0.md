# R8 probe: step-0 picks

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
