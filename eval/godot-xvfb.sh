#!/bin/sh
# Godot on a display-less Linux host (sctsvr6), for `eval/phase1.py --godot`.
#
#   GODOT_VK=lvp     CPU rendering through Mesa lavapipe (default; never touches
#                    the GPUs vLLM is using)
#   GODOT_VK=nvidia  an H100 through the NVIDIA ICD. GODOT_GPU is Godot's Vulkan
#                    device index, which need not match nvidia-smi's: confirm
#                    the device in the startup line is an idle card (0-2 hold
#                    vLLM on sctsvr6)
#
# Flights run under a virtual X server, because Godot needs a window to render
# a frame. `--headless` (replays) skips Xvfb: a replay captures no frames.
#
# Check the renderer line Godot prints at startup, e.g.
#   Vulkan 1.3.x - Forward+ - Using Device #0: ... llvmpipe ...
# If it says OpenGL / Compatibility, Vulkan failed and Godot fell back to a
# different renderer: the frames are not comparable, stop.
set -eu

GODOT_BIN=${GODOT_BIN:-$HOME/opt/godot/Godot_v4.7.2-stable_linux.x86_64}

icd() {
    for dir in /usr/share/vulkan/icd.d /etc/vulkan/icd.d; do
        if [ -f "$dir/$1" ]; then echo "$dir/$1"; return; fi
    done
    echo "godot-xvfb: no $1 in the Vulkan ICD dirs" >&2
    exit 1
}

gpu_args=""
case "${GODOT_VK:-lvp}" in
    # lavapipe takes every core it sees; sctsvr6 is shared, so cap it.
    lvp) driver=$(icd lvp_icd.json); export LP_NUM_THREADS="${LP_NUM_THREADS:-16}" ;;
    nvidia) driver=$(icd nvidia_icd.json); gpu_args="--gpu-index ${GODOT_GPU:-3}" ;;
    *) echo "godot-xvfb: GODOT_VK must be lvp or nvidia" >&2; exit 1 ;;
esac
# Newer loaders read VK_DRIVER_FILES, older ones VK_ICD_FILENAMES.
export VK_DRIVER_FILES="$driver" VK_ICD_FILENAMES="$driver"

resolution=""
for arg in "$@"; do
    case "$arg" in
        --headless) exec "$GODOT_BIN" "$@" ;;
        --frame-size=*) resolution="--resolution ${arg#--frame-size=}" ;;
    esac
done
# Create the window at the frame size. Under Xvfb there is no window manager,
# and run_session.gd's runtime window_set_size() leaves the project's 16:9
# shape: frames came out 768x432 instead of 768x768.

# XVFB_SERVERNUM pins the display: containers on the host network share X's
# abstract sockets, so parallel flights (one per lane) each need their own;
# `-a` alone picks :99 in every container.
server="-a"
[ -n "${XVFB_SERVERNUM:-}" ] && server="-n $XVFB_SERVERNUM"

# shellcheck disable=SC2086 # gpu_args, resolution and server are intentionally word-split
exec xvfb-run $server -s "-screen 0 1280x1024x24" \
    "$GODOT_BIN" --audio-driver Dummy --rendering-driver vulkan $gpu_args $resolution "$@"
