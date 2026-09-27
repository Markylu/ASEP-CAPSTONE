#!/usr/bin/env python3
"""Reproduce a recorded run's trajectory, without calling a model.

A navigation run is closed-loop: a different choice produces a different next
frame, so a VLM run cannot be replayed by feeding the saved frames back through
the model. What *is* exactly reproducible is the trajectory — replay the
recorded index sequence through the controller's SCRIPTED mode and the drone
flies the same path. (Saved frames still replay fine through *perception*
models: YOLO and Depth Anything V2 do not steer.)

    python eval/replay.py eval/runs/run_2026-09-14_1830

Writes <run_id>_replay next to the original and diffs the two pose streams.
Exit 0 when they match.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
GODOT_PROJECT = REPO_ROOT / "first-project"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def indices_of(run_dir: Path) -> List[int]:
    decisions = read_jsonl(run_dir / "decisions.jsonl")
    if not decisions:
        raise SystemExit("no decisions.jsonl in {0}".format(run_dir))
    ordered = sorted(decisions, key=lambda d: d["step"])
    missing = [d["step"] for d in ordered if "index" not in d]
    if missing:
        raise SystemExit("run has failed decisions at steps {0}; nothing to replay".format(missing))
    return [int(d["index"]) for d in ordered]


def scene_args(meta: Dict[str, Any]) -> List[str]:
    """The scene the run was flown on, as a positional argument.

    run.json already records it, so a replay needs no new flag and no site
    registry — it re-flies whatever `current_scene` was. A run recorded before
    sites existed carries res://main.tscn and replays exactly as it always did,
    and a run with no scene recorded falls back to the project's main_scene.
    """
    scene = meta.get("scene")
    return [str(scene)] if scene else []


def compare_events(original: List[Dict[str, Any]],
                   replayed: List[Dict[str, Any]]) -> int:
    """Site props must fire at the same step in a replay as in the run.

    This is the canary for prop timing. The agent idles for seconds per step
    waiting on the model in a live run and not at all in a scripted replay, so
    anything a prop does that is paced by elapsed time rather than by physics
    ticks shows up here first — usually as a deploy one step out, and then as a
    COLLISION DIFFERS a few steps later.
    """
    a = [(e.get("name"), e.get("step")) for e in original]
    b = [(e.get("name"), e.get("step")) for e in replayed]
    if a == b:
        if a:
            print("events match: " + ", ".join("{0}@{1}".format(n, s) for n, s in a))
        return 0
    print("EVENTS DIFFER:")
    print("  original: {0}".format(a))
    print("  replay:   {0}".format(b))
    return 1


def compare(original: List[Dict[str, Any]], replayed: List[Dict[str, Any]],
            tolerance: float) -> int:
    problems = 0
    if len(original) != len(replayed):
        print("STEP COUNT: original {0}, replay {1}".format(len(original), len(replayed)))
        problems += 1

    for step, (a, b) in enumerate(zip(original, replayed)):
        pa, pb = a.get("position", []), b.get("position", [])
        drift = max((abs(x - y) for x, y in zip(pa, pb)), default=0.0)
        yaw_drift = abs(float(a.get("yaw", 0.0)) - float(b.get("yaw", 0.0)))
        collide_a, collide_b = bool(a.get("collided")), bool(b.get("collided"))
        los_a = (a.get("goal") or {}).get("line_of_sight")
        los_b = (b.get("goal") or {}).get("line_of_sight")
        flag = ""
        if drift > tolerance or yaw_drift > tolerance:
            flag, problems = "  <-- DRIFT", problems + 1
        if collide_a != collide_b:
            flag, problems = "  <-- COLLISION DIFFERS", problems + 1
        # Same trajectory through a differently-timed world is still a failed
        # replay: what the agent could see is part of what is being reproduced.
        if los_a is not None and los_b is not None and los_a != los_b:
            flag, problems = "  <-- LINE OF SIGHT DIFFERS", problems + 1
        print("step {0:<3} pos drift {1:.5f}  yaw drift {2:.5f}{3}".format(
            step, drift, yaw_drift, flag))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--decider-url", default="http://127.0.0.1:8000",
                        help="only /run/start, /step and /run/end are used; no model is called")
    parser.add_argument("--godot", default=shutil.which("godot") or "godot")
    parser.add_argument("--tolerance", type=float, default=1e-3, help="metres, and radians for yaw")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--speed", type=float, default=1.0,
                        help="turn/move speed multiplier, for watching at a human pace. "
                             "Measured drift at 0.25x is 2.4e-5 m, well inside --tolerance, "
                             "but it is nonzero and accumulates, so cite runs flown at 1.0.")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    run_id = run_dir.name
    replay_id = run_id + "_replay"
    indices = indices_of(run_dir)

    meta = json.loads((run_dir / "run.json").read_text())
    frame_size = meta.get("frame_size") or [768, 768]

    print("replaying {0} on {1}: {2} steps, indices {3}".format(
        run_id, meta.get("scene") or "project main_scene", len(indices), indices))
    command = [
        args.godot, "--path", str(GODOT_PROJECT)] + scene_args(meta) + [
        "--",
        "--run-id=" + replay_id,
        "--decider-url=" + args.decider_url,
        "--scripted-indices=" + ",".join(str(i) for i in indices),
        "--frame-size={0}x{1}".format(int(frame_size[0]), int(frame_size[1])),
        "--max-steps={0}".format(len(indices)),
        # A replay must fly the whole recorded path, including any part after
        # the original happened to enter the arrival radius.
        "--stop-on-goal=false",
        # ...and including any part after the original ran out of collision
        # budget. The budget is a property of the ORIGINAL flight, already spent
        # when it decided where to stop; re-imposing it here truncates the replay
        # early, and a run that ends on `collision_budget` exits non-zero, so the
        # comparison below never even ran. Sites where the agent grinds against a
        # wall — s02's closed door — are exactly the ones worth replaying.
        "--max-collisions=-1",
    ]
    if meta.get("static_doors"):
        command.append("--static-doors=1")
    if args.speed != 1.0:
        command.append("--speed={0}".format(args.speed))
        print("watch mode at {0}x — trajectory is within tolerance but not "
              "bit-identical".format(args.speed))
    result = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout)
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    replay_dir = run_dir.parent / replay_id
    problems = compare(read_jsonl(run_dir / "steps.jsonl"),
                       read_jsonl(replay_dir / "steps.jsonl"),
                       args.tolerance)
    problems += compare_events(read_jsonl(run_dir / "events.jsonl"),
                               read_jsonl(replay_dir / "events.jsonl"))
    print()
    if problems:
        print("REPLAY MISMATCH: {0} problem(s). The trajectory is not reproducible "
              "from the recorded indices alone — look for unseeded randomness.".format(problems))
        return 1
    print("REPLAY OK: {0} reproduces {1} within {2} m".format(replay_id, run_id, args.tolerance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
