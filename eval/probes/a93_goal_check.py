"""a93's goal check on flown records. No model.

The perceiver names the goal on steps where the drone has no line of sight to
it; the navigator's first rule is the "goal this way" tag. a93 drops a report
whose strip lies more than off_deg off the bearing to the goal, the goal min_m
or more away (orchestrator.goal_off_line, the code a93 flies). This script
runs that rule over flown runs and counts, against the line of sight the
manifest records (evaluation only):

  reports made with no line of sight   dropped, and how many had raised a tag
                                       the navigator took
  reports made with one                dropped (it must leave these alone)
  runs                                 the step of the first taken tag the
                                       rule would have dropped, and the outcome

Open loop: it says what the rule removes, not what the drone does next.

    python eval/probes/a93_goal_check.py [--folders ...] [--sweep] [--out FILE]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT  # noqa: E402
from server.decider import agent as agents, orchestrator, spatial  # noqa: E402

FOLDERS = ("R44_survey_latch_v3,R45_survey_lineup,R46_behind_always,R47_station_guard,"
           "R49_no_sentence,R51_no_station_guard,R52_station_stall")
GOAL_TAGS = ("goal this way", "goal about one move ahead")


def folders(names: str) -> List[Path]:
    out = []
    for name in names.split(","):
        hits = sorted((REPO_ROOT / "eval" / "phase2").glob(name.split("_")[0] + "_*"))
        out += [h for h in hits if (h / "runs").is_dir()]
    return out


def read(names: str) -> List[Dict[str, Any]]:
    rows = []
    for folder in folders(names):
        for f in sorted(folder.glob("runs/*/*/*/decisions.jsonl")):
            site, arm, seed = f.parts[-4], f.parts[-3], f.parts[-2]
            won = bool(json.loads((f.parent / "metrics.json").read_text()).get("goal_reached"))
            for line in f.open():
                r = json.loads(line)
                result = (r.get("perceiver") or {}).get("result") or {}
                strip = result.get("goal_reported") or result.get("goal")
                if strip not in spatial.STRIPS:
                    continue
                truth = (r.get("manifest") or {}).get("goal") or {}
                tagged = [i for i, tags in (r.get("tags") or {}).items()
                          if any(t.startswith(GOAL_TAGS) for t in tags)]
                rows.append({"run": (folder.name.split("_")[0], site, arm, seed), "won": won,
                             "step": r["step"], "los": bool(truth.get("line_of_sight")),
                             "manifest": r["manifest"], "strip": strip,
                             "tagged": bool(tagged), "took": str(r.get("index")) in tagged})
    return rows


def line(rows: List[Dict[str, Any]], c: Dict[str, Any]) -> str:
    hit = [r for r in rows if orchestrator.goal_off_line({"goal": r["strip"]}, r["manifest"], c)]
    blind = [r for r in rows if not r["los"]]
    seen = [r for r in rows if r["los"]]
    hb, hs = [r for r in hit if not r["los"]], [r for r in hit if r["los"]]
    return ("off {0:4.0f} deg, min {1:3.1f} m | no line of sight: dropped {2:3d} of {3} "
            "({4:.0f}%), tag taken on {5} | line of sight: dropped {6:3d} of {7} ({8:.1f}%)").format(
                c["off_deg"], c["min_m"], len(hb), len(blind), 100.0 * len(hb) / max(len(blind), 1),
                sum(r["took"] for r in hb), len(hs), len(seen), 100.0 * len(hs) / max(len(seen), 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", default=FOLDERS)
    ap.add_argument("--agent", default="a93")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    rows = read(args.folders)
    c = dict(agents.get(args.agent).features["orchestrator"]["goal_check"])
    runs = sorted({r["run"] for r in rows})
    blind = [r for r in rows if not r["los"]]
    out = ["a93 goal check on {0} goal reports in {1} runs with one, of {2} "
           "(eval/probes/a93_goal_check.py)".format(len(rows), len(runs), args.folders), "",
           "Reports with no line of sight: {0} of {1}; they raised a goal tag on {2} steps and the "
           "navigator took it on {3}.".format(len(blind), len(rows), sum(r["tagged"] for r in blind),
                                              sum(r["took"] for r in blind)), ""]
    if args.sweep:
        for off in (15.0, 20.0, 26.0, 35.0, 45.0):
            for near in (0.0, 4.0):
                out.append(line(rows, dict(c, off_deg=off, min_m=near)))
    else:
        out.append(line(rows, c))
    first: Dict[Any, Dict[str, Any]] = {}
    for r in sorted(rows, key=lambda r: r["step"]):
        if r["took"] and not r["los"] and orchestrator.goal_off_line(
                {"goal": r["strip"]}, r["manifest"], c):
            first.setdefault(r["run"], r)
    every = collections.defaultdict(dict)
    for folder in folders(args.folders):
        for f in sorted(folder.glob("runs/*/*/*/metrics.json")):
            every[f.parts[-4][:3]][(folder.name.split("_")[0],) + f.parts[-4:-1]] = bool(
                json.loads(f.read_text()).get("goal_reached"))
    out += ["", "Runs by the step of the first taken tag the rule drops (no line of sight):"]
    for site in ("s03", "s02"):
        early = [k for k in every[site] if k in first and first[k]["step"] <= 4]
        late = [k for k in every[site] if k in first and first[k]["step"] > 4]
        none = [k for k in every[site] if k not in first]
        out.append("  {0}: by step 4, {1} runs, won {2} | later, {3} runs, won {4} | none, "
                   "{5} runs, won {6}".format(
                       site, len(early), sum(every[site][k] for k in early), len(late),
                       sum(every[site][k] for k in late), len(none),
                       sum(every[site][k] for k in none)))
    out += ["", "s03 runs with such a tag by step 4:"]
    for k in sorted(first):
        if k[1] == "s03" and first[k]["step"] <= 4:
            out.append("  {0} {1:8s} {2}  step {3}  reported {4:9s}  {5}".format(
                k[0], k[2], k[3], first[k]["step"], first[k]["strip"],
                "won" if first[k]["won"] else "lost"))
    text = "\n".join(out) + "\n"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
