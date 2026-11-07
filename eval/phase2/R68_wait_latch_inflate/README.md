# R68: a102 with a stop wall one cell wide either side, contested cells

**Agent:** `a103` (`e53c86de68a7`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep); **flown 2026-11-07**

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R70, the reference lane
(`a102`, carried in batch 4) flown in the same batch on the same renderer.** The last batch of the night.

## Change

`a99`'s one parameter on `a102` (`PATHFINDER_A103`, `inflate_stop_walls` 2 → 1). `a102` (the survey's stations
held 10 steps; `a94`'s latch) is otherwise unchanged.

## Evidence

- **R66 (`a102`) 23/30 against `a100`'s 18/30, carried**; **R65 (`a101`, `a100` with the one-cell walls) 22/30**
  in the same batch; R62 (`a99`, `a93` with them) 20/30 against 16/30. In 60 runs on two parents the one-cell
  wall has cost nothing visible at the s02 divider (surveys in 22 of 24 both times, 16 and 20 crossings) and
  the lobby stall it was built against (R58, R59 s03 `dynamic` seed 2) has not recurred for any agent since,
  so its mechanism is still untested (`eval/phase2/R62_mouth_inflate/summary.md`, `R65_wait_inflate/summary.md`).
- **Instance caveat:** every reference lane of the night flew on `:8007` and landed below its candidates
  (20, 21, 16, 18); R55's one-agent flight over the three instances won 9/12 on `:8004`, 4/10 on `:8006`, 5/8
  on `:8007`. This batch flies the reference on `:8004` and this candidate on `:8006`.
- Offline: 82 tests pass; `VLM_AGENT=a103 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed.

## Hypothesis

On `a102`, the one-cell stop wall costs nothing on s02 and removes the lobby stall when it occurs: `a103` scores
at least as many runs as the reference lane in the same batch.

## Predictions

| | R70 (`a102`, reference, `:8004`) | Predicted R68 (`a103`, `:8006`) |
|---|---|---|
| total | its own flight | reference +0 to +2 |
| s02 | | within 2 of the reference |
| s03 | | within 1; no run with min x above 14 |

## Manipulation check

- Every `run.json` carries `a103`, `e53c86de68a7`, `:8006`; every `godot.log` names `NVIDIA H100 PCIe`.
- No s03 run with min x above 14; every s03 run in the stem by step 8.
- `a102`'s rules unchanged: no station given up in transit before its tenth step; the latch within 9 steps of a
  square read in the shut tine.
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps; walls within
  4 points of R70's.

## Drop criterion

Three or more below R70: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed (nothing the model perceives or is told changes).

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-a` on `:8004`, H100 frames: s03 `dynamic`, s03 `final`, s02vc `dynamic`,
s02c `final`. Scored by the manipulation check.

## Host

Twelve lanes `~/asep-r68-l1..12`, four to an instance: **R70 (`a102`, the reference) lanes 1–4 on `:8004`**,
R68 (`a103`) lanes 5–8 on a copy on GPU 3 (`:8006`), R69 (`a104`) lanes 9–12 on a copy on GPU 4 (`:8007`); Godot
on GPU 5. `~/r68_fly.sh`. About 50 minutes. Recorded in `phase.json` "lanes".

## Builds on

R66 (`a102`), R65 (`a101`), R62 (`a99`). Branch `phase2/r68-latch-inflate-20` from `phase2/r65-wait-inflate`
(`be70a69`); R69 and R70 share the branch and the PR.

## Outcome

**Flown 2026-11-07, 20/30** (s02 15/24, s03 5/6) against the reference lane's 21/30 (R70, `a102` on `:8004`): one
below, a draw, not carried. No lobby stall for any agent for the third flight; every check held; s03 5/6 is the latch's
work (gaps 0–6). [summary.md](summary.md).
