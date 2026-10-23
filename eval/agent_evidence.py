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
- two turn-arounds in a row: a turn-around right after a turn-around, of
  decisions with a previous one (R5's loop, spin_failure).
- reason cites position: the reason reads the pose log (position, coordinates,
  "moved 0.0", the same spot, has not moved). Raw keyword hits; R5, without the
  pose log, scores 10-13%.
- pose in manifest: the decision's manifest has the position and yaw the pose
  log (p08 on) is built from.
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
- reason cites degrees / uses a compass word / heading arithmetic (R8): a number
  of degrees, a compass word (north, south-west, ...), or two- or three-digit
  numbers either side of a plus or minus ("287 + 180"). Raw regex hits.
- turn-around with the goal in view: a turn-around pick while the goal is
  visible (ground truth, as above), of decisions where it is visible.

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
#: The pose log (R6): the reason reads the drone's position or the distance moved.
POSITION = re.compile(r"\b(?:position|coordinates?|moved 0\.0|same (?:spot|position|place|location)|"
                      r"(?:has|have|hasn't|has not|did not|didn't) (?:not )?moved?)\b")
#: A reason that places the goal in the drone's surroundings now ("the goal is
#: still reported as ahead", "the goal is visible on the right"), per sentence.
#: A sentence does not count if it negates, looks back or is conditional. Built
#: for the R5 replay probe (eval/goal_probe.py) and checked on R4's reasons:
#: it flags 1 / 439 out-of-view decisions whose reason and goal field both say
#: not visible, 155 / 179 in-view decisions, and 155 / 781 out-of-view ones.
GOAL_NOW = re.compile(
    r"\b(?:goal|sphere)\b[^.;]{0,60}?\b(?:is|remains|appears|lies)\b"
    r"(?:\s+(?:still|now|consistently|clearly))?"
    r"(?:\s+(?:reported|located|positioned|seen))?(?:\s+as)?\s+"
    r"(?:visible|ahead|in (?:the )?view|in front|directly ahead|straight ahead"
    r"|to the (?:left|right)|on the (?:left|right))\b")
GOAL_NOT_NOW = re.compile(
    r"\b(?:not|no longer|n't|cannot|never|no|without"           # negated
    r"|was|were|last|earlier|previous(?:ly)?|before|step \d+|had"  # looks back
    r"|if|whether|check|until|once|unless|may|might|could|would)\b")  # conditional
SENTENCE = re.compile(r"(?<=[.!?;])\s+")
#: After a blocked forward move (R7): the drone moved less than half a step. The same
#: rule as R6's reasoning analysis, which reproduced its 123 blocked moves.
BLOCKED_M = 0.85
#: A sentence that says the drone is making progress, and one that says it did not
#: move. Built for R7 and calibrated on R6's recorded reasons: 84 of 123 progress
#: claims (the R6 analysis, with a hand-built classifier, reported 80) and 36 notes
#: (reported 38); R5: 24 of 36 and 4 (reported 20 and 7). Compare rounds with this
#: classifier, not with those figures.
PROGRESS = re.compile(
    r"\b(?:(?:has|have|had)\s+been|is|are|was|were|continues?\s+to|keeps?|kept)\s+"
    r"(?:consistently\s+|steadily\s+|successfully\s+|slowly\s+|also\s+)?"
    r"(?:moving|flying|advancing|progressing|heading|making)\b"
    r"|\bprogress(?:ing|ed)\b|\bmoving\s+(?:forward|steadily|straight|along|through|in|toward"
    r"|towards|ahead)\b"
    r"|\b(?:flying|flew|moved|advanced|advancing|continu(?:e|es|ing))\s+(?:straight|forward|ahead"
    r"|along|toward|towards|to\s+move|to\s+fly)\b|\bsuccessfully\s+(?:moved|flew|advanced)\b")
NOT_PROGRESS = re.compile(r"\b(?:not|no|n't|never|without|unable|cannot|can't|fail(?:ed|s)? to)\b")
NOTES_STUCK = re.compile(
    r"\b(?:did\s+not|didn't|has\s+not|hasn't|have\s+not|haven't|no\s+longer|never)\s+"
    r"(?:actually\s+|successfully\s+|really\s+|yet\s+)?"
    r"(?:move|moved|moving|advance|advanced|advancing|progress|change[d]?)\b"
    r"|\bmoved\s+0\.0\b|\b0\.0\s*m\b|\bstuck\b|\bstationary\b"
    r"|\bsame\s+(?:spot|position|place|location)\b|\bnot\s+(?:been\s+)?(?:making|made)\s+progress")
#: Prompts that carry the comparison lines (p10 on): shown after a blocked move?
COMPARE_PROMPTS = ("p10", "p11", "p12", "p13")
#: Heading in the reason (R8): a number of degrees, a compass word, and degree
#: arithmetic ("287 + 180", "heading 221 - 45"), two- or three-digit numbers either
#: side of a plus or minus. Coordinates do not match: their parts are split by a comma.
#: Step ranges ("steps 22-26") are excluded. R7: 23 reasons, every hit read by eye.
DEGREES = re.compile(r"\b\d{1,3}\s*(?:°|degrees?)")
COMPASS_WORD = re.compile(r"\b(?:north|south)(?:[- ]?(?:east|west))?\b|\b(?:east|west)(?:ward)?\b")
HEADING_ARITH = re.compile(r"(?<!steps )(?<!step )\b\d{2,3}(?:\s*(?:°|degrees?))?\s*[-+−]\s*\d{2,3}\b")
REVISIT_M = 1.0
REVISIT_GAP = 5
GOAL_REPORTS = ("ahead", "left", "right", "not_visible")

#: (counter, title, denominator counter)
COLUMNS = [("bearing", "reason cites bearing", "n"), ("distance", "reason cites distance", "n"),
           ("nearest", "nearest-bearing pick", "n"), ("obstacle", "obstacle word", "n"),
           ("turn", "turn-around pick", "n"), ("turn2", "two turn-arounds in a row", "pairs"),
           ("memory", "reason cites memory", "n"), ("position", "reason cites position", "n"),
           ("pose", "pose in manifest", "n"),
           ("blocked_after", "blocked forward move before", "n"),
           ("claim_after", "claims progress after a blocked move", "blocked_after"),
           ("note_after", "notes no movement after a blocked move", "blocked_after"),
           ("delivered", "comparison line shown after a blocked move", "blocked_after"),
           ("degrees", "reason cites degrees", "n"), ("compass", "reason uses a compass word", "n"),
           ("arith", "heading arithmetic", "n"),
           ("turn_in_view", "turn-around with the goal in view", "visible"),
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


def claims_progress(reason: str) -> bool:
    """Whether a reason says the drone is making progress (PROGRESS), per sentence."""
    return any(PROGRESS.search(s) and not NOT_PROGRESS.search(s)
               for s in SENTENCE.split(reason or ""))


def notes_no_movement(reason: str) -> bool:
    return any(NOTES_STUCK.search(s) for s in SENTENCE.split(reason or ""))


def blocked_forward(prev: Dict[str, Any], d: Dict[str, Any]) -> bool:
    """The move chosen at `prev` was a flight that moved < BLOCKED_M by `d`'s step."""
    a = ((prev.get("manifest") or {}).get("pose") or {}).get("position")
    b = ((d.get("manifest") or {}).get("pose") or {}).get("position")
    if not a or not b:
        return False
    chosen = any(x.get("index") == prev.get("index") and x.get("turn_around")
                 for x in (prev.get("manifest") or {}).get("actions", []))
    return not chosen and math.dist(a, b) < BLOCKED_M


def comparison_shown(run: Path, version: str, d: Dict[str, Any]) -> bool:
    """Re-render this decision's prompt from the recorded log and look for the line."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from server.decider import prompt as prompts
    from server.decider.recorder import Run
    p = prompts.get(version)
    memory = Run("evidence:{0}".format(run.name), run).memory(int(d["step"]))
    return "(blocked)" in p.render(p, d.get("manifest") or {}, memory, "not_visible")


def claims_goal(reason: str) -> bool:
    """Whether a reason says the goal is in view or in a direction now (GOAL_NOW)."""
    return any(GOAL_NOW.search(s) and not GOAL_NOT_NOW.search(s)
               for s in SENTENCE.split(reason or ""))


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
            was_turn = False
            prev_valid: Optional[Dict[str, Any]] = None
            version = info.get("prompt_version")
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
                turned = any(a.get("turn_around") and a["index"] == d.get("index")
                             for a in manifest.get("actions", []))
                c["turn"] += turned
                c["turn2"] += turned and was_turn
                c["turn_in_view"] += turned and truth in ("ahead", "left", "right")
                c["degrees"] += bool(DEGREES.search(reason))
                c["compass"] += bool(COMPASS_WORD.search(reason))
                c["arith"] += bool(HEADING_ARITH.search(reason))
                was_turn = turned
                c["position"] += bool(POSITION.search(reason))
                if not (d.get("error") or d.get("index") is None):
                    if prev_valid is not None and blocked_forward(prev_valid, d):
                        c["blocked_after"] += 1
                        c["claim_after"] += claims_progress(reason)
                        c["note_after"] += notes_no_movement(reason)
                        if version in COMPARE_PROMPTS:
                            c["delivered"] += comparison_shown(run, version, d)
                    prev_valid = d
                c["pose"] += here is not None and (manifest.get("pose") or {}).get("yaw") is not None
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
