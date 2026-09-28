# Phase 1 runner for a display-less Linux host (sctsvr6).
#
# Tools only: Godot 4.7.2 (official build), Xvfb, Mesa lavapipe, the decider's
# Python deps. The repo is bind-mounted at /repo at run time, so run data, the
# git SHA and the clean-tree check are the host checkout's. See README.md here.
FROM --platform=linux/amd64 ubuntu:24.04

ARG GODOT_VERSION=4.7.2
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates wget unzip git \
        python3 python3-venv \
        xvfb xauth \
        mesa-vulkan-drivers libvulkan1 libgl1 libegl1 \
        libx11-6 libxcursor1 libxinerama1 libxrandr2 libxi6 libxext6 libxrender1 \
        libxkbcommon0 libfontconfig1 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/godot && cd /opt/godot \
    && wget -q "https://github.com/godotengine/godot-builds/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip" \
    && unzip -q Godot_*.zip && rm Godot_*.zip \
    && ln -s "/opt/godot/Godot_v${GODOT_VERSION}-stable_linux.x86_64" /opt/godot/godot-bin \
    && /opt/godot/godot-bin --headless --version

COPY server/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# `godot` on PATH is the Xvfb wrapper, so eval/phase1.py and eval/replay.py
# pick it up with no --godot flag. Replays pass --headless and skip Xvfb.
COPY eval/godot-xvfb.sh /usr/local/bin/godot
COPY eval/docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod 755 /usr/local/bin/godot /usr/local/bin/entrypoint \
    && mkdir -m 1777 /tmp/home /tmp/.X11-unix

# Runs as the host user (see sweep.sh), who has no passwd entry here. Xvfb run
# by a non-root user cannot create /tmp/.X11-unix itself, hence it exists above.
ENV PATH=/opt/venv/bin:$PATH \
    GODOT_BIN=/opt/godot/godot-bin \
    GODOT_VK=lvp \
    HOME=/tmp/home \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /repo
ENTRYPOINT ["entrypoint"]
CMD ["bash"]
