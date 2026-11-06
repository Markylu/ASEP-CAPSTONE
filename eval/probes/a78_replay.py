"""Offline readouts for a78 (R38) on the recorded change-arm runs. No model, CPU only.

Open loop, as a73_replay: the drone flew a66's (R35: a75's) picks, so this says
what a78's planner would have said from where that drone stood, not where a78
goes. In particular the recorded drone never leaves the shut tine, so the
latch's last part (the lane shut once the drone is out) is not exercised here;
the unit tests cover it.

a78's latch needs the dead-end confirmer's answers, which no recorded run has.
`--answers` says where they come from:

  oracle        yes on an asked step where the drone stood in the shut tine
                facing its door, no on every other asked step: a confirmer that
                is never wrong. An upper bound on what the latch can do.
  always        yes on every asked step: a confirmer that cannot tell a
                corridor from a hall. What the latch costs in s02 then.
  probe:e01     the answers probe DE recorded for that prompt
                (eval/phase2/_probes/dead_end/calls_e01_*.jsonl); an asked step
                with no recorded answer gets none, as a failed call in flight.

`--places N` drops every answer given on a step where the memory already knew
more than N closed-door places (dead_end_trigger.closed_door_places): the
filter read off probe DE's answers after its gate failed
(eval/phase2/_probes/dead_end/README.md, section 3). Not an agent yet.

`--held-out` replays the runs of the held-out check instead (dead_end_heldout.py:
Round F's initial arms, R30, R32), with the answers that probe recorded. R32
flew a49, which records no route, so the a66 columns count R30 only there.

Readouts, against the gates in eval/phase2/R38_dead_end_latch/README.md:

1. s03 final/dynamic: the step the latch fires and the steps left; after it,
   steps in the shut tine whose route leaves by the crossbar (a73_replay's
   readout 3: reaches x >= 5 before x <= -6), a66 recorded against a78; and
   latched steps with "toward your target" on the turn-around (the steps the
   navigator's sentence is said on).
2. s02 final/dynamic: runs the latch fires in before the drone crossed, split
   by won and lost; near-side steps whose route crosses the divider inside the
   open door's gap (a73_replay's readout 2), a66 recorded against a78; steps
   with no route.

    python eval/probes/a78_replay.py [--answers oracle] [--folders final,R32P_repeat_a66,R35_wall_turn_only]
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dead_end_trigger as trigger  # noqa: E402
from a73_replay import (REPO_ROOT, TOWARD, chain, load, metrics, s02_crossing, s03_shut_side,  # noqa: E402
                        s03_shut_tine, in_tine, route_leaves_tine, turn_index)
from common import PROBES, spatial  # noqa: E402
from server.decider import agent as agents  # noqa: E402

CALLS = PROBES / "dead_end"


def probe_answers(prompt: str, calls: Path = CALLS) -> Dict[Tuple[str, str, str, str, int], str]:
    """Probe DE's recorded answers for one prompt, by (round, site, arm, seed, step)."""
    out: Dict[Tuple[str, str, str, str, int], str] = {}
    for fp in sorted(calls.glob("calls_{0}_*.jsonl".format(prompt))):
        for c in map(json.loads, fp.read_text().splitlines()):
            if c.get("result"):
                out[(c["folder"], c["site"], c["arm"], c["seed"], int(c["step"]))] = \
                    c["result"]["dead_end"]
    return out


def with_answers(rows: List[Dict[str, Any]], answer) -> List[Dict[str, Any]]:
    """The run's rows with `dead_end` written into the perceiver's result on
    the asked steps `answer(step)` gives one for, as orchestrator.confirm_dead_end
    leaves it."""
    out = []
    for r in rows:
        said = answer(r["step"])
        if said is not None:
            seen = dict(r.get("perceiver") or {})
            seen["result"] = dict(seen.get("result") or {}, dead_end=said)
            r = dict(r, perceiver=seen)
        out.append(r)
    return out


def frac(k: float, n: float) -> str:
    """'k/n (p%)'; a run set with no recorded route (a49's) has n = 0."""
    return "{0:.0f}/{1:.0f} ({2:.0%})".format(k, n, k / n) if n else "0/0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default="oracle")
    ap.add_argument("--folders", default=trigger.FOLDERS)
    ap.add_argument("--only", default="", help="substring filter on site/arm/seed")
    ap.add_argument("--places", type=int, default=None,
                    help="drop answers on steps with more closed-door places known than this")
    ap.add_argument("--held-out", action="store_true",
                    help="the runs and answers of the held-out check (dead_end_heldout.py): "
                         "initial arms included")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    a66 = agents.get("a66").features["orchestrator"]
    a78 = agents.get("a78").features["orchestrator"]
    cfg = spatial.config_for(a78)
    calls, arms_of = CALLS, {}
    if args.held_out:
        import dead_end_heldout as held
        calls, arms_of = held.OUT, held.HELD
        args.folders = ",".join(held.HELD)
    recorded = probe_answers(args.answers.split(":", 1)[1], calls) \
        if args.answers.startswith("probe:") else {}
    if args.answers.startswith("probe:") and not recorded:
        print("no probe DE answers for {0} under {1}".format(args.answers, calls))
        return 1

    lines = ["a78 replay, answers: {0}{1}{2} (open loop; eval/probes/a78_replay.py)".format(
        args.answers, "" if args.places is None else ", only while {0} or fewer closed-door "
        "places are known".format(args.places),
        ", on the held-out runs" if args.held_out else ""),
             "", "run                          | won | latch step, left | s03 route out a66 a78 "
             "(after latch) | sentence | s02 gap crossing a66 a78 | no route"]
    tot: Dict[str, float] = collections.defaultdict(float)
    latch_left: List[int] = []
    fired_s03d = runs_s03d = 0
    s02 = collections.Counter()
    for folder in args.folders.split(","):
        short = folder.split("_", 1)[0]
        for run in trigger.run_dirs(folder):
            site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
            name = "{0}/{1}/{2}/{3}".format(short, site, arm, seed)
            if arm not in arms_of.get(folder, ("final", "dynamic")) \
                    or (args.only and args.only not in name):
                continue
            rows = [r for r in load(run) if "step" in r and r.get("manifest")]
            met = metrics(run)
            info = trigger.read_run(run)
            asked, right = set(info["asked"]), set(info["asked_right"])
            if args.places is not None:
                known = trigger.closed_door_places(rows)
                asked = {step for step in asked if known[step] <= args.places}

            def answer(step: int) -> Optional[str]:
                if step not in asked:
                    return None
                if args.answers == "oracle":
                    return "yes" if step in right else "no"
                if args.answers == "always":
                    return "yes"
                return recorded.get((short, site, arm, seed, step))

            rec = chain(rows, spatial.config_for(a66), a66["pathfinder"], recorded=True)
            new = chain(with_answers(rows, answer), cfg, a78["pathfinder"], recorded=False)
            fired = next((row["step"] for row in new if (row["plan"] or {}).get("latch")), None)
            no_route = sum(1 for row in new if (row["plan"] or {}).get("fallback") not in (None, "none"))
            tot["no_route"] += no_route
            tot["steps"] += len(new)
            tine = cross = ""
            said = 0
            if arm == "initial":
                group = "initial_won" if info["won"] else "initial_lost"
                s02[group] += 1
                s02[group + "_latched"] += fired is not None
            elif site == "s03":
                side = s03_shut_side(run, arm, rows, met)
                k66, n66 = s03_shut_tine(rows, rec, side)
                k78, n = s03_shut_tine(rows, new, side)  # a49's runs record no route
                tot["t66"] += k66; tot["t78"] += k78; tot["tn66"] += n66; tot["tn"] += n
                ka = na = 0
                for r, row in zip(rows, new):
                    plan = row["plan"] or {}
                    if fired is None or r["step"] < fired or row["here"] is None:
                        continue
                    if side is not None and in_tine(row["here"], side) and plan.get("path_cells"):
                        na += 1
                        ka += route_leaves_tine(plan["path_cells"])
                    t = turn_index(r)
                    if plan.get("latch") and not plan["latch"]["out"] \
                            and TOWARD in row["tags"].get(t, []):
                        said += 1
                tot["la"] += ka; tot["ln"] += na; tot["said"] += said
                tine = "{0:3d} {1:3d} of {2:3d} ({3:3d} of {4:3d})".format(k66, k78, n, ka, na)
                if arm == "dynamic":
                    runs_s03d += 1
                    if fired is not None:
                        fired_s03d += 1
                        latch_left.append(60 - fired)
            else:
                k66, n66 = s02_crossing(rows, rec, site, met, arm)
                k78, n = s02_crossing(rows, new, site, met, arm)
                tot["x66"] += k66; tot["x78"] += k78; tot["xn66"] += n66; tot["xn"] += n
                cross = "{0:3d} {1:3d} of {2:3d}".format(k66, k78, n)
                group = "won" if info["won"] else "lost"
                s02[group] += 1
                if fired is not None and (info["crossed"] is None or fired < info["crossed"]):
                    s02[group + "_latched"] += 1
            lines.append("{0:28s} | {1:3s} | {2:>4s} {3:>4s} | {4:31s} | {5:3d} | {6:15s} | {7:3d}".format(
                name, "yes" if info["won"] else "no", trigger.show(fired),
                trigger.show(None if fired is None else 60 - fired), tine, said, cross, no_route))
            print(lines[-1], flush=True)

    lines.append("")
    if tot["tn"]:
        lines.append("s03 shut-tine steps after the first closed read whose route leaves by the "
                     "crossbar: a66 {0}, a78 {1}.".format(
                         frac(tot["t66"], tot["tn66"]), frac(tot["t78"], tot["tn"])))
    if tot["ln"]:
        lines.append("  of the shut-tine steps from the latch on: a78 {0:.0f}/{1:.0f} ({2:.0%}); "
                     "the sentence would be said on {3:.0f} latched steps.".format(
                         tot["la"], tot["ln"], tot["la"] / tot["ln"], tot["said"]))
    if runs_s03d:
        lines.append("s03 dynamic: the latch fires in {0} of {1} runs; steps left when it does: "
                     "median {2}, {3} with 25 or more.".format(
                         fired_s03d, runs_s03d,
                         int(statistics.median(latch_left)) if latch_left else "-",
                         sum(1 for v in latch_left if v >= 25)))
    if s02["won"] + s02["lost"]:
        lines.append("s02 change arms: the latch fires before the crossing in {0} of {1} won runs "
                     "and {2} of {3} lost runs.".format(
                         s02["won_latched"], s02["won"], s02["lost_latched"], s02["lost"]))
    if s02["initial_won"] + s02["initial_lost"]:
        lines.append("initial arms: the latch fires in {0} of {1} won runs and {2} of {3} lost "
                     "runs.".format(s02["initial_won_latched"], s02["initial_won"],
                                    s02["initial_lost_latched"], s02["initial_lost"]))
    if tot["xn"]:
        lines.append("s02 near-side steps after the switch whose route crosses the divider inside "
                     "the open door's gap: a66 {0}, a78 {1}.".format(
                         frac(tot["x66"], tot["xn66"]), frac(tot["x78"], tot["xn"])))
    lines.append("Steps with no route (soft or frontier fallback): {0:.0f} of {1:.0f}.".format(
        tot["no_route"], tot["steps"]))
    out = Path(args.out or REPO_ROOT / "eval/phase2/_probes/a78/replay_{0}{1}{2}.txt".format(
        args.answers.replace(":", "_"),
        "" if args.places is None else "_places{0}".format(args.places),
        "_heldout" if args.held_out else ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-8:]))
    print("->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
