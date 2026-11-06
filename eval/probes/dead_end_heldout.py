"""Probe DE, held-out check (R38, after the gate): does the places filter hold
on runs it was not fitted on?

Probe DE's gate failed for e01 (eval/phase2/_probes/dead_end/README.md, section
2). Read afterwards on the same answers, e01 kept only while the memory knows
at most two closed-door places (4 m) fires the latch's rule in 11 of 11 s03
dynamic runs and 1 of 88 s02 runs (section 3): a fit. This asks e01 on the
asked steps of runs no part of that fit saw, with the setting fixed here
before any call:

  final             initial arms (a66, 30 runs)
  R30_pathfinder    all three arms (a66, 18 runs)
  R32_repeat_a49    final and dynamic (a49, 30 runs)

and counts the latch's rule per run. Gate and method:
eval/phase2/_probes/dead_end_heldout/README.md (set before this ran).

    python eval/probes/dead_end_heldout.py sample ~/asep-final-l* ~/r30_shake ~/asep-r32-l*
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/dead_end_heldout.py run
    python eval/probes/dead_end_heldout.py score

`sample` and `run` need the frames (on the host the rounds flew on); `score`
needs neither frames nor a model.
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dead_end as de  # noqa: E402
import dead_end_trigger as trigger  # noqa: E402
from common import PROBES, load  # noqa: E402

OUT = Path(os.environ.get("DEAD_END_OUT") or PROBES / "dead_end_heldout")
de.OUT = OUT  # dead_end's sample, run and load_sample read and write here
PROMPT = "e01"
#: The runs: folder -> arms. None of them is in dead_end.FOLDERS' change arms.
HELD = {"final": ("initial",), "R30_pathfinder": ("initial", "final", "dynamic"),
        "R32_repeat_a49": ("final", "dynamic")}
#: The filter, fixed before any call: an answer counts only on a step where
#: the memory knows at most PLACES closed-door places, RADIUS_M apart.
PLACES = 2
RADIUS_M = 4.0
#: Set in the probe README before any call.
GATE = {"initial_runs_max": 0, "s02_runs_max": 2, "s03_dynamic_runs_min": 3}
GROUPS = ("initial", "s02 change", "s01 change", "s03 dynamic", "s03 final")


def group(site: str, arm: str) -> str:
    if arm == "initial":
        return "initial"
    if site == "s03":
        return "s03 " + arm
    return ("s02" if site.startswith("s02") else site) + " change"


def wanted(folder: str, arm: str) -> bool:
    return arm in HELD.get(folder, ())


def score() -> int:
    from server.decider import agent
    rule = agent.PATHFINDER_A78["dead_end_latch"]
    frames = {f["id"]: f for f in de.load_sample()}
    said: Dict[str, str] = {}
    latency: List[float] = []
    failed = 0
    for fp in sorted(OUT.glob("calls_{0}_*.jsonl".format(PROMPT))):
        for c in map(json.loads, fp.read_text().splitlines()):
            if c["id"] not in frames:
                continue
            latency.append(c["latency_ms"])
            if c.get("result"):
                said[c["id"]] = c["result"]["dead_end"]
            else:
                failed += 1
    if not said:
        print("no {0} calls under {1}".format(PROMPT, OUT))
        return 1
    by_run: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = collections.defaultdict(list)
    for f in frames.values():
        by_run[(f["folder"], f["site"], f["arm"], f["seed"])].append(f)

    runs: List[Dict[str, Any]] = []
    for folder, arms in HELD.items():
        short = folder.split("_", 1)[0]
        for run in trigger.run_dirs(folder):
            site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
            if arm not in arms:
                continue
            rows = [r for r in load(run) if r.get("manifest")]
            known = trigger.closed_door_places(rows, RADIUS_M)
            info = trigger.read_run(run)
            asked = sorted(by_run.get((short, site, arm, seed), []), key=lambda f: f["step"])
            answered = [f for f in asked if f["id"] in said]
            kept = [f for f in answered if known[f["step"]] <= PLACES]
            fire = de.first_fire([(f["step"], said[f["id"]]) for f in kept], rule)
            fire_all = de.first_fire([(f["step"], said[f["id"]]) for f in answered], rule)
            crossed = info["crossed"]
            runs.append({
                "name": "{0}/{1}/{2}/{3}".format(short, site, arm, seed), "round": short,
                "group": group(site, arm), "won": info["won"], "crossed": crossed,
                "asked_record": len(info["asked"]), "answered": answered, "kept": kept,
                "fire": fire, "fire_all": fire_all,
                "fire_near": fire is not None and (crossed is None or fire < crossed),
                "fire_all_near": fire_all is not None and (crossed is None or fire_all < crossed),
                "fire_where": next((f["where"] for f in kept if f["step"] == fire), None)})

    asked_record = sum(r["asked_record"] for r in runs)
    answered_n = sum(len(r["answered"]) for r in runs)
    lines = ["Probe DE, held-out check: {0} on the asked steps of {1} runs the places filter was "
             "not fitted on".format(PROMPT, len(runs)),
             "({0}).".format("; ".join("{0} {1}".format(f.split("_", 1)[0], "/".join(a))
                                       for f, a in HELD.items())),
             "Filter, fixed before any call: an answer counts only while at most {0} closed-door "
             "places are known ({1:g} m).".format(PLACES, RADIUS_M),
             "Rule for a run: yes on a step and on {0} of the last {1} answers, none older than "
             "{2} steps (a78's).".format(rule["yes_reads"], rule["of_reads"], rule["recent_steps"]),
             "", "{0} of {1} asked steps answered ({2} with a frame), {3} failed calls; median "
             "latency {4:.0f} ms".format(answered_n, asked_record, len(frames), failed,
                                         statistics.median(latency)), ""]

    def yes(fs: List[Dict[str, Any]]) -> str:
        return "{0}/{1}".format(sum(said[f["id"]] == "yes" for f in fs), len(fs))

    row = "{0:<14}{1:>5}{2:>9}{3:>11}{4:>10}{5:>10}{6:>10}{7:>12}{8:>11}"
    lines.append(row.format("group", "runs", "yes all", "yes kept", "fired", "near", "in time",
                            "fired, all", "near, all"))
    tally: Dict[str, Dict[str, int]] = {}
    for g in GROUPS:
        rs = [r for r in runs if r["group"] == g]
        tally[g] = {"runs": len(rs), "fired": sum(r["fire"] is not None for r in rs),
                    "near": sum(r["fire_near"] for r in rs),
                    "in_time": sum(r["fire"] is not None and 60 - r["fire"] >= 25 for r in rs)}
        lines.append(row.format(
            g, len(rs), yes([f for r in rs for f in r["answered"]]),
            yes([f for r in rs for f in r["kept"]]), tally[g]["fired"], tally[g]["near"],
            tally[g]["in_time"], sum(r["fire_all"] is not None for r in rs),
            sum(r["fire_all_near"] for r in rs)))
    lines += ["", "'yes all': yes answers of all answers; 'yes kept': of those the filter keeps.",
              "'fired': runs the rule fires in on the kept answers; 'near': before the drone "
              "crossed (s02: x < 0; s03: x < -7);",
              "'in time': with 25 or more steps left; 'fired, all' and 'near, all': the same on "
              "every answer, no filter.", "", "By round (fired on the kept answers / runs)"]
    for short in sorted({r["round"] for r in runs}):
        parts = []
        for g in GROUPS:
            rs = [r for r in runs if r["round"] == short and r["group"] == g]
            if rs:
                parts.append("{0} {1}/{2}".format(g, sum(r["fire"] is not None for r in rs),
                                                  len(rs)))
        lines.append("  {0:<6}".format(short) + "; ".join(parts))
    lines += ["", "Yes by where the drone stood (kept answers, all answers)"]
    for where in ("shut_tine", "s03_other", "s02"):
        every = [f for r in runs for f in r["answered"] if f["where"] == where]
        kept = [f for r in runs for f in r["kept"] if f["where"] == where]
        lines.append("  {0:<11}{1:>9}{2:>10}".format(where, yes(kept), yes(every)))
    lines += ["", "Runs the rule fires in on the kept answers"]
    for r in runs:
        if r["fire"] is not None:
            lines.append("  {0:<28} {1:<5} step {2:>2} ({3}), crossed {4}".format(
                r["name"], "won" if r["won"] else "lost", r["fire"], r["fire_where"],
                trigger.show(r["crossed"])))
    checks = [
        ("fires in none of the {0} initial runs".format(tally["initial"]["runs"]),
         tally["initial"]["fired"] <= GATE["initial_runs_max"]),
        ("fires before the crossing in at most {0} of the {1} s02 change-arm runs".format(
            GATE["s02_runs_max"], tally["s02 change"]["runs"]),
         tally["s02 change"]["near"] <= GATE["s02_runs_max"]),
        ("fires in at least {0} of the {1} s03 dynamic runs".format(
            GATE["s03_dynamic_runs_min"], tally["s03 dynamic"]["runs"]),
         tally["s03 dynamic"]["fired"] >= GATE["s03_dynamic_runs_min"]),
        ("every asked step answered", answered_n == asked_record)]
    lines.append("")
    for name, ok in checks:
        lines.append("{0}: {1}".format("PASS" if ok else "FAIL", name))
    passed = all(ok for _, ok in checks)
    lines.append("Held-out gate: {0}".format("PASS" if passed else "FAIL"))
    (OUT / "score.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("roots", nargs="+")
    r = sub.add_parser("run")
    r.add_argument("--shard", type=int, default=0)
    r.add_argument("--of", type=int, default=1)
    sub.add_parser("score")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "sample":
        return de.sample(args.roots, wanted)
    if args.cmd == "run":
        asyncio.run(de.run_probe(PROMPT, args.shard, args.of))
        return 0
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
