"""Offline readouts for a74 (R34) on Round F's 90 recorded runs. No model, CPU only.

a73_replay.py's three readouts (deadlock, s02 divider crossing, s03 shut tine)
for a list of cost-map variants, plus what a stricter map can cost:

4. True gap blocked. s02 near-side steps after the switch on which no row of
   the open door's gap is passable on the variant's map; s03 shut-tine steps
   after the closed read on which the open tine's door is not passable.
5. No route. Steps, over all 90 runs, on which the search fell back (soft
   walls or a frontier), and the same over the runs a66 solved.
6. Divider on the map. In the s02 runs a66 lost: the share of the divider's
   truly walled rows impassable at the last step, and rows re-opened per step.

Open loop, as a73_replay.py.

    python eval/probes/a74_replay.py [--variants a73,a74] [--out eval/phase2/_probes/a74/replay.txt]
"""
from __future__ import annotations

import argparse
import collections
import csv
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a73_replay as base  # noqa: E402
from a73_replay import (CELL, REPO_ROOT, agents, centre, first_closed_in_tine, geo, in_tine,  # noqa: E402
                        load, metrics, planner, run_dirs, spatial, switch_step, xy)

P73 = agents.PATHFINDER_A73
A17I = spatial.A17I

#: name -> (memory config, pathfinder parameters). a74 is the agent's own.
_A66 = agents.get("a66").features["orchestrator"]
_A74 = agents.get("a74").features["orchestrator"]
VARIANTS: Dict[str, Tuple[spatial.SpatialConfig, Dict[str, Any]]] = {
    "a66": (spatial.config_for(_A66), _A66["pathfinder"]),
    "a73": (A17I, P73),
    "a74": (spatial.config_for(_A74), _A74["pathfinder"]),
    # Tried and not carried (R34 README): ray floor at 3 per metre.
    "a74_ray3": (A17I, dict(_A74["pathfinder"], far_free_cost=3.0)),
}


def solved_runs(folder: str) -> set:
    out = set()
    path = REPO_ROOT / "eval" / "phase2" / folder / "labels.csv"
    if path.exists():
        for row in csv.DictReader(path.open()):
            if row.get("label") == "success":
                out.add((row["site"], row["arm"], "seed" + row["seed"]))
    return out


def chain(rows: List[Dict[str, Any]], cfg: spatial.SpatialConfig, p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """a73_replay.chain, keeping each step's memory and cost map."""
    out: List[Dict[str, Any]] = []
    recs: List[Dict[str, Any]] = []
    for r in rows:
        man = r.get("manifest") or {}
        here = xy(r)
        perception = (r.get("perceiver") or {}).get("result")
        mem = spatial.rebuild(recs, man, perception, cfg)
        gp = (man.get("goal") or {}).get("position")
        row: Dict[str, Any] = {"step": r["step"], "here": here, "plan": None, "tags": {},
                               "hidden": [], "cm": None}
        plan = None
        if here is not None and gp is not None:
            g = spatial.pose_xyh({"position": gp, "yaw": 0.0})
            plan = planner.pathfind(mem, man, recs, (g[0], g[1]), p).to_dict()
            stall = [tuple(c) for c in (plan.get("stall") or [])] + \
                    [tuple(c) for c in planner.stall_cells_from(recs, r["step"])]
            start, end = spatial.cell(here[:2]), spatial.cell((g[0], g[1]))
            row["cm"] = spatial.CostMap(mem, stall, p, include=(start, end), start=start)
        recs.append(dict(r, planner=plan))
        row["plan"] = plan
        wp = (plan or {}).get("waypoint")
        if wp and man.get("actions"):
            target = spatial.Target("path", "path", float(wp[0]), float(wp[1]),
                                    p["words"]["path"], r["step"])
            row["tags"] = spatial.project(mem, man, perception, target)
            row["hidden"] = spatial.hide_turn_around(mem, man, row["tags"])
        out.append(row)
    return out


def gap_open(cm: spatial.CostMap, xs: Tuple[int, int], y_centre: float) -> bool:
    """Whether some grid row of a doorway (cells xs across the wall, rows
    within the door's half width of y_centre) is passable right through."""
    for cy in range(int((y_centre - geo.DOOR_HALF) // CELL), int((y_centre + geo.DOOR_HALF) // CELL) + 1):
        if abs((cy + 0.5) * CELL - y_centre) >= geo.DOOR_HALF:
            continue
        if all(cm.cost((cx, cy)) is not None for cx in xs):
            return True
    return False


def score(run: Path, rows: List[Dict[str, Any]], new: List[Dict[str, Any]], met: Dict[str, Any],
          solved: bool) -> collections.Counter:
    site, arm = run.parts[-3], run.parts[-2]
    c: collections.Counter = collections.Counter()
    d = base.deadlock(rows, new)
    for k in ("a66_toward_on_turn", "a73_breaks", "a66_turned_again", "a73_hides_that_turn"):
        c[k] += d[k]
    for row in new:
        if row["plan"]:
            c["steps"] += 1
            c["fallback"] += row["plan"].get("fallback") != "none"
            if solved:
                c["steps_solved"] += 1
                c["fallback_solved"] += row["plan"].get("fallback") != "none"
    if arm == "initial":
        return c
    if site.startswith("s02") and not solved:
        # 6. Divider on the map (failed s02 runs): the share of the divider's
        # truly walled rows impassable at the run's last step, and rows that
        # were impassable on one step and passable on the next.
        door = geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"]
        wall_rows = [cy for cy in range(-14, 14) if abs((cy + 0.5) * CELL) <= geo.HALF_W
                     and abs((cy + 0.5) * CELL - door) >= geo.DOOR_HALF + CELL / 2.0]
        prev = None
        for row in new:
            if row["cm"] is None:
                continue
            walled = {cy for cy in wall_rows
                      if row["cm"].cost((0, cy)) is None or row["cm"].cost((-1, cy)) is None}
            if prev is not None:
                c["reopened"] += len(prev - walled)
                c["cov_steps"] += 1
            prev = walled
        if prev is not None:
            c["cov_runs"] += 1
            c["cov_end"] += len(prev) / float(len(wall_rows))
    if site.startswith("s02"):
        k, n = base.s02_crossing(rows, new, site, met, arm)
        c["x"] += k
        c["xn"] += n
        sw = switch_step(met)
        door_y = geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"]
        for r, row in zip(rows, new):
            here = row["here"]
            if (here is None or here[0] <= 0.5 or row["cm"] is None
                    or (arm == "dynamic" and (sw is None or r["step"] < sw))):
                continue
            c["gn"] += 1
            c["g_blocked"] += not gap_open(row["cm"], (0, -1), door_y)
    if site == "s03":
        side = base.s03_shut_side(run, arm, rows, met)
        k, n = base.s03_shut_tine(rows, new, side)
        c["t"] += k
        c["tn"] += n
        first = first_closed_in_tine(rows, side) if side else None
        if first is not None:
            open_y = 5.0 if side == "L" else -5.0   # map y = -z; L tine is y < 0
            for r, row in zip(rows, new):
                here = row["here"]
                if r["step"] < first or here is None or not in_tine(here, side) or row["cm"] is None:
                    continue
                c["dn"] += 1
                c["d_blocked"] += not gap_open(row["cm"], (-8, -9), open_y)
    return c


def pct(a: float, b: float) -> str:
    return "{0:.0f}/{1:.0f} ({2:.0%})".format(a, b, a / b if b else 0.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="final")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--out", default=str(REPO_ROOT / "eval/phase2/_probes/a74/replay.txt"))
    args = ap.parse_args()
    names = [v for v in args.variants.split(",") if v]
    solved = solved_runs(args.round)
    tot = {n: collections.Counter() for n in names}
    for run in run_dirs(args.round):
        rows = [r for r in load(run) if "step" in r and r.get("manifest")]
        met = metrics(run)
        key = (run.parts[-3], run.parts[-2], run.parts[-1])
        for n in names:
            cfg, p = VARIANTS[n]
            tot[n].update(score(run, rows, chain(rows, cfg, p), met, key in solved))
        print("/".join(key), flush=True)
    lines = ["a74 replay on {0} (open loop; eval/probes/a74_replay.py)".format(args.round), "",
             "variant         | repeat turns hidden | s02 route in true gap | s03 route out of shut tine | "
             "s02 true gap blocked | s03 open door blocked | no route, all steps | no route, solved runs | "
             "failed s02: divider walled at end, rows re-opened per step"]
    for n in names:
        c = tot[n]
        lines.append("{0:15s} | {1:19s} | {2:21s} | {3:26s} | {4:20s} | {5:21s} | {6:18s} | {7}".format(
            n, pct(c["a73_hides_that_turn"], c["a66_turned_again"]), pct(c["x"], c["xn"]),
            pct(c["t"], c["tn"]), pct(c["g_blocked"], c["gn"]), pct(c["d_blocked"], c["dn"]),
            pct(c["fallback"], c["steps"]), pct(c["fallback_solved"], c["steps_solved"]))
            + " | {0:.0%}, {1:.2f}".format(c["cov_end"] / max(1, c["cov_runs"]),
                                           c["reopened"] / max(1, c["cov_steps"])))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
