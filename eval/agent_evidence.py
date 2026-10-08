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

Deterministic: the same runs give the same file.
"""
from __future__ import annotations

import argparse
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

COLUMNS = [("bearing", "reason cites bearing"), ("distance", "reason cites distance"),
           ("nearest", "nearest-bearing pick"), ("obstacle", "obstacle word"),
           ("turn", "turn-around pick")]


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
            for d in read_jsonl(run / "decisions.jsonl"):
                reason = (d.get("reason") or "").lower()
                manifest = d.get("manifest") or {}
                c["n"] += 1
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
             "counts negations too; check reasons before citing it.".format(chance or "–"), "",
             "| Site | Arm | runs | decisions | " + " | ".join(t for _, t in COLUMNS) + " |",
             "|---|---|---|---|" + "---|" * len(COLUMNS)]
    pooled: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (site, arm) in sorted(cells, key=lambda k: (k[0], arm_rank.get(k[1], 9), k[1])):
        c = cells[(site, arm)]
        for key, value in c.items():
            pooled[arm][key] += value
        lines.append("| {0} | {1} | {2} | {3} | {4} |".format(
            site, arm, c["runs"], c["n"], " | ".join(pct(c[k], c["n"]) for k, _ in COLUMNS)))
    for arm in sorted(pooled, key=lambda a: (arm_rank.get(a, 9), a)):
        c = pooled[arm]
        lines.append("| **all** | {0} | {1} | {2} | {3} |".format(
            arm, c["runs"], c["n"], " | ".join(pct(c[k], c["n"]) for k, _ in COLUMNS)))
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
