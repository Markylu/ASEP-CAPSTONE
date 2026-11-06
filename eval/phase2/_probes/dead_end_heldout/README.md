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

## Result (run 2026-11-05)

561 calls, one at a time, from a checkout of `96245ac` (the commit that set the gate) in the
`asep-phase1` image on sctsvr6's `:8004`, with no flight running on the host. Every asked step
had its frame; no failed call, all on the `json_schema` rung, median 924 ms. Sample, calls and
[score.txt](score.txt) are here; the frames stay on the host.

| Readout | Pass | Result |
|---|---|---|
| `initial` runs the rule fires in | 0 of 36 | **1** |
| s02 change-arm runs the rule fires in before the crossing | at most 2 of 32 | 0 |
| s03 `dynamic` runs the rule fires in | at least 3 of 4 | 3 |
| Asked steps answered | all 561 | 561 |
| **Gate** | | **fail** |

**The gate fails on its first row.** By the rule set beforehand the filter is dropped and R38
ends where probe DE left it.

| Group | Runs | Yes, all answers | Yes, kept answers | Fired (filter) | Fired (no filter) |
|---|---|---|---|---|---|
| `initial` | 36 | 5/99 | 4/44 | 1 | 1 |
| s02 change arms | 32 | 170/424 | 1/83 | 0 | 25 |
| s03 `dynamic` | 4 | 17/20 | 14/16 | 3 (2 with 25+ steps left) | 3 |
| s03 `final` | 4 | 18/18 | 4/4 | 1 | 2 |

**The run that fails it:** Round F s03 `initial` seed 4, a run `a66` won. `e01` says yes at steps
28 and 30, with one and two closed-door places known. The drone stands at (−6.5, −4.0) and
(−6.3, −5.7): already through the tine's open door (x = −6), in the lobby beyond it, one step
before it is counted across at step 31, headed 299° and 97°, well off the tine's axis (180°). `e01`'s
reason at step 30: "a narrow passage with walls on both the left and right sides, running away
from the camera toward a closed door". The full latch fires there too
(`a78_replay.py --answers probe:e01 --places 2 --held-out`,
[replay](../a78/replay_probe_e01_places2_heldout.txt)): it takes the tine the drone has just
flown as the dead end, and for steps 30 to 32 the route runs back down that tine (39 to 44
cells, where `a66`'s recorded route is 7 to 10 cells to the goal), rejoining at step 33. Open
loop: the recorded drone flew `a66`'s picks.

What the answers show (read after the gate, so a description):

- **The s02 half held.** With the filter the rule fires in none of the 32 s02 change-arm runs
  and none of the 30 s02 and s01 `initial` runs; with no filter it fires in 25 of the 32. Kept
  s02 answers: 2 yes in 124. This is on runs the fit never saw, 24 of them flown by another
  agent (`a49`).
- **`e01` does not tell a shut tine from anything else in s03.** It says yes on 38 of 41 asked
  steps there: 27 of 30 in the shut tine facing its door and 11 of 11 anywhere else, 3 of those
  in the `initial` runs, where no door is shut. In s03 the trigger is therefore the perceiver's
  closed-door read, twice; `e01` adds only that the place looks like a corridor. The filter
  cannot help: a tine has one door, with it shut or not.
- The `initial` arms of s03 are barely exposed (3 asked steps in 6 runs, in 2 of them), and one
  of those two runs fired.
- s03 `dynamic`: fired at steps 19, 36 and 27, in the shut tine each time. The fourth run (R32
  seed 3) has no asked step: the door never shut in it. The count is the ceiling.
- s03 `final`: fired in R32 seed 3 (lost) at step 37, in the shut tine. In R32 seed 2 (lost) the
  yes answers in the shut tine come with three places known, and the filter drops them.
- The full latch on these runs with the filter: 3 of 4 s03 `dynamic` runs latched, the route out
  of the shut tine on 79 of 102 steps from the latch on (0 of 23 in R32 `dynamic` seed 2, not
  looked into), no s02 or s01 change-arm run latched, no step without a route. With no filter
  ([replay](../a78/replay_probe_e01_heldout.txt)): 25 of 34 change-arm runs latched and 79 steps
  without a route.

Where this leaves it: the places filter does what it was fitted to do in the hall, out of
sample. The dead-end call it gates is not a dead-end call in s03, and one won run in 36 pays
for that. Nothing here was flown.

