#!/bin/sh
# Inside the container: prove a flight renders and replays on this host.
# Fake router and decider on their own ports, one 60-step s02a flight under
# Xvfb, a headless replay. Output lands in eval/runs/_smoke_docker/ (outside
# the clean-tree check). Never cite it.
set -eu
S=eval/runs/_smoke_docker
rm -rf "$S"
mkdir -p "$S"

FAKE_PICK=straight uvicorn server.decider.fake_litellm:app --port 4101 >"$S/fake.log" 2>&1 &
VLM_STREAM=0 VLM_RTT_PROBE=0 LITELLM_BASE_URL=http://127.0.0.1:4101 VLM_MODEL=stub \
    RUNS_DIR="/repo/$S" python -m server.decider --profile remote --port 8110 >"$S/decider.log" 2>&1 &
python - <<'EOF'
import time, urllib.request
for _ in range(60):
    try:
        urllib.request.urlopen("http://127.0.0.1:8110/health", timeout=1)
        break
    except Exception:
        time.sleep(0.5)
else:
    raise SystemExit("smoke: decider did not come up; see eval/runs/_smoke_docker/decider.log")
EOF

start=$(date +%s)
godot --path first-project res://sites/s02a_doors_open_a/site.tscn -- \
    --run-id=smoke --decider-url=http://127.0.0.1:8110 --max-steps=60 --max-collisions=-1 \
    --frame-size=768x768 --world=dynamic --spawn-seed=3 >"$S/godot.log" 2>&1 || true
echo "flight: $(( $(date +%s) - start ))s"
grep -E "Vulkan|OpenGL|RUN ENDED" "$S/godot.log" || echo "smoke: no renderer/RUN ENDED line; see $S/godot.log"
echo "frames: $(ls "$S/smoke/frames" 2>/dev/null | wc -l) (want 60)"
python eval/replay.py "$S/smoke" --decider-url http://127.0.0.1:8110 --headless | tail -1
echo "Renderer must read Vulkan ... Forward+ ... llvmpipe. OpenGL/Compatibility means Vulkan failed: stop."
