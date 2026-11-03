#!/usr/bin/env python3
"""R30 shakedown and manipulation check in flight: a63's (or a64's) own runs,
scored against the limits in eval/phase2/R30_pathfinder/README.md. No model.

Per run: outcome, steps in the s03 shut tine after the first confirmed closed
door and steps in the open tine, steps in the s03 lobby, the s02 door crossing,
how often the navigator took "toward your target" (forward move / marker 0),
the share of steps with a route (fallback none), stall cells added, and the
longest turn-around streak. Walls are eval/r28_flight.py's job.

    python eval/r30_check.py ~/r30_shake/eval/phase2/R30_pathfinder/runs
    python eval/r30_check.py eval/phase2/R30_pathfinder/runs
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent / "probes"))
import common  # noqa: E402
from common import geo, load, metrics, spatial, xy  # noqa: E402

#: R30 README, "Manipulation check" and "On-policy shakedown".
SHUT_TINE_MAX, LOBBY_MAX, TOWARD_FWD_MIN, TOWARD_TURN_MIN = 8, 12, 0.70, 0.50
ROUTE_MIN, STREAK_MAX = 0.95, 10


def turned_around(r: Dict[str, Any]) -> bool:
    actions = {a["index"]: a for a in (r.get("manifest") or {}).get("actions") or []}
    return bool(actions.get(r.get("index"), {}).get("turn_around"))


def toward_of(r: Dict[str, Any]) -> Optional[int]:
    tags = r.get("tags") or {}
    return next((int(i) for i, words in tags.items()
                 if spatial.WORDS["toward_target"] in words), None)


def check_run(run: Path) -> Dict[str, Any]:
    rows = load(run)
    met = metrics(run)
    site, arm = run.parts[-3], run.parts[-2]
    sw = common.switch_step(met)
    end_m = None
    if rows:
        end_m = round(float((rows[-1]["manifest"].get("goal") or {})
                            .get("distance", float("nan"))), 1)
    out: Dict[str, Any] = {"run": "/".join(run.parts[-3:]), "steps": len(rows),
                           "solved": bool(met.get("goal_reached")), "end_m": end_m}
    # Navigator against the tags.
    fwd = fwd_taken = turn = turn_taken = 0
    streak = best = routed = stalls = 0
    for r in rows:
        t = toward_of(r)
        if t is not None and r.get("index") is not None:
            actions = {a["index"]: a for a in r["manifest"].get("actions") or []}
            if actions.get(t, {}).get("turn_around"):
                turn += 1
                turn_taken += r["index"] == t
            else:
                fwd += 1
                fwd_taken += r["index"] == t
        streak = streak + 1 if turned_around(r) else 0
        best = max(best, streak)
        plan = r.get("planner") or {}
        routed += plan.get("fallback") == "none"
        stalls += bool(plan.get("stall"))
    out.update({"toward_fwd": "{0}/{1}".format(fwd_taken, fwd),
                "toward_fwd_rate": fwd_taken / fwd if fwd else None,
                "toward_turn": "{0}/{1}".format(turn_taken, turn),
                "toward_turn_rate": turn_taken / turn if turn else None,
                "route_rate": routed / len(rows) if rows else None,
                "stalls": stalls, "streak": best})
    # s03 regions.
    if site == "s03":
        shut = common.s03_shut_side(arm, rows, sw)
        first_closed = next((r["step"] for r in rows if "closed" in (
            ((r.get("door_confirmer") or {}).get("result") or {}).values())), None)
        in_shut = in_open = lobby = 0
        for r in rows:
            p = xy(r)
            if p is None:
                continue
            region = common.s03_region(p[:2])
            lobby += region == "lobby"
            if shut is not None and region.startswith("tine"):
                if region == "tine_" + shut:
                    in_shut += first_closed is not None and r["step"] > first_closed
                else:
                    in_open += 1
        out.update({"shut_side": shut, "first_closed": first_closed, "shut_tine_after": in_shut,
                    "open_tine": in_open, "lobby": lobby})
    # s02: crossed the divider inside the open door's opening.
    if site.startswith("s02"):
        changed = arm == "final" or (arm == "dynamic" and sw is not None)
        yd = geo.S02_DOORS["A" if site in ("s02a", "s02va") else "C"] if changed else 0.0
        crossed = None
        poses = [xy(r) for r in rows]
        for k, (a, b) in enumerate(zip(poses, poses[1:])):
            if a is None or b is None or not (a[0] > 0 >= b[0]):
                continue
            t = a[0] / (a[0] - b[0])
            y = a[1] + (b[1] - a[1]) * t
            crossed = ("gap" if abs(y - yd) < geo.DOOR_HALF + 0.3 else "wall",
                       rows[k]["step"])
            break
        out["crossed"] = crossed
    return out


def verdict(c: Dict[str, Any]) -> List[str]:
    bad = []
    if c["streak"] >= STREAK_MAX:
        bad.append("streak {0}".format(c["streak"]))
    if c["route_rate"] is not None and c["route_rate"] < ROUTE_MIN:
        bad.append("route {0:.0%}".format(c["route_rate"]))
    # Rates are judged on five offers or more; fewer is reported, not failed.
    n_fwd, n_turn = int(c["toward_fwd"].split("/")[1]), int(c["toward_turn"].split("/")[1])
    if n_fwd >= 5 and c["toward_fwd_rate"] is not None and c["toward_fwd_rate"] < TOWARD_FWD_MIN:
        bad.append("toward fwd {0:.0%}".format(c["toward_fwd_rate"]))
    if (n_turn >= 5 and c["toward_turn_rate"] is not None
            and c["toward_turn_rate"] < TOWARD_TURN_MIN):
        bad.append("toward turn {0:.0%}".format(c["toward_turn_rate"]))
    if "shut_tine_after" in c:
        if c["first_closed"] is not None and c["shut_tine_after"] > SHUT_TINE_MAX:
            bad.append("shut tine {0}".format(c["shut_tine_after"]))
        if c["shut_side"] is not None and c["first_closed"] is not None and c["open_tine"] == 0:
            bad.append("open tine 0")
        if c["lobby"] > LOBBY_MAX:
            bad.append("lobby {0}".format(c["lobby"]))
    return bad


def main() -> int:
    roots = [Path(p) for p in sys.argv[1:]] or [Path("eval/phase2/R30_pathfinder/runs")]
    runs = []
    for root in roots:
        runs += sorted(p.parent for p in root.rglob("decisions.jsonl")
                       if "_attempts" not in p.parts)
    if not runs:
        print("no runs under", ", ".join(str(r) for r in roots))
        return 1
    print("{0:<22} {1:>5} {2:>6} {3:>7} {4:>9} {5:>9} {6:>6} {7:>5} {8:>6}  {9}".format(
        "run", "steps", "solved", "end m", "twd fwd", "twd turn", "route", "stall", "streak",
        "s03: shut/open/lobby | s02: crossed"))
    fails = 0
    for run in runs:
        c = check_run(run)
        extra = ""
        if "shut_tine_after" in c:
            extra = "shut {0} ({1}) after s{2}; open {3}; lobby {4}".format(
                c["shut_tine_after"], c["shut_side"], c["first_closed"], c["open_tine"],
                c["lobby"])
        elif "crossed" in c:
            extra = "crossed {0}".format(c["crossed"])
        bad = verdict(c)
        fails += bool(bad)
        print("{0:<22} {1:>5} {2:>6} {3:>7} {4:>9} {5:>9} {6:>5.0%} {7:>5} {8:>6}  {9}{10}".format(
            c["run"], c["steps"], "yes" if c["solved"] else "no", c["end_m"], c["toward_fwd"],
            c["toward_turn"], c["route_rate"] or 0.0, c["stalls"], c["streak"], extra,
            "  FAIL: " + ", ".join(bad) if bad else ""))
    print("\nlimits: shut tine after the closed door <= {0}, lobby <= {1}, toward fwd >= {2:.0%}, "
          "toward turn >= {3:.0%}, route >= {4:.0%}, streak < {5}. Walls: eval/r28_flight.py."
          .format(SHUT_TINE_MAX, LOBBY_MAX, TOWARD_FWD_MIN, TOWARD_TURN_MIN, ROUTE_MIN,
                  STREAK_MAX))
    print("{0} of {1} runs outside the limits".format(fails, len(runs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
