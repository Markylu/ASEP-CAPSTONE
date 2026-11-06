# Probe dead_end_heldout: the places filter on runs it was not fitted on

For R38 ([round write-up](../../R38_dead_end_latch/README.md)), after
[probe DE](../dead_end/README.md) failed its gate. On the operator's instruction ("Run held-out
probe"), 2026-11-05. `eval/probes/dead_end_heldout.py`.

## What is tested

Probe DE §3 found, on the answers its gate failed on, that `e01` ("is the drone in a dead-end
corridor that ends at that closed door?") kept only while the memory knows at most two
closed-door places (4 m apart) fires the latch's rule in 11 of 11 s03 `dynamic` runs and 1 of 88
s02 runs. That is a fit: the count and the radius were read off those answers. This asks `e01`
on runs no part of the fit saw and counts the same rule with the same setting.

## Runs

No model was ever asked `e01` on any of these. Asked steps (a closed-door read in the centre
three strips, as `a78`'s confirmer is asked) are counted from the repo's records:

| Group | Runs | Asked steps |
|---|---|---|
| `initial` arms: Round F (`a66`, 30) and R30 (`a66`, 6) | 36 | 99 |
| s02 change arms: R30 (`a66`, 8) and R32 (`a49`, 24) | 32 | 424 |
| s03 `dynamic`: R30 (1) and R32 (3) | 4 | 20 |
| s03 `final`: R30 (1) and R32 (3) | 4 | 18 |
| s01 change arms: R30 | 2 | 0 |
| **Total** | **78** | **561** |

147 of the 561 are steps the filter keeps ([filter.txt](../dead_end/filter.txt)).

## Fixed before any call

- Prompt `e01` (sha `4bd77647a0d7`), the clean frame, one call at a time on sctsvr6's `:8004`
  (`Qwen3-VL-30B-A3B`, remote profile, temperature 0), as probe DE.
- Filter: an answer counts only on a step where
  `dead_end_trigger.closed_door_places(rows, 4.0)` is at most 2.
- Rule per run: `a78`'s (`planner.latch_reads_agree`: yes on a step and on 2 of the last 3
  answers, none older than 15 steps), on the kept answers.

## Gate (set before any call)

| Readout | Pass |
|---|---|
| `initial` runs the rule fires in, anywhere in the run | 0 of 36 |
| s02 change-arm runs the rule fires in before the crossing | at most 2 of 32 |
| s03 `dynamic` runs the rule fires in | at least 3 of 4 |
| Asked steps answered | all 561 |

All four rows must hold. What the gate can tell apart, counted before any call with stand-in
answers (no model): a confirmer that is never wrong (yes in the shut tine facing its door, no
elsewhere) passes with 0, 0 and 3, so the s03 row asks for the ceiling; yes on every step fails
with 11 of 36 `initial` runs and 23 of 32 s02 runs.

Reported with no gate: s03 `final` runs (4) and where the drone stood
when the rule fired there; the s01 change arms (no asked step); the rule on every answer with no
filter; the s03 `dynamic` runs fired in with 25 or more steps left; the yes rates.

## What either outcome means

- **Pass:** the filter held on runs it was not fitted on. It becomes a candidate trigger for a
  new agent version (not `a78`, which stays dropped). It is still an open-loop count: the latch
  changes where the drone goes, and so which steps are asked.
- **Fail:** the filter was a fit to Round F, R32P and R35. It is dropped, and R38 ends where
  probe DE left it.

Known limits, before the result:

- The s03 side is thin: 4 `dynamic` runs, 20 asked steps. The weight of this check is on the
  `initial` and s02 rows, which the fit could not see (`initial`) or saw too kindly (s02).
- R32 flew `a49`: the same perceiver and door confirmer (`g05`, `d01`) but the older memory, so
  its drone approaches differently and its asked steps are a different mix.
- Still two site families. A hall with one door is in none of them.

## Result

Not run yet.
