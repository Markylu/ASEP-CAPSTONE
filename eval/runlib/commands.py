"""Build the argv for every external command, and execute none of them.

Keeping this pure is what lets the TUI be exercised without launching Godot,
and lets a future batch script fly the exact same command the UI shows in its
log pane — the command in the log is the command that ran, not a paraphrase.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .model import REPO_ROOT, Run

GODOT_PROJECT = REPO_ROOT / "first-project"
EXPORTS_DIR = REPO_ROOT / "eval" / "exports"
REPLAY_CLI = REPO_ROOT / "eval" / "replay.py"
DEFAULT_DECIDER_URL = "http://127.0.0.1:8000"

# Movie Maker fixes the recording to the project's default viewport before the
# run's own startup code executes, so --frame-size is silently ignored here.
MOVIE_VIEWPORT = (1152, 648)


class ToolMissing(RuntimeError):
    pass


def resolve(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        raise ToolMissing(
            "{0} not found on PATH. Install it, or put it on PATH, before "
            "using this action.".format(tool))
    return found


def site_scene(site_id: str) -> str:
    """res:// path of a site's scene. Sites are addressed by ID everywhere else."""
    return "res://sites/{0}/site.tscn".format(site_id)


def scene_args(run: Run) -> List[str]:
    """The map a run was flown on, as a positional argument before `--`.

    Godot takes the scene this way already (`godot --path <dir> <res://scene>`),
    so nothing about the existing --kebab=value flags changes, and the project's
    main_scene stays pointed at main.tscn for a bare launch and for F5.
    """
    return [run.scene] if run.scene else []


def run_command(site_id: str, run_id: str,
                decider_url: str = DEFAULT_DECIDER_URL,
                max_steps: int = 30,
                frame_size: Sequence[int] = (768, 768)) -> List[str]:
    """Fly a NEW model run on a named site — the launch people type by hand."""
    width, height = frame_size
    return [
        resolve("godot"), "--path", str(GODOT_PROJECT), site_scene(site_id), "--",
        "--run-id=" + run_id,
        "--decider-url=" + decider_url,
        "--max-steps={0}".format(int(max_steps)),
        "--frame-size={0}x{1}".format(int(width), int(height)),
    ]


def world_args(run: Run) -> List[str]:
    """The layout and start pose the live run flew; a replay must match both."""
    meta = {**run.metrics, **run.meta}
    out = []
    if meta.get("world"):
        out.append("--world=" + str(meta["world"]))
    elif run.static_doors:
        out.append("--static-doors=1")
    if meta.get("spawn_seed") is not None:
        out.append("--spawn-seed={0}".format(int(meta["spawn_seed"])))
    return out


def indices_arg(run: Run) -> str:
    if not run.replayable:
        raise ValueError(run.unreplayable_reason)
    return ",".join(str(i) for i in run.indices)


def watch_command(run: Run, speed: float = 1.0,
                  frame_size: Optional[Sequence[int]] = None) -> List[str]:
    """A scripted run calls no model, so watching needs no decider running."""
    width, height = frame_size or (1280, 720)
    return [
        resolve("godot"), "--path", str(GODOT_PROJECT)] + scene_args(run) + [
        "--",
        "--scripted-indices=" + indices_arg(run),
        "--max-steps={0}".format(len(run.indices)),
        # The index list already stops where the live run stopped; a collision
        # budget here would cut a replay of an uncapped run short.
        "--max-collisions=-1",
        "--speed={0}".format(speed),
        "--frame-size={0}x{1}".format(int(width), int(height)),
        "--stop-on-goal=false",
    ] + world_args(run)


def verify_command(run: Run, speed: float = 1.0,
                   decider_url: str = DEFAULT_DECIDER_URL) -> List[str]:
    """Shell out to the existing CLI so there is one drift implementation."""
    if not run.replayable:
        raise ValueError(run.unreplayable_reason)
    command = [sys.executable, str(REPLAY_CLI), str(run.path),
               "--decider-url=" + decider_url]
    if speed != 1.0:
        command.append("--speed={0}".format(speed))
    return command


def record_command(run: Run, avi_path: Path, speed: float = 0.3,
                   fps: int = 30) -> List[str]:
    """--frame-size is deliberately absent; see MOVIE_VIEWPORT."""
    return [
        resolve("godot"), "--path", str(GODOT_PROJECT)] + scene_args(run) + [
        "--write-movie", str(avi_path), "--fixed-fps", str(int(fps)), "--",
        "--scripted-indices=" + indices_arg(run),
        "--max-steps={0}".format(len(run.indices)),
        # The index list already stops where the live run stopped; a collision
        # budget here would cut a replay of an uncapped run short.
        "--max-collisions=-1",
        "--speed={0}".format(speed),
        "--stop-on-goal=false",
    ] + world_args(run)


def transcode_command(avi_path: Path, out_path: Path, crf: int = 20,
                      scale_width: Optional[int] = None) -> List[str]:
    """Movie Maker writes MJPEG AVI at roughly 1.4 MB/s; this is not optional."""
    command = [resolve("ffmpeg"), "-y", "-i", str(avi_path)]
    if scale_width:
        command += ["-vf", "scale={0}:-2".format(int(scale_width))]
    command += ["-c:v", "libx264", "-crf", str(int(crf)),
                "-pix_fmt", "yuv420p", "-an", str(out_path)]
    return command


def reel_command(concat_file: Path, out_path: Path, crf: int = 20) -> List[str]:
    """The concat demuxer holds each captioned frame for its own duration."""
    return [
        resolve("ffmpeg"), "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-crf", str(int(crf)),
        "-pix_fmt", "yuv420p", "-r", "30", str(out_path),
    ]


def ffprobe_command(path: Path) -> List[str]:
    return [
        resolve("ffprobe"), "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,duration,width,height",
        "-of", "default=noprint_wrappers=1", str(path),
    ]


def replay_dir_for(run: Run) -> Path:
    """Where replay.py will write, and what a stale directory poisons."""
    # A run recorded with --run-dir replays into its own replay/ folder.
    if run.meta.get("run_dir"):
        return run.path / "replay"
    return run.path.parent / (run.path.name + "_replay")


def shell_preview(command: Sequence[str]) -> str:
    """For the log pane: readable, and honest about what actually ran."""
    parts = []
    for token in command:
        parts.append("'{0}'".format(token) if " " in token else token)
    return " ".join(parts)
