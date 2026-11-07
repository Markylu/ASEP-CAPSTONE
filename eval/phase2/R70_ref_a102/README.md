# R70: a102 again, batch 5's reference lane on H100 frames (host round), contested cells

**Agent:** `a102` (`e405aeb4a004`), as R66 flew it, unchanged · **Prompt:** `p17` (`cb3578251cfe`) ·
**Perceiver:** `g05` · **Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100
(`GODOT_VK=nvidia`) · **Status:** laid out 2026-11-07 (Claude, overnight); **flown 2026-11-07**

Written before flying. A host round under the operator's rule of 2026-11-06 ("3+1 with reference lane"). `a102`
was carried in batch 4 (R66, 23/30 against `a100`'s 18/30), so it is batch 5's parent and reference. **This
reference flies on `:8004`, not `:8007`**: the four earlier reference lanes all flew on `:8007` and all landed
below their batch's candidates (R58 20, R61 21, R64 16, R67 18 against candidates at 19–23), and R55's one-agent
flight over the three instances won 9/12 on `:8004`, 4/10 on `:8006`, 5/8 on `:8007`. Design: the ten contested
cells, seeds 1–3, 30 runs.

## Change

**No agent change.** `a102` on H100 frames beside R68 (`a103`) and R69 (`a104`), same commit, same minutes. Its
second flight; the first was on `:8006`.

## Hypothesis

`a102` on H100 frames reads as in R66 within the family's spread: 19–25 of 30, s02 15–22, s03 2–6. If it reads
below 20 here on `:8004`, the instance is not what made the night's references low.

## Predictions

| | R66 (`a102`, `:8006`) | `a100` (2 flights) | `a93` (4 flights) | Predicted R70 |
|---|---|---|---|---|
| total | 23/30 | 22, 18 | 19, 20, 21, 16 | 19–25 |
| s02 | 20/24 | 18, 15 | 17, 17, 16, 13 | 15–22 |
| s03 | 3/6 | 4, 3 | 2, 3, 5, 3 | 2–6 |

## What it decides

The comparison for R68 and R69; `a102`'s second sample; and the first reference lane off `:8007`. The morning
report reads the night's carries against it.

## Manipulation check

- Every `run.json` carries `a102`, `e405aeb4a004`, `:8004`; every `godot.log` names `NVIDIA H100 PCIe`.
- No station given up in transit before its tenth step; the latch within 9 steps of a square read in the shut tine.
- Walls in flight within 4 points of R66's (20.5 / 9.6 / 12.0).
- The survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps.

## Drop criterion

Not applicable (a reference).

## Probe gate

Not needed (no change).

## Shakedown

None (30 valid runs in R66, 4 in its shakedown).

## Host

Lanes 1–4 of `~/asep-r68-l1..12` on `:8004`, beside R68 (`:8006`) and R69 (`:8007`); Godot on GPU 5.
`~/r68_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R66 (the same agent). Branch `phase2/r68-latch-inflate-20` (shared with R68 and R69).

## Outcome

**Flown 2026-11-07, 21/30** (s02 18/24, s03 3/6) on `:8004`: within the 19–25 predicted, two below R66's 23; `a102`
over two flights is 22 a flight (`a100` 20, `a93` 19). The first reference lane off `:8007` landed between its two
candidates (20, 23): the instance is not what made the night's reference lanes low. The bar for R68 and R69.
[summary.md](summary.md).
