# Why R25D scored 14/18

Analysis of 2026-10-29, after the round. It uses the recorded runs only, with no model calls, plus
step-0 frame hashes read on sctsvr6.

## Short answer

R25D's score comes from a real but modest gain from memory `a17b` and an agent with fewer
moving parts, on top of a lucky draw. Runs are not reproducible: the same first frame with the
same 999-token input gives different perceiver readings in different rounds at temperature 0.
Each run is therefore a random draw from step 0. An agent with the a17b family's typical
per-cell rates scores 14/18 or more about 3% of the time. The best of six such rounds does so
about 15% of the time.

## Where the +3 came from

Per-run outcomes, with steps to the goal or the final distance, for the rows where the rounds
differ:

| run | R20 (`a37`) | R25 (`a48`) | **R25D (`a49`)** | R22K (`a43`) |
|---|---|---|---|---|
| s02a/dynamic | 18.9 m | ok@22 | ok@23 | 12.8 m |
| s02c/final | ok@33 | 12.5 m | 11.1 m | 13.9 m |
| s02c/dynamic | 20.0 m | ok@27 | ok@27 | ok@28 |
| s02va/dynamic | 19.4 m | 16.6 m | **ok@34** | ok@26 |
| s02vc/final | 16.7 m | 17.3 m | **ok@43** | ok@37 |
| s02vc/dynamic | 14.1 m | 20.7 m | **ok@36** | 13.6 m |
| s03/final | ok@53 | ok@34 | 9.2 m | 9.4 m |

Against R20 (the same agent on memory `a17`), R25D gained five s02 runs and lost s02c `final` and
s03 `final`. Every gain is an s02 run: the open door was found and passed.

## 1. Not the side choice

At the s02 divider a run is decided by whether the drone first goes toward the open door. Over
all rounds, R1 to R26N (312 s02 `final`/`dynamic` runs):
- right side first: solved 68 of 184 (37%);
- wrong side first: solved 13 of 100 (13%);
- never along the divider: solved 0 of 28.

R25D went to the right side first in 6 of 8 runs, the same as R19, R19K, R20 and R22K. The
difference is what came next: R25D got through on 5 of its 6, against R20's 2 of 6 and R22K's 3
of 6.

## 2. Memory a17b helps at the door (real, modest)

s02 `final`/`dynamic` runs, steps before crossing, within 3 m of the open door:

| | runs reaching 3 m | solved | steps there | "searched already" noted | turn-arounds |
|---|---|---|---|---|---|
| `a17` (R19–R21K) | 33 | 15 (45%) | 147 | 80 (54%) | 30 (20%) |
| `a17b` (R22–R26N) | 35 | 20 (57%) | 124 | 32 (26%) | 19 (15%) |

No run that never came within 3 m of the open door was solved (0 of 28). `a17b` writes no wall
at the end of an `open_near` strip. That halves the false "searched already" notes beside the
open door, so the drone turns away from it less often. Turn-arounds against a forward "toward"
dropped across the whole round (R20 14, R25D 4).

## 3. Fewer moving parts

R25D has no along-the-wall items (R21/R22: `final` fell to 2/6), no "other way" item (R26: 9/18)
and no goal confirmer. The goal confirmer shows no consistent effect across the seven paired
rounds (with c01 minus without: +4, +1, +1, −1, +2, −2, −2; the last two pairs are R25D/R25 and
R26N/R26). Of the `a17b` agents, `a49` is the closest to the plain goal-reach agent; the others
added detour machinery that the record says costs `final` runs.

## 4. Luck: runs are not reproducible

- **Same input, different reading.** The step-0 frame is byte-identical across R22K, R25, R25D,
  R26 and R26N (md5 of `f000000.png` on the lanes), with the same pose, prompt `g05` and
  999-token input. Even so, the perceiver read it as all `open_near` in R25D and all `open_far`
  in R25 for s02vc `final`. In s02c `final` the readings also differ. Temperature is 0; the
  shared vLLM batches 8 lanes, and batched inference is not bit-stable.
- **Trajectories split early.** R25D and R25 differ only by the goal confirmer, which made no
  call before the split. Their trajectories split at step 1 (s01, s02va `final`), 2 (s03), 6
  (s02c) and 11 (s02vc).
- **Simulation.** The `a17b` family's per-cell success rates (six rounds) give an expected total
  of 11.3 ± 1.4. Leaving R25D out: expected 10.8, P(≥ 14) = 2.6%. Since the best of six similar
  rounds is the one being singled out, P(max ≥ 14) is about 15%.
- **R25D's rarest wins.** s02a `dynamic` and s02vc `dynamic` were solved by 1 of the 5 other
  `a17b` rounds each; s02a `final` and s02va `dynamic` by 2 of 5 each.

## What this means

- Keep `a49` as the base. Its pieces have support of their own: `a17b` at the door, no along
  items, no "other way".
- Treat 14/18 as an upper draw: about 11–12 is the more likely level.
- One-seed rounds cannot separate changes worth ±1–2 runs. Re-flying `a49` 2–3 more times
  (repeats of seed 1 already vary run to run) would give its real rate before more is built on
  it.
- The perceiver's instability on an identical frame is the largest single noise source. Making
  the perceiver steadier (several reads per step with a majority vote, or a stable rung without
  retries) would help both scores and measurement.
