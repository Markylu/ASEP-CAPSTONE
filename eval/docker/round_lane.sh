#!/bin/sh
# Phase 2 lane N of K for one round: own checkout DIR, decider rnd-lN on :810N, Godot cache and
# X display :10N. Cells are order.txt lines N', N'+K, ... where N' = (N-1) % K + 1, so a second
# round flying at the same time takes lanes K+1..2K.
# Run inside tmux: sh ~/round_lane.sh N K DIR AGENT SHA ROUND FOLDER
# (the host's ~/round_lane.sh is a copy of this file)
#
# Host layout, from the environment (eval/docker/sweep.sh reads the same variables):
#   LITELLM_BASE_URL=http://127.0.0.1:8006   this lane's vLLM instance; unset, :8004
#   GODOT_VK=nvidia GODOT_RENDER_GPU=5       render on that H100; unset, lavapipe
# Record the layout in the round's phase.json "lanes" (eval/phase2_merge.py --lanes).
set -u
N=$1; K=$2; D=$3; AGENT=$4; SHA=$5; ROUND=$6; FOLDER=$7
cd "$D"
export PHASE1_DECIDER=$(echo "$ROUND" | tr 'A-Z' 'a-z')-l$N DECIDER_PORT=$((8100 + N)) PHASE1_STATE=$HOME/.cache/asep-phase1-l$N XVFB_SERVERNUM=$((100 + N))
echo "=== lane $N $ROUND $AGENT preflight $(date -u) sha $(git rev-parse --short HEAD) dirty $(git status --short | wc -l)"
echo "=== lane $N layout: vllm ${LITELLM_BASE_URL:-http://127.0.0.1:8004 (default)} render ${GODOT_VK:-lvp}${GODOT_RENDER_GPU:+ gpu $GODOT_RENDER_GPU}"
[ -z "$(git status --short)" ] || { echo "dirty tree, not flying"; exit 1; }
eval/docker/sweep.sh stop 2>/dev/null
eval/docker/sweep.sh decider --agent "$AGENT"
for i in $(seq 1 60); do curl -s -m 2 127.0.0.1:$DECIDER_PORT/health | grep -q "$SHA" && break; sleep 2; done
curl -s -m 2 127.0.0.1:$DECIDER_PORT/health | grep -q "$SHA" || { echo "decider did not report $AGENT $SHA"; exit 1; }
echo "=== lane $N start $(date -u)"; curl -s 127.0.0.1:$DECIDER_PORT/health; echo
M=$(( (N - 1) % K + 1 ))
for cell in $(awk -v m="$M" -v k="$K" 'NR % k == m % k' eval/phase2/$FOLDER/order.txt); do
    echo "=== $cell start $(date -u)"
    eval/docker/sweep.sh phase2 run --round "$ROUND" --only "$cell" --headless-replay --godot /repo/eval/godot-xvfb.sh
    echo "=== $cell end $(date -u)"
done
eval/docker/sweep.sh stop
# Every flight's renderer, counted: one line, and the device the layout line names.
echo "=== lane $N renderers:"
grep -h "Using Device" eval/phase2/$FOLDER/runs/*/*/*/godot.log 2>/dev/null | sed 's/^.*Using Device/Using Device/' | sort | uniq -c
echo LANEDONE
