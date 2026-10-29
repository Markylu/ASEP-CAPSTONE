"""Close a Phase 2 round flown on parallel lanes and merged into one checkout.

Each lane flies its cells with `phase2.py run --only` in its own checkout, so
no lane's matrix.csv or phase.json sees the whole round. After the lanes' run
directories are merged here, this re-validates every cell (phaselib's own
checks, at the round's SHA), marks the valid ones in matrix.csv with their end
reason, and sets phase.json complete with the finish time, the lanes and a
note. Nothing is flown.

    python3 eval/phase2_merge.py R14 --lanes "4 lanes: ~/asep-r14-l1..l4" --note "..."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2 import PHASE  # noqa: E402
from phaselib import now, read_json, write_json  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("round")
    ap.add_argument("--lanes", default="")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    unit = args.round
    folder = PHASE.phase_dir(unit)
    phase = read_json(folder / "phase.json")
    rows = PHASE.load_matrix()
    bad = 0
    for site, arm, seed in PHASE.order_of(unit):
        run_dir = PHASE.run_dir_for(unit, site, arm, seed)
        reasons = PHASE.validate(unit, site, arm, seed, run_dir, phase.get("git_sha"))
        row = PHASE.latest_row(rows, unit, site, arm, seed)
        if reasons:
            bad += 1
            print("{0}/{1}/{2}: {3}".format(site, arm, seed, "; ".join(reasons)))
            continue
        row["status"] = "valid"
        row["end_reason"] = read_json(run_dir / "metrics.json").get("end_reason", "")
    PHASE.save_matrix(rows)
    if bad == 0:
        phase.update({"status": "complete", "finished": phase.get("finished") or now()})
        if args.note:
            phase["notes"] = args.note
        if args.lanes:
            phase["lanes"] = args.lanes
        write_json(folder / "phase.json", phase)
    PHASE.write_readme()
    print("{0}: {1} invalid".format(unit, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
