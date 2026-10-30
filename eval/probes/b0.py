"""Probe B0 (no model): can code tell that the s03 dead end is used up?

Belief under test (docs/research/probe-plan.md, B): when the model keeps
ignoring the way out, code should notice the pocket is used up and move the
target. Three exhaustion rules are replayed over every recorded run's rebuilt
memory and scored against geo. Rules, target choice, scoring and gate:
eval/phase2/_probes/b0/README.md (committed before this ran).

    python3 eval/probes/b0.py [--first 15] [--last 26]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PROBES, load, memory_config, metrics, path_to_goal, pct, runs,  # noqa: E402
                    s03_region, s03_shut_side, solved_step, switch_step, true_goal, world,
                    world_key, write_jsonl, xy)
from server.decider import planner, spatial  # noqa: E402

POCKET_N, POCKET_R = 10, 3.0
STALL_N, STALL_GAIN = 12, 1.0
BLACKLIST_NEAR = 1.5
OUTSIDE_M = 6.0
MOVE_M = 1.7
MAX_STEPS = 60
EXIT_NEAR_X = -4.0
HIT_AFTER = 5
RULES = ("R-pocket", "R-blacklist", "R-stall")
OUT = PROBES / "b0"


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def fires(rule, poses, way, mem, here, goal, failed):
    if rule == "R-pocket":
        if len(poses) < POCKET_N or way == "open":
            return False
        c = centroid(poses[-POCKET_N:])
        return all(spatial.dist(p, c) <= POCKET_R for p in poses[-POCKET_N:])
    if rule == "R-stall":
        if len(poses) <= STALL_N or way == "open" or goal is None:
            return False
        return spatial.dist(poses[-STALL_N - 1], goal) - spatial.dist(poses[-1], goal) < STALL_GAIN
    if rule == "R-blacklist":
        if way != "walled":
            return False
        top = mem.search_frontiers(here[:2], limit=3)
        return not top or all(any(spatial.dist(pt, tuple(f)) <= BLACKLIST_NEAR for f in failed)
                              for pt, _, _ in top)
    raise ValueError(rule)


def target_for(mem, here, poses, failed):
    c = centroid(poses[-POCKET_N:])
    for pt, _, path_m in mem.search_frontiers(here[:2], blacklist=[tuple(f) for f in failed],
                                              limit=10):
        if spatial.dist(pt, c) > OUTSIDE_M:
            return pt, path_m
    return None, None


def replay(run):
    rows = load(run["path"])
    met = metrics(run["path"])
    goal = true_goal(rows)
    cfg = memory_config(rows)
    first: dict = {rule: None for rule in RULES}
    poses = []
    for i, r in enumerate(rows):
        here = xy(r)
        if here is None:
            continue
        poses.append(here[:2])
        way = (r.get("planner") or {}).get("way")
        todo = [rule for rule in RULES if first[rule] is None]
        if way is None or not todo:
            continue
        mem = spatial.rebuild(rows[:i], r["manifest"], (r.get("perceiver") or {}).get("result"), cfg)
        failed = planner.failed_detours(rows[:i + 1])
        for rule in todo:
            if fires(rule, poses, way, mem, here, goal, failed):
                pt, path_m = target_for(mem, here, poses, failed)
                first[rule] = {"step": r["step"], "target": pt, "path_m": path_m}
    return rows, met, goal, first


def shut_tine_story(run, rows, met):
    """(step the shut tine was entered, step first near its exit wall), or None."""
    side = s03_shut_side(run["arm"], rows, switch_step(met))
    if side is None:
        return None
    entered = near = None
    for r in rows:
        p = xy(r)
        if p is None or s03_region(p[:2]) != "tine_" + side:
            continue
        entered = r["step"] if entered is None else entered
        if near is None and p[0] <= EXIT_NEAR_X:
            near = r["step"]
    return (entered, near) if near is not None else None


def useful(run, rows, met, goal, fire):
    pt = fire["target"]
    if pt is None or goal is None:
        return False
    side = s03_shut_side(run["arm"], rows, switch_step(met))
    other = "tine_" + ("R" if side == "L" else "L")
    if s03_region(pt) not in ("crossbar", other):
        return False
    key = world_key(run["site"], run["arm"], fire["step"], rows, met)
    free = world(run["site"], run["arm"], fire["step"], rows, met)
    rest = path_to_goal(key, free, goal, pt)
    return math.isfinite(rest) and fire["step"] + (fire["path_m"] + rest) / MOVE_M <= MAX_STEPS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=15)
    ap.add_argument("--last", type=int, default=26)
    args = ap.parse_args()

    out_rows, tine_runs = [], []
    t = {rule: {"tine": 0, "hit": 0, "useful": 0, "solved": 0, "harm": 0, "initial_fire": 0}
         for rule in RULES}
    for run in runs(args.first, args.last):
        rows, met, goal, first = replay(run)
        name = "{0}/{1}/{2}".format(run["round"], run["site"], run["arm"])
        solved = solved_step(rows, met)
        story = None
        if run["site"] == "s03" and run["arm"] in ("final", "dynamic") and solved is None:
            story = shut_tine_story(run, rows, met)
            if story:
                tine_runs.append("{0} (tine @{1}, exit wall @{2})".format(name, *story))
        rec = {"run": name, "solved_step": solved, "shut_tine": story}
        for rule in RULES:
            f = first[rule]
            rec[rule] = f
            c = t[rule]
            if story:
                c["tine"] += 1
                if f and story[0] <= f["step"] <= story[1] + HIT_AFTER:
                    c["hit"] += 1
                    c["useful"] += useful(run, rows, met, goal, f)
            if solved is not None:
                c["solved"] += 1
                c["harm"] += bool(f and f["step"] < solved)
            c["initial_fire"] += bool(run["arm"] == "initial" and f)
        out_rows.append(rec)
    write_jsonl(OUT / "fires.jsonl", out_rows)

    lines = ["B0 over R{0}-R{1}: {2} runs; shut-tine failures: {3}".format(
        args.first, args.last, len(out_rows), len(tine_runs))]
    lines += ["  " + s for s in tine_runs]
    lines += ["", "| rule | hits | useful target (of hits) | harm (solved runs fired before "
              "success) | initial runs fired | gate |", "|---|---|---|---|---|---|"]
    for rule in RULES:
        c = t[rule]
        ok = bool(c["tine"] and c["hit"] / c["tine"] >= 0.8
                  and c["hit"] and c["useful"] / c["hit"] >= 0.8
                  and c["solved"] and c["harm"] / c["solved"] <= 0.10)
        lines.append("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
            rule, pct(c["hit"], c["tine"]), pct(c["useful"], c["hit"]),
            pct(c["harm"], c["solved"]), c["initial_fire"], "PASS" if ok else "fail"))
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
