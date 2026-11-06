# R54: a93 again with Godot rendered on an H100 (host round), contested cells

**Agent:** `a93` (`8cc0bfc63d4e`), R53's, unchanged · **Prompt:** `p17` (`cb3578251cfe`) ·
**Perceiver:** `g05` · **Door confirmer:** `d01` · **Memory:** `a17f` ·
**Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`), not lavapipe ·
**Status:** laid out 2026-11-06 by Claude on the operator's instruction ("do one more cycle of
the loop"); every decision here is Claude's, with its reason; not flown

Written before flying. Spec: `docs/phase2-test-plan.md` (host rounds, changelog 2026-11-02: a
round may change the host and not the agent, with the same agent sha in every run). Design: the
ten contested cells, seeds 1–3, 30 runs, flown at the same time as R53 and read against it.

## Change

**No agent change. Godot renders on an H100 instead of under lavapipe**
(`eval/docker/sweep.sh`, `GODOT_VK=nvidia GODOT_RENDER_GPU=5`, commit `738a6c3`). The agent,
its sha, the prompt, the sites, the seeds and the model are R53's.

## Why

On 2026-11-06 the operator allowed flights to be spread over the GPUs and asked for a trial of
three model instances and a render card. Under lavapipe a lane takes about 12 cores and the
host carries 8 to 10 lanes; rendered on an H100, 24 lanes ran at 25% CPU and 4.5 times the
steps a minute of a four-lane night (`eval/docker/README.md`). `eval/docker/README.md` also
says a renderer change is a config change, and no round has flown on H100 frames. This one
does, beside the same agent on lavapipe.

## Evidence

- **Same poses, nearly the same pixels:** a fake-decider flight takes the same path to 0.000 m
  under either renderer; under 0.7% of pixels differ by more than 8 of 255, on thin edges (tile lines, door
  frames).
- **`g05` on 210 matched frame pairs** (four R52 runs replayed under both, each frame read
  twice, alone): fields agree between the renderers on 76 to 80%, and between two reads of
  the same frame on 81 to 82%; doorway fields about 91% either way; floor fields 55 to 63%
  across against 64 to 68% within. One probe, not repeated, scratch data on the host.
- **One cell end to end** (`a92`, s02vc `dynamic` seed 2, throwaway checkout): valid, replay ok.

## Hypothesis

A round flown on H100 frames reads like the same round on lavapipe: R54 is within 4 of R53
(the spread two flights of one agent showed on 2026-11-06), with s02 within 3, and the
flight-time readings below are within their limits.

## Predictions

| | R53 (lavapipe) | Predicted R54 (H100) |
|---|---|---|
| total | 22–27 predicted | within 4 of R53 |
| s02 | 19–22 predicted | within 3 of R53 |
| s03 | 3–5 predicted | 1–5 (six runs: not read alone) |

## Manipulation check

- Every run's `godot.log` names `NVIDIA H100 PCIe` (the lane log counts them); R53's, llvmpipe.
- Every `run.json` carries `a93`, `8cc0bfc63d4e` and `litellm_base_url` `:8007`.
- Walls in flight (`eval/r28_flight.py`): missed and phantom within 4 points of R53's.
- Goal reports with no line of sight per run, and the share the check drops, within a third
  of R53's (`eval/probes/a93_goal_check.py --folders R54_h100_frames`).
- The survey starts in at least 19 of the 24 s02 runs by step 8; a route on at least 95% of
  steps.

## What it decides

- **Within the limits:** later rounds may fly on H100 frames (12 lanes at four to an instance,
  three rounds at once), each saying so in `phase.json` "lanes". One flight does not prove the
  renderers equal; it says no gap larger than a flight's own noise showed.
- **Outside them:** H100 rounds are read only against H100 rounds, and the bar would need one
  flight there before anything is compared with it. That flight is the operator's to ask for
  (no control rounds by default).
- Either way R54 is a second flight of `a93`: R53 and R54 together are 60 runs of it.

## Host

Four lanes, `~/asep-r54-l9..12`, on a copy on GPU 4 (`:8007`), alone on its instance; Godot on
GPU 5 (9 GB of it in the trial, 24 lanes). Lane numbers 9–12 so that ports and X displays do
not meet R53's 1–8. R53's eight lavapipe lanes take most of the CPU beside it.

## Builds on

R53 (`a93`). Branch `phase2/r53-goal-check`; R54 is committed on the same branch, as R29N and
R29S shared one.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
