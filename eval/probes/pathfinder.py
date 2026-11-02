"""Offline probe for a63's route planner (R30). No model calls, CPU only.

For every recorded step of the given rounds, the memory is rebuilt as a63
would build it (spatial.rebuild with A17D, from that run's own records and
perception), planner.pathfind runs on it, and the route is scored against the
site geometry (eval/probes/common.py, R11's geo.py) with the door state the
run actually had. Open loop: the drone flew a49's route, so this says where
a63 would have steered from the places a49 stood, not where a63 goes.

Readouts and gates: eval/phase2/_probes/pathfinder/README.md, written before
this script runs.

    python eval/probes/pathfinder.py run --first 20 --last 26           # tuning set
    python eval/probes/pathfinder.py run --first 27 --last 29 --tag held --append
    python eval/probes/pathfinder.py score [--tag held]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import PROBES, geo, load, metrics, runs, spatial  # noqa: E402
from server.decider import agent as agents, planner  # noqa: E402

OUT = PROBES / "pathfinder"
P = agents.PATHFINDER_A63
CELL = spatial.CELL_M
#: The s03 stem mouth and the s02 door x, in map coordinates.
STEM_MOUTH = (15.0, 0.0)
DOOR_X = 0.0


class TruthMap:
    """A cost map from the site geometry, for the true shortest route."""

    def __init__(self, free) -> None:
        self.free = free
        self.box = (int(math.floor(geo.X_MIN / CELL)) - 1, int(math.floor(geo.X_MAX / CELL)) + 1,
                    int(math.floor(-geo.HALF_W / CELL)) - 1, int(math.floor(geo.HALF_W / CELL)) + 1)

    def cost(self, c: Tuple[int, int]) -> Optional[float]:
        x, y = (c[0] + 0.5) * CELL, (c[1] + 0.5) * CELL
        return 1.0 if self.free(x, y) else None

    def inside(self, c: Tuple[int, int]) -> bool:
        x0, x1, y0, y1 = self.box
        return x0 <= c[0] <= x1 and y0 <= c[1] <= y1


class Both:
    """a63's cost map restricted to truly free cells: a route here is one the
    drone's map allows and the site allows."""

    def __init__(self, cm: spatial.CostMap, truth: TruthMap) -> None:
        self.cm, self.truth = cm, truth

    def cost(self, c: Tuple[int, int]) -> Optional[float]:
        a = self.cm.cost(c)
        return None if a is None or self.truth.cost(c) is None else a

    def inside(self, c: Tuple[int, int]) -> bool:
        return self.truth.inside(c)


def open_door_y(site: str, changed: bool) -> Optional[float]:
    if not site.startswith("s02"):
        return None
    if not changed:
        return geo.S02_DOORS["B"]
    return geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"]


def ray_passes(here: spatial.Point, wp: spatial.Point, target: spatial.Point,
               within_m: float) -> bool:
    """Whether the ray from here through wp passes within within_m of target,
    with target ahead along it."""
    d = spatial.dist(here, wp)
    if d < 1e-6:
        return False
    ux, uy = (wp[0] - here[0]) / d, (wp[1] - here[1]) / d
    t = (target[0] - here[0]) * ux + (target[1] - here[1]) * uy
    if t <= 0:
        return False
    off = math.hypot(here[0] + t * ux - target[0], here[1] + t * uy - target[1])
    return off <= within_m


def toward_index(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
                 perception: Optional[Dict[str, Any]], target: spatial.Target) -> Optional[int]:
    tags = spatial.project(mem, manifest, perception, target)
    return next((i for i, words in tags.items() if spatial.WORDS["toward_target"] in words),
                None)


def recorded_toward(rec: Dict[str, Any]) -> Optional[int]:
    tags = rec.get("tags") or {}
    return next((int(i) for i, words in tags.items()
                 if spatial.WORDS["toward_target"] in words), None)


def run_dir(run: Dict[str, Any]) -> Path:
    """The run's folder: the lane copy where it exists, else the repo's."""
    if Path(run["path"]).exists():
        return Path(run["path"])
    return (common.REPO_ROOT / "eval" / "phase2" / run["folder"] / "runs" / run["site"]
            / run["arm"] / run["seed"])


def all_runs(first: int, last: int) -> List[Dict[str, Any]]:
    """The lane index's runs plus any round the index predates (R27 on),
    found under the repo's eval/phase2."""
    out = list(runs(first, last))
    have = {(r["folder"], r["site"], r["arm"], r["seed"]) for r in out}
    for d in sorted((common.REPO_ROOT / "eval" / "phase2").glob(
            "R*/runs/*/*/seed*/decisions.jsonl")):
        run = d.parent
        row = {"folder": run.parts[-5], "round": common.round_id(run.parts[-5]),
               "site": run.parts[-3], "arm": run.parts[-2], "seed": run.parts[-1], "path": run}
        n = common.round_number(row["round"])
        if n is not None and first <= n <= last and (
                row["folder"], row["site"], row["arm"], row["seed"]) not in have:
            out.append(row)
    return sorted(out, key=lambda r: (r["folder"], r["site"], r["arm"]))


def score_run(run: Dict[str, Any], tag: str) -> List[Dict[str, Any]]:
    path = run_dir(run)
    if not (path / "decisions.jsonl").exists():
        return []
    rows = load(path)
    met = metrics(path)
    site, arm = run["site"], run["arm"]
    sw = common.switch_step(met)
    solved = common.solved_step(rows, met)
    goal = common.true_goal(rows)
    if goal is None:
        return []
    shut = common.s03_shut_side(arm, rows, sw) if site == "s03" else None
    first_closed = next((r["step"] for r in rows
                         if "closed" in (((r.get("door_confirmer") or {}).get("result") or {})
                                         .values())), None)
    out = []
    for k, r in enumerate(rows):
        here = common.xy(r)
        if here is None:
            continue
        step = r["step"]
        perception = (r.get("perceiver") or {}).get("result")
        mem = spatial.rebuild(rows[:k], r["manifest"], perception, spatial.A17D)
        plan = planner.pathfind(mem, r["manifest"], rows[:k], goal, P)
        key = common.world_key(site, arm, step, rows, met)
        free = common.world(site, arm, step, rows, met)
        truth = TruthMap(free)
        start, end = spatial.cell(here[:2]), spatial.cell(goal)
        true_path = planner.astar(truth, start, end, max_nodes=200000)
        cm = spatial.CostMap(mem, planner.stall_cells_from(rows[:k], step), P,
                             include=(start, end))
        sealed_true = (true_path is not None
                       and any(cm.cost(c) is None for c in true_path[1:-1]))
        # Added after the first run (README, tuning log): the true shortest
        # route hugs corners, so a corner cell next to a seen wall counts as
        # "sealed" while a route a cell over is open. What matters: is there
        # any true route left on a63's map, and does a63's route rely on
        # unknown ground that is in truth wall.
        both = Both(cm, truth)
        no_route = true_path is not None and planner.astar(both, start, end, max_nodes=200000) is None
        punches = any(truth.cost(c) is None for c in plan.path[1:-1])
        wp = plan.waypoint
        row: Dict[str, Any] = {
            "tag": tag, "round": run["round"], "site": site, "arm": arm, "step": step,
            "x": round(here[0], 2), "y": round(here[1], 2), "solved": solved is not None,
            "fallback": plan.fallback, "path_m": plan.path_m,
            "true_path_m": (round(sum(spatial.dist(planner._centre(a), planner._centre(b))
                                      for a, b in zip(true_path, true_path[1:])), 2)
                            if true_path else None),
            "sealed_true_path": sealed_true,
            "no_true_route": no_route, "punches": punches,
            "wp": [round(wp[0], 2), round(wp[1], 2)] if wp else None,
            "region": common.s03_region(here[:2]) if site == "s03" else None,
        }
        # Route agreement: the true route a few cells on, and the waypoint bearing.
        if true_path and len(true_path) > 1 and wp:
            want = spatial.bearing(here[:2], planner._centre(true_path[min(3, len(true_path) - 1)]))
            row["bearing_err"] = round(abs(spatial.wrap(spatial.bearing(here[:2], wp) - want)), 1)
        # s03: the shut tine after the door was confirmed closed, and the lobby.
        if site == "s03" and wp:
            region = row["region"]
            in_shut = (shut is not None and region == "tine_" + shut and here[0] < -3.0
                       and first_closed is not None and step > first_closed)
            row["shut_tine"] = in_shut
            if in_shut:
                row["exits"] = wp[0] > here[0] + 0.3
                # 1b (added after the first run): never toward the sealed exit.
                row["not_to_exit"] = wp[0] >= here[0] - 0.3
            if region == "lobby":
                row["lobby"] = True
                row["to_mouth"] = ray_passes(here[:2], wp, STEM_MOUTH, 2.0) or (
                    wp[0] < 15.0 and abs(wp[1]) <= 1.5)
        # s02: within 4 m of the open door on the near side.
        yd = open_door_y(site, bool(key[1]))
        if yd is not None and here[0] > 0.5 and spatial.dist(here[:2], (DOOR_X, yd)) <= 4.0:
            row["near_door"] = True
            cross = next((c for c in plan.path if c[0] < 0), None)
            if cross is not None:
                cy = (cross[1] + 0.5) * CELL
                row["crosses_gap"] = abs(cy - yd) < geo.DOOR_HALF + CELL / 2.0
            else:
                row["crosses_gap"] = False
        # initial safety: a63's "toward" against the pick a49 made and its own tag.
        if run["round"] == "R25D" and r.get("index") is not None:
            row["pick"] = r["index"]
            row["toward_a63"] = toward_index(mem, r["manifest"], perception, plan.target)
            row["toward_a49"] = recorded_toward(r)
        out.append(row)
    return out


def cmd_run(args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "steps.jsonl"
    mode = "a" if args.append else "w"
    n = 0
    with out_path.open(mode) as fh:
        for run in all_runs(args.first, args.last):
            rows = score_run(run, args.tag)
            for row in rows:
                fh.write(json.dumps(row) + "\n")
            n += len(rows)
            print("{0} {1}/{2}: {3} steps".format(run["round"], run["site"], run["arm"],
                                                  len(rows)))
    print("wrote {0} steps to {1}".format(n, out_path))
    return 0


def rate(rows: List[Dict[str, Any]], key: str) -> Tuple[int, int, float]:
    n = sum(1 for r in rows if key in r)
    k = sum(1 for r in rows if r.get(key))
    return k, n, (100.0 * k / n if n else float("nan"))


def cmd_score(args: argparse.Namespace) -> int:
    rows = [json.loads(l) for l in (OUT / "steps.jsonl").read_text().splitlines() if l.strip()]
    if args.tag:
        rows = [r for r in rows if r.get("tag") == args.tag]
    lines = ["pathfinder probe: {0} steps, tag {1!r}".format(len(rows), args.tag or "all"), ""]
    gates: List[Optional[bool]] = []

    def add(name: str, k: int, n: int, pct: float, ok: Optional[bool], gate: str) -> None:
        gates.append(ok)
        lines.append("{0:<46} {1:>5}/{2:<5} {3:6.1f}%  gate {4:<11} {5}".format(
            name, k, n, pct, gate, "pass" if ok else ("FAIL" if ok is not None else "")))

    s03 = [r for r in rows if r["site"] == "s03"]
    k, n, pct = rate([r for r in s03 if r.get("shut_tine")], "exits")
    add("s03 shut tine: waypoint leads out (+x)", k, n, pct, pct >= 80.0, ">= 80%")
    k, n, pct = rate([r for r in s03 if r.get("shut_tine")], "not_to_exit")
    add("s03 shut tine: never toward the sealed exit (1b)", k, n, pct, pct >= 80.0, ">= 80%")
    k, n, pct = rate([r for r in s03 if r.get("lobby")], "to_mouth")
    add("s03 lobby: waypoint ray through the stem mouth", k, n, pct, pct >= 70.0, ">= 70%")
    s02 = [r for r in rows if r.get("near_door")]
    k, n, pct = rate(s02, "crosses_gap")
    add("s02 near the open door: route crosses in the gap", k, n, pct, pct >= 60.0, ">= 60%")
    not_tine = [r for r in rows
                if not (r["site"] == "s03" and (r.get("region") or "").startswith("tine"))]
    k, n, pct = rate(not_tine, "sealed_true_path")
    add("sealing harm (outside the s03 tines)", k, n, pct, pct <= 5.0, "<= 5%")
    k, n, pct = rate(rows, "no_true_route")
    add("no true route left on a63's map (4b)", k, n, pct, pct <= 5.0, "<= 5%")
    k, n, pct = rate(rows, "punches")
    add("route relies on unknown that is wall (4c)", k, n, pct, None, "report")
    r25 = [r for r in rows if r["round"] == "R25D" and r.get("solved") and "pick" in r]
    f63 = sum(1 for r in r25 if r.get("toward_a63") is not None and r["toward_a63"] == r["pick"])
    o63 = sum(1 for r in r25 if r.get("toward_a63") is not None)
    f49 = sum(1 for r in r25 if r.get("toward_a49") is not None and r["toward_a49"] == r["pick"])
    o49 = sum(1 for r in r25 if r.get("toward_a49") is not None)
    p63 = 100.0 * f63 / o63 if o63 else float("nan")
    p49 = 100.0 * f49 / o49 if o49 else float("nan")
    if r25:
        add("R25D solved runs: a49's pick = a63's toward", f63, o63, p63, p63 >= p49 - 5.0,
            ">= a49-5pt")
        lines.append("{0:<46} {1:>5}/{2:<5} {3:6.1f}%  (a49's own toward-follow rate)".format(
            "R25D solved runs: a49's pick = a49's toward", f49, o49, p49))
    lines.append("")
    lines.append("Reported, not gated:")
    fb = collections.Counter(r["fallback"] for r in rows)
    lines.append("  fallbacks: {0}".format(dict(fb)))
    errs = [r["bearing_err"] for r in rows if "bearing_err" in r]
    if errs:
        within = sum(1 for e in errs if e <= 30.0)
        lines.append("  waypoint bearing within 30 deg of the true route's: {0}/{1} = {2:.1f}%"
                     .format(within, len(errs), 100.0 * within / len(errs)))
    for site in sorted({r["site"] for r in rows}):
        k, n, pct = rate([r for r in rows if r["site"] == site], "sealed_true_path")
        lines.append("  sealing harm {0}: {1}/{2} = {3:.1f}%".format(site, k, n, pct))
    if s02:
        outside = sum(1 for r in s02 if r.get("crosses_gap") is False)
        lines.append("  s02 near the door: route crosses the wall outside the gap on {0}/{1}"
                     .format(outside, len(s02)))
    lines.append("")
    lines.append("GATE: {0}".format("pass" if all(g for g in gates if g is not None) else "FAIL"))
    text = "\n".join(lines) + "\n"
    print(text)
    (OUT / ("score_{0}.txt".format(args.tag) if args.tag else "score.txt")).write_text(text)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--first", type=int, default=20)
    r.add_argument("--last", type=int, default=26)
    r.add_argument("--tag", default="tune")
    r.add_argument("--append", action="store_true")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("score")
    s.add_argument("--tag", default=None)
    s.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
