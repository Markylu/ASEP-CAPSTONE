"""Third readout for a72 (R31): where the route crosses the s02 divider.

Per s02 final/dynamic step with the drone on the near side (x > 0.5) and a
route: the route's first divider cell. Through the true open door's gap
(good), through a phantom cell (the map's floor on a wall), or no crossing
(the route goes nowhere past the divider: a frontier fallback). Configs:
a66 as recorded; a72 (a17h + commit); a72g (a72 on weak far floor, a17g's
near_free_m 2.5 and far_free_cost 1.6); a17g alone with a65's planner.

    python eval/probes/a72_replay3.py
"""
from __future__ import annotations

import collections
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO_ROOT, geo, load, metrics, spatial  # noqa: E402
from a72_replay import DIVIDER, centre, chain, run_dirs, flips  # noqa: E402
from server.decider import agent as agents  # noqa: E402

A72G_MEM = replace(spatial.A17H, name="a17h+near", near_free_m=2.5)
CONFIGS = {
    "a66rec": (spatial.A17F, agents.PATHFINDER_A65, True),
    "a72": (spatial.A17H, agents.PATHFINDER_A72, False),
    "a72g": (A72G_MEM, dict(agents.PATHFINDER_A72, far_free_cost=1.6), False),
    "a17g": (spatial.A17G, dict(agents.PATHFINDER_A65, far_free_cost=1.6), False),
}


def crossing(plan, gap):
    cells = [tuple(c) for c in (plan or {}).get("path_cells") or []]
    for c in cells:
        if c in DIVIDER:
            return "gap" if c in gap else "phantom"
        if centre(c)[0] < -0.5:
            return "phantom"
    return "none"


def main() -> int:
    tot = {k: collections.Counter() for k in CONFIGS}
    lines = ["run           | " + " | ".join("{0:>22s}".format(k + " gap/phantom/none") for k in CONFIGS)]
    for run in run_dirs("R30"):
        site, arm = run.parts[-3], run.parts[-2]
        if not site.startswith("s02") or arm == "initial":
            continue
        rows = [r for r in load(run) if "step" in r]
        met = metrics(run)
        cols = []
        for k, (cfg, p, rec) in CONFIGS.items():
            out = chain(rows, cfg, p, recorded=rec)
            c = collections.Counter()
            for row in out:
                if row["here"] is None or row["here"][0] <= 0.5 or not row["plan"]:
                    continue
                free = common.world(site, arm, row["step"], rows, met)
                gap = {x for x in DIVIDER if free(*centre(x))}
                c[crossing(row["plan"], gap)] += 1
            f, n = flips(out)
            c["flips"] += f
            tot[k].update(c)
            cols.append("{0:3d}/{1:3d}/{2:3d} f{3:2d}".format(c["gap"], c["phantom"], c["none"], f))
        lines.append("{0:13s} | {1}".format(site + "/" + arm, " | ".join("{0:>22s}".format(x) for x in cols)))
        print(lines[-1], flush=True)
    lines.append("")
    for k in CONFIGS:
        c = tot[k]
        n = c["gap"] + c["phantom"] + c["none"]
        lines.append("{0:7s}: route through the true gap on {1}/{2} near-side steps ({3:.0%}), phantom {4}, none {5}; flips {6}".format(
            k, c["gap"], n, c["gap"] / max(1, n), c["phantom"], c["none"], c["flips"]))
    out = REPO_ROOT / "eval/phase2/_probes/a72/replay3.txt"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-4:])); print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
