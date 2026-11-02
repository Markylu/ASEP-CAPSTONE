# Probe LD: lighting and depth perception

**Script:** `eval/probes/ld.py` · **Renderer:** `first-project/tools/ld_render.tscn` and
`tools/ld_rig.tscn` · **Prompts:** `w01` (g05's floor question alone) and `ld01` (metres per
strip, new, never flown) · **Status:** gate set 2026-10-31, run 2026-11-01, **refuted**. No flying.

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

2026-11-01 on sctsvr6, checkout `~/asep-ld-probe` on `research/ld-probe`. Gate and code committed
first (`181705c`, `3b35ed9`); the renderer merged at `cd3b105`; two render-0 detector fixes
(`26ab35b`, `a9f8b7c`) before any model call.

- **Renders:** in the `asep-phase1` container (Godot 4.7.2, Xvfb, lavapipe; the host has no Godot).
  1,680 rows, 0 failed, about 0.4 s a rig frame and 1–2 s a site frame. The `godot` wrapper must
  not be the container's PID 1: `xvfb-run` waits for Xvfb's SIGUSR1, which PID 1 never receives,
  and hangs with no output. Flights never met this because `phase2.py` is PID 1 there. The probe
  runs it under `sh -c`.
- **Render 0:** the floor line against a light wall at 2, 3, 4 and 6 m sits 304, 199, 152 and
  98 px below the image centre: **eye height 1.48 m** (spread 0.05 m), nearest visible floor
  **1.56 m**. The 1.84 m in `prompt.py`'s g05 note and `agent.py:330` assumes 1.75 m and is off
  by 0.28 m; not changed here. At 6 m the rig wall's shadow (12 m tall, sun at 62°) ends short of
  the camera and the nearest floor is sunlit, which the first detector mistook for wall.
- **Fidelity** (`fidelity.txt`): set B under L0 against the recorded frames, 150 frames, median
  100.0% of channel values within 2/255, 141 of 150 at or above 90% (gate: 135). Nine frames
  fall under, the lowest 74.0% (`R27/s02c/final/11`), all `final` or `dynamic` s02 frames where a
  door leaf's position differs; the walls and floor match.
- **Smoke:** five `w01` calls on `:8004` against the 0.3 m rig frames, all at the `json_schema`
  rung, 1.0–5.8 s, every strip `no_floor`. Removed before the run.
- **Calls:** four shards, one call at a time each: `:8004` (no flight running) and three copies
  on GPUs 3–5 (`:8006`–`:8008`, same image, weights and flags), each in its own container,
  repeat-major. 10,080 calls (2,520 a shard) in 2 h 45 min, median 1,982 ms, p90 8.9 s. 204
  failed (2.0%), all `every rung failed` on a `JSONDecodeError` at the `json_schema` rung, the
  reason running past the token limit (W01 had 2.6%). Rungs: `json_schema` 8,961, `json_object`
  543, `text` 372. Failed calls are counted in `fail` and left out of the rates. The copies and
  shard containers were removed afterwards; `renders.jsonl` is the renderer's index of the 1,684
  frames (the PNGs stay on sctsvr6, gitignored).
- **Recall of the failed calls** (`recall.jsonl`, after the run, on `fix/reason-maxlength`): the
  68 failed image/reads re-called on `:8004` with `maxLength` 2,000 on the schema's `reason`.
  68 of 68 parse, all at the `json_schema` rung, median 2.9 s; 54 reasons sit at the cap, 14
  stopped short (426–2,000 characters) on their own. The capped text is a loop: one sentence
  ("The floor ends at the bottom of the image in the lower right, but not in the upper left.")
  repeated to the limit. The cap rescues the parse, not the reading: on these 40 `w01` frames
  the reads miss 17 of 28 blocked strips and call 30 of 172 open strips walls (the run's L0:
  15.9% and 13.8%). The frames that loop are the frames the model cannot read.

## Result

`score.txt`. Set A is the rig, set B the real poses; rates are over strips, reads pooled.

**Refuted.** No lighting moves the rig's missed walls by 10 pts, and on the real poses every
other lighting reads *more* walls as open floor than the sites' own:

| | A missed | A phantom | B missed | B phantom |
|---|---|---|---|---|
| L0 sites' | 17.6% | 32.6% | 15.9% | 13.8% |
| L1 20° behind | −2.3 | −4.3 | **+8.1** | −4.2 |
| L2 20° side | −2.8 | +4.9 | **+14.1** | −5.5 |
| L3 62° behind | +6.4 | −7.8 | **+9.5** | −0.5 |
| L4 85° behind | +2.8 | −5.3 | **+6.4** | −3.1 |
| L5 ambient only | +6.6 | −13.4 | **+13.8** | −2.6 |
| L6 ceiling, ambient | +9.7 | −1.5 | **+19.3** | −1.5 |

- **The replay reproduces flight.** B under L0 misses 15.9% of walls under 1 m; `g05` missed
  16.5% of the same frames' strips in R27's flights, `w01` 16.5% on set F. The pose, door state
  and lighting carry over, so set B's rows are the frames the agent flew with.
- **The sites' lighting is the best of the seven for walls.** A low sun from behind (L1, L2)
  takes 2–3 pts off the rig's misses, far short of 10, and adds 8–14 pts on the real poses. Every
  lighting that lifts the floor (ambient only, the lit ceiling) makes the model say *floor* more
  often: phantoms fall, misses rise, the same trade R27 and R28 found from the prompt side. The
  model is not reading the near wall from shadow lines or lit faces.
- **The rig over-reads walls.** On the rig the model calls 71% of strips at 1–1.5 m and 42% at
  1.5–2 m `no_floor` (phantom 32.6% against 13.8% on the real poses): a 12 m plain wall filling
  the frame carries no scale cue. Under 1 m it still misses 17.6% (0.5–1 m bin: 261 of 342 read
  `no_floor`), so the misses are not a clutter effect of the sites either.
- **Metres are not usable.** `ld01`'s median |log(est/true)| is 0.92 on the real poses (a factor
  2.5) and 1.14 on the rig (3.1); 15–24% of strips land within ×1.5; the bias is positive (reads
  far). Lightings L1, L2 and L6 raise the share reading ≥ 8 m from 3.7% to 20–44% on B, the
  numeric face of the same shift toward *open*.
- **Three repeats, one answer.** 3,359 of 3,360 image/read pairs returned byte-identical results
  across the three repeats, failures included (an image that failed, failed thrice). At
  temperature 0, one call at a time and a warm prefix cache (repeat-major order, so every call
  after the first found the system prompt cached), the model is deterministic on this server.
  This fits the noise row of `probe-plan.md`, which put the 18.6% repeat disagreement at
  concurrency 1 on cold against cached prefixes, and N1's batching lottery: the disagreement is
  the server's state, not sampling. The extra repeats bought nothing here.
- **Two thirds of the flight misses do not come back.** On the 33 frames where `g05` missed a wall
  in flight, the L0 replay misses 32.5% of the blocked strips (36.7–59.2% under the other
  lightings). The same frame, read alone, finds most of those walls: the misses in flight were
  largely the lottery, not the image.

**Where this leaves the belief.** The scene is not the lever: re-lighting the sites would cost
walls, not win them. The 0.5–1 m misses survive every light, so they sit in the wording or the
code (`w05`), and two thirds of the flight-time misses are the server's state (batching, cold
prefixes), which no prompt or scene change touches. Separately, render 0 puts the eye at 1.48 m and the nearest visible floor at
1.56 m; the g05 note and `agent.py:330` say 1.84 m. Not changed here.
