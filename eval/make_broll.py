#!/usr/bin/env python3
"""Throwaway: cut presentation b-roll from a recorded run.

Not part of the measurement harness. It re-flies a run's recorded index list —
the same SCRIPTED replay `replay_tui`'s "export flight" uses, so the trajectory
is the one the model actually flew — and films it from a cinematic camera
instead of the agent's head, then burns the model's own reasons over the top.

    python3 eval/make_broll.py run_2026-09-20_1502_s01_nocollisioncap \
        --shots reveal,chase,fpv,split --steps 14

Nothing here should be cited. `--speed` below 1.0 slows the agent AND the site
props, which is right for a video and wrong for a number.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runlib import commands, procs
from runlib.model import RUNS_DIR, Run, load_run

SCRATCH = Path(tempfile.gettempdir()) / "broll"
BROLL_SCENE = "res://tools/broll.tscn"
SHOTS = ("reveal", "chase", "orbit", "dolly", "fpv")
# `reveal` is the clean beauty shot; `fpv` already has the agent's own HUD
# naming the chosen action, so a caption there would say it twice.
UNCAPTIONED = ("reveal", "fpv")
# Movie Maker fixes capture to the project's default viewport whatever the
# window is resized to — measured, not assumed. Subtitles are laid out against
# it, so it has to be the real number.
CAPTURE = (1152, 648)

STEP_LINE = re.compile(r"^BROLL STEP (\d+) FRAME (\d+)")


# --------------------------------------------------------------------- argv

def cinematic_command(run: Run, indices: Sequence[int], cam: str, avi: Path,
                      speed: float, fps: int,
                      subs: Optional[Path] = None) -> List[str]:
    """The site goes under `broll.tscn`; every run flag is unchanged.

    `VLMNavRunSession` reads `OS.get_cmdline_user_args()` directly rather than
    its own position in the tree, so nesting the site one level deeper changes
    nothing about how the replay is driven.
    """
    return [
        commands.resolve("godot"), "--path", str(commands.GODOT_PROJECT),
        BROLL_SCENE, "--write-movie", str(avi), "--fixed-fps", str(int(fps)),
        "--",
        "--site=" + (run.scene or ""),
        "--cam=" + cam,
        "--frame-size={0}x{1}".format(*CAPTURE),
        "--scripted-indices=" + ",".join(str(i) for i in indices),
        "--max-steps={0}".format(len(indices)),
        "--max-collisions=-1",
        "--speed={0}".format(speed),
        "--stop-on-goal=false",
    ] + (["--static-doors=1"] if run.static_doors else []) \
      + (["--subs=" + str(subs)] if subs is not None else [])


# ---------------------------------------------------------------- captions

## Two sentences is what fits in the band and what a room can read in the
## second or so a step lasts. The full reason is in decisions.jsonl.
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def trim_reason(text: str, sentences: int = 2, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    if not text:
        return "(no reason recorded)"
    kept = " ".join(SENTENCE.split(text)[:sentences])
    if len(kept) > limit:
        kept = kept[:limit].rsplit(" ", 1)[0] + " …"
    return kept


def build_subs(run: Run, indices: Sequence[int], path: Path,
               caption: str) -> Path:
    """What broll.gd draws over the footage, keyed by 0-based decision step.

    The captions are drawn in-engine rather than burned on with ffmpeg: this
    machine's ffmpeg has no `ass`, `subtitles` or `drawtext` filter, and
    drawing in Godot is frame-exact anyway — the text changes on the tick the
    step starts, with no timing to reconcile afterwards.
    """
    steps = {}
    for decision in run.decisions:
        if decision.step >= len(indices):
            continue
        steps[str(decision.step)] = {
            "action": "action {0}".format(decision.index)
                      if decision.index is not None else "FAILED",
            "reason": trim_reason(decision.reason or decision.error or ""),
        }
    path.write_text(json.dumps({"header": caption, "steps": steps}, indent=1),
                    encoding="utf-8")
    return path


# ------------------------------------------------------------------ ffmpeg

def transcode(avi: Path, out: Path, crf: int = 19) -> List[str]:
    """Movie Maker writes MJPEG AVI at roughly 1.4 MB/s; this is not optional."""
    return [
        commands.resolve("ffmpeg"), "-y", "-i", str(avi),
        "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
        "-pix_fmt", "yuv420p", "-an", str(out),
    ]


def split_command(top: Path, bottom: Path, out: Path) -> List[str]:
    """Same trajectory, same fps, same length — frame-synced by construction.

    Stacked rather than side by side: two 16:9 panes in a row make a 32:9
    letterbox that is unreadable on a slide. `chase` goes on top so its header
    sits at the very top of the frame and its caption band lands on the seam,
    reading as a caption under the upper pane.

    1152x648 twice over is 1152x1296; scaling to 1080 tall gives 960x1080,
    which drops onto a 16:9 slide with room beside it.
    """
    return [
        commands.resolve("ffmpeg"), "-y", "-i", str(top), "-i", str(bottom),
        "-filter_complex",
        "[0:v][1:v]vstack=inputs=2[s];[s]scale=-2:1080[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-crf", "19", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-an", str(out),
    ]


def probe(path: Path) -> str:
    out = subprocess.run(commands.ffprobe_command(path), capture_output=True,
                         text=True)
    return " ".join(out.stdout.split())


# -------------------------------------------------------------------- driver

async def shoot(run: Run, indices: List[int], shot: str, speed: float,
                fps: int, subs: bool) -> Optional[Path]:
    """Render one shot. None when Godot or ffmpeg refused."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    commands.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    avi = SCRATCH / "{0}_{1}.avi".format(run.run_id, shot)
    out = commands.EXPORTS_DIR / "{0}_{1}.mp4".format(run.run_id, shot)

    caption = None
    if subs and run.decisions:
        caption = build_subs(run, indices,
                             SCRATCH / "{0}_subs.json".format(shot),
                             header(run, len(indices)))
    command = cinematic_command(run, indices, shot, avi, speed, fps,
                                subs=caption)

    log: List[str] = []
    print("$ " + commands.shell_preview(command))
    code = await procs.Runner().run(command, log.append)
    # `VLMNavRunSession._end` quits non-zero for an abnormal stop — a collision
    # budget, a wall-clock limit. The movie is already on disk by then, so the
    # file is the authority on whether the render worked, not the exit code.
    if not avi.is_file() or avi.stat().st_size < 1024:
        print("  godot exited {0} and wrote no movie".format(code))
        print("\n".join(log[-20:]))
        return None
    if code != 0:
        reason = next((l for l in reversed(log) if "RUN ENDED" in l), "")
        print("  godot exited {0} — {1}".format(code, reason.strip() or "no reason logged"))
    steps = sum(1 for line in log if STEP_LINE.match(line.strip()))
    if steps != len(indices):
        print("  warning: {0} of {1} steps reached the camera".format(
            steps, len(indices)))

    command = transcode(avi, out)
    print("$ " + commands.shell_preview(command))
    code = await procs.Runner().run(command, lambda _line: None)
    if code != 0:
        print("  ffmpeg exited {0}".format(code))
        return None
    print("  -> {0}   {1}".format(out, probe(out)))
    return out


def header(run: Run, shown: int) -> str:
    bits = [run.site_citation or run.site_id or "?", run.model]
    if run.n_steps:
        bits.append("{0} steps, {1} collisions".format(run.n_steps, run.collisions))
    if shown < run.n_steps:
        bits.append("first {0} shown".format(shown))
    return "  ·  ".join(bits)


async def main_async(args) -> int:
    run = load_run(RUNS_DIR / args.run_id)
    if not run.replayable:
        print("cannot re-fly this run: {0}".format(run.unreplayable_reason))
        return 1
    if not run.scene:
        print("run.json records no scene — nothing says which map to load")
        return 1

    indices = run.indices[:args.steps] if args.steps else run.indices
    print("{0}  {1}  {2} of {3} steps at speed {4}".format(
        run.run_id, run.site_id, len(indices), len(run.indices), args.speed))

    made = {}
    for shot in [s for s in args.shots if s != "split"]:
        path = await shoot(run, indices, shot, args.speed, args.fps,
                           subs=args.subs and shot not in UNCAPTIONED)
        if path is not None:
            made[shot] = path

    if "split" in args.shots:
        top = made.get("chase") or await shoot(
            run, indices, "chase", args.speed, args.fps, subs=args.subs)
        bottom = made.get("fpv") or await shoot(
            run, indices, "fpv", args.speed, args.fps, subs=False)
        if top and bottom:
            out = commands.EXPORTS_DIR / "{0}_split.mp4".format(run.run_id)
            command = split_command(top, bottom, out)
            print("$ " + commands.shell_preview(command))
            code = await procs.Runner().run(command, lambda _line: None)
            print("  -> {0}   {1}".format(out, probe(out)) if code == 0
                  else "  ffmpeg exited {0}".format(code))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--shots", default="reveal,chase,fpv,split",
                        help="reveal,chase,orbit,dolly,fpv,split")
    parser.add_argument("--speed", type=float, default=0.22,
                        help="below 1.0 slows the agent and the props together")
    parser.add_argument("--steps", type=int, default=0,
                        help="replay only the first N steps (0 = all)")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--no-subs", dest="subs", action="store_false",
                        help="skip the burned-in reasons")
    args = parser.parse_args()
    args.shots = [s.strip() for s in args.shots.split(",") if s.strip()]
    unknown = [s for s in args.shots if s not in SHOTS + ("split",)]
    if unknown:
        parser.error("unknown shot(s): " + ", ".join(unknown))
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
