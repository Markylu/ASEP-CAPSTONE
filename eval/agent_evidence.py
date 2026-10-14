#!/usr/bin/env python3
"""What the agent leaned on, per site and arm: the numbers a round's README cites.

    python eval/agent_evidence.py eval/phase1
    python eval/agent_evidence.py eval/phase1 --out eval/phase2/R1_no_goal_hint/evidence.md
    python eval/agent_evidence.py eval/phase2/R1_no_goal_hint     # manipulation check

Each path is a phase folder (every citable unit under it) or one unit folder
(taken as given, citable or not). Only `runs/` is read, never `_attempts/`, so
each cell is its current valid attempt.

Columns, over every decision in the cell:

- reason cites bearing: the reason contains the word "bearing".
- reason cites distance: the reason states a goal distance ("24.0 m away").
- nearest-bearing pick: the chosen action is the forward action whose heading
  is closest to the goal's true bearing (manifest ground truth, which every
  agent's run records whether or not the prompt shows it). Chance is
  1 / forward actions.
- obstacle word: wall, door, obstacle, block, cube, dead end or barrier. Raw
  keyword hits, negations included ("no visible obstacles"): read the reasons
  before citing it.
- turn-around pick: action 0.
- reason cites memory: the reason refers back to earlier steps (earlier,
  previous, already, before, again, last time, "step N"). Raw keyword hits, so
  agents without memory score above zero too; compare against a baseline round.
- revisit: the drone is within 1 m of where it was at least 5 decisions
  earlier in the same run (manifest pose), i.e. it is going back over ground.
- same pick: the action index equals the previous decision's. Of decisions
  that have a previous one. Index meaning changes with the view, so a high rate
  is a lock-in on one marker, not on one direction.
- copied reason: the reason, whitespace-normalised, equals the previous
  decision's word for word. Same denominator as same pick.
- goal visible: ground truth, the goal is in line of sight and inside the
  camera's horizontal field of view (|bearing| <= fov / 2). Line of sight is a
  ray to the sphere (vlmnav_controller.gd), so a beam showing above an occluder
  counts as not visible. 1 - this is the majority-class rate a goal report has
  to beat.
- goal report agrees: of decisions that carry a `goal` field (agents whose reply
  reports it), the share matching ground truth: not_visible as above, else
  ahead when the straight action is the nearest heading, left or right by the
  sign of the bearing (positive is left). "–" for agents without the field.
- goal seen when visible: of decisions with a `goal` field where the goal is
  visible, the share not reported as not_visible.

Deterministic: the same runs give the same file.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phaselib import ARMS, REPO_ROOT, read_json, read_jsonl  # noqa: E402

BEARING = re.compile(r"\bbearing\b")
DISTANCE = re.compile(r"\d+(?:\.\d+)?\s*(?:m|meters?|metres?)\s+away")
OBSTACLE = re.compile(r"\b(?:wall|door|obstacle|block|cube|dead end|barrier)")
MEMORY = re.compile(r"\b(?:earlier|previous(?:ly)?|already|before|again|last time|step \d+)\b")
REVISIT_M = 1.0
REVISIT_GAP = 5
GOAL_REPORTS = ("ahead", "left", "right", "not_visible")

#: (counter, title, denominator counter)
COLUMNS = [("bearing", "reason cites bearing", "n"), ("distance", "reason cites distance", "n"),
           ("nearest", "nearest-bearing pick", "n"), ("obstacle", "obstacle word", "n"),
           ("turn", "turn-around pick", "n"), ("memory", "reason cites memory", "n"),
           ("revisit", "revisit", "n"), ("same_pick", "same pick", "pairs"),
           ("copied", "copied reason", "pairs"), ("visible", "goal visible", "n"),
           ("goal_ok", "goal report agrees", "reports"),
           ("goal_seen", "goal seen when visible", "reports_visible")]


def units_under(path: Path) -> List[Path]:
    """A unit folder as given, or every citable unit of a phase folder."""
    if (path / "phase.json").is_file():
        return [path]
    units = []
    for child in sorted(p for p in path.iterdir() if (p / "phase.json").is_file()):
        if read_json(child / "phase.json").get("citable"):
            units.append(child)
    return units


def run_dirs(unit: Path) -> List[Path]:
    return sorted(p.parent for p in (unit / "runs").glob("*/*/seed*/decisions.jsonl"))


def nearest_forward(manifest: Dict[str, Any]) -> Tuple[Optional[int], int]:
    """The forward action closest to the goal bearing, and how many there were."""
    bearing = (manifest.get("goal") or {}).get("bearing_deg")
    forward = [a for a in manifest.get("actions", []) if not a.get("turn_around")]
    if bearing is None or not forward:
        return None, len(forward)
    best = min(forward, key=lambda a: (abs(float(a["theta_deg"]) - float(bearing)),
                                       a["index"]))
    return best["index"], len(forward)


def true_goal(manifest: Dict[str, Any]) -> Optional[str]:
    """Where the goal is in this frame, in the reply's terms; None if unknown."""
    goal = manifest.get("goal") or {}
    bearing = goal.get("bearing_deg")
    if bearing is None:
        return None
    half_fov = float((manifest.get("config") or {}).get("fov_deg", 87.0)) / 2.0
    if not goal.get("line_of_sight") or abs(float(bearing)) > half_fov:
        return "not_visible"
    forward = [a for a in manifest.get("actions", []) if not a.get("turn_around")]
    if forward:
        nearest = min(forward, key=lambda a: abs(float(a["theta_deg"]) - float(bearing)))
        if float(nearest["theta_deg"]) == 0.0:
            return "ahead"
    return "left" if float(bearing) > 0 else "right"


def tally(units: List[Path]) -> Tuple[Dict[Tuple[str, str], Dict[str, int]], Dict[str, Any]]:
    cells: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    meta: Dict[str, Any] = {"runs": 0, "prompts": set(), "agents": set(), "forward": set()}
    for unit in units:
        for run in run_dirs(unit):
            site, arm = run.parts[-3], run.parts[-2]
            info = read_json(run / "run.json") if (run / "run.json").is_file() else {}
            meta["runs"] += 1
            meta["prompts"].add(info.get("prompt_version") or "?")
            meta["agents"].add(info.get("agent_version") or "a00")
            c = cells[(site, arm)]
            c["runs"] += 1
            seen: List[List[float]] = []
            previous: Optional[Dict[str, Any]] = None
            for d in read_jsonl(run / "decisions.jsonl"):
                reason = (d.get("reason") or "").lower()
                manifest = d.get("manifest") or {}
                c["n"] += 1
                if previous is not None:
                    c["pairs"] += 1
                    c["same_pick"] += d.get("index") == previous.get("index")
                    c["copied"] += (" ".join(reason.split()) ==
                                    " ".join((previous.get("reason") or "").lower().split()))
                previous = d
                truth = true_goal(manifest)
                c["visible"] += truth not in (None, "not_visible")
                if d.get("goal") in GOAL_REPORTS and truth is not None:
                    c["reports"] += 1
                    c["goal_ok"] += d["goal"] == truth
                    if truth != "not_visible":
                        c["reports_visible"] += 1
                        c["goal_seen"] += d["goal"] != "not_visible"
                c["memory"] += bool(MEMORY.search(reason))
                here = (manifest.get("pose") or {}).get("position")
                if here:
                    c["revisit"] += any(math.dist(here, p) < REVISIT_M
                                        for p in seen[:max(0, len(seen) - REVISIT_GAP + 1)])
                    seen.append(here)
                c["bearing"] += bool(BEARING.search(reason))
                c["distance"] += bool(DISTANCE.search(reason))
                c["obstacle"] += bool(OBSTACLE.search(reason))
                best, forward = nearest_forward(manifest)
                if forward:
                    meta["forward"].add(forward)
                c["nearest"] += best is not None and d.get("index") == best
                c["turn"] += any(a.get("turn_around") and a["index"] == d.get("index")
                                 for a in manifest.get("actions", []))
    return cells, meta


def pct(k: int, n: int) -> str:
    return "{0:.0%}".format(k / n) if n else "–"


def render(paths: List[Path], units: List[Path],
           cells: Dict[Tuple[str, str], Dict[str, int]], meta: Dict[str, Any]) -> str:
    def rel(p: Path) -> str:
        p = p.resolve()
        return str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT) else str(p)

    chance = ", ".join("1/{0} = {1:.0%}".format(k, 1 / k) for k in sorted(meta["forward"]))
    arm_rank = {arm: i for i, arm in enumerate(ARMS)}
    lines = ["# Agent evidence", "",
             "Generated by `python eval/agent_evidence.py {0}`. Do not edit by hand.".format(
                 " ".join(rel(p) for p in paths)), "",
             "Units: {0}. Runs: {1}. Prompt: {2}. Agent: {3}.".format(
                 ", ".join("`{0}`".format(rel(u)) for u in units), meta["runs"],
                 ", ".join(sorted(meta["prompts"])), ", ".join(sorted(meta["agents"]))), "",
             "Percentages are of decisions. Nearest-bearing chance: {0}. Obstacle word "
             "counts negations too; check reasons before citing it. Same pick and copied reason "
             "are of decisions with a previous one; goal report columns are of decisions that "
             "carry a report (agreement must beat 1 − goal visible).".format(chance or "–"), "",
             "| Site | Arm | runs | decisions | " + " | ".join(t for _, t, _ in COLUMNS) + " |",
             "|---|---|---|---|" + "---|" * len(COLUMNS)]
    pooled: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (site, arm) in sorted(cells, key=lambda k: (k[0], arm_rank.get(k[1], 9), k[1])):
        c = cells[(site, arm)]
        for key, value in c.items():
            pooled[arm][key] += value
        lines.append("| {0} | {1} | {2} | {3} | {4} |".format(
            site, arm, c["runs"], c["n"], " | ".join(pct(c[k], c[d]) for k, _, d in COLUMNS)))
    for arm in sorted(pooled, key=lambda a: (arm_rank.get(a, 9), a)):
        c = pooled[arm]
        lines.append("| **all** | {0} | {1} | {2} | {3} |".format(
            arm, c["runs"], c["n"], " | ".join(pct(c[k], c[d]) for k, _, d in COLUMNS)))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path,
                        help="phase folder (its citable units) or one unit folder")
    parser.add_argument("--out", type=Path, help="write the table here as well")
    args = parser.parse_args()

    units = [u for p in args.paths for u in units_under(p)]
    if not units:
        print("no units found under {0}".format(", ".join(map(str, args.paths))))
        return 1
    cells, meta = tally(units)
    text = render(args.paths, units, cells, meta)
    print(text, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
