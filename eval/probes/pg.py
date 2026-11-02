#!/usr/bin/env python3
"""Probe PG: a map-geometry pocket cue at every step of a49's runs, offline. Gate
and method: eval/phase2/_probes/pg/README.md. No model calls.

    python eval/probes/pg.py eval/phase2/R25D_door_confirmer_open_near_unwalled/runs \
        eval/phase2/R29N_host_noise_shared/runs eval/phase2/R29S_host_noise_solo/runs
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from server.decider import agent, spatial  # noqa: E402
from server.decider.orchestrator import goal_at  # noqa: E402

CFG = agent.get("a49").spatial_config
R_M, GAP_DEG, WALL_M, WALL_DEG, GOAL_DEG, MIN_CELLS, RECENT = 5.0, 60.0, 3.0, 30.0, 45.0, 15, 5
OUT = REPO_ROOT / "eval" / "phase2" / "_probes" / "pg"


def pose(r):
    return spatial.pose_xyh((r.get("manifest") or {}).get("pose"))


def centre(c):
    return ((c[0] + 0.5) * spatial.CELL_M, (c[1] + 0.5) * spatial.CELL_M)


def clusters(bearings):
    if not bearings:
        return []
    b = sorted(bearings)
    groups = [[b[0]]]
    for x in b[1:]:
        if x - groups[-1][-1] > GAP_DEG:
            groups.append([x])
        else:
            groups[-1].append(x)
    if len(groups) > 1 and (groups[0][0] + 360.0) - groups[-1][-1] <= GAP_DEG:
        groups[0] = groups.pop() + groups[0]
    return [sum(spatial.wrap(x - g[0]) for x in g) / len(g) + g[0] for g in groups]


def pocket(mem, here, goal):
    reach = mem.reach(here[:2])
    local = {c: d for c, d in reach.items() if d <= R_M}
    exits = []
    for c in local:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (c[0] + dx, c[1] + dy)
                if n in reach and reach[n] > R_M:
                    exits.append(spatial.bearing(here[:2], centre(c)))
                    break
            else:
                continue
            break
    ex = clusters(exits)
    want = spatial.bearing(here[:2], goal)
    walled = any(spatial.dist(here[:2], centre(c)) <= WALL_M
                 and abs(spatial.wrap(spatial.bearing(here[:2], centre(c)) - want)) <= WALL_DEG
                 for c in list(mem.wall) + list(mem.stop_wall))
    toward_goal = any(abs(spatial.wrap(e - want)) <= GOAL_DEG for e in ex)
    return {"n_local": len(local), "n_exits": len(ex), "walled": walled,
            "exit_toward_goal": toward_goal,
            "pocket": len(local) >= MIN_CELLS and len(ex) <= 1 and walled and not toward_goal}


def place(site, arm, here, shut_sign):
    if site == "s03":
        if here[0] < 5.0 and abs(here[1]) >= 3.0:
            if arm == "initial":
                return "s03_open"
            sign = -1.0 if arm == "final" else shut_sign
            return "s03_dead" if sign is not None and here[1] * sign > 0 else "s03_open"
        return "s03_else"
    return "s02" if site.startswith("s02") else site


def closed_perc(r):
    return any(l.get("doorway") == "closed"
               for l in ((r.get("perceiver") or {}).get("result") or {}).get("lanes", []))


def closed_d01(r):
    return "closed" in (((r.get("door_confirmer") or {}).get("result") or {}).values())


def steps(root: Path):
    rnd = root.resolve().parent.name.split("_")[0]
    for run in sorted(root.glob("*/*/seed*")):
        site, arm = run.parts[-3], run.parts[-2]
        rows = sorted((json.loads(l) for l in (run / "decisions.jsonl").open()),
                      key=lambda r: r.get("step", 0))
        poses = [pose(r) for r in rows]
        shut_sign = next((1.0 if p[1] > 0 else -1.0 for p in poses
                          if p is not None and p[0] < 5.0 and abs(p[1]) >= 3.0), None)
        for i, r in enumerate(rows):
            here = poses[i]
            goal = goal_at(r["manifest"])
            if here is None or goal is None:
                continue
            mem = spatial.rebuild(rows[:i], r["manifest"],
                                  (r.get("perceiver") or {}).get("result"), CFG)
            pk = pocket(mem, here, goal)
            recent = rows[max(0, i - RECENT + 1):i + 1]
            yield dict(pk, round=rnd, run=f"{site}/{arm}", step=r["step"],
                       place=place(site, arm, here, shut_sign), steps_left=60 - r["step"],
                       closed_perc=any(closed_perc(x) for x in recent),
                       closed_d01=any(closed_d01(x) for x in recent),
                       x=round(here[0], 1), y=round(here[1], 1))


RULES = {"P pocket": lambda c: c["pocket"],
         "PC pocket & closed_perc": lambda c: c["pocket"] and c["closed_perc"],
         "PD pocket & closed_d01": lambda c: c["pocket"] and c["closed_d01"]}


def main() -> int:
    rows = [c for root in sys.argv[1:] for c in steps(Path(root))]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "steps.jsonl").open("w") as fh:
        for c in rows:
            fh.write(json.dumps(c) + "\n")
    lines = ["steps by place: " + ", ".join(f"{k} {v}" for k, v in sorted(
        Counter(c["place"] for c in rows).items()))]
    dead_runs = sorted({(c["round"], c["run"]) for c in rows if c["place"] == "s03_dead"})
    lines.append("shut-tine runs: " + ", ".join(f"{r}/{u}" for r, u in dead_runs))
    for name, rule in RULES.items():
        first = {}
        for c in rows:
            if c["place"] == "s03_dead" and rule(c):
                first.setdefault((c["round"], c["run"]), c["steps_left"])
        ok1 = sum(v >= 28 for v in first.values()) >= 4
        per_place = defaultdict(lambda: [0, 0])
        per_run = Counter()
        for c in rows:
            per_place[c["place"]][1] += 1
            if rule(c):
                per_place[c["place"]][0] += 1
                per_run[(c["round"], c["run"])] += 1
        s02_runs_over = [k for k, v in per_run.items() if k[1].startswith("s02") and v > 5]
        f, n = per_place["s02"]
        ok2 = f <= 0.05 * n and not s02_runs_over
        f3, n3 = per_place["s03_open"]
        ok3 = f3 <= 0.10 * max(1, n3)
        f4, n4 = per_place["s01"]
        ok4 = f4 <= 0.05 * max(1, n4)
        lines.append(f"{name}: " + "; ".join(
            f"{p} {per_place[p][0]}/{per_place[p][1]}" for p in sorted(per_place)))
        lines.append(f"   first fire in shut tine, steps left: " + ", ".join(
            f"{r}/{u} {first.get((r, u), '-')}" for r, u in dead_runs)
            + f" -> >=28 on {sum(v >= 28 for v in first.values())}/5 [{'pass' if ok1 else 'FAIL'}]")
        lines.append(f"   s02 {f}/{n} ({f/max(1,n):.1%}), runs over 5 fires: "
                     f"{', '.join('/'.join(k) + ' ' + str(per_run[k]) for k in s02_runs_over) or 'none'}"
                     f" [{'pass' if ok2 else 'FAIL'}]; s03_open {f3}/{n3} [{'pass' if ok3 else 'FAIL'}];"
                     f" s01 {f4}/{n4} [{'pass' if ok4 else 'FAIL'}]"
                     f" -> {'PASS' if ok1 and ok2 and ok3 and ok4 else 'fail'}")
        fires = [c for c in rows if rule(c) and c["place"] != "s03_dead"]
        if fires:
            by = Counter((c["round"], c["run"]) for c in fires)
            lines.append("   fires outside the shut tine by run: " + ", ".join(
                f"{r}/{u} {v}" for (r, u), v in sorted(by.items())))
    lines.append("")
    lines.append("shut-tine steps (pocket fields):")
    for c in rows:
        if c["place"] == "s03_dead":
            lines.append(f"  {c['round']} {c['run']} s{c['step']:2d} ({c['x']},{c['y']}) local={c['n_local']} "
                         f"exits={c['n_exits']} walled={int(c['walled'])} exit_toward_goal={int(c['exit_toward_goal'])} "
                         f"pocket={int(c['pocket'])} closed_perc={int(c['closed_perc'])} closed_d01={int(c['closed_d01'])}")
    text = "\n".join(lines)
    (OUT / "score.txt").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
