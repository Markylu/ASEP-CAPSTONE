#!/usr/bin/env python3
"""Probe CR: the s03 crossbar fork in a49's record, offline. Gate and method:
eval/phase2/_probes/cr/README.md. No model calls.

    python eval/probes/cr.py eval/phase2/R25D_door_confirmer_open_near_unwalled/runs \
        eval/phase2/R29N_host_noise_shared/runs eval/phase2/R29S_host_noise_solo/runs
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))
from server.decider import spatial  # noqa: E402
from server.decider.orchestrator import goal_at  # noqa: E402
import geo  # noqa: E402

MIN_M, SIDE_LO, SIDE_HI, AHEAD_DEG, NEARER_M, BUDGET_STEP, CUE_STEPS = 1.5, 60.0, 120.0, 45.0, 0.5, 24, 8
OUT = REPO_ROOT / "eval" / "phase2" / "_probes" / "cr"


def pose(r):
    return spatial.pose_xyh((r.get("manifest") or {}).get("pose"))


def closed_perc(r):
    return any(l.get("doorway") == "closed"
               for l in ((r.get("perceiver") or {}).get("result") or {}).get("lanes", []))


def closed_d01(r):
    return "closed" in (((r.get("door_confirmer") or {}).get("result") or {}).values())


def fork(here, goal, menu, ask, side_hi=SIDE_HI, one_side=False):
    """T: walled/blocked, two side frontiers (one, when one_side), nothing ahead or
    nearer the goal."""
    if ask not in ("walled", "blocked"):
        return None
    want = spatial.bearing(here[:2], goal)
    d_here = spatial.dist(here[:2], goal)
    left = right = None
    for t in menu:
        if t.get("kind") not in ("frontier", "opening"):
            continue
        p = (t["x"], t["y"])
        off = spatial.wrap(spatial.bearing(here[:2], p) - want)
        if abs(off) <= AHEAD_DEG or spatial.dist(p, goal) < d_here - NEARER_M:
            return None
        if t.get("kind") != "frontier" or spatial.dist(here[:2], p) < MIN_M:
            continue
        if SIDE_LO <= off <= side_hi and left is None:
            left = t
        elif -side_hi <= off <= -SIDE_LO and right is None:
            right = t
    if one_side:
        return (left or right, right or left) if (left or right) else None
    return (left, right) if left and right else None


def side_good(site, arm, step, here, t):
    if not site.startswith("s02"):
        return None
    doors = geo.open_doors(site, arm, step)
    if not doors:
        return False
    dy = min(abs(here[1] - geo.S02_DOORS[d]) for d in doors)
    return min(abs(t["y"] - geo.S02_DOORS[d]) for d in doors) < dy - 0.5


def main() -> int:
    calls, runs = [], []
    for root in map(Path, sys.argv[1:]):
        rnd = root.resolve().parent.name.split("_")[0]
        for run in sorted(root.glob("*/*/seed*")):
            site, arm = run.parts[-3], run.parts[-2]
            rows = sorted((json.loads(l) for l in (run / "decisions.jsonl").open()),
                          key=lambda r: r.get("step", 0))
            poses = [pose(r) for r in rows]
            info = {"round": rnd, "run": f"{site}/{arm}"}
            if site == "s03":
                info["crossbar"] = next((r["step"] for r, p in zip(rows, poses) if p and p[0] < 8), None)
                tine_i = next((i for i, p in enumerate(poses) if p and p[0] < 5 and abs(p[1]) >= 3), None)
                info["tine"] = rows[tine_i]["step"] if tine_i is not None else None
                if tine_i is not None:
                    after = rows[tine_i:]
                    info["d01_closed"] = next((r["step"] for r in after if closed_d01(r)), None)
                    info["perc_closed"] = next((r["step"] for r in after if closed_perc(r)), None)
                info["first_fire"] = None
            for i, r in enumerate(rows):
                s = r.get("strategist") or {}
                ask = (r.get("planner") or {}).get("ask")
                here, goal = poses[i], goal_at(r["manifest"])
                if ask is None or s.get("menu") is None or here is None or goal is None:
                    continue
                f = fork(here, goal, s["menu"], ask)
                f_wide = fork(here, goal, s["menu"], ask, side_hi=150.0)
                f_one = fork(here, goal, s["menu"], ask, side_hi=150.0, one_side=True)
                where = ("s03_crossbar" if site == "s03" and 4.5 <= here[0] < 8 else
                         "s03_else" if site == "s03" else
                         "s02_divider" if site.startswith("s02") and abs(here[0]) < 3 else
                         "s02_else" if site.startswith("s02") else site)
                c = {"round": rnd, "run": f"{site}/{arm}", "step": r["step"], "place": where,
                     "ask": ask, "fire": f is not None, "fire_wide": f_wide is not None, "fire_one": f_one is not None, "x": round(here[0], 1), "y": round(here[1], 1),
                     "pick": (s.get("result") or {}).get("target")}
                if f:
                    c["sides"] = [f[0]["id"], f[1]["id"]]
                    g = [side_good(site, arm, r["step"], here, t) for t in f]
                    c["good_side"] = any(g) if site.startswith("s02") else None
                    if site == "s03" and where == "s03_crossbar" and info.get("first_fire") is None:
                        info["first_fire"] = r["step"]
                if site == "s03" and where == "s03_crossbar":
                    if f_wide and info.get("first_wide") is None:
                        info["first_wide"] = r["step"]
                    if f_one and info.get("first_one") is None:
                        info["first_one"] = r["step"]
                calls.append(c)
            if site == "s03":
                runs.append(info)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "calls.jsonl").open("w") as fh:
        for c in calls:
            fh.write(json.dumps(c) + "\n")
    L = []
    by = Counter(c["place"] for c in calls)
    fires = Counter(c["place"] for c in calls if c["fire"])
    L.append("calls by place (fires): " + ", ".join(f"{k} {by[k]} ({fires[k]})" for k in sorted(by)))
    failed = [i for i in runs if i["run"] != "s03/initial" and not (i["round"] == "R29S" and i["run"] == "s03/final")]
    L.append("s03 runs: round/run crossbar tine first_fork_fire d01_closed_after_entry perc_closed_after_entry")
    for i in runs:
        L.append("  {round} {run}: crossbar {crossbar} tine {tine} fire {first_fire} d01 {d01} perc {perc}".format(
            d01=i.get("d01_closed"), perc=i.get("perc_closed"), **i))
    g1 = sum(i["first_fire"] is not None for i in failed)
    g2 = sum(i["first_fire"] is not None and i["first_fire"] <= BUDGET_STEP for i in failed)
    def within(i, k):
        return i.get(k) is not None and i.get("tine") is not None and i[k] - i["tine"] <= CUE_STEPS
    g4d = sum(within(i, "d01_closed") for i in failed)
    g4p = sum(within(i, "perc_closed") for i in failed)
    s02e = [c for c in calls if c["place"] == "s02_else"]; f02e = [c for c in s02e if c["fire"]]
    s02d = [c for c in calls if c["place"] == "s02_divider"]; f02d = [c for c in s02d if c["fire"]]
    s01 = [c for c in calls if c["place"] == "s01"]; f01 = [c for c in s01 if c["fire"]]
    L.append(f"gate 1: fork fires at a crossbar call in {g1}/5 failed runs [{'pass' if g1 >= 4 else 'FAIL'}]")
    L.append(f"gate 2: first fire at step <= {BUDGET_STEP} in {g2}/5 [{'pass' if g2 >= 4 else 'FAIL'}]")
    L.append(f"gate 3: s02 away from divider {len(f02e)}/{len(s02e)} ({len(f02e)/max(1,len(s02e)):.1%}), "
             f"s01 {len(f01)}/{len(s01)} [{'pass' if len(f02e) <= 0.1*len(s02e) and len(f01) <= 0.05*max(1,len(s01)) else 'FAIL'}]")
    L.append(f"gate 4: turn-back cue within {CUE_STEPS} steps of tine entry: d01 {g4d}/5, perceiver {g4p}/5 "
             f"[{'pass' if max(g4d, g4p) >= 4 else 'FAIL'}]")
    L.append(f"s02 divider fires (reported): {len(f02d)}/{len(s02d)}; a side toward an open door listed on "
             f"{sum(bool(c.get('good_side')) for c in f02d)} of them; runs: " + ", ".join(
                 f"{k[0]}/{k[1]} {v}" for k, v in sorted(Counter((c['round'], c['run']) for c in f02d).items())))
    if f02e:
        L.append("s02 fires away from the divider: " + ", ".join(f"{c['round']}/{c['run']}@{c['step']} ({c['x']},{c['y']})" for c in f02e))
    for key, fk in (("first_wide", "fire_wide"), ("first_one", "fire_one")):
        n1 = sum(i.get(key) is not None for i in failed); n2 = sum(i.get(key) is not None and i[key] <= BUDGET_STEP for i in failed)
        fd = sum(c[fk] for c in s02d); fe = sum(c[fk] for c in s02e); f1 = sum(c[fk] for c in s01)
        L.append(f"variant {key}: crossbar fire in {n1}/5 failed runs, <= {BUDGET_STEP} in {n2}/5; first fires " +
                 ", ".join(f"{i['round']}/{i['run']} {i.get(key)}" for i in failed) +
                 f"; s02 divider {fd}/{len(s02d)}, s02 else {fe}/{len(s02e)}, s01 {f1}/{len(s01)}")
    L.append("")
    L.append("s03 crossbar calls:")
    for c in calls:
        if c["place"] == "s03_crossbar":
            L.append(f"  {c['round']} {c['run']} s{c['step']:2d} ({c['x']},{c['y']}) ask={c['ask']} fire={int(c['fire'])} "
                     f"wide={int(c['fire_wide'])} one={int(c['fire_one'])} sides={c.get('sides')} pick={c['pick']}")
    text = "\n".join(L)
    (OUT / "score.txt").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
