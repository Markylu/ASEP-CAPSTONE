"""Offline readouts for a72 (R31) on R30's recorded runs. No model, CPU only.

Open loop: the drone flew a66's route, so this says what a72's memory and
planner would have said from where a66 stood, not where a72 goes. Three
readouts, against the gates in eval/phase2/R31_two_pose_commit/README.md:

1. Phantom divider floor (s02 sites). Per step, the s02 divider cells (|x| <=
   0.5 m) that are truly wall yet claimed as floor by a look: strong (free /
   free_near) or soft (a17h's soft_door). a17f (a66's memory) against a17h.
   Also whether the true open door's gap cells are passable on each step.
2. Stem mouth sealed (s03). Per step, whether any cell across the stem mouth
   (x in [14.5, 15.5], |y| <= 1.5) is impassable on the cost map: a17f
   against a17h (a71 s03: one nose-on no_floor read at s4 sealed it for good).
3. Route flips. Per run, the steps on which the waypoint's bearing from the
   drone turned by more than 90 degrees against the step before: a66 as
   recorded, a17h without commitment, and a72 (a17h + commit) chained over
   the run's records (each step's planner record replaced by the replay's own).

    python eval/probes/a72_replay.py [--round R30] [--out eval/phase2/_probes/a72/replay.txt]
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO_ROOT, geo, load, metrics, spatial, xy  # noqa: E402
from server.decider import agent as agents, planner  # noqa: E402

CELL = spatial.CELL_M
A66 = agents.get("a66").features["orchestrator"]
A72 = agents.get("a72").features["orchestrator"]


def run_dirs(rid: str) -> List[Path]:
    out = []
    for d in sorted((REPO_ROOT / "eval" / "phase2").glob(rid + "_*/runs/*/*/seed*/decisions.jsonl")):
        out.append(d.parent)
    return out


def centre(c: Tuple[int, int]) -> spatial.Point:
    return (c[0] + 0.5) * CELL, (c[1] + 0.5) * CELL


def divider_cells() -> List[Tuple[int, int]]:
    out = []
    for cy in range(int(-geo.HALF_W / CELL) - 1, int(geo.HALF_W / CELL) + 2):
        for cx in (-1, 0):
            x, y = centre((cx, cy))
            if abs(x) <= 0.5 + CELL / 2.0 and abs(y) <= geo.HALF_W:
                out.append((cx, cy))
    return out


def stem_mouth_cells() -> List[Tuple[int, int]]:
    out = []
    for cx in range(int(14.0 / CELL), int(16.0 / CELL) + 1):
        for cy in range(-3, 4):
            x, y = centre((cx, cy))
            if 14.5 <= x <= 15.5 and abs(y) <= 1.5:
                out.append((cx, cy))
    return out


DIVIDER = divider_cells()
MOUTH = stem_mouth_cells()


def chain(rows: List[Dict[str, Any]], cfg: spatial.SpatialConfig, p: Dict[str, Any],
          recorded: bool = False) -> List[Dict[str, Any]]:
    """Per step: the memory a `cfg` agent builds from the run's records and
    the plan `p` makes on it, with the planner records chained (unless
    `recorded`: a66's own recorded plans)."""
    out = []
    recs: List[Dict[str, Any]] = []
    for r in rows:
        man = r.get("manifest") or {}
        here = xy(r)
        perception = (r.get("perceiver") or {}).get("result")
        mem = spatial.rebuild(recs, man, perception, cfg)
        goal = man.get("goal") or {}
        gp = goal.get("position")
        row = {"step": r["step"], "here": here, "mem": mem, "plan": None}
        if recorded:
            row["plan"] = r.get("planner")
            recs.append(r)
        elif here is not None and gp is not None:
            g = spatial.pose_xyh({"position": gp, "yaw": 0.0})
            plan = planner.pathfind(mem, man, recs, (g[0], g[1]), p)
            row["plan"] = plan.to_dict()
            recs.append(dict(r, planner=row["plan"]))
        else:
            recs.append(dict(r, planner=None))
        out.append(row)
    return out


def flips(rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Steps whose waypoint bearing from the drone turned > 90 deg, and steps counted."""
    n = f = 0
    last = None
    for row in rows:
        plan, here = row["plan"], row["here"]
        wp = (plan or {}).get("waypoint")
        if not wp or here is None:
            last = None
            continue
        b = spatial.bearing(here[:2], (wp[0], wp[1]))
        if last is not None:
            n += 1
            if abs(spatial.wrap(b - last)) > 90.0:
                f += 1
        last = b
    return f, n


def divider_counts(rows_mem: List[Dict[str, Any]], site: str, arm: str, rec: List[Dict[str, Any]],
                   met: Dict[str, Any], p: Dict[str, Any]) -> Dict[str, float]:
    strong = soft = gap_ok = steps = 0
    for row in rows_mem:
        mem = row["mem"]
        if row["here"] is None:
            continue
        free = common.world(site, arm, row["step"], rec, met)
        stall = planner.stall_cells_from(rec, row["step"])
        cm = spatial.CostMap(mem, stall, p, include=(spatial.cell(row["here"][:2]),),
                             start=spatial.cell(row["here"][:2]))
        softset = mem.soft_door_cells() if mem.cfg.two_pose else set()
        claimed_strong = set(mem.free) | set(mem.free_near)
        gap_cells = [c for c in DIVIDER if free(*centre(c))]
        wall_cells = [c for c in DIVIDER if not free(*centre(c))]
        strong += sum(1 for c in wall_cells if c in claimed_strong and cm.cost(c) is not None)
        soft += sum(1 for c in wall_cells if c in softset and c not in claimed_strong
                    and cm.cost(c) is not None)
        gap_ok += all(cm.cost(c) is not None for c in gap_cells)
        steps += 1
    return {"steps": steps, "strong_per_step": strong / max(1, steps),
            "soft_per_step": soft / max(1, steps), "gap_passable": gap_ok / max(1, steps)}


def mouth_sealed(rows_mem: List[Dict[str, Any]], rec: List[Dict[str, Any]], p: Dict[str, Any]) -> Tuple[int, int]:
    sealed = steps = 0
    for row in rows_mem:
        if row["here"] is None:
            continue
        stall = planner.stall_cells_from(rec, row["step"])
        cm = spatial.CostMap(row["mem"], stall, p, include=(spatial.cell(row["here"][:2]),),
                             start=spatial.cell(row["here"][:2]))
        steps += 1
        # The mouth is sealed when no column across it is passable.
        cols = collections.defaultdict(list)
        for c in MOUTH:
            cols[c[0]].append(cm.cost(c) is not None)
        if any(not any(v) for v in cols.values()):
            sealed += 1
    return sealed, steps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="R30")
    ap.add_argument("--out", default=str(REPO_ROOT / "eval/phase2/_probes/a72/replay.txt"))
    args = ap.parse_args()
    lines = ["a72 replay on {0} (open loop; eval/probes/a72_replay.py)".format(args.round), ""]
    lines.append("run                 | divider phantom floor /step: a17f strong | a17h strong soft | gap passable a17f a17h | mouth sealed a17f a17h | flips a66rec a17h a72")
    tot = collections.defaultdict(float)
    for run in run_dirs(args.round):
        site, arm = run.parts[-3], run.parts[-2]
        rows = [r for r in load(run) if "step" in r]
        met = metrics(run)
        name = "{0}/{1}".format(site, arm)
        mem_f = chain(rows, spatial.A17F, agents.PATHFINDER_A65, recorded=True)
        mem_h = chain(rows, spatial.A17H, agents.PATHFINDER_A65)
        a72 = chain(rows, spatial.A17H, agents.PATHFINDER_A72)
        cells = ""
        if site.startswith("s02"):
            df = divider_counts(mem_f, site, arm, rows, met, agents.PATHFINDER_A65)
            dh = divider_counts(mem_h, site, arm, rows, met, agents.PATHFINDER_A72)
            cells = "{0:5.2f} | {1:5.2f} {2:5.2f} | {3:4.0%} {4:4.0%}".format(
                df["strong_per_step"], dh["strong_per_step"], dh["soft_per_step"],
                df["gap_passable"], dh["gap_passable"])
            tot["f_strong"] += df["strong_per_step"]; tot["h_strong"] += dh["strong_per_step"]
            tot["h_soft"] += dh["soft_per_step"]; tot["f_gap"] += df["gap_passable"]
            tot["h_gap"] += dh["gap_passable"]; tot["s02"] += 1
        mouth = ""
        if site == "s03":
            sf, n = mouth_sealed(mem_f, rows, agents.PATHFINDER_A65)
            sh, _ = mouth_sealed(mem_h, rows, agents.PATHFINDER_A72)
            mouth = "{0:2d}/{2} {1:2d}/{2}".format(sf, sh, n)
        ff, n = flips(mem_f)
        fh, _ = flips(mem_h)
        f72, _ = flips(a72)
        kept = sum(1 for r in a72 if (r["plan"] or {}).get("kept"))
        tot["ff"] += ff; tot["fh"] += fh; tot["f72"] += f72; tot["n"] += n
        lines.append("{0:19s} | {1:38s} | {2:11s} | {3:2d} {4:2d} {5:2d} of {6:2d} (kept {7})".format(
            name, cells, mouth, ff, fh, f72, n, kept))
        print(lines[-1], flush=True)
    if tot["s02"]:
        lines.append("")
        lines.append("s02 mean phantom divider floor per step: a17f strong {0:.2f}; a17h strong {1:.2f}, soft {2:.2f}. "
                     "True gap passable: a17f {3:.0%}, a17h {4:.0%}.".format(
                         tot["f_strong"] / tot["s02"], tot["h_strong"] / tot["s02"],
                         tot["h_soft"] / tot["s02"], tot["f_gap"] / tot["s02"], tot["h_gap"] / tot["s02"]))
    lines.append("Route flips over {0:.0f} steps: a66 recorded {1:.0f}, a17h {2:.0f}, a72 {3:.0f}.".format(
        tot["n"], tot["ff"], tot["fh"], tot["f72"]))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-2:]))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
