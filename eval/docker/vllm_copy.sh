#!/bin/sh
# A copy of sctsvr6's :8004 Qwen3-VL instance on one GPU: same image, weights and flags
# (docker inspect qwen3-vl-2gpu), weights from the local cache. About three minutes to serve.
#
#   eval/docker/vllm_copy.sh PORT GPU      e.g. 8006 3; then LITELLM_BASE_URL=http://127.0.0.1:8006
#   docker rm -f qwen3-vl-c<PORT>          stop it
#
# Limit: 4 Qwen3-VL instances on the host, counting :8004. Check `nvidia-smi` for a free card
# first, and stop every copy when the batch is done. :8005 is someone else's.
set -eu
PORT=$1; GPU=$2
if nvidia-smi -i "$GPU" --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -q .; then
    echo "vllm_copy.sh: GPU $GPU is in use" >&2
    exit 1
fi
docker run -d --name "qwen3-vl-c$PORT" --gpus "\"device=$GPU\"" --ipc=host --shm-size=16g \
    -p "127.0.0.1:$PORT:8000" \
    -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
    -e HF_HUB_OFFLINE=1 -e VLLM_ENGINE_READY_TIMEOUT_S=3600 \
    vllm/vllm-openai:v0.23.0 \
    Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 --host 0.0.0.0 --port 8000 --api-key sk-local \
    --trust-remote-code --tensor-parallel-size 1 --max-model-len 32768 \
    --gpu-memory-utilization 0.90 --limit-mm-per-prompt '{"image": 16}' \
    --served-model-name Qwen3-VL-30B-A3B
echo "qwen3-vl-c$PORT starting on GPU $GPU; ready when: curl -s -H 'Authorization: Bearer sk-local' 127.0.0.1:$PORT/v1/models"
