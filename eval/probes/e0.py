"""Probe E0 (no model): do old blocks and "searched" notes mislead after a door switch?

Belief under test (docs/research/probe-plan.md, E): blocks and seen cells never
expire, so after the s02 switch opens a door, notes made before it may still
steer the drone away from the new way. Reads the tags each navigator call was
actually shown. Definitions and gate: eval/phase2/_probes/e0/README.md
(committed before this ran).

    python3 eval/probes/e0.py [--first 15] [--last 26]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PROBES, geo, load, memory_config, metrics, pct, runs, solved_step,  # noqa: E402
                    switch_step, write_jsonl, world, xy)
from server.decider import spatial  # noqa: E402

RAY_CAP_M = 12.0
OPENED_BY_M = 1.0
WALL_NEAR_DOOR_M = 1.0
STALE_OPEN_M = 2.5
STALE_OPEN_AFTER = 3
BLOCK = re.compile(r"(?:blocked|stopped short) here before \(step (\d+)\)")
SEARCHED = "searched already this way"
OUT = PROBES / "e0"


def new_door(site: str):
    return 0.0, geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"]


def cell_centre(c):
    return (c[0] + 0.5) * spatial.CELL_M, (c[1] + 0.5) * spatial.CELL_M


def scan(run):
    rows = load(run["path"])
    met = metrics(run["path"])
    sw = switch_step(met)
    if sw is None:
        return None
    old = world(run["site"], run["arm"], sw, rows, met)
    new = world(run["site"], run["arm"], sw + 1, rows, met)
    door, b_door = new_door(run["site"]), (0.0, geo.S02_DOORS["B"])
    cfg = memory_config(rows)
    rec = {"run": "{0}/{1}/{2}".format(run["round"], run["site"], run["arm"]),
           "switch": sw, "solved_step": solved_step(rows, met), "doorward_calls": 0,
           "stale_calls": 0, "stale_block": 0, "stale_searched": 0, "examples": [],
           "wall_at_new_door_calls": 0, "stale_open_b_calls": 0, "post_calls": 0}
    for i, r in enumerate(rows):
        here = xy(r)
        if r["step"] <= sw or here is None or r.get("index") is None:
            continue
        rec["post_calls"] += 1
        tags = {int(k): v for k, v in (r.get("tags") or {}).items()}
        doorward = []
        for a in r["manifest"].get("actions") or []:
            if a.get("turn_around"):
                continue
            h = spatial.action_heading(a, here[2])
            gain = (geo.ray(new, here[0], here[1], h, max_d=RAY_CAP_M)
                    - geo.ray(old, here[0], here[1], h, max_d=RAY_CAP_M))
            if gain >= OPENED_BY_M:
                doorward.append(int(a["index"]))
        if doorward:
            rec["doorward_calls"] += 1
            stale = False
            for idx in doorward:
                for note in tags.get(idx, []):
                    m = BLOCK.search(note)
                    if m and int(m.group(1)) <= sw:
                        rec["stale_block"] += 1
                        stale = True
                    if SEARCHED in note:
                        rec["stale_searched"] += 1
                        stale = True
            if stale:
                rec["stale_calls"] += 1
                if len(rec["examples"]) < 3:
                    rec["examples"].append({"step": r["step"], "doorward": doorward,
                                            "tags": {k: tags.get(k) for k in doorward},
                                            "picked": r["index"]})
        mem = spatial.rebuild(rows[:i], r["manifest"], (r.get("perceiver") or {}).get("result"), cfg)
        walls = list(mem.wall) + list(mem.stop_wall)
        if any(spatial.dist(cell_centre(c), door) <= WALL_NEAR_DOOR_M for c in walls):
            rec["wall_at_new_door_calls"] += 1
        if r["step"] > sw + STALE_OPEN_AFTER and any(
                spatial.dist((o.x, o.y), b_door) <= STALE_OPEN_M
                for o in mem.listed_openings(r["step"])):
            rec["stale_open_b_calls"] += 1
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=15)
    ap.add_argument("--last", type=int, default=26)
    args = ap.parse_args()

    recs = []
    for run in runs(args.first, args.last):
        if run["site"].startswith("s02") and run["arm"] == "dynamic":
            rec = scan(run)
            if rec:
                recs.append(rec)
    write_jsonl(OUT / "runs.jsonl", recs)

    counted = [r for r in recs if r["doorward_calls"]]
    stale = [r for r in counted if r["stale_calls"]]
    clean = [r for r in counted if not r["stale_calls"]]

    def solved(rs):
        return sum(r["solved_step"] is not None for r in rs)

    share = len(stale) / len(counted) if counted else 0.0
    verdict = "HOLDS" if share >= 0.30 else ("DROP" if share < 0.10 else "no call")
    lines = [
        "E0 over R{0}-R{1}: {2} s02 dynamic runs with a switch; {3} offered a door-ward action "
        "after it".format(args.first, args.last, len(recs), len(counted)),
        "",
        "runs with a stale note on a door-ward action: " + pct(len(stale), len(counted))
        + "  -> gate: " + verdict,
        "  door-ward calls: {0}; with a stale note: {1} (pre-switch block notes {2}, "
        "'searched' notes {3})".format(sum(r["doorward_calls"] for r in counted),
                                       sum(r["stale_calls"] for r in counted),
                                       sum(r["stale_block"] for r in counted),
                                       sum(r["stale_searched"] for r in counted)),
        "solved: with stale notes " + pct(solved(stale), len(stale))
        + "; without " + pct(solved(clean), len(clean)),
        "",
        "secondary (memory rebuilt):",
        "  runs with a wall cell within {0} m of the new door after the switch: {1}".format(
            WALL_NEAR_DOOR_M, pct(sum(bool(r["wall_at_new_door_calls"]) for r in recs), len(recs))),
        "  runs listing an open doorway at shut door B > {0} steps after the switch: {1}".format(
            STALE_OPEN_AFTER, pct(sum(bool(r["stale_open_b_calls"]) for r in recs), len(recs))),
    ]
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
