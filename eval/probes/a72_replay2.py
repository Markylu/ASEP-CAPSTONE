"""Second readout for a72 (R31) on R30's s02 runs. No model.

1. Door-ray phantoms: s02 divider cells that are truly wall and hold floor
   written by an open-doorway's rays (a17f: free_near is written by door rays
   only; a17h: by confirmed openings only), per step. Openings confirmed under
   a17h: phantom (farther than DOOR_HALF from the true open door) or true.
2. Wall-line inference, measured only: with near floor tracked (a17h plus
   near_free_m 2.5, so free_near = floor within 2.5 m or through a confirmed
   door), the divider cells lying between two seen wall cells at most span_m
   apart along the divider, with no visit and no near floor between: how
   many are truly wall (phantom floor the inference would seal) and on how
   many steps the true gap would be bridged (sealed wrongly).

    python eval/probes/a72_replay2.py
"""
from __future__ import annotations

import collections
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO_ROOT, geo, load, metrics, spatial, xy  # noqa: E402
from a72_replay import DIVIDER, centre, chain, run_dirs  # noqa: E402
from server.decider import agent as agents  # noqa: E402

SPAN_M = 6.0
H2 = replace(spatial.A17H, name="a17h+near", near_free_m=2.5)


def main() -> int:
    tot = collections.Counter()
    lines = ["run           | door-ray phantom cells/step a17f a17h | a17h openings confirmed phantom/true"
             " | line: phantom sealed/step | true gap bridged steps"]
    for run in run_dirs("R30"):
        site, arm = run.parts[-3], run.parts[-2]
        if not site.startswith("s02"):
            continue
        rows = [r for r in load(run) if "step" in r]
        met = metrics(run)
        mem_f = chain(rows, spatial.A17F, agents.PATHFINDER_A65, recorded=True)
        mem_h = chain(rows, spatial.A17H, agents.PATHFINDER_A65)
        mem_n = chain(rows, H2, agents.PATHFINDER_A65)
        df = dh = steps = 0
        sealed = bridged = 0
        for rf, rh, rn in zip(mem_f, mem_h, mem_n):
            if rf["here"] is None:
                continue
            steps += 1
            free = common.world(site, arm, rf["step"], rows, met)
            wall_cells = [c for c in DIVIDER if not free(*centre(c))]
            gap_cells = {c for c in DIVIDER if free(*centre(c))}
            df += sum(1 for c in wall_cells if c in rf["mem"].free_near)
            dh += sum(1 for c in wall_cells if c in rh["mem"].free_near)
            # Wall-line inference on the divider's two columns.
            m = rn["mem"]
            hard = set(m.wall) | set(m.firm_wall) | set(m.door_wall) | set(m.stop_wall) | set(m.near_wall)
            keep = set(m.visits) | set(m.free_near)
            hit_gap = False
            for cx in (-1, 0):
                ys = sorted(c[1] for c in hard if c[0] == cx and abs(centre(c)[1]) <= geo.HALF_W)
                for a, b in zip(ys, ys[1:]):
                    if (b - a) * spatial.CELL_M > SPAN_M or b - a < 2:
                        continue
                    between = [(cx, y) for y in range(a + 1, b)]
                    if any(c in keep for c in between):
                        continue
                    for c in between:
                        if c in gap_cells:
                            hit_gap = True
                        elif c not in hard:
                            sealed += 1
            bridged += hit_gap
        # Openings confirmed under a17h at the run's end: phantom or true.
        last = mem_h[-1]["mem"]
        doors = geo.open_doors(site, arm, 999)
        conf = [o for o in last.openings if last.opening_confirmed(o)]
        phantom = sum(1 for o in conf if not any(abs(o.x) < 2.0 and abs(o.y - geo.S02_DOORS[d]) < geo.DOOR_HALF + 1.0
                                                 for d in doors))
        lines.append("{0:13s} | {1:5.2f} {2:5.2f} | {3} / {4} | {5:5.2f} | {6:2d}/{7}".format(
            site + "/" + arm, df / steps, dh / steps, phantom, len(conf) - phantom,
            sealed / steps, bridged, steps))
        print(lines[-1], flush=True)
        tot["df"] += df / steps; tot["dh"] += dh / steps; tot["n"] += 1
        tot["sealed"] += sealed / steps; tot["bridged"] += bridged; tot["steps"] += steps
        tot["phantom"] += phantom; tot["true"] += len(conf) - phantom
    lines.append("")
    lines.append("s02 mean door-ray phantom cells per step: a17f {0:.2f}, a17h {1:.2f}; openings confirmed under a17h: "
                 "{2} phantom, {3} true. Wall-line inference (span <= {4:.0f} m): {5:.2f} phantom cells sealed per step; "
                 "true gap bridged on {6} of {7} steps.".format(
                     tot["df"] / tot["n"], tot["dh"] / tot["n"], tot["phantom"], tot["true"], SPAN_M,
                     tot["sealed"] / tot["n"], tot["bridged"], tot["steps"]))
    out = REPO_ROOT / "eval/phase2/_probes/a72/replay2.txt"
    out.write_text("\n".join(lines) + "\n")
    print(lines[-1]); print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
