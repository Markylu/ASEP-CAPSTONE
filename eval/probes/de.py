#!/usr/bin/env python3
"""Probe DE: the s03 dead end in a49's record, offline. Gate and method:
eval/phase2/_probes/de/README.md. No model calls.

    python eval/probes/de.py eval/phase2/R25D_door_confirmer_open_near_unwalled/runs \
        eval/phase2/R29N_host_noise_shared/runs eval/phase2/R29S_host_noise_solo/runs
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))
from server.decider import spatial  # noqa: E402
import geo  # noqa: E402

RECENT, DWELL_STEPS, DWELL_M, FAR_M = 5, 10, 4.0, 6.0
OUT = REPO_ROOT / "eval" / "phase2" / "_probes" / "de"


def pose(r):
    return spatial.pose_xyh((r.get("manifest") or {}).get("pose"))


def place(site, arm, here, shut_sign=None):
    """s03_dead: in the shut tine (final: L, y < 0; dynamic: the tine first entered,
    whose door slams); s03_open: in the other tine; s03_else: lobby, stem, crossbar."""
    if site == "s03":
        if arm != "initial" and here[0] < 5.0 and abs(here[1]) >= 3.0:
            sign = -1.0 if arm == "final" else shut_sign
            return "s03_dead" if sign is not None and here[1] * sign > 0 else "s03_open"
        return "s03_else"
    return "s02" if site.startswith("s02") else site


def closed_perc(r):
    return any(l.get("doorway") == "closed"
               for l in ((r.get("perceiver") or {}).get("result") or {}).get("lanes", []))


def closed_d01(r):
    return "closed" in (((r.get("door_confirmer") or {}).get("result") or {}).values())


def good(site, arm, step, here, it):
    free = geo.world(site, arm, step)
    if not free(it["x"], it["y"]):
        return False
    if site == "s03":
        return it["x"] >= 3.0 or (abs(it["y"]) >= 3.5 and it["y"] * here[1] < 0)
    if site.startswith("s02"):
        doors = geo.open_doors(site, arm, step)
        if not doors:
            return False
        dy = min(abs(here[1] - geo.S02_DOORS[d]) for d in doors)
        return min(abs(it["y"] - geo.S02_DOORS[d]) for d in doors) < dy - 0.5
    return True


def calls(root: Path):
    rnd = root.resolve().parent.name.split("_")[0]
    for run in sorted(root.glob("*/*/seed*")):
        site, arm = run.parts[-3], run.parts[-2]
        rows = [json.loads(l) for l in (run / "decisions.jsonl").open()]
        rows.sort(key=lambda r: r.get("step", 0))
        poses = [pose(r) for r in rows]
        shut_sign = next((1.0 if p[1] > 0 else -1.0 for p in poses
                          if p is not None and p[0] < 5.0 and abs(p[1]) >= 3.0), None)
        first_dead = None
        for i, r in enumerate(rows):
            s = r.get("strategist") or {}
            ask = (r.get("planner") or {}).get("ask")
            here = poses[i]
            if ask is None or s.get("menu") is None or here is None:
                continue
            step = r["step"]
            where = place(site, arm, here, shut_sign)
            recent = rows[max(0, i - RECENT + 1):i + 1]
            last = [p for p in poses[max(0, i - DWELL_STEPS):i] if p is not None]
            dwell = sum(1 for p in last if spatial.dist(p[:2], here[:2]) <= DWELL_M)
            menu = s["menu"]
            far = max(menu, key=lambda t: spatial.dist(here[:2], (t["x"], t["y"])), default=None)
            if far is not None and spatial.dist(here[:2], (far["x"], far["y"])) < FAR_M:
                far = None
            pick = (s.get("result") or {}).get("target")
            if where == "s03_dead" and first_dead is None:
                first_dead = step
            yield {"round": rnd, "run": f"{site}/{arm}", "step": step, "place": where,
                   "closed_perc": any(closed_perc(x) for x in recent),
                   "closed_d01": any(closed_d01(x) for x in recent),
                   "dwell": dwell, "n_last": len(last),
                   "openings": sum(t.get("kind") == "opening" for t in menu),
                   "far": far["id"] if far else None,
                   "far_good": bool(far) and good(site, arm, step, here, far),
                   "pick": pick, "picked_far": bool(far) and pick == far["id"],
                   "steps_left": 60 - step, "first_dead": first_dead == step}


RULES = {
    "A closed_perc": lambda c: c["closed_perc"],
    "B closed_d01": lambda c: c["closed_d01"],
    "C closed_perc & dwell>=7": lambda c: c["closed_perc"] and c["dwell"] >= 7,
    "D dwell>=7": lambda c: c["dwell"] >= 7,
    "E closed_perc & no opening listed": lambda c: c["closed_perc"] and c["openings"] == 0,
    "F E & dwell>=4": lambda c: c["closed_perc"] and c["openings"] == 0 and c["dwell"] >= 4,
    "G closed_d01 & no opening listed": lambda c: c["closed_d01"] and c["openings"] == 0,
}


def main() -> int:
    rows = [c for root in sys.argv[1:] for c in calls(Path(root))]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "calls.jsonl").open("w") as fh:
        for c in rows:
            fh.write(json.dumps(c) + "\n")
    lines = []
    by = Counter(c["place"] for c in rows)
    lines.append("calls by place: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    dead = [c for c in rows if c["place"] == "s03_dead"]
    runs_dead = sorted({(c["round"], c["run"]) for c in dead})
    lines.append(f"s03 dead-end calls: {len(dead)} in {len(runs_dead)} runs: " +
                 ", ".join(f"{r}/{u}" for r, u in runs_dead))
    lines.append("far item on dead-end calls: {0} exist, {1} good, picked {2}".format(
        sum(bool(c["far"]) for c in dead), sum(c["far_good"] for c in dead),
        sum(c["picked_far"] for c in dead)))
    for name, rule in RULES.items():
        fire = [c for c in dead if rule(c)]
        per_run = {k: any(rule(c) for c in dead if (c["round"], c["run"]) == k) for k in runs_dead}
        s02 = [c for c in rows if c["place"] == "s02"]
        s01 = [c for c in rows if c["place"] == "s01"]
        f02 = [c for c in s02 if rule(c)]
        f01 = [c for c in s01 if rule(c)]
        g = sum(c["far_good"] for c in fire)
        ok1 = len(fire) >= 0.8 * len(dead) and all(per_run.values())
        ok2 = fire and g >= 0.9 * len(fire)
        ok3 = len(f02) <= 0.1 * max(1, len(s02)) and len(f01) <= 0.1 * max(1, len(s01))
        first = [c["steps_left"] for c in rows if c["place"] == "s03_dead" and rule(c)]
        lines.append(
            f"{name}: dead-end fires {len(fire)}/{len(dead)} ({len(fire)/max(1,len(dead)):.0%}), "
            f"runs {sum(per_run.values())}/{len(per_run)} [{'pass' if ok1 else 'FAIL'}]; "
            f"far item good on fires {g}/{len(fire)} [{'pass' if ok2 else 'FAIL'}]; "
            f"s02 fires {len(f02)}/{len(s02)} ({len(f02)/max(1,len(s02)):.0%}), "
            f"s01 {len(f01)}/{len(s01)} [{'pass' if ok3 else 'FAIL'}]"
            f" -> {'PASS' if ok1 and ok2 and ok3 else 'fail'}")
        if f02:
            lines.append("   s02 fires, far item good: {0}/{1}; calls: {2}".format(
                sum(c["far_good"] for c in f02), len(f02),
                ", ".join(f"{c['round']}/{c['run']}@{c['step']}" for c in f02)))
    # budget: steps left at the first dead-end call per run where each rule first fires
    for name, rule in RULES.items():
        firsts = {}
        for c in dead:
            k = (c["round"], c["run"])
            if rule(c) and k not in firsts:
                firsts[k] = c["steps_left"]
        lines.append(f"{name}: steps left at first fire per run: " +
                     ", ".join(f"{r}/{u} {v}" for (r, u), v in sorted(firsts.items())) +
                     f"; >= 28 on {sum(v >= 28 for v in firsts.values())}/{len(runs_dead)}")
    lines.append("")
    lines.append("dead-end calls:")
    for c in dead:
        lines.append(f"  {c['round']} {c['run']} s{c['step']:2d} closed_perc={int(c['closed_perc'])} "
                     f"closed_d01={int(c['closed_d01'])} dwell={c['dwell']}/{c['n_last']} openings={c['openings']} "
                     f"far={c['far']} good={int(c['far_good'])} pick={c['pick']}")
    text = "\n".join(lines)
    (OUT / "score.txt").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
