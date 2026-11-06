# R55: a89 again with Godot rendered on an H100 (host round), contested cells

**Agent:** `a89` (`85cda76df25b`), as R49 flew it, unchanged · **Prompt:** `p17` (`cb3578251cfe`) ·
**Perceiver:** `g05` · **Door confirmer:** `d01` · **Memory:** `a17f` ·
**Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`), not lavapipe ·
**Status:** laid out 2026-11-06 on the operator's call ("Yes, fly a89") after R54; the layout is
Claude's, with its reason; not flown

Written before flying. Spec: `docs/phase2-test-plan.md` (host rounds, changelog 2026-11-02).
Design: the ten contested cells, seeds 1–3, 30 runs, read against R49 (`a89` on lavapipe,
23/30) and beside R53/R54 (`a93` on lavapipe 24/30, on H100 frames 19/30).

## Change

**No agent change. The bar's agent flown on H100 frames.** `a89`, its sha, the prompt, the
sites, the seeds and the model are R49's; the renderer is R54's.

## Why

R54 put `a93` on H100 frames at 19/30 against 24/30 on lavapipe's, flown beside it: a gap of 5,
outside the 4 allowed, with every reading below the score inside its limit. One flight each
cannot say whether the 5 is the renderer or a flight's own spread (23, 19, 20 for near-identical
agents on lavapipe on 2026-11-06). Flying the bar's agent on H100 frames gives the renderer a
second reading on a second agent, and gives H100 frames a bar of their own if they need one.

## Hypothesis

`a89` on H100 frames reads like `a89` on lavapipe: within 4 of R49's 23/30, with s02 within 3
of 21/24. Then R54's gap was a flight's spread and later rounds may fly on H100 frames and be
read against the lavapipe bar, each saying so in `phase.json` "lanes".

## Predictions

| | R49 (`a89`, lavapipe) | R54 (`a93`, H100) | Predicted R55 (`a89`, H100) |
|---|---|---|---|
| total | 23/30 | 19/30 | 19–27; within 4 of 23 if the renderer is clear |
| s02 | 21/24 | 17/24 | 18–22 |
| s03 | 2/6 | 2/6 | 1–5 (six runs: not read alone) |

## What it decides

- **Within 4 of 23:** H100 frames are cleared for rounds read against the lavapipe bar; R54's
  19 is read as one low flight of `a93`, and `a93`'s two flights stand at 43/60.
- **Below 19:** the renderer costs runs. H100 rounds are read against H100 rounds only, with
  R55 as their bar; lavapipe stays for rounds read against `a85`/`a89`.
- **At 19 or 18:** not settled; a third H100 flight is the operator's call.

## Manipulation check

- Every run's `godot.log` names `NVIDIA H100 PCIe`; every `run.json` carries `a89`,
  `85cda76df25b`.
- Walls in flight (`eval/r28_flight.py`): missed and phantom within 4 points of R49's
  (20.6 / 9.2 / 13.5) and R54's (19.2 / 11.5 / 15.5).
- The survey starts in at least 19 of the 24 s02 runs by step 8 (R49: 21); a route on at
  least 95% of steps.
- Goal reports with no line of sight per run within a third of R49's (`a89` has no check: the
  count is of reports made, `eval/probes/a93_goal_check.py --folders R55_h100_a89`).

## Shakedown

None: the lane path on H100 frames flew R54's 30 runs valid an hour before, and `a89` has
flown 30 valid runs (R49). Nothing in code is new.

## Host

Twelve lanes, `~/asep-r55-l1..12`, four to an instance: lanes 1–4 on `:8004`, 5–8 on a copy on
GPU 3 (`:8006`), 9–12 on a copy on GPU 4 (`:8007`), the per-instance load every round has had;
Godot on GPU 5. Nothing else of Claude's on the host. About 15 minutes.

## Builds on

R54 (the renderer), R49 (the agent). Branch `phase2/r55-h100-a89` from `phase2/r53-goal-check`
(`21d2458`).

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
