#!/usr/bin/env python3
"""R27 manipulation check in flight: missed and phantom walls of the perceiver's
readings on the s02/s03 steps, against geo with each run's own world, and how
often both reads came back. Check: eval/phase2/R27_mirrored_nr_perceiver/README.md,
"Manipulation check". Truth as the probes (eval/probes/c1f1.truth).

    python eval/r27_flight.py eval/phase2/R27_mirrored_nr_perceiver/runs \
        eval/phase2/R25D_door_confirmer_open_near_unwalled/runs
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "probes"))
from c1f1 import STRIPS, truth  # noqa: E402
from common import load, metrics, xy  # noqa: E402

MISSED_MAX, PHANTOM_MAX, BOTH_MIN = 0.08, 0.20, 0.95


def readings(r):
    p, m = r.get("perceiver") or {}, r.get("perceiver_mirror") or {}
    return {"fused": p.get("result"), "own": p.get("result_own"),
            "mirror": m.get("result_unmirrored")}


def check(root: Path) -> list:
    tally = {k: [0, 0, 0, 0] for k in ("fused", "own", "mirror")}  # miss, blocked, phantom, open
    steps = both = 0
    for run in sorted(root.glob("*/*/seed*")):
        site, arm = run.parts[-3], run.parts[-2]
        rows, met = load(run), metrics(run)
        for r in rows:
            got = readings(r)
            steps += 1
            both += bool(got["own"] and got["mirror"])
            if not (site.startswith("s02") or site == "s03") or xy(r) is None:
                continue
            t = truth(site, arm, r, rows, met)["lanes"]
            for k, res in got.items():
                if not res:
                    continue
                floor = {l["strip"]: l["floor"] for l in res["lanes"]}
                for s in STRIPS:
                    if t[s]["floor"] == "blocked_near":
                        tally[k][1] += 1
                        tally[k][0] += floor[s] != "blocked_near"
                    else:
                        tally[k][3] += 1
                        tally[k][2] += floor[s] == "blocked_near"
    lines = ["== {0}".format(root), "  steps {0}, both reads on {1} ({2:.1%})".format(
        steps, both, both / max(1, steps))]
    for k, (miss, blocked, phantom, open_) in tally.items():
        if blocked + open_:
            lines.append("  {0:7s} missed wall {1:5.1%} ({2}/{3})   phantom wall {4:5.1%} "
                         "({5}/{6})".format(k, miss / max(1, blocked), miss, blocked,
                                            phantom / max(1, open_), phantom, open_))
    miss, blocked, phantom, open_ = tally["fused"]
    if tally["own"][1] + tally["own"][3]:  # a mirrored agent: the README's check
        oks = [miss / max(1, blocked) <= MISSED_MAX, phantom / max(1, open_) <= PHANTOM_MAX,
               both / max(1, steps) >= BOTH_MIN]
        lines.append("  check: missed <= 8% {0}, phantom <= 20% {1}, both reads >= 95% {2}"
                     .format(*("pass" if ok else "FAIL" for ok in oks)))
    return lines


def main() -> int:
    for root in sys.argv[1:]:
        print("\n".join(check(Path(root))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
