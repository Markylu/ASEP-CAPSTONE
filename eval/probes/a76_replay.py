"""Offline readouts for a76 (R36) on flown runs. No model, CPU only.

Open loop: the drone flew a66's (or a75's) route, so this says which doorway
a76's planner would have laid the waypoint on from where that agent stood, not
where a76 goes. The planner records are chained (each step's record replaced
by the replay's own), so the per-doorway budget is spent as a76 would spend it
on these poses.

1. Where the rule fires. s02 change arms, near side after the switch: steps
   the waypoint is laid on the true open door (a remembered doorway within
   2 m of it), on a doorway elsewhere on the divider (|x| < 1.5 m), or on a
   doorway off the divider; by phase, and split by whether the run was won.
2. At the door. Near-side steps within 4 m of the true open door: the
   waypoint's bearing within 30 degrees of the door's, as recorded and under a76.
3. s03. Steps the rule fires, by the drone's region and by what the doorway
   is: the open exit door, the shut one, or neither (within 2 m of a door).

    python eval/probes/a76_replay.py [--folders final,R32P_repeat_a66,R35_wall_turn_only]
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from a73_replay import REPO_ROOT, agents, geo, load, metrics, planner, run_dirs, spatial, switch_step, xy  # noqa: E402

P76 = agents.PATHFINDER_A76
S03_DOORS = {"L": (-6.5, -5.0), "R": (-6.5, 5.0)}


def chain(rows: List[Dict[str, Any]], cfg: spatial.SpatialConfig) -> List[Dict[str, Any]]:
    out, recs = [], []
    for r in rows:
        man = r.get("manifest") or {}
        here = xy(r)
        mem = spatial.rebuild(recs, man, (r.get("perceiver") or {}).get("result"), cfg)
        gp = (man.get("goal") or {}).get("position")
        plan = None
        if here is not None and gp is not None:
            g = spatial.pose_xyh({"position": gp, "yaw": 0.0})
            plan = planner.pathfind(mem, man, recs, (g[0], g[1]), P76).to_dict()
        recs.append(dict(r, planner=plan))
        out.append({"step": r["step"], "here": here, "plan": plan, "rec": r.get("planner")})
    return out


def toward(here, plan, point) -> bool:
    wp = (plan or {}).get("waypoint")
    return bool(wp) and abs(spatial.wrap(spatial.bearing(here[:2], (wp[0], wp[1]))
                                         - spatial.bearing(here[:2], point))) < 30.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", default="final,R32P_repeat_a66,R35_wall_turn_only")
    ap.add_argument("--out", default=str(REPO_ROOT / "eval/phase2/_probes/a76/replay.txt"))
    args = ap.parse_args()
    tot: Dict[Any, int] = collections.Counter()
    lines = ["a76 replay (open loop; eval/probes/a76_replay.py) on " + args.folders, ""]
    for folder in args.folders.split(","):
        for run in run_dirs(folder):
            site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
            if arm not in ("final", "dynamic"):
                continue
            rows = [r for r in load(run) if "step" in r]
            met = metrics(run)
            won = "won" if met.get("goal_reached") else "lost"
            steps = chain(rows, common.memory_config(rows))
            sw = switch_step(met) if arm == "dynamic" else -1
            c: Dict[str, int] = collections.Counter()
            if site.startswith("s02"):
                door = (0.0, geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"])
                for row in steps:
                    here = row["here"]
                    if here is None or sw is None or row["step"] <= sw or here[0] <= 0.5:
                        continue
                    c["near"] += 1
                    d = (row["plan"] or {}).get("door")
                    if d:
                        at = (d["x"], d["y"])
                        kind = ("real" if spatial.dist(at, door) < 2.0
                                else "divider" if abs(at[0]) < 1.5 else "off_divider")
                        c["fire_" + kind] += 1
                        c["phase_" + kind + "_" + d["phase"]] += 1
                    if spatial.dist(here[:2], door) < 4.0:
                        c["at_door"] += 1
                        c["at_door_rec_toward"] += toward(here, row["rec"], door)
                        c["at_door_a76_toward"] += toward(here, row["plan"], door)
                        c["at_door_fire_real"] += bool(d) and kind == "real"
                for k, v in c.items():
                    tot[("s02", won, k)] += v
                tot[("s02", won, "runs")] += 1
                for kind in ("real", "divider", "off_divider"):
                    tot[("s02", won, "runs_fire_" + kind)] += c["fire_" + kind] > 0
                lines.append("{0:20s} {1:5s} {2:7s} {3} {4:4s} near {5:3d} fires real {6:2d} divider {7:2d} off {8:2d} | "
                             "at door {9:2d}: toward rec {10:2d} a76 {11:2d}".format(
                                 folder[:20], site, arm, seed, won, c["near"], c["fire_real"],
                                 c["fire_divider"], c["fire_off_divider"], c["at_door"],
                                 c["at_door_rec_toward"], c["at_door_a76_toward"]))
            elif site == "s03":
                shut = common.s03_shut_side(arm, rows, sw if arm == "dynamic" else None)
                for row in steps:
                    here = row["here"]
                    if here is None:
                        continue
                    c["steps"] += 1
                    d = (row["plan"] or {}).get("door")
                    if not d:
                        continue
                    at = (d["x"], d["y"])
                    side = next((s for s, q in S03_DOORS.items() if spatial.dist(at, q) < 2.0), None)
                    kind = "neither" if side is None else ("shut_door" if side == shut else "open_door")
                    c["fire_" + kind] += 1
                    c["region_" + common.s03_region(here[:2])] += 1
                for k, v in c.items():
                    tot[("s03", won, k)] += v
                tot[("s03", won, "runs")] += 1
                lines.append("{0:20s} {1:5s} {2:7s} {3} {4:4s} steps {5:3d} fires open door {6:2d} shut door {7:2d} "
                             "neither {8:2d}".format(folder[:20], site, arm, seed, won, c["steps"],
                                                     c["fire_open_door"], c["fire_shut_door"], c["fire_neither"]))
            else:
                continue
            print(lines[-1], flush=True)
    lines.append("")
    for k in sorted(tot, key=str):
        lines.append("{0:5s} {1:5s} {2:32s} {3}".format(k[0], k[1], k[2], tot[k]))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-80:]))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
