#!/usr/bin/env python3
"""R28 on-policy check and manipulation check in flight: missed and phantom
walls of the merged reading (floors from w01), of g05's own read and of the
wall reader alone on the s02/s03 steps, against geo with each run's own world;
how often both reads came back; and each run's longest turn-around streak.
Limits: eval/phase2/R28_wall_reader/README.md, "On-policy check" and
"Manipulation check". Truth as the probes (eval/probes/c1f1.truth).

    python eval/r28_flight.py ~/r28_shake/eval/phase2/R28_wall_reader/runs
    python eval/r28_flight.py eval/phase2/R28_wall_reader/runs \
        eval/phase2/R25D_door_confirmer_open_near_unwalled/runs
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "probes"))
from c1f1 import STRIPS, truth  # noqa: E402
from common import load, metrics, xy  # noqa: E402

MISSED_MAX, PHANTOM_MAX, S03_PHANTOM_MAX, BOTH_MIN, STREAK_MAX = 0.08, 0.15, 0.20, 0.95, 10
KINDS = ("merged", "own", "wall")


def readings(r):
    p, w = r.get("perceiver") or {}, r.get("wall_reader") or {}
    return {"merged": p.get("result"), "own": p.get("result_own"), "wall": w.get("result")}


def turned_around(r) -> bool:
    actions = {a["index"]: a for a in (r.get("manifest") or {}).get("actions") or []}
    return bool(actions.get(r.get("index"), {}).get("turn_around"))


def streak(rows) -> int:
    best = n = 0
    for r in rows:
        n = n + 1 if turned_around(r) else 0
        best = max(best, n)
    return best


def check(root: Path) -> list:
    # miss, blocked, phantom, open, s03 phantom, s03 open
    tally = {k: [0] * 6 for k in KINDS}
    steps = both = 0
    streaks = []
    for run in sorted(root.glob("*/*/seed*")):
        site, arm = run.parts[-3], run.parts[-2]
        rows, met = load(run), metrics(run)
        streaks.append(("{0}/{1}".format(site, arm), streak(rows)))
        for r in rows:
            got = readings(r)
            steps += 1
            both += bool(got["own"] and got["wall"])
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
                        ph = floor[s] == "blocked_near"
                        tally[k][3] += 1
                        tally[k][2] += ph
                        if site == "s03":
                            tally[k][5] += 1
                            tally[k][4] += ph
    lines = ["== {0}".format(root), "  steps {0}, both reads on {1} ({2:.1%})".format(
        steps, both, both / max(1, steps))]
    for k, (miss, blocked, phantom, open_, s03_ph, s03_open) in tally.items():
        if blocked + open_:
            lines.append("  {0:7s} missed wall {1:5.1%} ({2}/{3})   phantom wall {4:5.1%} "
                         "({5}/{6})   s03 phantom {7:5.1%} ({8}/{9})".format(
                             k, miss / max(1, blocked), miss, blocked,
                             phantom / max(1, open_), phantom, open_,
                             s03_ph / max(1, s03_open), s03_ph, s03_open))
    longest = max((n for _, n in streaks), default=0)
    lines.append("  longest turn-around streak {0} ({1})".format(
        longest, ", ".join("{0} {1}".format(c, n) for c, n in streaks if n == longest)))
    miss, blocked, phantom, open_, s03_ph, s03_open = tally["merged"]
    if tally["wall"][1] + tally["wall"][3]:  # an agent with a wall reader: the README's check
        oks = [miss / max(1, blocked) <= MISSED_MAX, phantom / max(1, open_) <= PHANTOM_MAX,
               s03_ph / max(1, s03_open) <= S03_PHANTOM_MAX, both / max(1, steps) >= BOTH_MIN,
               longest < STREAK_MAX]
        lines.append("  check: missed <= 8% {0}, phantom <= 15% {1}, s03 phantom <= 20% {2}, "
                     "both reads >= 95% {3}, turn-around streak < 10 {4}"
                     .format(*("pass" if ok else "FAIL" for ok in oks)))
    return lines


def main() -> int:
    for root in sys.argv[1:]:
        print("\n".join(check(Path(root))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
