"""R22 floor-ends probe (no model): the navigator's notes from memory a17 against a17b.

a17b writes no wall at the end of an open_near (g05 "bottom") strip. Every
recorded step is replayed into both memories (spatial.rebuild of the records up
to it, the recorded perception and target) and each offered forward move's
notes are compared (spatial.project). Scored against the site model (R11's
analysis/geo.py) for how far each move's heading is truly free.

    python3 eval/r22_floor_ends_probe.py eval/phase2/R15_known_goal_reach/runs ...

Gate (R22 README): s03 toward moves noted "searched already" at most 100 over
R15-R17K; the share of forward moves noted "new ground" that are truly blocked
within 1.9 m no more than 7%.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))

from server.decider import spatial  # noqa: E402
from spatial_replay import load, runs_under  # noqa: E402
import geo  # noqa: E402

BLOCKED_M = 1.9
MEMORIES = {"a17": spatial.A17, "a17b": spatial.A17B}


def main() -> int:
    t: Counter = Counter()
    for root in sys.argv[1:]:
        for run in runs_under(Path(root).resolve()):
            site, arm = run.parts[-3], run.parts[-2]
            rows = load(run)
            for i, r in enumerate(rows):
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                if here is None:
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                target = spatial.Target.from_dict(r.get("target"))
                free = geo.world(site, arm, r["step"])
                forward = [a for a in r["manifest"].get("actions") or []
                           if not a.get("turn_around")]
                for name, cfg in MEMORIES.items():
                    mem = spatial.rebuild(rows[:i], r["manifest"], perception, cfg)
                    tags = spatial.project(mem, r["manifest"], perception, target)
                    any_new = False
                    for a in forward:
                        note = tags.get(int(a["index"]), [])
                        new = spatial.WORDS["new_ground"] in note
                        searched = spatial.WORDS_A17["searched"] in note
                        toward = spatial.WORDS["toward_target"] in note
                        h = spatial.action_heading(a, here[2])
                        blocked = geo.ray(free, here[0], here[1], h, max_d=BLOCKED_M) < BLOCKED_M
                        t[(name, "moves")] += 1
                        t[(name, "searched")] += searched
                        t[(name, "new")] += new
                        t[(name, "new_blocked")] += new and blocked
                        t[(name, "toward_searched")] += toward and searched
                        if site == "s03":
                            t[(name, "s03_toward_searched")] += toward and searched
                        any_new |= new
                    t[(name, "steps")] += 1
                    t[(name, "no_forward_new")] += not any_new
    for name in MEMORIES:
        g = lambda k: t[(name, k)]  # noqa: E731
        print("{0:5s} forward moves {1}: searched {2}, new ground {3} (truly blocked within "
              "{4} m: {5} = {6:.1%}); toward+searched {7} (s03 {8}); steps with no forward "
              "new ground {9}/{10} = {11:.0%}".format(
                  name, g("moves"), g("searched"), g("new"), BLOCKED_M, g("new_blocked"),
                  g("new_blocked") / max(1, g("new")), g("toward_searched"),
                  g("s03_toward_searched"), g("no_forward_new"), g("steps"),
                  g("no_forward_new") / max(1, g("steps"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
