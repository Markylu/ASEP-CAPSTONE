#!/bin/sh
# Phase 1 on a display-less Linux host, in Docker. Run from anywhere on the host.
#
#   eval/docker/sweep.sh build                  # build the image (once, and after
#                                               # godot-xvfb.sh or requirements change)
#   eval/docker/sweep.sh smoke                  # fake decider, one 60-step flight,
#                                               # headless replay; no model time
#   eval/docker/sweep.sh decider [--fake]       # start the decider on :8100, detached
#   eval/docker/sweep.sh phase1 run --mini-phase 1Ba
#   eval/docker/sweep.sh phase1 status
#   eval/docker/sweep.sh logs | stop | shell
#
# Containers use the host network, so the decider reaches vLLM on
# 127.0.0.1:8004 directly, and run as the host user, so everything they write
# into the checkout is owned by you.
set -eu

REPO=$(cd "$(dirname "$0")/../.." && pwd)
IMAGE=${PHASE1_IMAGE:-asep-phase1:latest}
DECIDER=phase1-decider
STATE=${PHASE1_STATE:-$HOME/.cache/asep-phase1}
# Not 8000: vLLM's text models hold :8000-:8003 on sctsvr6.
DECIDER_PORT=${DECIDER_PORT:-8100}

run() {
    tty=""
    [ -t 0 ] && tty="-i"
    [ -t 1 ] && tty="$tty -t"
    gitconfig=""
    [ -f "$HOME/.gitconfig" ] && gitconfig="-v $HOME/.gitconfig:/tmp/home/.gitconfig:ro"
    # A home that outlives the container keeps Godot's shader cache, which
    # lavapipe is slow to rebuild. Outside the repo, so it never dirties it.
    mkdir -p "$STATE"
    # shellcheck disable=SC2086 # tty and gitconfig are intentionally word-split
    docker run --rm $tty --network host --user "$(id -u):$(id -g)" \
        -v "$REPO:/repo" -v "$STATE:/tmp/home" $gitconfig \
        -e USER="${USER:-operator}" -e LP_NUM_THREADS="${LP_NUM_THREADS:-16}" \
        "$@"
}

cmd=${1:-}
[ $# -gt 0 ] && shift
case "$cmd" in
    build)
        docker build -f "$REPO/eval/docker/Dockerfile" -t "$IMAGE" "$REPO"
        ;;
    smoke)
        run "$IMAGE" sh eval/docker/smoke.sh
        ;;
    decider)
        fake=""
        if [ "${1:-}" = "--fake" ]; then
            # The stand-in router: proves the plumbing, never cite its runs.
            fake="FAKE_PICK=straight uvicorn server.decider.fake_litellm:app --port 4101 >/dev/null 2>&1 &
                  export VLM_STREAM=0 VLM_RTT_PROBE=0 LITELLM_BASE_URL=http://127.0.0.1:4101 VLM_MODEL=stub;"
        fi
        run -d --name "$DECIDER" "$IMAGE" \
            sh -c "$fake exec python -m server.decider --profile remote --port $DECIDER_PORT"
        echo "decider starting on 127.0.0.1:$DECIDER_PORT (logs: $0 logs)"
        ;;
    logs)
        docker logs -f "$DECIDER"
        ;;
    stop)
        docker rm -f "$DECIDER"
        ;;
    phase1)
        if { [ "${1:-}" = "run" ] || [ "${1:-}" = "demo" ]; } && ! printf '%s\n' "$@" | grep -q -- "--decider-url"; then
            set -- "$@" --decider-url "http://127.0.0.1:$DECIDER_PORT"
        fi
        run "$IMAGE" python eval/phase1.py "$@"
        ;;
    shell)
        run "$IMAGE" bash
        ;;
    *)
        sed -n '2,13p' "$0"
        exit 1
        ;;
esac
