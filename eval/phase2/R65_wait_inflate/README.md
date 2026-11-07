# R65: a100 with a stop wall one cell wide either side, contested cells

**Agent:** `a101` (`42ae7616cca1`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep); **flown 2026-11-07**

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R67, the reference lane
(`a100`, carried in batch 3) flown in the same batch on the same renderer.**

## Change

`a99`'s one parameter on `a100` (`PATHFINDER_A101`, `inflate_stop_walls` 2 → 1): a move stopped short seals one
cell either side of the bump over unknown ground, not two. `a100` (the survey's stations held 10 steps in
transit) is otherwise unchanged.

## Evidence

- **R63 (`a100`) 22/30 against `a93`'s 16/30 in the same batch, carried**; one station given up in transit
  (at its tenth step) against five at the sixth (`eval/phase2/R63_station_wait/summary.md`).
- **R62 (`a99`) 20/30 against the same 16/30**, every check held, but no lobby stall occurred for either
  agent, so the change's mechanism (a bump at the s03 stem's mouth sealing it, R58 and R59 s03 `dynamic`
  seed 2) was not exercised; at the s02 divider the narrower stop wall cost nothing visible (survey in 22 of
  24, 16 crossings) (`eval/phase2/R62_mouth_inflate/summary.md`).
- The two parameters touch different parts (the cost map's bumps; the survey's transit).
- Offline: 82 tests pass; `VLM_AGENT=a101 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed.

## Hypothesis

On `a100`, the narrower stop wall costs nothing on s02 and removes the lobby stall when it occurs: `a101`
scores at least as many runs as the reference lane (`a100`) in the same batch.

## Predictions

| | R67 (`a100`, reference) | Predicted R65 (`a101`) |
|---|---|---|
| total | its own flight | reference +0 to +2 |
| s02 | | within 2 of the reference |
| s03 | | reference +0 to +1; no run with min x above 14 |

## Manipulation check

- Every `run.json` carries `a101`, `42ae7616cca1`; every `godot.log` names `NVIDIA H100 PCIe`.
- No s03 run ends with min x above 14; every s03 run in the stem by step 8.
- No station given up in transit before its tenth step (`a100`'s rule, carried).
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps; walls in
  flight within 4 points of R67's.

## Drop criterion

Three or more below R67: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed (nothing the model perceives or is told changes).

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-a` on `:8004`, H100 frames: s03 `dynamic`, s03 `final`, s02vc
`dynamic`, s02c `final`. Scored by the manipulation check.

## Host

Twelve lanes `~/asep-r65-l1..12`, four to an instance: **R65 (`a101`) lanes 1–4 on `:8004`**, R66 (`a102`)
lanes 5–8 on a copy on GPU 3 (`:8006`), R67 (`a100`) lanes 9–12 on a copy on GPU 4 (`:8007`); Godot on GPU 5.
`~/r65_fly.sh`. About 50 minutes. Recorded in `phase.json` "lanes".

## Builds on

R63 (`a100`), R62 (`a99`). Branch `phase2/r65-wait-inflate` from `phase2/r62-mouth-stall` (`7e3e2f5`); R66 and
R67 share the branch and the PR.

## Outcome

**Flown 2026-11-07, 22/30** (s02 20/24, s03 2/6) against the reference lane's 18/30 (R67, `a100`): four above, a
carry by the rule but not the parent (`a102` at 23 in the same batch); no lobby stall for either agent again, the
mechanism still untested, no visible cost at the divider in 60 runs. Instance caveat: the reference flew on `:8007`
as in every batch. [summary.md](summary.md). Rides into R68 (`a103`) on `a102`.
