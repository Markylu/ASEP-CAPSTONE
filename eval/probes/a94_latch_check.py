"""a94's latch trigger on flown records, gated as in flight. No model.

confined_trigger.py run open loop over every step; in flight the latch cannot
fire while the wall survey runs (a86, after_survey), so this copy skips the
steps whose planner record carries a survey not yet done. Otherwise the same
script: --agent a93 is the trigger a93 flies, --agent a94 the one with one
square closed read (reads 1) and the corridor drifted into without a turn
(planner._from_line). eval/phase2/R56_latch_line/README.md.

    python eval/probes/a94_latch_check.py --agent a94 --folders R44_survey_latch_fixed,...,R55_h100_a89 --runs
"""
from __future__ import annotations

import argparse
import collections
import itertools
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import dead_end_trigger as trigger  # noqa: E402
from common import REPO_ROOT, load, metrics, spatial, switch_step, xy  # noqa: E402
from server.decider import agent as agents, planner  # noqa: E402

FOLDERS = "final,R32P_repeat_a66,R35_wall_turn_only"
#: Every site's goal, map coordinates (a86's rule reads the direct line to it).
GOAL = (-12.0, 0.0)


def read_run(run: Path) -> Dict[str, Any]:
    """The run's trail, its closed-door reads in the centre strips, and where
    the drone stood on every step (evaluation only)."""
    site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
    rows = [r for r in load(run) if r.get("manifest")]
    met = metrics(run)
    sw = switch_step(met)
    shut = trigger.shut_tine(arm, run, rows, sw) if site == "s03" else None
    trail: List[Tuple[int, float, float, float]] = []
    closed: List[int] = []
    crossed = None
    region: Dict[int, str] = {}
    for r in rows:
        here = xy(r)
        if here is None:
            continue
        step = r["step"]
        trail.append((step, here[0], here[1], here[2]))
        if crossed is None and here[0] < (-7.0 if site == "s03" else 0.0):
            crossed = step
        region[step] = common.s03_region(here[:2]) if site == "s03" else "s02"
        lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
        if any(l.get("doorway") == "closed" and l.get("strip") in spatial.CENTRAL_STRIPS
               for l in lanes):
            closed.append(step)
    surveying = {r["step"] for r in rows if ((r.get("planner") or {}).get("survey") or {}).get("phase") not in (None, "done")}
    return {"surveying": surveying, "site": site, "arm": arm, "seed": seed, "won": bool(met.get("goal_reached")),
            "steps": len(rows), "switch": sw, "shut": shut, "crossed": crossed,
            "trail": trail, "closed": closed, "region": region}


def first_fire(info: Dict[str, Any], d: Dict[str, Any]) -> Optional[Tuple[int, Dict[str, Any]]]:
    """The first step planner.confined_run fires at, and the run it names."""
    trail, closed = info["trail"], info["closed"]
    if not closed:
        return None
    for i, (step, x, y, h) in enumerate(trail):
        if step < closed[0] or step in info["surveying"]:
            continue  # gated as in flight: no latch while the survey runs
        found = planner.confined_run(trail[:i + 1], [s for s in closed if s <= step],
                                     (x, y, h), step, d, GOAL)
        if found is not None:
            began, since, axis, run = found
            return step, {"began": began, "since": since, "axis": axis, "run": run}
    return None


def tally(infos: List[Dict[str, Any]], d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = collections.Counter()
    left: List[int] = []
    rows = []
    for info in infos:
        hit = first_fire(info, d)
        fired = hit[0] if hit else None
        site, arm = info["site"], info["arm"]
        before = fired is not None and (info["crossed"] is None or fired < info["crossed"])
        where = info["region"].get(fired) if fired is not None else None
        if arm == "initial":
            out["initial"] += 1
            out["initial_fired"] += fired is not None
        elif site == "s03":
            key = "s03_" + arm
            out[key] += 1
            right = fired is not None and where == info["shut"]
            out[key + "_right"] += right
            out[key + "_wrong"] += fired is not None and not right
            if arm == "dynamic" and right:
                left.append(60 - fired)
                out["s03_dynamic_25"] += 60 - fired >= 25
            if arm == "final" and info["won"]:
                out["s03_final_won_fired"] += before
        else:
            key = "s02_won" if info["won"] else "s02_lost"
            out[key] += 1
            out[key + "_fired"] += before
        rows.append((info, fired, where, hit[1] if hit else None))
    out["left_median"] = int(statistics.median(left)) if left else None
    out["rows"] = rows
    return out


def line(d: Dict[str, Any], t: Dict[str, Any]) -> str:
    c = d["confined"]
    return ("half {0:.1f} dwell {1} facing {2:.0f} reads {3} | s03 dyn right {4}/{5} (25+ left: "
            "{6}, median left {7}) wrong {8} | s03 final right {9}/{10} wrong {11} won-fired {12} | "
            "s02 won {13}/{14} lost {15}/{16} | initial {17}/{18}").format(
                c["half_m"], c["dwell_steps"], c["facing_deg"], c["reads"],
                t["s03_dynamic_right"], t["s03_dynamic"], t["s03_dynamic_25"], t["left_median"],
                t["s03_dynamic_wrong"], t["s03_final_right"], t["s03_final"], t["s03_final_wrong"],
                t["s03_final_won_fired"], t["s02_won_fired"], t["s02_won"], t["s02_lost_fired"],
                t["s02_lost"], t["initial_fired"], t["initial"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", default=FOLDERS)
    ap.add_argument("--agent", default="a79")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--runs", action="store_true", help="list every run")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    infos = [dict(read_run(run), folder=folder.split("_", 1)[0])
             for folder in args.folders.split(",") for run in trigger.run_dirs(folder)]
    base = dict(agents.get(args.agent).features["orchestrator"]["pathfinder"]["dead_end_latch"])
    lines = ["Confined-lane trigger on {0} runs of {1} (eval/probes/confined_trigger.py)".format(
        len(infos), args.folders), ""]
    if args.sweep:
        for half, dwell, facing, reads in itertools.product(
                (1.2, 1.5, 1.8, 2.1), (3, 4, 5, 6), (45.0,), (1, 2)):
            d = dict(base, confined=dict(base["confined"], half_m=half, dwell_steps=dwell,
                                         facing_deg=facing, reads=reads))
            lines.append(line(d, tally(infos, d)))
    else:
        t = tally(infos, base)
        lines.append(line(base, t))
        if args.runs:
            lines.append("")
            for info, fired, where, hit in t["rows"]:
                if info["arm"] == "initial" and fired is None:
                    continue
                lines.append("{0:5s} {1:6s} {2:8s} {3:6s} won {4:3s} switch {5:>3s} crossed {6:>3s} "
                             "closed {7:>3s} fired {8:>3s} in {9} {10}".format(
                                 info["folder"], info["site"], info["arm"], info["seed"],
                                 "yes" if info["won"] else "no", trigger.show(info["switch"]),
                                 trigger.show(info["crossed"]),
                                 trigger.show(info["closed"][0] if info["closed"] else None),
                                 trigger.show(fired), where,
                                 "" if hit is None else "run {0:.1f} m axis {1:.0f} since {2}".format(
                                     hit["run"], hit["axis"], hit["since"])))
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
