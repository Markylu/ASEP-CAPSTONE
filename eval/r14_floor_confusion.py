"""Confusion of true clear distance x g05 floor_end on recorded runs (ROOT...)."""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "eval")
import r12_probe as rp
from r12_probe import spatial, geo, label, load, runs_under, site_arm, true_reach
BINS = [(0, 1.0), (1.0, 1.9), (1.9, 3.0), (3.0, 5.0), (5.0, 8.0), (8.0, 99)]
conf = Counter()
for root in sys.argv[1:]:
    for run in runs_under(Path(root).resolve()):
        site, arm = site_arm(run)
        for r in load(run):
            res = ((r.get("perceiver") or {}).get("result")) or {}
            here = spatial.pose_xyh(r["manifest"].get("pose"))
            if not res or here is None:
                continue
            free = geo.world(site, arm, r["step"])
            for lane in res.get("lanes") or []:
                if lane.get("strip") not in spatial.STRIPS or not lane.get("floor_end"):
                    continue
                d = true_reach(free, here[:2], (here[2] + spatial.strip_offset(lane["strip"])) % 360.0)
                b = next(b for b in BINS if b[0] <= d < b[1])
                conf[(b, lane["floor_end"])] += 1
ends = ["no_floor", "bottom", "lower", "middle"]
print("true m      " + " ".join("%9s" % e for e in ends))
for b in BINS:
    print("%-10s " % ("%g-%g" % b) + " ".join("%9d" % conf[(b, e)] for e in ends))
tot = {e: sum(conf[(b, e)] for b in BINS) for e in ends}
for e in ends:
    under = sum(conf[(b, e)] for b in BINS if b[1] <= 1.9)
    print("%-9s n=%5d  true<1.9m (move of 1.7 fails) %.1f%%" % (e, tot[e], 100 * under / max(1, tot[e])))
