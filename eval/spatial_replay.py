"""Rebuild the a13 spatial memory from recorded runs, check it, and draw it.

The memory (server/decider/spatial.py) is a pure function of decisions.jsonl,
so any recorded run can be replayed into it, including runs flown by agents
that never had it (they simply have no perceiver reports: visits and blocked
moves only). This script is evaluation: it may read the manifest's goal
ground truth to score the goal belief. The agent never does.

    python eval/spatial_replay.py check eval/phase2/R7_comparison_lines/runs
    python eval/spatial_replay.py draw  eval/phase2/R7_comparison_lines/runs/s03/final/seed1 \\
        --out /tmp/s03.png [--step 40]

`check` reports, per run:
- blocked / short moves found by the memory against the R7 comparison lines'
  own count (prompt.BLOCKED_BELOW_M, SHORT_BELOW_M), which must agree;
- landing error: where the fan says a full move ends against where the next
  decision was, for moves that were not blocked (mean should be well under a
  cell; wall slides make the max larger);
- for runs with perceiver reports (a13 on), goal-belief error in metres at the
  last step, how many picks carried "blocked here before", and how often the
  critic and the strategist were called.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from server.decider import prompt as prompts, spatial  # noqa: E402


def load(run: Path) -> List[Dict[str, Any]]:
    path = run / "decisions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return sorted((r for r in rows if "step" in r), key=lambda r: r["step"])


def runs_under(root: Path) -> List[Path]:
    return sorted(p.parent for p in root.rglob("decisions.jsonl") if "_attempts" not in p.parts)


def true_goal(rows: List[Dict[str, Any]]) -> Optional[spatial.Point]:
    """Evaluation only: the goal's map position from the manifest."""
    for r in rows:
        goal = (r.get("manifest") or {}).get("goal") or {}
        if goal.get("position"):
            x, _, z = goal["position"]
            return float(x), -float(z)
    return None


def memory_at(rows: List[Dict[str, Any]], k: int) -> spatial.SpatialMemory:
    """The memory the agent had at rows[k], with that step's own perception."""
    r = rows[k]
    return spatial.rebuild(rows[:k], r["manifest"], (r.get("perceiver") or {}).get("result"))


def label(run: Path) -> str:
    return "/".join(run.parts[-3:])


def check_run(run: Path) -> Dict[str, Any]:
    rows = load(run)
    mem = memory_at(rows, len(rows) - 1)
    lines_blocked = lines_short = 0
    errors: List[float] = []
    for a, b in zip(rows, rows[1:]):
        if a.get("index") is None:
            continue
        chosen = next((x for x in a["manifest"]["actions"] if x["index"] == a["index"]), None)
        pa = spatial.pose_xyh(a["manifest"].get("pose"))
        pb = spatial.pose_xyh(b["manifest"].get("pose"))
        if chosen is None or chosen.get("turn_around") or pa is None or pb is None:
            continue
        moved = spatial.dist(pa[:2], pb[:2])
        lines_blocked += moved < prompts.BLOCKED_BELOW_M
        lines_short += prompts.BLOCKED_BELOW_M <= moved < prompts.SHORT_BELOW_M
        if moved >= prompts.SHORT_BELOW_M:
            land = spatial.ahead(pa[:2], spatial.action_heading(chosen, pa[2]),
                                 float(chosen.get("r") or 1.7))
            errors.append(spatial.dist(land, pb[:2]))
    out: Dict[str, Any] = {
        "run": label(run),
        "steps": len(rows),
        "blocked": sum(b.kind == "blocked" for b in mem.blocks),
        "short": sum(b.kind == "short" for b in mem.blocks),
        "lines_blocked": lines_blocked,
        "lines_short": lines_short,
        "landing_mean_m": round(sum(errors) / len(errors), 2) if errors else None,
        "landing_max_m": round(max(errors), 2) if errors else None,
        "cells_visited": len(mem.visits),
        "loop_score": round(mem.loop_score(), 2),
    }
    if any(r.get("perceiver") for r in rows):
        truth = true_goal(rows)
        belief = mem.goal_belief()
        out["goal_belief_err_m"] = (round(spatial.dist(truth, belief[:2]), 1)
                                    if truth and belief else None)
        out["picks_tagged_blocked"] = sum(
            1 for r in rows if r.get("index") is not None and any(
                t.startswith("blocked") for t in (r.get("tags") or {}).get(str(r["index"]), [])))
        out["critic_calls"] = sum(1 for r in rows if r.get("critic"))
        out["strategist_calls"] = sum(1 for r in rows if r.get("strategist"))
    return out


def cmd_check(args: argparse.Namespace) -> int:
    bad = 0
    for run in runs_under(Path(args.root).resolve()):
        row = check_run(run)
        agree = row["blocked"] == row["lines_blocked"] and row["short"] == row["lines_short"]
        bad += not agree
        print(json.dumps(row) + ("" if agree else "   <-- memory disagrees with the R7 lines"))
    print("runs disagreeing with the R7 lines: {0}".format(bad))
    return 1 if bad else 0


def _strip_ok(r: Dict[str, Any]) -> Optional[bool]:
    """Evaluation only: the perceiver's goal strip within one of the truth, on a
    frame where the goal is in view; None when it is not in view."""
    import math
    goal = (r.get("manifest") or {}).get("goal") or {}
    b = float(goal.get("bearing_deg", 180.0))
    half = spatial.FOV_DEG / 2.0
    if not goal.get("line_of_sight") or abs(b) > half:
        return None
    got = ((r.get("perceiver") or {}).get("result") or {}).get("goal")
    if got not in spatial.STRIPS:
        return False
    u = math.tan(math.radians(b)) / math.tan(math.radians(half))
    truth = next((i for i, e in enumerate((0.6, 0.2, -0.2, -0.6)) if u > e), 4)
    return abs(spatial.STRIPS.index(got) - truth) <= 1


def _picked_turn_around(r: Dict[str, Any]) -> bool:
    actions = (r.get("manifest") or {}).get("actions") or []
    return any(a.get("index") == r.get("index") and a.get("turn_around") for a in actions)


#: A strategist's target is goal-ward when its point is at least this much
#: nearer the true goal than the drone is. With no margin, q01's answers in R9
#: already scored 60% (most of the map is nearer a far goal); with 3 m, 35%.
GOALWARD_M = 3.0


def goal_gain(here: spatial.Point, target: spatial.Point, goal: spatial.Point) -> float:
    """How much nearer the goal the target is than the drone, in metres."""
    return spatial.dist(here, goal) - spatial.dist(target, goal)


def goalward(r: Dict[str, Any]) -> Optional[bool]:
    """Evaluation only: whether a strategist call chose a target at least
    GOALWARD_M nearer the true goal than the drone is. The goal entry counts by
    where it was placed (a13: the estimate; a14: the true position), and
    "explore" is never goal-ward. None for a call with no answer."""
    plan = r.get("strategist") or {}
    chosen = (plan.get("result") or {}).get("target")
    if chosen is None:
        return None
    goal = true_goal([r])
    here = spatial.pose_xyh((r.get("manifest") or {}).get("pose"))
    t = next((m for m in plan.get("menu") or [] if m.get("id") == chosen), None)
    if goal is None or here is None or t is None:
        return False
    return goal_gain(here[:2], (t["x"], t["y"]), goal) >= GOALWARD_M


def _goalward(rows: List[Dict[str, Any]]) -> str:
    calls = [g for g in (goalward(r) for r in rows if r.get("strategist")) if g is not None]
    return "{0}/{1}".format(sum(calls), len(calls))


def manip_run(run: Path) -> Dict[str, Any]:
    """R9 manipulation-check counts for one a13 run (R10: and a14)."""
    from collections import Counter
    rows = load(run)
    decided = [r for r in rows if r.get("index") is not None]
    poses = [spatial.pose_xyh((r.get("manifest") or {}).get("pose")) for r in rows]
    revisits = sum(1 for k, p in enumerate(poses) if p is not None and any(
        q is not None and spatial.dist(p[:2], q[:2]) < 1.0 for q in poses[:max(0, k - 4)]))
    in_view = [ok for ok in (_strip_ok(r) for r in rows) if ok is not None]
    out_view = [r for r in rows if _strip_ok(r) is None and r.get("perceiver")]
    phantom = sum(1 for r in out_view
                  if ((r["perceiver"].get("result") or {}).get("goal") in spatial.STRIPS))
    metrics = {}
    if (run / "metrics.json").is_file():
        metrics = json.loads((run / "metrics.json").read_text())
    final = check_run(run)
    return {
        "run": label(run),
        "steps": len(rows),
        "reached": metrics.get("goal_reached"),
        "collisions": metrics.get("collisions"),
        "tags_delivered": sum(1 for r in decided if r.get("tags")),
        "picks_tagged_blocked": final.get("picks_tagged_blocked", 0),
        "critic": sum(1 for r in rows if r.get("critic")),
        "critic_changed": sum(1 for r in rows if (r.get("critic") or {}).get("changed")),
        "strategist": sum(1 for r in rows if r.get("strategist")),
        "triggers": dict(Counter((r.get("strategist") or {}).get("trigger")
                                 for r in rows if r.get("strategist"))),
        "modes": dict(Counter(r.get("mode") for r in decided)),
        "perceiver_failed": sum(1 for r in rows if r.get("perceiver")
                                and r["perceiver"].get("result") is None),
        "goal_strip_ok": "{0}/{1}".format(sum(in_view), len(in_view)),
        "phantom": "{0}/{1}".format(phantom, len(out_view)),
        "goal_belief_err_m": final.get("goal_belief_err_m"),
        # R10 (a14): the turn rule, and what the strategist steered by.
        "turn_hidden": sum(1 for r in decided if r.get("hidden")),
        "turn_arounds": sum(1 for r in decided if _picked_turn_around(r)),
        "no_target": sum(1 for r in decided if not r.get("target")),
        "target_kinds": dict(Counter((r.get("target") or {}).get("kind", "none")
                                     for r in decided)),
        "strategist_goalward": _goalward(rows),
        "revisit_rate": round(revisits / len(rows), 2) if rows else None,
        "step_latency_ms_mean": round(sum(r.get("step_latency_ms") or 0 for r in rows)
                                      / len(rows), 1) if rows else None,
    }


def cmd_manip(args: argparse.Namespace) -> int:
    for run in runs_under(Path(args.root).resolve()):
        print(json.dumps(manip_run(run)))
    return 0


def cmd_draw(args: argparse.Namespace) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    run = Path(args.run).resolve()
    rows = load(run)
    k = len(rows) - 1 if args.step is None else next(
        i for i, r in enumerate(rows) if r["step"] == args.step)
    mem = memory_at(rows, k)
    c = spatial.CELL_M
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for cells, colour in ((mem.free, "#d9ecd9"), (mem.wall, "#555555")):
        for (i, j) in cells:
            ax.add_patch(Rectangle((i * c, j * c), c, c, color=colour, lw=0))
    for (i, j), steps in mem.visits.items():
        ax.add_patch(Rectangle((i * c, j * c), c, c, color="#9ec5e8",
                                   alpha=min(1.0, 0.25 * len(steps)), lw=0))
    xs = [x for _, x, _, _ in mem.trail]
    ys = [y for _, _, y, _ in mem.trail]
    ax.plot(xs, ys, "-", color="#1f4e79", lw=1)
    ax.plot(xs[-1:], ys[-1:], "o", color="#1f4e79")
    for b in mem.blocks:
        tip = spatial.ahead((b.x, b.y), b.heading, 0.8)
        ax.plot([b.x, tip[0]], [b.y, tip[1]], "-", lw=2,
                color="#c00000" if b.kind == "blocked" else "#e69500")
    for r in mem.goal_rays:
        tip = spatial.ahead((r.x, r.y), r.heading, spatial.GOAL_RANGE_M.get(r.range, 10.0))
        ax.plot([r.x, tip[0]], [r.y, tip[1]], "-", lw=0.6, color="#d04040", alpha=0.5)
    belief = mem.goal_belief()
    if belief:
        ax.plot([belief[0]], [belief[1]], "x", color="#d04040", ms=10, mew=2,
                label="goal belief")
    for o in mem.openings:
        ax.plot([o.x], [o.y], "s", ms=7, mfc="none",
                mec="#888888" if o.closed else ("#9ec5e8" if o.passed else "#2e8b57"))
        ax.annotate(o.label, (o.x, o.y), fontsize=7, xytext=(3, 3), textcoords="offset points")
    truth = true_goal(rows)
    if truth:
        ax.plot([truth[0]], [truth[1]], "*", color="#d04040", ms=12,
                label="goal (truth, eval only)")
    target = spatial.Target.from_dict(rows[k].get("target"))
    if target:
        ax.plot([target.x], [target.y], "D", color="#7a3db8", ms=7,
                label="target: " + target.id)
    ax.set_xlim(-25, 25)
    ax.set_ylim(-12.5, 12.5)
    ax.set_aspect("equal")
    ax.set_title("{0}  step {1}".format(label(run), rows[k]["step"]))
    ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    fig.savefig(args.out, dpi=110)
    print(args.out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="rebuild every run under ROOT and check the memory")
    c.add_argument("root")
    m = sub.add_parser("manip", help="R9 manipulation-check counts for every a13 run under ROOT")
    m.add_argument("root")
    d = sub.add_parser("draw", help="draw one run's memory as a top-down map")
    d.add_argument("run")
    d.add_argument("--out", required=True)
    d.add_argument("--step", type=int)
    args = parser.parse_args()
    return {"check": cmd_check, "manip": cmd_manip, "draw": cmd_draw}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
