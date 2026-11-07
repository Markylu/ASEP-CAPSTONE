# R56: a93 with the latch fired by one square read and from the line's departure, contested cells

**Agent:** `a94` (`3ac7eac6e09d`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep), not flown

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06 (`eval/docker/README.md`, changelog). Design: the ten contested cells, seeds 1–3, 30 runs,
**read against R58, the reference lane (`a93`) flown in the same batch on the same renderer.** The
lavapipe numbers (`a93` 24/30, R53) are quoted for the record only.

## Change

One change to the planner, in the dead-end latch's trail trigger (`planner.confined_run`,
`PATHFINDER_A94`):

1. **One square closed read fires it, not two** (`confined.reads` 2 → 1). The read must still be
   taken in the centre three strips with the drone looking along the run (within 70 degrees of
   its axis), and the other conditions (the drone confined to the run's lane, not still advancing
   down it, no ground stood on beside it) are unchanged.
2. **A corridor the drone drifted into without a turn** is recognised from where its trail left the
   direct line from the spawn to the goal (`planner._from_line`, `confined.from_line`): when the
   drone is now more than `off_line_m` (2.5 m) off that line, the first trail point beyond that
   band (after the last one within it) is the corridor's mouth and the line's own bearing its
   axis; the same confinement, advance, beside and read checks apply from that point on, the
   lane's span measured as `from_line_span_m` (3.4 m, the tine's width and a little, against
   `span_m` 2.8 for a run's own axis). Before, a straight run that reached back to the spawn was
   never a corridor (its mouth would have been the spawn).

Everything else is `a93`: the goal-report check, the survey, the latch's exit, the reopening, the
navigator's notes.

## Evidence

- **Where `a93` loses s03 `dynamic` (1/3 in R53 and R54; `a89` 1/3 in R49 and R55):** in the tines,
  not the lobby. The latch comes late or never: R55 s03 `dynamic` seed 1 read the shut door at
  step 25 and latched at 58 (28 steps in the shut tine); R54 `dynamic` seed 3 read it at 18 and
  never latched (42 steps); R51 `dynamic` seed 2 at 18, never; R54 `final` seed 1 at 13, latched at
  35; R49 `final` seed 2 at 17, latched at 44 (`eval/phase2/R5[345]_*/summary.md`).
- **Why, on the record** (the trigger replayed condition by condition, `eval/probes/a94_latch_check.py`
  and the scratch diagnosis of 2026-11-07): in R55 `dynamic` seed 1 the one condition unmet from
  step 25 to 57 was the second read: the drone turned about at the door and never faced it again
  while in the tine. In R54 `dynamic` seed 3, R54 `final` seed 1 and R49 `final` seed 2 the straight
  run found reached back to the spawn (the drift from the stem into the tine stayed under the
  30-degree segment rule), so `_turned_into` was false and no corridor was found until the drone
  turned about and a shorter run ended at the door.
- **The change on the record, gated as in flight** (no latch while a survey runs;
  `python eval/probes/a94_latch_check.py --agent a94 --folders R44_survey_latch_fixed,R45_survey_lineup,R46_behind_always,R47_station_guard,R49_no_sentence,R51_no_station_guard,R52_station_stall,R53_goal_check,R54_h100_frames,R55_h100_a89 --runs`,
  300 runs): the latch fires in the shut tine in **29 of 30** s03 `dynamic` runs (`a93`: 26), never
  later than `a93`'s and earlier in 10 of the 60 s03 runs: R55 `dynamic` 1 at **25, not 58**; R54
  `final` 1 at **21, not 35**; R54 `dynamic` 3 at **24** and R51 `dynamic` 2 at **22** where `a93`
  never fired (closed reads from 18 in both); R49 `dynamic` 2 at 46, not 56; R53 `dynamic` 3 at 27,
  not 32; R44 `dynamic` 1 at 43, not 47; R47 `dynamic` 1 at 54, not 58; R55 `dynamic` 2 at 22, not
  24; R51 `dynamic` 1 at 58 where `a93` never fired. It fires in the wrong tine in none. R49 `final`
  2 stays at 44 (the drone stood beside the lane).
- **Cost in s02, same replay:** a latch before the drone crossed the divider in **7 of 167 won runs**
  (`a93`: 6) and 35 of 73 lost runs (`a93`: 24).
- **First shakedown (at `c403f7b`, the from-line axis then the bearing from the mouth to the
  drone):** s03 `final` 1 read the shut door at 13 and latched at 31 (lost), s03 `dynamic` 1 read at
  18, latched at 24, won in 50. On the record of that `final` run the mouth-to-drone axis swung with
  the zigzag and the lane's span with it (2.9 to 3.4 m against 2.8); with the line's bearing as the
  axis, the mouth at the first point off the line and `from_line_span_m` 3.4 the trigger fires at 26
  on that trail. The agent was changed before flying (its sha moved; this round's lock with it) and
  the shakedown re-flown at the flying commit. Open loop: the replay cannot say what the drone
  does after a latch, only where one would have fired.
- Offline: `python -m pytest server/decider/tests -q` 82 passed; `VLM_AGENT=a94 python
  eval/probes/a63_smoke.py` 627/627 steps planned, 0 failed.

## Hypothesis

With the latch firing on the first square read and for a corridor drifted into, `a94` leaves the
shut s03 tine sooner than `a93` and wins at least as many runs as the reference lane in the same
batch, with the gain on s03 `dynamic`.

## Predictions

Against R58 (`a93`, the same batch, H100 frames; `a93`'s earlier H100 flight R54 was 19/30, s02
17/24, s03 2/6).

| | R58 (`a93`, reference) | Predicted R56 (`a94`) |
|---|---|---|
| total | its own flight | reference +0 to +3 |
| s02 | | within 2 of the reference |
| s03 `dynamic` | | 1–2 of 3 (the four `a93`/`a89` flights: 1/3 each) |
| s03 `final` | | within 1 of the reference |

## Manipulation check

- Every `run.json` carries `a94`, `3ac7eac6e09d`; every `godot.log` names `NVIDIA H100 PCIe`.
- In the s03 runs that read a closed door in the centre three strips, the gap from the first such
  read to the latch is **at most 9 steps in at least 7 of them** and **the longest gap is under 22**
  (`a93`, R53+R54: 7 of 10 within 9; gaps of 22 and 42 in the other two; one run never latched).
- No latch fires in the open tine or the stem (`eval/probes/confined_trigger.py --runs` on the
  round's records: `wrong 0`).
- A latch before crossing in **at most 2 of the won s02 runs** (R53+R54 `a93`: 1 of 36).
- Unbroken: the survey starts in at least 19 of 24 s02 runs by step 8; a route on at least 95% of
  steps; walls in flight (`eval/r28_flight.py`) within 4 points of R58's.

## Drop criterion

Three or more runs below R58 on the 30: dropped. Within 2 either way: a draw, not carried (the
next batch builds on the best parent so far). Three or more above: carried as the next batch's
parent and reference.

## Probe gate

Not needed: the change touches nothing the model perceives or is told (the latch is read from the
trail and the perceiver's existing closed-door reads). The offline gate above (fires in the shut
tine in at least 26 of 30 s03 `dynamic` runs, never later than `a93`, at most 8 of 167 won s02
runs with a latch before crossing) passed: 29, never later, 7.

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-a` on `:8004`, H100 frames: s03 `final`, s03 `dynamic`
(the cells the change targets), s02c `final` and s02vc `final` (the s02 cells where `a93`'s latch
fired in R53–R55). Scored by the manipulation check; wins not required.

## Host

Twelve lanes `~/asep-r56-l1..12`, four to an instance: **R56 (`a94`) lanes 1–4 on `:8004`**, R57
(`a95`) lanes 5–8 on a copy on GPU 3 (`:8006`), R58 (`a93`, the reference) lanes 9–12 on a copy on
GPU 4 (`:8007`); Godot on GPU 5 (`GODOT_VK=nvidia GODOT_RENDER_GPU=5`). `~/r56_fly.sh`. About
15 minutes. Recorded in `phase.json` "lanes".

## Builds on

R53/R54 (`a93`). Branch `phase2/r56-latch-line` from `phase2/r55-h100-a89` (`e61e0cd`); R57 and
R58 share the branch and the PR, as R53 and R54 did.

## Outcome

Not flown yet.
