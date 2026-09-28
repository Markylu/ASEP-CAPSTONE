# Phase 1 on a headless Linux host (Docker)

Runs `eval/phase1.py` on a machine with no display, such as sctsvr6, so a sweep
does not take over the operator's laptop. Godot renders under Xvfb through
Mesa lavapipe (CPU Vulkan): no GPU is touched, so vLLM's cards are left alone.

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

## Citing runs flown here

Frames rendered by lavapipe are not the pixels Metal renders on the Mac, and
decision latency without the tunnel is lower. Both are inputs to the results,
so a host change is a config change (docs/phase1-test-plan.md §3, §7.1): fly
every citable mini-phase on one host, re-fly any already flown elsewhere, and
record the change in the §15 changelog.
