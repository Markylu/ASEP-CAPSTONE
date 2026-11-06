"""R39 manipulation check in flight: a79's own runs against the limits in
eval/phase2/R39_confined_latch/README.md. No model.

Per run: outcome; the step the door switched; the step the latch fired, its
axis and mouth; the step the drone was first out past the mouth; steps in the
s03 shut tine before and after the latch; latched steps with "toward your
target" on the turn-around (the sentence), and how many of those took it; the
s02 crossing; the share of steps with a route.

    python eval/probes/a79_check.py <runs dir> [<runs dir> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import dead_end_trigger as trigger  # noqa: E402
from common import load, metrics, switch_step, xy  # noqa: E402


def check_run(run: Path) -> Dict[str, Any]:
    site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
    rows = [r for r in load(run) if r.get("manifest")]
    met = metrics(run)
    sw = switch_step(met)
    shut = trigger.shut_tine(arm, run, rows, sw) if site == "s03" else None
    out: Dict[str, Any] = {"run": "{0}/{1}/{2}".format(site, arm, seed),
                           "won": bool(met.get("goal_reached")), "steps": len(rows),
                           "switch": sw, "latch": None, "axis": None, "mouth": None,
                           "out": None, "tine_before": 0, "tine_after": 0, "said": 0,
                           "took": 0, "crossed": None, "routed": 0, "open_tine": 0}
    for r in rows:
        here = xy(r)
        if here is None:
            continue
        step = r["step"]
        plan = r.get("planner") or {}
        out["routed"] += plan.get("fallback") == "none"
        latch = plan.get("latch")
        if latch and out["latch"] is None:
            out["latch"] = latch["step"]
            out["axis"] = latch["axis_deg"]
            out["mouth"] = latch["origin"]
        if latch and latch.get("out") and out["out"] is None:
            out["out"] = step
        if out["crossed"] is None and here[0] < (-7.0 if site == "s03" else 0.0):
            out["crossed"] = step
        if site == "s03":
            region = common.s03_region(here[:2])
            after_shut = arm == "final" or (sw is not None and step >= sw)
            if shut is not None and region == shut and after_shut:
                out["tine_after" if out["latch"] is not None else "tine_before"] += 1
            if region in ("tine_L", "tine_R") and region != shut:
                out["open_tine"] += 1
        if r.get("route_behind"):
            out["said"] += 1
            actions = {a["index"]: a for a in r["manifest"].get("actions") or []}
            out["took"] += bool(actions.get(r.get("index"), {}).get("turn_around"))
    return out


def main() -> int:
    runs: List[Path] = []
    for root in sys.argv[1:]:
        runs += [d.parent for d in sorted(Path(root).glob("**/decisions.jsonl"))]
    show = trigger.show
    print("run                  | won | steps | switch | latch | axis  | mouth          | out | "
          "shut tine before/after latch | open tine | sentence took/said | crossed | route")
    for run in runs:
        o = check_run(run)
        print("{0:20s} | {1:3s} | {2:5d} | {3:>6s} | {4:>5s} | {5:>5s} | {6:14s} | {7:>3s} | "
              "{8:>3d} / {9:<3d}                    | {10:>9d} | {11:>3d} / {12:<3d}          | "
              "{13:>7s} | {14}/{15}".format(
                  o["run"], "yes" if o["won"] else "no", o["steps"], show(o["switch"]),
                  show(o["latch"]), show(o["axis"]), show(o["mouth"]), show(o["out"]),
                  o["tine_before"], o["tine_after"], o["open_tine"], o["took"], o["said"],
                  show(o["crossed"]), o["routed"], o["steps"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
