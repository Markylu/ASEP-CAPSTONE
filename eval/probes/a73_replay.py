"""Offline readouts for a73 (R33) on Round F's 90 recorded runs. No model, CPU only.

Open loop: the drone flew a66's picks, so this says what a73's memory, planner
and tags would have said from where a66 stood, not where a73 goes. Three
readouts, against the gates in eval/phase2/R33_wall_turn_costmap/README.md:

1. Deadlock offers. Recorded steps where the previous decision was a
   turn-around taken with every strip blocked_near and this step offered
   "toward your target" on the turn-around again (a66's tags, as recorded),
   and how many of those steps a73's tags and turn rule would not offer the
   turn-around on. Also the recorded back-to-back turn-around pairs.
2. Divider crossing (s02 final/dynamic, near side, after the switch). Steps
   whose route crosses x = 0 inside the open door's gap, a66 recorded against
   a73 chained (each step's planner record replaced by the replay's own).
3. Shut tine (s03 final/dynamic, after the first closed-door confirmation
   inside the shut tine). Steps whose route leaves the tine by the crossbar
   (reaches x >= 5 before x <= -6), a66 recorded against a73 chained.

    python eval/probes/a73_replay.py [--round final] [--out eval/phase2/_probes/a73/replay.txt]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO_ROOT, geo, load, metrics, spatial, switch_step, xy  # noqa: E402
from server.decider import agent as agents, planner  # noqa: E402

CELL = spatial.CELL_M
TOWARD = spatial.WORDS["toward_target"]


def run_dirs(folder: str) -> List[Path]:
    return [d.parent for d in sorted(
        (REPO_ROOT / "eval" / "phase2" / folder).glob("runs/*/*/seed*/decisions.jsonl"))]


def centre(c: Tuple[int, int]) -> spatial.Point:
    return (c[0] + 0.5) * CELL, (c[1] + 0.5) * CELL


def chain(rows: List[Dict[str, Any]], cfg: spatial.SpatialConfig, p: Dict[str, Any],
          recorded: bool) -> List[Dict[str, Any]]:
    """Per step: memory, plan (recorded, or the replay's own chained over the
    run), the tags on that plan's target, and the turn-around indices hidden."""
    out: List[Dict[str, Any]] = []
    recs: List[Dict[str, Any]] = []
    for r in rows:
        man = r.get("manifest") or {}
        here = xy(r)
        perception = (r.get("perceiver") or {}).get("result")
        mem = spatial.rebuild(recs, man, perception, cfg)
        gp = (man.get("goal") or {}).get("position")
        row: Dict[str, Any] = {"step": r["step"], "here": here, "plan": None, "tags": {},
                               "hidden": []}
        plan: Optional[Dict[str, Any]] = None
        if recorded:
            plan = r.get("planner")
            recs.append(r)
        elif here is not None and gp is not None:
            g = spatial.pose_xyh({"position": gp, "yaw": 0.0})
            plan = planner.pathfind(mem, man, recs, (g[0], g[1]), p).to_dict()
            recs.append(dict(r, planner=plan))
        else:
            recs.append(dict(r, planner=None))
        row["plan"] = plan
        wp = (plan or {}).get("waypoint")
        if wp and man.get("actions"):
            target = spatial.Target("path", "path", float(wp[0]), float(wp[1]),
                                    p["words"]["path"], r["step"])
            tags = spatial.project(mem, man, perception, target)
            row["tags"] = tags
            row["hidden"] = spatial.hide_turn_around(mem, man, tags)
        out.append(row)
    return out


def turn_index(r: Dict[str, Any]) -> Optional[int]:
    return next((int(a["index"]) for a in (r.get("manifest") or {}).get("actions") or []
                 if a.get("turn_around")), None)


def picked_turn(r: Dict[str, Any]) -> bool:
    i = r.get("index")
    return i is not None and i == turn_index(r)


def nose_on(r: Dict[str, Any]) -> bool:
    lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
    return bool(lanes) and all(l.get("floor") == "blocked_near" for l in lanes)


def deadlock(rows: List[Dict[str, Any]], a73: List[Dict[str, Any]]) -> Dict[str, int]:
    """Readout 1 on one run."""
    out = collections.Counter()
    for i in range(1, len(rows)):
        prev, r = rows[i - 1], rows[i]
        if picked_turn(prev) and picked_turn(r):
            out["ta_pairs"] += 1
        if not (picked_turn(prev) and nose_on(prev)):
            continue
        out["after_wall_turn"] += 1
        t = turn_index(r)
        rec_tags = (r.get("tags") or {}).get(str(t), [])
        if TOWARD in rec_tags:
            out["a66_toward_on_turn"] += 1
            row = a73[i]
            if t in row["hidden"] or TOWARD not in row["tags"].get(t, []):
                out["a73_breaks"] += 1
        if picked_turn(r):
            out["a66_turned_again"] += 1
            if t in a73[i]["hidden"]:
                out["a73_hides_that_turn"] += 1
    return out


def crossing_y(path: List[List[int]]) -> Optional[float]:
    """Map y where the route's cell centres first cross x = 0 going -x."""
    for a, b in zip(path, path[1:]):
        xa, ya = centre((a[0], a[1]))
        xb, yb = centre((b[0], b[1]))
        if xa > 0.0 >= xb:
            t = xa / (xa - xb) if xa != xb else 0.0
            return ya + (yb - ya) * t
    return None


def s02_crossing(rows: List[Dict[str, Any]], plans: List[Dict[str, Any]], site: str,
                 met: Dict[str, Any], arm: str) -> Tuple[int, int]:
    """Readout 2 on one run: steps on the near side after the switch whose
    route crosses the divider inside the open door's gap, and steps counted."""
    sw = switch_step(met)
    door_y = geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"]
    k = n = 0
    for r, row in zip(rows, plans):
        here = row["here"]
        if here is None or here[0] <= 0.5:
            continue
        if arm == "dynamic" and (sw is None or r["step"] < sw):
            continue
        path = (row["plan"] or {}).get("path_cells") or []
        if not path:
            continue
        n += 1
        y = crossing_y(path)
        if y is not None and abs(y - door_y) <= geo.DOOR_HALF + CELL / 2.0:
            k += 1
    return k, n


def s03_shut_side(run: Path, arm: str, rows: List[Dict[str, Any]], met: Dict[str, Any]) -> Optional[str]:
    if arm == "final":
        closed = json.loads((run / "run.json").read_text()).get("final_closed") or []
        return "L" if "BranchL" in closed else ("R" if "BranchR" in closed else None)
    return common.s03_shut_side(arm, rows, switch_step(met))


def in_tine(p: spatial.Point, side: str) -> bool:
    return -6.0 <= p[0] < 5.0 and (3.5 <= -p[1] <= 6.5 if side == "L" else 3.5 <= p[1] <= 6.5)


def route_leaves_tine(path: List[List[int]]) -> bool:
    for c in path:
        x, _ = centre((c[0], c[1]))
        if x >= 5.0:
            return True
        if x <= -6.0:
            return False
    return False


def first_closed_in_tine(rows: List[Dict[str, Any]], side: str) -> Optional[int]:
    for r in rows:
        here = xy(r)
        if here is None or not in_tine(here, side):
            continue
        lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
        if any(l.get("doorway") == "closed" for l in lanes):
            return r["step"]
    return None


def s03_shut_tine(rows: List[Dict[str, Any]], plans: List[Dict[str, Any]], side: Optional[str]) -> Tuple[int, int]:
    """Readout 3 on one run: after the first closed read inside the shut tine,
    steps in that tine whose route leaves it by the crossbar, and steps counted."""
    if side is None:
        return 0, 0
    first = first_closed_in_tine(rows, side)
    if first is None:
        return 0, 0
    k = n = 0
    for r, row in zip(rows, plans):
        here = row["here"]
        if r["step"] < first or here is None or not in_tine(here, side):
            continue
        path = (row["plan"] or {}).get("path_cells") or []
        if not path:
            continue
        n += 1
        k += route_leaves_tine(path)
    return k, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="final")
    ap.add_argument("--out", default=str(REPO_ROOT / "eval/phase2/_probes/a73/replay.txt"))
    ap.add_argument("--only", default="", help="substring filter on site/arm/seed")
    args = ap.parse_args()
    a66 = agents.get("a66").features["orchestrator"]
    a73 = agents.get("a73").features["orchestrator"]
    cfg66, cfg73 = spatial.config_for(a66), spatial.config_for(a73)
    lines = ["a73 replay on {0} (open loop; eval/probes/a73_replay.py)".format(args.round), "",
             "run                   | deadlock: wall-turns a66 toward-on-turn a73-breaks | "
             "turned-again a73-hides | TA pairs | s02 gap crossing a66 a73 | s03 route out a66 a73"]
    tot: Dict[str, float] = collections.defaultdict(float)
    for run in run_dirs(args.round):
        site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
        name = "{0}/{1}/{2}".format(site, arm, seed)
        if args.only and args.only not in name:
            continue
        rows = [r for r in load(run) if "step" in r and r.get("manifest")]
        met = metrics(run)
        rec = chain(rows, cfg66, a66["pathfinder"], recorded=True)
        new = chain(rows, cfg73, a73["pathfinder"], recorded=False)
        d = deadlock(rows, new)
        for k, v in d.items():
            tot[k] += v
        cross = tine = ""
        if site.startswith("s02") and arm != "initial":
            k66, n = s02_crossing(rows, rec, site, met, arm)
            k73, _ = s02_crossing(rows, new, site, met, arm)
            cross = "{0:3d} {1:3d} of {2:3d}".format(k66, k73, n)
            tot["x66"] += k66; tot["x73"] += k73; tot["xn"] += n
        if site == "s03" and arm != "initial":
            side = s03_shut_side(run, arm, rows, met)
            k66, n = s03_shut_tine(rows, rec, side)
            k73, _ = s03_shut_tine(rows, new, side)
            tine = "{0:3d} {1:3d} of {2:3d}".format(k66, k73, n)
            tot["t66"] += k66; tot["t73"] += k73; tot["tn"] += n
        lines.append("{0:21s} | {1:3d} {2:3d} {3:3d} | {4:3d} {5:3d} | {6:3d} | {7:15s} | {8:15s}".format(
            name, d["after_wall_turn"], d["a66_toward_on_turn"], d["a73_breaks"],
            d["a66_turned_again"], d["a73_hides_that_turn"], d["ta_pairs"], cross, tine))
        print(lines[-1], flush=True)
    lines.append("")
    lines.append("Deadlock: {0:.0f} steps after a wall turn; a66 offered toward on the turn-around on {1:.0f}, "
                 "a73 breaks {2:.0f} of those. a66 turned again on {3:.0f}; a73 hides that turn-around on {4:.0f}. "
                 "Recorded back-to-back turn-around pairs: {5:.0f}.".format(
                     tot["after_wall_turn"], tot["a66_toward_on_turn"], tot["a73_breaks"],
                     tot["a66_turned_again"], tot["a73_hides_that_turn"], tot["ta_pairs"]))
    if tot["xn"]:
        lines.append("s02 near-side steps after the switch whose route crosses the divider inside the open door's gap: "
                     "a66 {0:.0f}/{2:.0f} ({3:.0%}), a73 {1:.0f}/{2:.0f} ({4:.0%}).".format(
                         tot["x66"], tot["x73"], tot["xn"], tot["x66"] / tot["xn"], tot["x73"] / tot["xn"]))
    if tot["tn"]:
        lines.append("s03 shut-tine steps after the closed read whose route leaves by the crossbar: "
                     "a66 {0:.0f}/{2:.0f} ({3:.0%}), a73 {1:.0f}/{2:.0f} ({4:.0%}).".format(
                         tot["t66"], tot["t73"], tot["tn"], tot["t66"] / tot["tn"], tot["t73"] / tot["tn"]))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-4:]))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
