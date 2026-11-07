# R66: a100 with a94's latch (one square read, the corridor drifted into), contested cells

**Agent:** `a102` (`e405aeb4a004`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep); **flown 2026-11-07**

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R67, the reference lane
(`a100`) flown in the same batch on the same renderer.**

## Change

`a94`'s dead-end latch on `a100` (`PATHFINDER_A102`: `a100`'s planner with `a94`'s `dead_end_latch`): the
trail trigger fires on one square closed read (not two), and a corridor the drone drifted into without a turn
is recognised from where its trail left the direct line (the first point off it as the mouth, the line's
bearing as axis, a 3.4 m lane). `a100`'s survey (stations held 10 steps) is unchanged.

## Evidence

- **The latch's mechanism held in two flights**: across R56 (`a94`) and R59 (`a98`) it fired within 6 steps
  of the first square closed read in 5 of 5 runs that reached the shut s03 door, and 3 of those 5 were won
  through it; `a93` in the same batches latched 5, 33, 6, 6 steps after the read and never in one run
  (`eval/phase2/R56_latch_line/summary.md`, `R59_latch_survey/summary.md`). Totals were level (20 against 20,
  20 against 21): the s03 `dynamic` runs lost were lost before the door.
- **R63 (`a100`)** s03 `dynamic` 1/3: seed 2 read a closed door from the lobby at step 1 and latched only at
  33 (`a93`'s two-read trigger); seed 3 read at 34, latched at 39, not through in time.
- The two changes touch different parts (the latch, held off while a survey runs; the survey's transit) and
  different sites (s03; s02).
- Offline: 82 tests pass; `VLM_AGENT=a102 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed. The
  latch replay (`eval/probes/a94_latch_check.py --agent a94`, R44–R58): 29 of 30 s03 `dynamic` fires in the
  shut tine (`a93` 26), s02 won runs with a latch before crossing 7 of 167 (`a93` 6).

## Hypothesis

On `a100`, the latch wins the s03 `dynamic` runs that reach the shut door and costs nothing on s02: `a102`
scores at least as many runs as the reference lane in the same batch, with s03 `dynamic` above it.

## Predictions

| | R67 (`a100`, reference) | Predicted R66 (`a102`) |
|---|---|---|
| total | its own flight | reference +0 to +2 |
| s02 | | within 2 of the reference |
| s03 `dynamic` | | 1–2 of 3, every latch within 9 steps of a square read |

## Manipulation check

- Every `run.json` carries `a102`, `e405aeb4a004`; every `godot.log` names `NVIDIA H100 PCIe`.
- In the s03 runs that read a closed door square in the shut tine, the latch comes within 9 steps; no latch in
  the open tine or the stem.
- No station given up in transit before its tenth step; a latch before crossing in at most 3 won s02 runs.
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps; walls in
  flight within 4 points of R67's.

## Drop criterion

Three or more below R67: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed (nothing the model perceives or is told changes).

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-b` on `:8006`, H100 frames: s03 `dynamic`, s03 `final`, s02vc `final`,
s02a `dynamic`. Scored by the manipulation check.

## Host

Lanes 5–8 of `~/asep-r65-l1..12` on `:8006` (a copy of `:8004` on GPU 3), beside R65 (`:8004`) and R67
(`:8007`); Godot on GPU 5. `~/r65_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R63 (`a100`), R56 (`a94`). Branch `phase2/r65-wait-inflate` (shared with R65 and R67).

## Outcome

**Flown 2026-11-07, 23/30** (s02 20/24, s03 3/6) against the reference lane's 18/30 (R67): five above, **carried**;
the night's highest H100 flight. The latch fired 5–11 steps after the read in 5 of 5 runs that read the door in the
tine; s03 `dynamic` 1/3 against 1/3; the five-run gain is on s02, where `a102` and `a100` share every line, so it is
spread (and perhaps instance: the reference flew on `:8007`). `a102` is batch 5's parent and reference, on `:8004`.
[summary.md](summary.md).
