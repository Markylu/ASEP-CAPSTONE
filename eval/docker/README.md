# Phase 1 on a headless Linux host (Docker)

Runs `eval/phase1.py` on a machine with no display, such as sctsvr6, so a sweep
does not take over the operator's laptop. Godot renders under Xvfb through
Mesa lavapipe (CPU Vulkan) by default: no GPU is touched, so vLLM's cards are
left alone. `GODOT_VK=nvidia` renders on an idle H100 instead (below).

The image holds tools only (Godot 4.7.2 official, Xvfb, Mesa, the decider's
Python deps). The checkout is bind-mounted at `/repo`, so run data, the git SHA
and the clean-tree check are the host checkout's, and files are owned by you.
Containers use the host network: the decider reaches vLLM on `127.0.0.1:8004`
with no SSH tunnel.

## Use

```bash
eval/docker/sweep.sh build        # once; again after godot-xvfb.sh or requirements change
eval/docker/sweep.sh smoke        # fake decider, one 60-step flight, headless replay
eval/docker/sweep.sh decider      # real decider on :8100, detached (--fake for the stub)
eval/docker/sweep.sh phase1 run --mini-phase 1Ba
eval/docker/sweep.sh phase1 demo --mini-phase 1A   # fly 1A's order into eval/runs/demo_*; records nothing
eval/docker/sweep.sh stop
```

Run long sweeps inside `tmux` so they survive an SSH disconnect.

`smoke` passes when it prints a `Vulkan ... Forward+ ... llvmpipe` renderer
line, `RUN ENDED: max_steps after 60 steps`, 60 frames and `REPLAY OK`. If the
renderer line says OpenGL or Compatibility, Vulkan failed and Godot fell back
to a different renderer: stop, the frames would not be comparable. After the
first run, `git status` must still be clean (the project import writes only the
git-ignored `first-project/.godot/`).

## Knobs

| Env | Default | |
|---|---|---|
| `DECIDER_PORT` | `8100` | not 8000: vLLM's text models hold :8000-:8003 on sctsvr6 |
| `LP_NUM_THREADS` | `16` | lavapipe threads; the host is shared |
| `PHASE1_STATE` | `~/.cache/asep-phase1` | container home: Godot's shader cache survives runs |
| `PHASE1_IMAGE` | `asep-phase1:latest` | |
| `LITELLM_BASE_URL` | unset: `:8004` | the vLLM instance a lane's decider calls |
| `GODOT_VK` | `lvp` | `nvidia` renders on an H100; needs `GODOT_RENDER_GPU` |
| `GODOT_RENDER_GPU` | none | nvidia-smi index of a card no vLLM holds; refused if one does |
| `XVFB_SERVERNUM` | unset: `xvfb-run -a` | pin per lane; honoured by `eval/godot-xvfb.sh`, which flights pass with `--godot` |

## Many lanes: instances and a render GPU

Under lavapipe a lane takes about 12 cores, so the CPU carries 8 to 10 lanes and
one vLLM instance saturates at about 8. To fly more, spread the lanes over
copies of `:8004` and render on a spare H100. Measured 2026-11-06 with 24 lanes
of `a89` on three instances and one render card: CPU 25% of 128 cores, about
166 steps a minute in all (the four-lane night before: about 37), model time
per step 5.9 s median (4.2 s) because 8 lanes share an instance, not 4.

```bash
# a copy of :8004 on GPU 3 (same image, weights and flags); stop it when the flights are done
eval/docker/vllm_copy.sh 8006 3
# one lane of a round on that instance, Godot on GPU 5
LITELLM_BASE_URL=http://127.0.0.1:8006 GODOT_VK=nvidia GODOT_RENDER_GPU=5 \
    sh ~/round_lane.sh 5 4 ~/asep-r53-l5 a89 85cda76df25b R53 R53_folder
```

**The rule for rounds (operator, 2026-11-06).** Screening rounds fly on three instances, four
lanes each, Godot on a spare H100, and **one instance always flies the reference agent** (the
bar's, `a89` at the time of writing) beside the candidates on the same renderer; a candidate is
read against that reference flight. H100 frames cost about 5 runs in 30 against lavapipe
(R54: `a93` 24 → 19; R55: `a89` 23 → 18, both on s02) although `g05` reads matched frames the
same (`eval/phase2/R55_h100_a89/summary.md`); the cause is unresolved, so the reference flies
every time. A round that must be read against the lavapipe bar's own numbers flies on
lavapipe, two instances, four lanes each (R53, 21 minutes).

`round_lane.sh` here is the lane script (the host's `~/round_lane.sh` is a copy);
it prints the lane's layout before flying and every flight's renderer line after.
Limits and cautions:

- At most 4 Qwen3-VL instances on sctsvr6, counting `:8004`; stop the copies
  when the flights are done.
- 8 lanes on an instance doubles the batch neighbours of the rounds flown with
  4. Four lanes on each of three instances keeps that load and flies three
  rounds at once.
- The image's own `godot` wrapper predates `XVFB_SERVERNUM`: lanes that do not
  pass `--godot /repo/eval/godot-xvfb.sh` collide on X displays beyond ten.
- Xvfb failed to start in 2 of 48 flights flown back to back in one container
  in the trial. A lane starts a container per cell; watch the lane log for
  `Xvfb failed to start` all the same.

## Citing runs flown here

Frames rendered on an H100 are not lavapipe's pixels either: same poses and
scene, thin edges differ (under 0.7% of pixels by more than 8 of 255). On 210
matched frame pairs from four R52 runs, `g05`'s fields agreed between the two
renderers on 76 to 80%, and between two reads of the same frame on 81 to 82%
(doorway fields about 91% either way; 2026-11-06, one probe, not repeated). By
the rule below a renderer change is still a config change: say which renderer a
round flew on in its `phase.json` "lanes", and compare rounds flown on the same.

Frames rendered by lavapipe are not the pixels Metal renders on the Mac, and
decision latency without the tunnel is lower. Both are inputs to the results,
so a host change is a config change (docs/phase1-test-plan.md §3, §7.1): fly
every citable mini-phase on one host, re-fly any already flown elsewhere, and
record the change in the §15 changelog.
