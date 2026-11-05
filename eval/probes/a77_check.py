"""R37's manipulation check on flown a77 runs. No model.

    python eval/probes/a77_check.py DIR [DIR ...]     # each DIR holds runs/<site>/<arm>/seedN

Per run, from decisions.jsonl and the memory rebuilt from it (a17k):
- planner.door steps by phase, by what the doorway is (the true open door
  within 2 m; s03: an exit door within 2 m), and the most steps on one label;
- of doorways looked at: a strong read or a close within two steps of the look;
- strong doorways in the memory at the door / elsewhere per step (s02 near side);
- within 4 m of the true open door (s02 near side): door within 45 degrees of
  the heading, waypoint within 30 degrees of the door.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from a73_replay import agents, geo, load, metrics, spatial, switch_step, xy  # noqa: E402

CFG = spatial.config_for(agents.get("a77").features["orchestrator"])
S03_DOORS = {"L": (-6.5, -5.0), "R": (-6.5, 5.0)}


def main() -> int:
    for root in sys.argv[1:]:
        for d in sorted(Path(root).glob("runs/*/*/seed*/decisions.jsonl")):
            run = d.parent
            site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
            rows = [r for r in load(run) if "step" in r]
            met = metrics(run)
            sw = switch_step(met) if arm == "dynamic" else -1
            c = collections.Counter()
            labels = collections.Counter()
            looked = {}
            recs = []
            mems = []
            for r in rows:
                mem = spatial.rebuild(recs, r.get("manifest") or {}, (r.get("perceiver") or {}).get("result"), CFG)
                recs.append(r)
                mems.append({o.label: (o.strong, o.closed, o.passed, o.x, o.y) for o in mem.openings})
            if site.startswith("s02"):
                doors = [(0.0, geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"])]
            else:
                shut = common.s03_shut_side(arm, rows, sw if arm == "dynamic" else None)
                doors = [q for s, q in S03_DOORS.items() if s != shut]
            for i, r in enumerate(rows):
                here = xy(r)
                plan = r.get("planner") or {}
                door = plan.get("door")
                if door:
                    at = (door["x"], door["y"])
                    real = any(spatial.dist(at, q) < 2.0 for q in doors)
                    c["{0}_{1}".format(door["phase"], "door" if real else "other")] += 1
                    labels[(door["label"], door["phase"] == "look")] += 1
                    if door["phase"] == "look":
                        looked.setdefault(door["label"], i)
                if here is None or not site.startswith("s02") or sw is None or r["step"] <= sw or here[0] <= 0.5:
                    continue
                c["near"] += 1
                live = [v for v in mems[i].values() if v[0] and not v[1] and not v[2]]
                c["strong_door"] += any(spatial.dist((v[3], v[4]), doors[0]) < 2.0 for v in live)
                c["strong_else"] += sum(1 for v in live if spatial.dist((v[3], v[4]), doors[0]) >= 2.0)
                if spatial.dist(here[:2], doors[0]) < 4.0:
                    c["at_door"] += 1
                    c["in_view"] += abs(spatial.wrap(spatial.bearing(here[:2], doors[0]) - here[2])) < 45.0
                    wp = plan.get("waypoint")
                    c["wp_toward"] += bool(wp) and abs(spatial.wrap(
                        spatial.bearing(here[:2], (wp[0], wp[1])) - spatial.bearing(here[:2], doors[0]))) < 30.0
            settled = 0
            for label, i in looked.items():
                for m in mems[i + 1:i + 4]:
                    v = m.get(label)
                    if v and (v[0] or v[1]):
                        settled += 1
                        break
            print("{0}/{1}/{2} {3} steps {4} | door steps {5} | most on one label: approach {6} look {7} | "
                  "looked {8} settled {9} | near {10} strong at door {11} elsewhere {12} | "
                  "at door {13} in view {14} wp toward {15}".format(
                      site, arm, seed, "WON" if met.get("goal_reached") else "LOST", len(rows),
                      json.dumps({k: v for k, v in sorted(c.items()) if k.split("_")[0] in ("look", "line", "through")}),
                      max([v for (l, look), v in labels.items() if not look] or [0]),
                      max([v for (l, look), v in labels.items() if look] or [0]),
                      len(looked), settled, c["near"], c["strong_door"], c["strong_else"],
                      c["at_door"], c["in_view"], c["wp_toward"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
