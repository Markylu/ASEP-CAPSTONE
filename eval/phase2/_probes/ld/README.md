# Probe LD: lighting and depth perception

**Script:** `eval/probes/ld.py` · **Renderer:** `first-project/tools/ld_render.tscn` and
`tools/ld_rig.tscn` · **Prompts:** `w01` (g05's floor question alone) and `ld01` (metres per
strip, new, never flown) · **Status:** gate set 2026-10-31, before any call. No flying.

Comes from [what-we-learned.md](../../../../docs/research/what-we-learned.md): `a49`'s perceiver
misses about one real wall in six, and every prompt change that cut the misses (R27, R28's five
readers) added phantom walls. This probe leaves the prompt alone and changes the image.

## Belief

The lighting of the scene sets how well the model tells a wall under 1 m from open floor. The
sites light every wall the same way: one sun at 62° elevation travelling toward +x, a grey sky for
ambient, no ceiling, dark grid walls on a dark floor. At the s02 spawn the divider face the drone
looks at has normal +x, so the sun never lights it: the "dark plain surface" g05's prompt warns
about is the standard view of the one wall that decides s02. A shadow line at the wall's base, a
lit wall face, or a wall/ceiling edge whose height encodes distance should move the missed-wall
rate; if none does, the model is not reading depth from lighting cues and the lever is elsewhere.

Set F ([agree](../agree/README.md), 576 R27 flight frames): 316 truly blocked strips, `g05` missed
52 (16.5%) in 33 frames. The misses sit at 0.4–1.0 m; nose-on walls at 0.3 m (137 strips) are
almost never missed (3). The missed strips were read `bottom` 28, `lower` 14, `middle` 10.

## Method

Two image sets, rendered on sctsvr6 with lavapipe (`eval/godot-xvfb.sh`), the renderer eval
frames use; Mac renders are not pixel-identical.

- **A, rig** (`tools/ld_rig.tscn`): one wall in an empty room with the sites' materials. The
  camera is the agent's (768², 87° horizontal, level, at the spawn height) at
  d ∈ {0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0, 6.0} m, the wall
  turned 0°, 30° or 60° to the view, wall material dark (the sites') or light. 90 poses. Truth
  per strip is one ray down the strip's centre to the wall plane, capped at 15 m, as
  `r12_probe.true_reach`; classes as `c1f1.floor_class` (blocked under 1 m, near under 3 m).
- **B, real poses:** every set-F frame with at least one truly blocked strip (107) plus 43
  open-only controls drawn by site (seed `ld`), re-rendered in their own site at the recorded pose
  and door state (`common.world_key`). 150 poses. Truth is set F's own.
- **Seven lightings**, camera-relative so set B gets the same stimulus as set A:

  | id | sun | ambient | ceiling |
  |---|---|---|---|
  | L0 | the sites' (62°, energy 3.05, shadows) | sky, as the sites | no |
  | L1 | 20° elevation, behind the camera | as L0 | no |
  | L2 | 20°, from the side (+90°) | as L0 | no |
  | L3 | 62°, behind the camera | as L0 | no |
  | L4 | 85°, behind the camera | as L0 | no |
  | L5 | off | white, energy 1.0 | no |
  | L6 | off | white, energy 2.0 | at 3.3 m, wall material |

  1,680 images.
- **Reads:** `w01` (g05's floor ends, through `a49`'s floor map) and `ld01` (metres per strip),
  three repeats each, repeat-major so a repeat is never its own prefix-cache neighbour. One call
  at a time per instance, four shards: `:8004` with no flight running, `:8006`–`:8008` on GPUs
  3–5, stopped afterwards. About 10,000 calls.
- **Render 0** before anything: the rig with a light wall at 2, 3, 4 and 6 m under L0; the pixel
  row of the floor line gives the eye height. The scene files put the floor surface at y = 0.25
  and the camera at 1.75, so the eye should be 1.5 m up and the nearest visible floor 1.58 m
  away, not the 1.84 m `prompt.py`'s g05 note and `agent.py` assume. Zero model calls.
- **Fidelity:** set B under L0 against the recorded frames, share of channel values within 2/255.

## Gate (set before any call)

Scored per set and lighting on pooled reads (what the agent would see); majority-of-3 reported.
- *missed wall*: truth under 1 m, read not `no_floor`; *phantom wall*: truth open, read `no_floor`.
- `ld01`: median |log(est/true)|, share within ×1.5, signed bias, share reading ≥ 8 m where
  truth is capped; diagnostic only (g04's metre bands over-read far in flight).
- agreement across the 3 reads, per strip.

A lighting **matters** if, against L0,
1. set A's missed-wall rate moves by ≥ 10 pts, with phantom walls ≤ L0 + 2 pts when the move is
   an improvement; and
2. set B's moves by ≥ 5 pts the same way, with the same phantom rule.

Movement on A alone is **no call** (the rig does not carry to the sites). No lighting moving A by
10 pts is **refuted**: the model's wall reading does not depend on these lighting cues. Fidelity
must put ≥ 90% of B/L0 frames at ≥ 90% matching pixels, or set B's rows are not the frames the
model flew with and the run stops before any call.

Belief holds → the next round may fly `a49` under the winning lighting as its own round, with a
re-flown `a49` under L0 beside it, since the sites' lighting is part of the frozen config.
Belief refuted → the lever is the prompt or code (`w05`), not the scene.

## Run

_To be filled: date, branch and sha, checkout, render 0 result, fidelity, calls per set, shards,
median latency, failed calls._

## Result

_To be filled from `score.txt`._
