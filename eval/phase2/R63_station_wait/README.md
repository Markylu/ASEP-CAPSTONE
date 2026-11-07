# R63: a93 with the survey's stations held 10 steps in transit, contested cells

**Agent:** `a100` (`22e2941dc494`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep), not flown

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R64, the reference lane
(`a93`) flown in the same batch on the same renderer.**

## Change

One parameter of the wall survey (`PATHFINDER_A100`, `survey.stall_steps` 6 → 10): a station that has not
come half a metre nearer is given up after 10 steps in transit, not 6. Nothing else changes (R52's `a92`
tried 12 on `a91`'s planner, without the station guard; this is `a93`'s planner).

## Evidence

- **Batch 2 (R59, R60, R61), nine s02 losses of three agents whose survey is `a93`'s:** in six the first or
  second station was given up at the sixth step of transit while the drone flew straight at the shut door
  with "toward your target" on the sharp turn to the station (R59 s02vc `dynamic` 2 and 3: both stations given
  up, 6 steps each, **no look at all**, lost; R61 s02c `dynamic` 1 and s02c `final` 2; R60 s02vc `dynamic` 3
  and s02c `final` 1). The survey timelines (scratch `survey_timeline.py`) show `tr0` → `tr1` six steps after
  the start in each. In R59 s02vc `dynamic` 2 the navigator took straight on steps 5–7 with the tag on sharp
  left, turned at step 8 and was given up at 11, 1.3 m from where a look would have begun.
- **Across the night:** runs that looked from their first station crossed in most flights; runs that gave both
  stations up in transit were lost in every case seen (R59 s02vc `dynamic` 2 and 3, R57 s02va `dynamic` 2).
- **R52** (`a92`: 12 steps, on `a91`): 20/30 against `a91`'s 19/30; "the longer wait won the one run that
  called on it" (`eval/phase2/R52_station_stall/README.md`). R45's and R51's data had 9 first stations given up
  in transit, 3 of them won.
- Offline: 82 tests pass; `VLM_AGENT=a100 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed.

## Hypothesis

Held four steps longer, the first station is reached and looked from in the runs where the navigator is
slow to turn, and `a100` scores at least as many runs as the reference lane in the same batch, the gain on
the c and vc sites.

## Predictions

| | R64 (`a93`, reference) | Predicted R63 (`a100`) |
|---|---|---|
| total | its own flight | reference +0 to +3 |
| s02 | | reference +0 to +3; stations given up in transit in at most half as many runs |
| s03 | | within 1 of the reference (no survey there) |

## Manipulation check

- Every `run.json` carries `a100`, `22e2941dc494`; every `godot.log` names `NVIDIA H100 PCIe`.
- **No station given up in transit before its tenth step**; stations given up in transit in at most half as
  many s02 runs as in R64.
- The survey in at least 19 of 24 s02 runs by step 8; no survey in any s03 run.
- Unbroken: a route on at least 95% of steps; walls in flight within 4 points of R64's.

## Drop criterion

Three or more below R64: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed (nothing the model perceives or is told changes).

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-b` on `:8006`, H100 frames: s02vc `dynamic`, s02c `final`, s02a
`dynamic` (the stations), s03 `dynamic` (unchanged). Scored by the manipulation check.

## Host

Lanes 5–8 of `~/asep-r62-l1..12` on `:8006` (a copy of `:8004` on GPU 3), beside R62 (`:8004`) and R64
(`:8007`); Godot on GPU 5. `~/r62_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R53/R54 (`a93`); R52 (`a92`) for the idea. Branch `phase2/r62-mouth-stall` (shared with R62 and R64).

## Outcome

Not flown yet.
