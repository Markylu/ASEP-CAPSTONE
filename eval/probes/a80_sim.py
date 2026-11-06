"""A closed-loop check of the route planner's code on the sites' 2D geometry. No model, no Godot.

The planner (planner.pathfind), the memory (spatial.rebuild) and the tags
(spatial.project, hide_turn_around) are the agent's own code. What is
simulated is everything else: the drone moves on R11's 2D site model
(analysis/geo.py), a perceiver that reads the truth (floor to the first wall
along each strip's centre ray; a doorway where that ray meets a door within
`--door-deg` of square to the divider; with `--noise`, doorways and walls
misread at the rates probe door_read and Round F's flight measured), and a
navigator that takes the move tagged "toward your target" (with `--slip`, any
open move that often instead). It answers one question a recorded-run replay cannot: does the
state machine do what it was written to do when the drone goes where it
sends it? It says nothing about what the model reads or picks.

    python eval/probes/a80_sim.py --agent a80 [--slip 0.2] [--trace s02a/dynamic]
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import geo, spatial  # noqa: E402
from server.decider import agent as agents, planner  # noqa: E402

GOAL = (-12.0, 0.0)
RADIUS = 0.45
FAN = [(0, 180.0, True), (1, 43.5, False), (2, 21.75, False), (3, 0.0, False),
       (4, -21.75, False), (5, -43.5, False)]


def manifest(step: int, pose: Tuple[float, float, float]) -> Dict[str, Any]:
    x, y, h = pose
    return {"step": step,
            "pose": {"position": [x, 1.75, -y], "yaw": math.radians(h - 90.0)},
            "goal": {"position": [GOAL[0], 1.0, -GOAL[1]]},
            "actions": [{"index": i, "r": 0.0 if turn else 1.7, "theta_deg": th,
                         "theta": math.radians(th), "turn_around": turn} for i, th, turn in FAN]}


#: Probe door_read (docs/research/round-f-analysis.md §9), by the look's angle
#: off square at 2-9 m: the open door read open, a shut door read open, a blank
#: wall strip read open. Used with --noise.
DOOR_READ = [(20.0, 157 / 158, 1 / 283, 1 / 366), (40.0, 36 / 41, 1 / 89, 17 / 939),
             (60.0, 67 / 92, 3 / 131, 33 / 346), (90.0, 112 / 231, 79 / 522, 76 / 393)]
#: Round F in flight (eval/r28_flight.py): a wall within 1 m read open, open floor read no_floor.
MISSED_WALL, PHANTOM_WALL = 0.167, 0.124
#: A shut door read closed when it is in the strip (no measurement: a guess, stated).
CLOSED_READ = 0.7


def perceive(free, doors_open, pose, door_deg: float,
             noise: Optional[random.Random] = None) -> Dict[str, Any]:
    x, y, h = pose
    lanes = []
    for strip in spatial.STRIPS:
        hd = (h + spatial.strip_offset(strip)) % 360.0
        d = geo.ray(free, x, y, hd, max_d=12.0)
        if noise is not None:
            if d < 1.6 and noise.random() < MISSED_WALL:
                d = 5.0
            elif d >= 1.6 and noise.random() < PHANTOM_WALL:
                d = 1.0
        floor, end = (("blocked_near", "no_floor") if d < 1.6 else
                      ("open_near", "bottom") if d < 4.0 else ("open_far", "lower"))
        door: Any = False
        c = math.cos(math.radians(hd))
        if x > 0.5 and c < -0.05:
            t = (0.5 - x) / c
            yhit = y + t * math.sin(math.radians(hd))
            off = abs(spatial.wrap(hd - 180.0))
            if t <= 12.0 and geo.ray(free, x, y, hd, max_d=12.0) >= t - 0.1:
                at = next((name for name, dy in geo.S02_DOORS.items()
                           if abs(yhit - dy) < geo.DOOR_HALF), None)
                if noise is None:
                    if at is not None and off <= door_deg:
                        door = "open" if at in doors_open else "closed"
                else:
                    _, p_open, p_shut_open, p_wall_open = next(r for r in DOOR_READ if off <= r[0])
                    roll = noise.random()
                    if at is not None and at in doors_open:
                        door = "open" if roll < p_open else False
                    elif at is not None:
                        door = ("open" if roll < p_shut_open
                                else "closed" if roll < p_shut_open + CLOSED_READ else False)
                    elif roll < p_wall_open:
                        door = "open"
        lanes.append({"strip": strip, "floor": floor, "floor_end": end, "doorway": door})
    return {"goal": "not_visible", "goal_range": None, "lanes": lanes}


def fly(site: str, arm: str, feats: Dict[str, Any], slip: float, rng: random.Random,
        door_deg: float, trace: bool, noisy: bool = False) -> Dict[str, Any]:
    cfg = spatial.config_for(feats)
    p = feats["pathfinder"]
    pose = (20.0 if "v" in site else 12.0, 0.0, 180.0)
    recs: List[Dict[str, Any]] = []
    crossed = None
    survey_steps = 0
    for step in range(60):
        changed = arm == "final" or (arm == "dynamic" and step >= 4)
        doors = geo.open_doors(site, "final" if changed else "initial", 0)
        free = lambda a, b: geo.free_s02(a, b, doors)  # noqa: E731
        man = manifest(step, pose)
        seen = perceive(free, doors, pose, door_deg, rng if noisy else None)
        mem = spatial.rebuild(recs, man, seen, cfg)
        plan = planner.pathfind(mem, man, recs, GOAL, p).to_dict()
        wp = plan["waypoint"]
        target = spatial.Target("path", "path", float(wp[0]), float(wp[1]), p["words"]["path"], step)
        tags = spatial.project(mem, man, seen, target)
        hidden = spatial.hide_turn_around(mem, man, tags)
        offered = [a for a in man["actions"] if a["index"] not in hidden]
        shut = ("wall close", "blocked", "stopped short")
        open_moves = [a for a in offered if not a["turn_around"]
                      and not any(w.startswith(shut) for w in tags.get(a["index"], []))]
        pick = next((a for a in offered
                     if spatial.WORDS["toward_target"] in tags.get(a["index"], [])), None)
        if pick is None or (open_moves and rng.random() < slip):
            pick = rng.choice(open_moves) if open_moves else next(
                a for a in man["actions"] if a["turn_around"])
        sv = plan.get("survey") or {}
        survey_steps += bool(sv) and sv.get("phase") != "done"
        if trace:
            print("  {0:2d} ({1:5.1f},{2:5.1f}) h{3:4.0f} wp ({4:5.1f},{5:5.1f}) pick {6} {7} {8}".format(
                step, pose[0], pose[1], pose[2], wp[0], wp[1], pick["index"],
                "survey {0} i{1} wall {2}".format(sv.get("phase"), sv.get("i"), sv.get("wall")) if sv else "",
                "latch" if plan.get("latch") else ""))
        recs.append({"step": step, "manifest": man, "perceiver": {"result": seen},
                     "planner": plan, "index": pick["index"], "tags": tags})
        x, y, h = pose
        if pick["turn_around"]:
            pose = (x, y, (h + 180.0) % 360.0)
        else:
            ah = (h + pick["theta_deg"]) % 360.0
            reach = max(0.0, min(1.7, geo.ray(free, x, y, ah, max_d=3.0) - RADIUS))
            pose = (x + reach * math.cos(math.radians(ah)), y + reach * math.sin(math.radians(ah)), ah)
        if crossed is None and pose[0] < 0.0:
            crossed = step + 1
        if spatial.dist(pose[:2], GOAL) <= 1.0:
            return {"won": True, "steps": step + 1, "crossed": crossed, "survey": survey_steps}
    return {"won": False, "steps": 60, "crossed": crossed, "survey": survey_steps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="a80")
    ap.add_argument("--slip", type=float, default=0.0)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--door-deg", type=float, default=60.0)
    ap.add_argument("--trace", default="")
    ap.add_argument("--noise", action="store_true",
                    help="doorway and wall reads wrong at the rates measured in flight")
    args = ap.parse_args()
    feats = agents.get(args.agent).features["orchestrator"]
    won = n = 0
    for site in ("s02a", "s02c", "s02va", "s02vc"):
        for arm in ("initial", "final", "dynamic"):
            cell = "{0}/{1}".format(site, arm)
            if args.trace and args.trace != cell:
                continue
            outs = [fly(site, arm, feats, args.slip, random.Random(seed), args.door_deg,
                        bool(args.trace), args.noise) for seed in range(args.seeds)]
            n += len(outs)
            won += sum(o["won"] for o in outs)
            print("{0} {1:14s} won {2}/{3} steps {4} crossed {5} survey steps {6}".format(
                args.agent, cell, sum(o["won"] for o in outs), len(outs),
                [o["steps"] for o in outs], [o["crossed"] for o in outs],
                [o["survey"] for o in outs]))
    print("{0}: {1}/{2}".format(args.agent, won, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
