# R62: a93 with a stop wall one cell wide either side, not two, contested cells

**Agent:** `a99` (`03c0c43ab9b3`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep); **flown 2026-11-07**

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R64, the reference lane
(`a93`) flown in the same batch on the same renderer.**

## Change

One parameter of the planner's cost map (`PATHFINDER_A99`, `inflate_stop_walls` 2 → 1): a move stopped
short writes a stop wall one cell ahead, and the cost map widens it over unknown ground by one cell either
side (0.85 m), not two (1.7 m). Seen floor and visited cells are never sealed, as before. Nothing else
changes.

## Evidence

- **Two lobby stalls in two flights, same seed, two agents** (`a93` R58, `a98` R59; s03 `dynamic` seed 2;
  scratch traces of 2026-11-07): the drone is stopped at the stem's mouth at step 3 or 4 (x = 16, y = 1.7,
  heading 158, a 1.1 m move), the stop wall and its two-cell wings seal the mouth (its cells are still
  unknown ground at step 4), the route turns to the lobby's unknown north and the drone spends the rest of
  the run there (min x 15.2, 57 steps, no goal report, no latch; labelled `pre_change_failure`). In R61 the
  same seed went down the stem at once and was won at 51. The stem is 3 m wide (3.5 cells): a bump at its
  edge inflated by two cells seals it; by one, two cells stay open.
- **Why two was chosen** (`server/decider/agent.py`, `PATHFINDER_A63`): "the s03 divider and the s02 door
  wall are unknown to the map until bumped, and each bump then seals about 4 m of it" (probe pathfinder,
  first run, R30). Since then `a17d`'s door walls and `a17f`'s firm walls write the shut door and nose-on
  walls from reads before any bump, so the inflation carries less.
- No offline replay is possible without the memory's state; the shakedown's s03 cells and the flight are
  the test. Offline: 82 tests pass; `VLM_AGENT=a99 python eval/probes/a63_smoke.py` 627/627 planned, 0
  failed.

## Hypothesis

With the stop wall one cell wide, a bump at the stem's mouth no longer seals it, no s03 run stalls in the
lobby, and `a99` scores at least as many runs as the reference lane in the same batch.

## Predictions

| | R64 (`a93`, reference) | Predicted R62 (`a99`) |
|---|---|---|
| total | its own flight | reference +0 to +2 |
| s02 | | within 2 of the reference (the s02 bump is at the divider, whose shut door is written from reads) |
| s03 | | reference +0 to +1; no run with min x above 14 |

## Manipulation check

- Every `run.json` carries `a99`, `03c0c43ab9b3`; every `godot.log` names `NVIDIA H100 PCIe`.
- **No s03 run ends with min x above 14** (`a93`: R58 and R59 one each, R61 none).
- Every s03 run is in the stem (x < 15) by step 8.
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps; walls in
  flight within 4 points of R64's; the latch in s03 within 9 steps of a square read.

## Drop criterion

Three or more below R64: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed (nothing the model perceives or is told changes).

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-a` on `:8004`, H100 frames: s03 `dynamic`, s03 `final` (the stem),
s02vc `final`, s02c `dynamic` (the divider's bumps must still seal). Scored by the manipulation check.

## Host

Twelve lanes `~/asep-r62-l1..12`, four to an instance: **R62 (`a99`) lanes 1–4 on `:8004`**, R63 (`a100`)
lanes 5–8 on a copy on GPU 3 (`:8006`), R64 (`a93`) lanes 9–12 on a copy on GPU 4 (`:8007`); Godot on GPU 5.
`~/r62_fly.sh`. About 45 minutes. Recorded in `phase.json` "lanes".

## Builds on

R53/R54 (`a93`). Branch `phase2/r62-mouth-stall` from `phase2/r59-latch-survey` (`e8b348d`); R63 and R64 share
the branch and the PR.

## Outcome

**Flown 2026-11-07, 20/30** (s02 16/24, s03 4/6) against the reference lane's 16/30 (R64, `a93`'s lowest of four
H100 flights): four above, a carry by the rule, but not the parent (`a100` stood at 22 in the same batch) and the
mechanism untested: no run of either agent stalled in the lobby (every s03 run in the stem by step 4). Every check
held. [summary.md](summary.md). Rides into R65 (`a101`) on `a100`.
