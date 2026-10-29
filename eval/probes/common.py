"""Shared pieces for the research probes (docs/research/probe-plan.md).

Runs are found through the lane index (eval/phase2/_probes/lanes.jsonl, written
by lanes.py) when it exists, else under the repo's own eval/phase2/*/runs. Ground
truth comes from R11's analysis/geo.py, extended here with the door state each
run actually had (the switch step from metrics.json, and for s03 the tine whose
door shut). Evaluation only: nothing here is shown to the model.
"""
from __future__ import annotations

import heapq
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (REPO_ROOT, REPO_ROOT / "eval", REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from server.decider import agent as agents, spatial  # noqa: E402
from spatial_replay import load, true_goal  # noqa: E402,F401
import geo  # noqa: E402

PROBES = REPO_ROOT / "eval" / "phase2" / "_probes"
INDEX = PROBES / "lanes.jsonl"
GRID_M = 0.25


def round_id(folder: str) -> str:
    """'R25D_door_confirmer_...' -> 'R25D'."""
    return folder.split("_", 1)[0]


def round_number(rid: str) -> Optional[int]:
    digits = ""
    for ch in rid[1:]:
        if not ch.isdigit():
            break
        digits += ch
    return int(digits) if rid.startswith("R") and digits else None


def runs(first: int = 0, last: int = 999) -> Iterator[Dict[str, Any]]:
    """One entry per flown run, rounds R<first>..R<last> by number:
    {round, folder, site, arm, seed, path}. Prefers the lane index."""
    if INDEX.exists():
        rows = [json.loads(l) for l in INDEX.read_text().splitlines() if l.strip()]
        rows = [{**r, "path": Path(r["decisions_dir"])} for r in rows]
    else:
        rows = []
        for d in sorted((REPO_ROOT / "eval" / "phase2").glob("R*/runs/*/*/seed*/decisions.jsonl")):
            run = d.parent
            rows.append({"folder": run.parts[-5], "round": round_id(run.parts[-5]),
                         "site": run.parts[-3], "arm": run.parts[-2], "seed": run.parts[-1],
                         "path": run})
    for r in sorted(rows, key=lambda r: (r["folder"], r["site"], r["arm"])):
        n = round_number(r["round"])
        if n is not None and first <= n <= last:
            yield r


def metrics(run: Path) -> Dict[str, Any]:
    p = run / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else {}


def switch_step(met: Dict[str, Any]) -> Optional[int]:
    return next((e["step"] for e in met.get("events") or []
                 if e.get("name") in ("doors_switched", "occluder_deployed")), None)


def solved_step(rows: List[Dict[str, Any]], met: Dict[str, Any]) -> Optional[int]:
    """The step the goal was reached at, or None."""
    if not met.get("goal_reached"):
        return None
    return int(met.get("steps") or (rows[-1]["step"] + 1 if rows else 0))


def xy(r: Dict[str, Any]) -> Optional[spatial.Pose]:
    return spatial.pose_xyh((r.get("manifest") or {}).get("pose"))


def s03_shut_side(arm: str, rows: List[Dict[str, Any]], sw: Optional[int]) -> Optional[str]:
    """The tine whose exit door is shut: L from load in `final` (seed1:
    final_closed BranchL), the tine the drone was in at the switch in `dynamic`."""
    if arm == "final":
        return "L"
    if arm == "dynamic" and sw is not None:
        at = next((r for r in rows if r["step"] >= sw and xy(r)), None)
        if at:
            return "L" if xy(at)[1] < 0 else "R"
    return None


def _changed(arm: str, step: int, sw: Optional[int], default: Optional[int]) -> bool:
    if arm == "final":
        return True
    if arm != "dynamic":
        return False
    if sw is not None:
        return step > sw
    return default is not None and step >= default


def world_key(site: str, arm: str, step: int, rows: List[Dict[str, Any]],
              met: Dict[str, Any]) -> Tuple:
    """Which world the run was in at this step, as a hashable key."""
    sw = switch_step(met)
    if site == "s03":
        side = s03_shut_side(arm, rows, sw)
        return (site, side if _changed(arm, step, sw, None) else None)
    return (site, _changed(arm, step, sw, geo.SWITCH_STEP))


def world(site: str, arm: str, step: int, rows: List[Dict[str, Any]], met: Dict[str, Any]):
    """geo's free(x, y) for this run at this step, with the run's own switch."""
    key = world_key(site, arm, step, rows, met)
    if site == "s03":
        closed = (key[1],) if key[1] else ()
        return lambda x, y: geo.free_s03(x, y, closed)
    if site.startswith("s02"):
        doors = geo.open_doors(site, "final" if key[1] else "initial", 0)
        return lambda x, y: geo.free_s02(x, y, doors)
    if site == "s01":
        return lambda x, y: geo.free_s01(x, y, key[1])
    raise ValueError(site)


_FIELDS: Dict[Tuple, Dict[Tuple[int, int], float]] = {}


def path_to_goal(key: Tuple, free, goal: spatial.Point, p: spatial.Point) -> float:
    """Ground-truth path metres from p to the goal over free floor (Dijkstra on a
    0.25 m grid, 8-connected), inf when there is no path. One field per world."""
    fk = key + (round(goal[0], 1), round(goal[1], 1))
    if fk not in _FIELDS:
        _FIELDS[fk] = _field(free, goal)
    field = _FIELDS[fk]
    c = _cell(p)
    if c in field:
        return field[c]
    best = math.inf  # p may sit just inside a wall: snap to free floor within 0.5 m
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            v = field.get((c[0] + dx, c[1] + dy))
            if v is not None:
                best = min(best, v + GRID_M * math.hypot(dx, dy))
    return best


def _cell(p: spatial.Point) -> Tuple[int, int]:
    return int(math.floor(p[0] / GRID_M)), int(math.floor(p[1] / GRID_M))


def _centre(c: Tuple[int, int]) -> spatial.Point:
    return (c[0] + 0.5) * GRID_M, (c[1] + 0.5) * GRID_M


def _field(free, goal: spatial.Point) -> Dict[Tuple[int, int], float]:
    start = _cell(goal)
    dist = {start: 0.0}
    heap = [(0.0, start)]
    moves = [(dx, dy, GRID_M * math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
             if dx or dy]
    while heap:
        d, c = heapq.heappop(heap)
        if d > dist.get(c, math.inf):
            continue
        for dx, dy, w in moves:
            n = (c[0] + dx, c[1] + dy)
            if d + w < dist.get(n, math.inf) and free(*_centre(n)):
                dist[n] = d + w
                heapq.heappush(heap, (d + w, n))
    return dist


def memory_config(rows: List[Dict[str, Any]]) -> spatial.SpatialConfig:
    """The memory the run's own agent used."""
    version = next((r.get("agent_version") for r in rows if r.get("agent_version")), None)
    cfg = agents.get(version).spatial_config if version else None
    return cfg or spatial.A13


def s03_region(p: spatial.Point) -> str:
    x, y = p
    if x >= 15.0:
        return "lobby"
    if x >= 8.0:
        return "stem"
    if x >= 5.0:
        return "crossbar"
    if x >= -6.0:
        return "tine_L" if y < 0 else "tine_R"
    if x >= -7.0:
        return "exit_wall"
    return "chamber"


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def pct(a: float, b: float) -> str:
    return "{0}/{1} = {2:.0%}".format(a, b, a / b) if b else "{0}/0".format(a)
