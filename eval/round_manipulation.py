"""Per run of a Phase 2 round: what the map and the drone did, from the records.

The manipulation check for R14 on (eval/phase2/R14_open_floor/README.md):
share of perceiver strips the map took as blocked_near, turn-arounds picked,
the farthest the drone got from its start, collisions and the outcome.

    python3 eval/round_manipulation.py eval/phase2/R14_open_floor/runs [more roots]
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.decider import spatial  # noqa: E402


def run_row(d: Path):
    m = json.loads((d / "metrics.json").read_text())
    recs = [json.loads(line) for line in (d / "decisions.jsonl").read_text().splitlines()
            if line.strip()]
    lanes = [lane for r in recs
             for lane in ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []]
    blocked = sum(lane.get("floor") == "blocked_near" for lane in lanes) / max(1, len(lanes))
    turns = sum(1 for r in recs if r.get("index") == 0)
    pts = [p[:2] for p in (spatial.pose_xyh(r["manifest"].get("pose")) for r in recs) if p]
    far = max((math.dist(pts[0], q) for q in pts), default=0.0)
    return m, blocked, turns, far


def main() -> int:
    for root in sys.argv[1:]:
        print("==", root)
        rows = []
        for d in sorted(Path(root).glob("*/*/seed1")):
            if not (d / "metrics.json").is_file():
                continue
            m, blocked, turns, far = run_row(d)
            rows.append((blocked, turns, far))
            print("  {0:<16} {1:<12} steps {2:>2}  blocked_near {3:>4.0%}  turn-arounds {4:>2}  "
                  "max from start {5:>5.1f} m  collisions {6}".format(
                      "/".join(d.parts[-3:-1]), m.get("end_reason"), m.get("steps"),
                      blocked, turns, far, m.get("collisions")))
        if rows:
            print("  median: blocked_near {0:.0%}, turn-arounds {1:g}, max from start "
                  "{2:.1f} m".format(*(statistics.median(c) for c in zip(*rows))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
