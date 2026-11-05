"""How g05 and d01 read the s02 doors, by range and angle, on flown frames. No model.

Every recorded step holds the perceiver's lanes: `doorway` per strip after the
door confirmer (d01 is asked only about strips g05 called open), and
`doorway_reported` where d01 overturned g05. Against the site's geometry
(evaluation only) each of the three divider doors in view on the near side is
one look: its range, its obliqueness (the angle between the line of sight and
the door's own line, 0 = square on), and what the strip holding its centre
said. Blank divider wall: each strip whose centre ray meets the divider more
than 2.4 m from any door centre.

    python eval/probes/door_read.py [--folders final,R30_pathfinder,R32P_repeat_a66,R35_wall_turn_only]
"""
from __future__ import annotations

import argparse
import collections
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from a73_replay import REPO_ROOT, geo, load, metrics, run_dirs, spatial, switch_step, xy  # noqa: E402

RANGES = [(0, 2), (2, 4), (4, 6), (6, 9), (9, 30)]
ANGLES = [(0, 20), (20, 40), (40, 60), (60, 91)]
HALF_FOV = spatial.FOV_DEG / 2.0


def bin_of(v: float, bins: List[Tuple[int, int]]) -> str:
    for lo, hi in bins:
        if lo <= v < hi:
            return "{0}-{1}".format(lo, hi)
    return "?"


def strip_at(off: float) -> str:
    return min(spatial.STRIPS, key=lambda s: abs(spatial.wrap(spatial.strip_offset(s) - off)))


def reads(lanes: List[Dict[str, Any]], strip: str) -> Tuple[Any, Any]:
    """(g05's read, the read after d01) for one strip."""
    lane = next((l for l in lanes if l.get("strip") == strip), {})
    final = lane.get("doorway")
    return lane.get("doorway_reported", final), final


def word(v: Any) -> str:
    return v if v in ("open", "closed") else "none"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", default="final,R30_pathfinder,R32P_repeat_a66,R35_wall_turn_only")
    ap.add_argument("--out", default=str(REPO_ROOT / "eval/phase2/_probes/door_read/door_read.txt"))
    args = ap.parse_args()
    t: Dict[Any, int] = collections.Counter()
    for folder in args.folders.split(","):
        for run in run_dirs(folder):
            site, arm = run.parts[-3], run.parts[-2]
            if not site.startswith("s02"):
                continue
            rows = [r for r in load(run) if "step" in r]
            met = metrics(run)
            for r in rows:
                here = xy(r)
                lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
                if here is None or here[0] <= 0.5 or len(lanes) != len(spatial.STRIPS):
                    continue
                changed = common.world_key(site, arm, r["step"], rows, met)[1]
                opened = geo.open_doors(site, "final" if changed else "initial", 0)
                t[("frames",)] += 1
                for name, dy in geo.S02_DOORS.items():
                    at = (0.0, dy)
                    off = spatial.wrap(spatial.bearing(here[:2], at) - here[2])
                    if abs(off) > HALF_FOV - 3.0:
                        continue
                    d = spatial.dist(here[:2], at)
                    obl = abs(math.degrees(math.atan2(here[1] - dy, here[0])))
                    g, f = reads(lanes, strip_at(off))
                    # A door 2.4 m wide can straddle two strips: the neighbour's read too.
                    k = spatial.STRIPS.index(strip_at(off))
                    near = [reads(lanes, spatial.STRIPS[j]) for j in (k - 1, k, k + 1)
                            if 0 <= j < len(spatial.STRIPS)]
                    truth = "open" if name in opened else "shut"
                    key = (truth, bin_of(d, RANGES), bin_of(obl, ANGLES))
                    t[key + ("n",)] += 1
                    t[key + ("g05_" + word(g),)] += 1
                    t[key + ("d01_" + word(f),)] += 1
                    t[key + ("near_g05_open",)] += any(a == "open" for a, _ in near)
                    t[key + ("near_d01_open",)] += any(b == "open" for _, b in near)
                for s in spatial.STRIPS:
                    h = (here[2] + spatial.strip_offset(s)) % 360.0
                    c = math.cos(math.radians(h))
                    if c >= -0.05:
                        continue
                    d = here[0] / -c
                    y = here[1] + d * math.sin(math.radians(h))
                    if d > 30 or abs(y) > geo.HALF_W or min(abs(y - v) for v in geo.S02_DOORS.values()) < 2.4:
                        continue
                    obl = abs(math.degrees(math.acos(min(1.0, -c))))
                    g, f = reads(lanes, s)
                    key = ("wall", bin_of(d, RANGES), bin_of(obl, ANGLES))
                    t[key + ("n",)] += 1
                    t[key + ("g05_" + word(g),)] += 1
                    t[key + ("d01_" + word(f),)] += 1
    lines = ["door_read (eval/probes/door_read.py) on " + args.folders,
             "s02 near-side frames: {0}".format(t[("frames",)]), ""]
    for truth, title in (("open", "TRUE OPEN DOOR: looks, then share read open / closed by g05, and after d01; "
                                  "last pair: open in the strip or a neighbour (g05, d01)"),
                         ("shut", "SHUT DOOR (leaf): looks, then share read open / closed by g05, and after d01"),
                         ("wall", "BLANK DIVIDER WALL (strip centre ray): strips, share read open / closed")):
        lines += [title, "range m | " + " | ".join("{0:>34s}".format("angle " + bin_of(a[0], ANGLES)) for a in ANGLES)]
        for rb in RANGES:
            cells = []
            for ab in ANGLES:
                key = (truth, bin_of(rb[0], RANGES), bin_of(ab[0], ANGLES))
                n = t[key + ("n",)]
                if not n:
                    cells.append("{0:>34s}".format("-"))
                    continue
                pc = lambda k: "{0:3.0f}".format(100.0 * t[key + (k,)] / n)
                s = "{0:4d} g05 {1}/{2} d01 {3}/{4}".format(n, pc("g05_open"), pc("g05_closed"),
                                                           pc("d01_open"), pc("d01_closed"))
                if truth == "open":
                    s += " nb {0}/{1}".format(pc("near_g05_open"), pc("near_d01_open"))
                cells.append("{0:>34s}".format(s))
            lines.append("{0:7s} | ".format(bin_of(rb[0], RANGES)) + " | ".join(cells))
        lines.append("")
    lines.append("2-9 m, by angle: open door read open in its strip or a neighbour (g05, after d01); "
                 "after d01 a shut door read open; blank wall read open (g05, after d01)")
    for ab in ANGLES:
        a = bin_of(ab[0], ANGLES)
        def tot(truth: str, k: str) -> int:
            return sum(t[(truth, bin_of(rb[0], RANGES), a, k)] for rb in RANGES[1:4])
        lines.append("angle {0:6s} open {1}/{4} {2}/{4}, own strip closed by d01 {3}; shut {5}/{6}; wall {7}/{9} {8}/{9}".format(
            a, tot("open", "near_g05_open"), tot("open", "near_d01_open"),
            tot("open", "d01_closed") - tot("open", "g05_closed"), tot("open", "n"),
            tot("shut", "d01_open"), tot("shut", "n"),
            tot("wall", "g05_open"), tot("wall", "d01_open"), tot("wall", "n")))
    lines.append("")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
