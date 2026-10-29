"""How a perceiver's floor ends (g05, g06) match the site model (R14, R15).

For every strip a perceiver answered on recorded runs, the true clear distance
along the strip's centre ray (R11's 2D site model, eval/r12_probe.true_reach)
against the answer. By default the answers are the records' own (`perceiver`);
with --answers, a probe's (r12_probe.py run-g04 --agent a24), matched by run
and step, and only steps it answered are counted.

    python3 eval/r14_floor_confusion.py eval/phase2/R12_staged_search/runs
    python3 eval/r14_floor_confusion.py RUNS --answers g06.jsonl

Evaluation only: reads ground truth to score.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r12_probe import geo, label, load, runs_under, site_arm, spatial, true_reach  # noqa: E402

BINS = [(0, 1.0), (1.0, 1.9), (1.9, 3.0), (3.0, 5.0), (5.0, 8.0), (8.0, 99)]
#: A 1.7 m move fails on a strip whose true clear distance is under this.
MOVE_FAILS_M = 1.9


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--answers", help="a probe's answers (jsonl: run, step, result)")
    args = ap.parse_args()
    answers = None
    if args.answers:
        answers = {}
        for line in Path(args.answers).read_text().splitlines():
            j = json.loads(line) if line.strip() else {}
            if j.get("result"):
                answers[(j["run"], j["step"])] = j["result"]
    conf: Counter = Counter()
    order: list = []
    steps = 0
    for root in args.roots:
        for run in runs_under(Path(root).resolve()):
            site, arm = site_arm(run)
            for r in load(run):
                if answers is not None:
                    res = answers.get((label(run), r["step"]))
                else:
                    res = ((r.get("perceiver") or {}).get("result"))
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                if not res or here is None:
                    continue
                steps += 1
                free = geo.world(site, arm, r["step"])
                for lane in res.get("lanes") or []:
                    end = lane.get("floor_end")
                    if lane.get("strip") not in spatial.STRIPS or not end:
                        continue
                    if end not in order:
                        order.append(end)
                    d = true_reach(free, here[:2],
                                   (here[2] + spatial.strip_offset(lane["strip"])) % 360.0)
                    b = next(b for b in BINS if b[0] <= d < b[1])
                    conf[(b, end)] += 1
    ends = [e for e in ("no_floor", "wall_at_bottom", "bottom", "lower", "middle", "runs_on")
            if e in order] + [e for e in order if e not in (
                "no_floor", "wall_at_bottom", "bottom", "lower", "middle", "runs_on")]
    print("steps {0}".format(steps))
    print("true m      " + " ".join("{0:>15}".format(e) for e in ends))
    for b in BINS:
        print("{0:<10} ".format("{0:g}-{1:g}".format(*b)) +
              " ".join("{0:>15}".format(conf[(b, e)]) for e in ends))
    for e in ends:
        n = sum(conf[(b, e)] for b in BINS)
        fails = sum(conf[(b, e)] for b in BINS if b[1] <= MOVE_FAILS_M)
        far = sum(conf[(b, e)] for b in BINS if b[0] >= 8.0)
        print("{0:<15} n={1:>5}  true < {2} m (a 1.7 m move fails) {3:5.1f}%  clear past 8 m "
              "{4:5.1f}%".format(e, n, MOVE_FAILS_M, 100.0 * fails / max(1, n),
                                 100.0 * far / max(1, n)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
