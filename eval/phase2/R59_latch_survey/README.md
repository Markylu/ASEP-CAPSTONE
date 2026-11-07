# R59: a94's latch and a95's survey start together on a93, contested cells

**Agent:** `a98` (`6905821be0ab`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep); **flown 2026-11-07**

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R61, the reference lane
(`a93`) flown in the same batch on the same renderer.**

## Change

`a94`'s latch and `a95`'s survey start, both on `a93` (`PATHFINDER_A98`): the dead-end latch's trail
trigger fired by one square closed read and for a corridor drifted into without a turn (mouth at the
first point off the direct line, the line's bearing as axis, lane span 3.4 m: R56); and the wall survey
started for a drone on the direct line now, not only one that never left it (R57). Nothing else changes.
Two changes, each flown alone in the batch before; this round asks whether they add. They touch different
code (the latch, held off while a survey runs; the survey's start) and different sites (s03, s02).

## Evidence

- **R56 (`a94`) 20/30 against the reference's 20/30, s03 `dynamic` 2/3 against 0/3**: both wins through a
  latch 6 steps after the first square read; every latch within 6 steps of its read (`a93` in the same
  batch: 5 and 33). s02 16 against 17 (`eval/phase2/R56_latch_line/summary.md`).
- **R57 (`a95`) 22/30 against 20/30, s02 19/24 against 17/24**; the rule acted in 2 of 24 runs (both lost)
  and the gain came in cells where it did not; no survey in s03 (`eval/phase2/R57_survey_line_now/summary.md`).
- **On the record, both rules at once** (`python eval/probes/a94_latch_check.py --agent a98 --folders
  R44..R58`, 390 runs, survey-gated): the latch fires in the shut tine in 37 of 39 s03 `dynamic` runs
  (`a93`: 34), wrong tine 0, a latch before crossing in 11 of 219 won s02 runs (`a93`: 9). The survey rule
  starts a survey in 11 of 296 runs that had none in R44–R55, all s02 (`eval/probes/a95_survey_start.py`).
- Offline: 82 tests pass; `VLM_AGENT=a98 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed.

## Hypothesis

The two changes add: `a98` wins at least as many runs as the reference lane in the same batch, with s03
`dynamic` above `a93`'s and s02 not below it.

## Predictions

| | R61 (`a93`, reference) | Predicted R59 (`a98`) |
|---|---|---|
| total | its own flight | reference +0 to +3 |
| s02 | | within 2 of the reference |
| s03 `dynamic` | | 1–2 of 3 (`a93` on H100 frames: 1/3, 1/3, 0/3) |
| s03 `final` | | within 1 of the reference |

## Manipulation check

- Every `run.json` carries `a98`, `6905821be0ab`; every `godot.log` names `NVIDIA H100 PCIe`.
- In the s03 runs that read a closed door square in the shut tine, the latch comes within 9 steps (R56:
  4, 6, 6); no latch in the open tine or the stem.
- The survey starts in at least 22 of 24 s02 runs by step 8 and in every s02 run whose trail comes back
  within 2.5 m of the line with a square closed read; no survey in any s03 run.
- A latch before crossing in at most 3 won s02 runs (R56: 0; R57: 2; R58: 1).
- Unbroken: a route on at least 95% of steps; walls in flight within 4 points of R61's.

## Drop criterion

Three or more below R61: dropped. Within 2: a draw, not carried. Three or more above: carried as the
next batch's parent and reference.

## Probe gate

Not needed (nothing the model perceives or is told changes). Offline gate: the combined replay above (at
least 34 of 39 s03 `dynamic` fires, at most 12 of 219 won s02 runs with a latch before crossing): passed, 37
and 11.

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-a` on `:8004`, H100 frames: s03 `dynamic`, s03 `final` (the latch),
s02vc `final`, s02a `dynamic` (the survey). Scored by the manipulation check; wins not required.

## Host

Twelve lanes `~/asep-r59-l1..12`, four to an instance: **R59 (`a98`) lanes 1–4 on `:8004`**, R60 (`a96`)
lanes 5–8 on a copy on GPU 3 (`:8006`), R61 (`a93`, the reference) lanes 9–12 on a copy on GPU 4 (`:8007`);
Godot on GPU 5 (`GODOT_VK=nvidia GODOT_RENDER_GPU=5`). `~/r59_fly.sh`. About 45 minutes for the three rounds
(batch 1 took 45). Recorded in `phase.json` "lanes".

## Builds on

R56 (`a94`) and R57 (`a95`), on R53/R54's `a93`. Branch `phase2/r59-latch-survey` from `phase2/r56-latch-line`
(`3f71f9d`); R60 and R61 share the branch and the PR.

## Outcome

**Flown 2026-11-07, 20/30** (s02 17/24, s03 3/6) against the reference lane's 21/30 (R61): one below, a draw, not
carried; the two changes did not add (s02 +1, s03 −2). The latch fired 5 steps after the read in both runs that reached
the shut door; the two other s03 `dynamic` runs never got there (one never left the lobby). The survey rule started one
survey in the s03 stem (won anyway) and none in s02 that the old rule would have refused. [summary.md](summary.md).
