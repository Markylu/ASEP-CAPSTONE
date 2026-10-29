"""R24 through-the-doorway probe (no model): a46's items at every recorded s02 detour call.

At each recorded detour call (the planner asked: walled, blocked or stall) on an
s02 site, the memory is rebuilt from the records up to it (the recorded
perception, after the doorway confirmer where the agent had one) and
planner.through_doorways builds the items. Each is scored against the site
model (R11's analysis/geo.py): is the gap it aims at within 1.2 m of a door open
at that step, and are both legs (drone to the point in front, then through to
the point beyond) clear.

    python3 eval/r24_through_probe.py eval/phase2/R20_door_confirmer/runs ...

Gate (R24 README): of the items built, at least 70% aim within 1.2 m of an open
door, and of those at least 80% have both legs clear.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))

from server.decider import agent, planner, spatial  # noqa: E402
from server.decider.orchestrator import goal_at  # noqa: E402
from spatial_replay import load, runs_under  # noqa: E402
import geo  # noqa: E402

DOOR_M = 1.2


def main() -> int:
    a = agent.get("a46")
    orch = a.features["orchestrator"]
    cfg, along, p = a.spatial_config, orch["along_wall"], orch["through"]
    share = p["front_m"] / (p["front_m"] + p["beyond_m"])
    for root in sys.argv[1:]:
        t: Counter = Counter()
        for run in runs_under(Path(root).resolve()):
            site, arm = run.parts[-3], run.parts[-2]
            if not site.startswith("s02"):
                continue
            rows = load(run)
            for i, r in enumerate(rows):
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                goal = goal_at(r["manifest"])
                if (r.get("planner") or {}).get("ask") is None or here is None or goal is None:
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                mem = spatial.rebuild(rows[:i], r["manifest"], perception, cfg)
                items = planner.through_doorways(mem, here, r["step"], goal, along, p)
                t["calls"] += 1
                near = abs(here[0]) < 4.0
                t["calls_near_divider"] += near
                t["calls_with_item"] += bool(items)
                t["near_with_item"] += near and bool(items)
                free = geo.world(site, arm, r["step"])
                doors = geo.open_doors(site, arm, r["step"])
                for it in items:
                    assert it.via is not None
                    gx = it.x + (it.via[0] - it.x) * share
                    gy = it.y + (it.via[1] - it.y) * share
                    t["items"] += 1
                    real = abs(gx) <= DOOR_M and any(
                        abs(gy - geo.S02_DOORS[d]) <= DOOR_M for d in doors)
                    t["at_open_door"] += real
                    if real:
                        clear = (geo.segment_clear(free, here[:2], (it.x, it.y))
                                 and geo.segment_clear(free, (it.x, it.y), tuple(it.via)))
                        t["at_open_door_clear"] += clear
        print(root)
        for k in sorted(t):
            print("  {0}: {1}".format(k, t[k]))
        if t["items"]:
            print("  at an open door {0:.0%}; of those, both legs clear {1:.0%}".format(
                t["at_open_door"] / t["items"],
                t["at_open_door_clear"] / max(1, t["at_open_door"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
