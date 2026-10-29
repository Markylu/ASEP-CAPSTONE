#!/bin/sh
# Import the Godot project once per checkout: first-project/.godot/ is
# git-ignored, and a flight without it fails on missing textures.
set -eu
if [ ! -d /repo/first-project/.godot/imported ]; then
    echo "entrypoint: importing the Godot project (first run in this checkout)" >&2
    godot --headless --path /repo/first-project --import >/dev/null 2>&1 || true
    if [ ! -d /repo/first-project/.godot/imported ]; then
        echo "entrypoint: import failed; run: godot --headless --path first-project --import" >&2
        exit 1
    fi
fi
exec "$@"
