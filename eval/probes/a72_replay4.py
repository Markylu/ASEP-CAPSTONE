"""Fourth readout (measurement only, no agent): a wall halo on the s02 divider.

A nose-on wall run (three or more adjacent no_floor strips) is extended
`halo` cells along its own line beyond each end, over far floor, never over a
visit, near floor (within 2.5 m) or a confirmed door's floor. On weak far
floor (near_free_m 2.5, far_free_cost 1.6) with a17h's two-pose rules and
commitment. Same crossing readout as a72_replay3.py, plus how often the true
gap is impassable (the halo sealing the real door).

    python eval/probes/a72_replay4.py
"""
from __future__ import annotations

import collections
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO_ROOT, load, metrics, spatial  # noqa: E402
from a72_replay import DIVIDER, centre, chain, run_dirs, flips  # noqa: E402
from a72_replay3 import crossing  # noqa: E402
from server.decider import agent as agents, planner  # noqa: E402
from server.decider.spatial import (CELL_M, PARAMS_A17, PARAMS_A17D, STRIPS, ahead, cell, dist,
                                    strip_ray_offsets)  # noqa: E402

MEM = replace(spatial.A17H, name="a17h+near", near_free_m=2.5)
PLAN = dict(agents.PATHFINDER_A72, far_free_cost=1.6)
HALO = {"cells": 1}


def extend_walls_halo(self, step, where, perception):
    """spatial.SpatialMemory._extend_walls with the halo and the strong-floor exception."""
    P4 = PARAMS_A17D
    here = where[:2]
    floors = {l.get("strip"): l.get("floor") for l in perception.get("lanes") or []}
    reach = PARAMS_A17["floor_range_m"]["blocked_near"] + CELL_M / 2.0
    du = max(abs(d) for d in PARAMS_A17["cone_rays"])
    strong = set(self.visits) | set(self.free_near)
    run: List[str] = []
    for strip in list(STRIPS) + [None]:
        if strip is not None and floors.get(strip) == "blocked_near":
            run.append(strip)
            continue
        written = set()
        if len(run) >= P4["wall_run_min"]:
            left = strip_ray_offsets(run[0], [du])[0]
            right = strip_ray_offsets(run[-1], [-du])[0]
            a = ahead(here, (where[2] + left) % 360.0, reach)
            b = ahead(here, (where[2] + right) % 360.0, reach)
            length = dist(a, b)
            if length > 1e-6:
                ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
                ext = HALO["cells"] * CELL_M
                d = -ext
                while d <= length + ext + 1e-9:
                    c = cell((a[0] + ux * d, a[1] + uy * d))
                    beyond = d < 0 or d > length
                    if c not in self.visits and not (beyond and c in strong):
                        self.wall[c] = step
                        self.free.pop(c, None)
                        written.add(c)
                    d += CELL_M / 2.0
        if written and self.cfg.two_pose:
            self._promote(step, here, written, self.wall_runs)
            veto = spatial.PARAMS_A17H["veto_m"]
            for o in self.openings:
                if o.passed:
                    continue
                if any(dist(((c[0] + 0.5) * CELL_M, (c[1] + 0.5) * CELL_M), (o.x, o.y)) < veto
                       for c in written):
                    self._strong_close(o, step, here)
        run = []


def main() -> int:
    spatial.SpatialMemory._extend_walls = extend_walls_halo
    results = {}
    for halo in (1, 3, 5):
        HALO["cells"] = halo
        tot = collections.Counter()
        for run in run_dirs("R30"):
            site, arm = run.parts[-3], run.parts[-2]
            if not site.startswith("s02") or arm == "initial":
                continue
            rows = [r for r in load(run) if "step" in r]
            met = metrics(run)
            out = chain(rows, MEM, PLAN)
            for row in out:
                if row["here"] is None or not row["plan"]:
                    continue
                free = common.world(site, arm, row["step"], rows, met)
                gap = {x for x in DIVIDER if free(*centre(x))}
                stall = planner.stall_cells_from(rows, row["step"])
                cm = spatial.CostMap(row["mem"], stall, PLAN, include=(cell(row["here"][:2]),),
                                     start=cell(row["here"][:2]))
                tot["steps"] += 1
                tot["gap_sealed"] += not all(cm.cost(c) is not None for c in gap)
                if row["here"][0] > 0.5:
                    tot[crossing(row["plan"], gap)] += 1
            f, _ = flips(out)
            tot["flips"] += f
        results[halo] = tot
        n = tot["gap"] + tot["phantom"] + tot["none"]
        print("halo {0}: route through the true gap {1}/{2} ({3:.0%}), phantom {4}, none {5}; "
              "true gap impassable on {6}/{7} steps; flips {8}".format(
                  halo, tot["gap"], n, tot["gap"] / max(1, n), tot["phantom"], tot["none"],
                  tot["gap_sealed"], tot["steps"], tot["flips"]), flush=True)
    out = REPO_ROOT / "eval/phase2/_probes/a72/replay4.txt"
    out.write_text("\n".join(
        "halo {0}: gap {1} phantom {2} none {3}; gap impassable {4}/{5}; flips {6}".format(
            h, t["gap"], t["phantom"], t["none"], t["gap_sealed"], t["steps"], t["flips"])
        for h, t in results.items()) + "\n")
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
