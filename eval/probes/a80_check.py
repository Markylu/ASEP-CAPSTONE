"""R40 manipulation check in flight: a80's own runs against the limits in
eval/phase2/R40_wall_survey/README.md. No model.

Per run: outcome; the step the survey started and the side it took first;
steps in each phase (transit, look, through); frames taken square to the
wall; whether the wall's range became known; the step the survey ended and
how (through the wall, stations used up, budget); the s02 crossing; the share
of steps with a route.

    python eval/probes/a80_check.py <runs dir> [<runs dir> ...]
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dead_end_trigger as trigger  # noqa: E402
from common import load, metrics, switch_step, xy  # noqa: E402


def check_run(run: Path) -> Dict[str, Any]:
    site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
    rows = [r for r in load(run) if r.get("manifest")]
    met = metrics(run)
    out: Dict[str, Any] = {"run": "{0}/{1}/{2}".format(site, arm, seed),
                           "won": bool(met.get("goal_reached")), "steps": len(rows),
                           "switch": switch_step(met), "start": None, "order": None,
                           "phases": collections.Counter(), "seq": [], "looks": 0, "wall": None,
                           "ended": None, "crossed": None, "routed": 0, "rays": 0}
    last = None
    for r in rows:
        here = xy(r)
        if here is None:
            continue
        step = r["step"]
        plan = r.get("planner") or {}
        out["routed"] += plan.get("fallback") == "none"
        if out["crossed"] is None and here[0] < (-7.0 if site == "s03" else 0.0):
            out["crossed"] = step
        sv = plan.get("survey")
        if not sv:
            continue
        if out["start"] is None:
            out["start"], out["order"] = sv["step"], sv["order"]
        tag = "{0}{1}".format(sv["phase"], sv["i"])
        if tag != last:
            out["seq"].append("{0}@{1}".format(tag, step))
            last = tag
        if sv["phase"] == "done":
            if out["ended"] is None:
                out["ended"] = step
            continue
        out["phases"][sv["phase"]] += 1
        out["looks"], out["wall"] = sv["looks"], sv.get("wall")
        out["rays"] = max(out["rays"], len(sv.get("rays") or []))
    return out


def main() -> int:
    runs: List[Path] = []
    for root in sys.argv[1:]:
        runs += [d.parent for d in sorted(Path(root).glob("**/decisions.jsonl"))]
    show = trigger.show
    print("run                  | won | steps | switch | start | order        | transit look through | "
          "square looks | wall  | ended | crossed | route | phases")
    for run in runs:
        o = check_run(run)
        print("{0:20s} | {1:3s} | {2:5d} | {3:>6s} | {4:>5s} | {5:12s} | {6:>7d} {7:>4d} {8:>7d} | "
              "{9:>12d} | {10:>5s} | {11:>5s} | {12:>7s} | {13}/{14} | {15}".format(
                  o["run"], "yes" if o["won"] else "no", o["steps"], show(o["switch"]),
                  show(o["start"]), show(o["order"]), o["phases"]["transit"], o["phases"]["look"],
                  o["phases"]["through"], o["looks"], show(o["wall"]), show(o["ended"]),
                  show(o["crossed"]), o["routed"], o["steps"], " ".join(o["seq"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
