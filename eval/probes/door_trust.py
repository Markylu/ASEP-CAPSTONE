"""Which doorway reads to trust (a77, R37), on flown frames. No model.

Every strip read open after d01 in the s02 near-side frames, split by whether
its centre ray meets the divider inside the true open door (real) or not
(phantom), under candidate rules a memory could apply from the frame alone:
the strip, the look's angle off square from the neighbours' floor ends (the
scratch form of spatial.look_angle), how many strips read open. Prints each
rule's precision and recall. Run from the repo root:

    python eval/probes/door_trust.py
"""
import sys, collections, math
sys.path.insert(0, 'eval/probes')
import common
from a73_replay import geo, load, metrics, run_dirs, spatial, xy
RNG = {"no_floor": 0.8, "bottom": 2.5, "lower": 4.5, "middle": 8.0}
RANK = {"no_floor": 0, "bottom": 1, "lower": 2, "middle": 3}
t = collections.Counter(); ends = collections.Counter()
def est(lanes, k):
    """Estimated angle off square of the look along strip k, from the floor ends of
    the nearest strip each side that is not an open doorway."""
    pts = {}
    for j, l in enumerate(lanes):
        r = RNG.get(l.get("floor_end"))
        if r is None: continue
        th = math.radians(spatial.strip_offset(spatial.STRIPS[j]))
        pts[j] = (r * math.cos(th), r * math.sin(th))
    left = [j for j in range(k - 1, -1, -1) if j in pts and lanes[j].get("doorway") != "open"]
    right = [j for j in range(k + 1, 5) if j in pts and lanes[j].get("doorway") != "open"]
    if not left or not right: return None
    a, b = pts[left[0]], pts[right[0]]
    wall = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))  # wall direction in drone frame
    ray = spatial.strip_offset(spatial.STRIPS[k])
    d = abs(spatial.wrap(wall - ray)) % 180.0
    return abs(d - 90.0)   # 0 = square
for folder in "final,R30_pathfinder,R32P_repeat_a66,R35_wall_turn_only".split(","):
    for run in run_dirs(folder):
        site, arm = run.parts[-3], run.parts[-2]
        if not site.startswith("s02"): continue
        rows = [r for r in load(run) if "step" in r]; met = metrics(run)
        for r in rows:
            here = xy(r)
            lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
            if here is None or here[0] <= 0.5 or len(lanes) != 5: continue
            changed = common.world_key(site, arm, r["step"], rows, met)[1]
            opened = geo.open_doors(site, "final" if changed else "initial", 0)
            for k, l in enumerate(lanes):
                if l.get("doorway") != "open": continue
                h = (here[2] + spatial.strip_offset(spatial.STRIPS[k])) % 360.0
                c = math.cos(math.radians(h))
                if c >= -0.02:
                    truth, obl = "phantom", 90.0
                else:
                    d = here[0] / -c; y = here[1] + d * math.sin(math.radians(h))
                    truth = "real" if any(abs(y - geo.S02_DOORS[n]) < 1.7 for n in opened) else "phantom"
                    obl = math.degrees(math.acos(min(1.0, -c)))
                e = est(lanes, k)
                eb = "none" if e is None else "%02d-%02d" % (int(e // 20) * 20, int(e // 20) * 20 + 20)
                t[(truth, "est", eb)] += 1
                ranks = [RANK.get(x.get("floor_end")) for x in lanes]
                rk = [x for x in ranks if x is not None]
                t[(truth, "spread", max(rk) - min(rk) if rk else -1)] += 1
                t[(truth, "end", str(l.get("floor_end")))] += 1
                t[(truth, "nopen", sum(1 for x in lanes if x.get("doorway") == "open"))] += 1
                t[(truth, "nclosed", sum(1 for x in lanes if x.get("doorway") == "closed"))] += 1
                t[(truth, "strip", spatial.STRIPS[k])] += 1
                nopen = sum(1 for x in lanes if x.get("doorway") == "open")
                centre = k == 2; inner = k in (1, 2, 3); sq = e is not None and e < 20
                end = l.get("floor_end")
                for name, ok in (("all", True), ("centre", centre), ("inner", inner), ("sq", sq), ("centre&sq", centre and sq),
                                 ("inner&sq", inner and sq), ("sq&nopen1", sq and nopen == 1), ("centre&nopen1", centre and nopen == 1),
                                 ("inner&sq&nopen1", inner and sq and nopen == 1), ("centre|sq&nopen1", centre or (sq and nopen == 1)),
                                 ("sq&far", sq and end in ("lower", "middle")), ("centre&far", centre and end in ("lower", "middle")),
                                 ("nopen1", nopen == 1)):
                    if ok: t[("rule", name, truth)] += 1
                tb = "%02d" % (int(obl // 20) * 20)
                if e is not None: t[("cal", tb, eb)] += 1
names = sorted({k[1] for k in t if k[0] == "rule"})
for n in names:
    r, p = t[("rule", n, "real")], t[("rule", n, "phantom")]
    print("%-20s real %4d phantom %4d precision %3.0f%% recall %3.0f%%" % (n, r, p, 100*r/max(1,r+p), 100*r/t[("rule","all","real")]))
