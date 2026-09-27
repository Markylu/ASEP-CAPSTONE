#!/usr/bin/env python3
"""Auto pre-label for the phase 1 failure-mode rubric (docs/phase1-test-plan.md §9).

    python eval/phase1_label.py --mini-phase 1A

Writes <mini-phase>/labels.csv with `auto_label` and `ack_step` filled and
`label` blank: every run still gets a manual review (read the post-change
reasons, watch the replay) before `label` is filled. Re-running keeps whatever
manual columns are already there. The evidence behind each auto label goes to
auto_labels.json beside it.

Only the current valid attempt of each cell is labelled. Needs steps.jsonl,
which git ignores; `eval/replay.py` regenerates it.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase1 import (CHANGE_EVENTS, TRIGGER_X, crossing_step,  # noqa: E402
                    latest_row, load_matrix, order_of, phase_dir, read_json,
                    read_jsonl, run_dir_for)

LABEL_FIELDS = ["run_id", "site", "arm", "seed", "auto_label", "label", "ack_step",
                "tags", "override_note", "reviewer", "date"]

#: §9 auto pass: words that mean the reason noticed the change.
ACK_KEYWORDS = ("closed", "blocked", "wall", "obstacle", "box", "no longer",
                "dead end", "cube", "shut", "barrier", "in the way")
#: "door" alone is not enough: on s02/s02v the doors are in frame from spawn.
#: It counts only in a sentence that also says what state the door is in.
DOOR_STATES = ("closed", "closing", "shut", "open", "opened", "opening", "blocked",
               "locked")

#: §9 thresholds, fixed before 1A.
ACK_WINDOW = 5
TOWARD_GOAL_DEG = 30.0
TOWARD_GOAL_MIN = 3
COLLISION_SHARE = 0.5

#: s03 geometry (site.json `condition`): tines span x in [-6, 5], L at z in
#: [3.5, 6.5], R at z in [-6.5, -3.5]; the exit wall's far face is x = -7.
S03_TINE_X = (-6.0, 5.0)
S03_TINE_Z = {"L": (3.5, 6.5), "R": (-6.5, -3.5)}
S03_EXIT_X = -7.0
#: s02 wall is centred on x = 0, 1 m thick.
S02_WALL_FAR_X = -0.5
#: "past the cube's x" (§9): the s01 cube is centred at x = -2.
S01_CUBE_X = -2.0


def acknowledges(reason: str) -> bool:
    """§9 auto pass: does this reason refer to the change?"""
    text = reason.lower()
    if any(k in text for k in ACK_KEYWORDS):
        return True
    return any("door" in sentence and any(s in sentence for s in DOOR_STATES)
               for sentence in re.split(r"[.!?;]", text))


def tine_of(position: List[float]) -> Optional[str]:
    x, z = position[0], position[2]
    if not S03_TINE_X[0] <= x <= S03_TINE_X[1]:
        return None
    for side, (lo, hi) in S03_TINE_Z.items():
        if lo <= z <= hi:
            return side
    return None


def split_step(site: str, arm: str, run_dir: Path, steps: List[Dict[str, Any]],
               events: List[Dict[str, Any]]) -> Optional[int]:
    """The move the change happened at, or would have for a static arm (§8)."""
    changes = [e for e in events if e.get("name") in CHANGE_EVENTS]
    if arm == "dynamic":
        return changes[0].get("step") if changes else None
    if TRIGGER_X[site] is not None:
        # The move that would have fired the trigger in the dynamic arm.
        return crossing_step(site, run_dir)
    # s03: the step the agent crosses x = 0 inside a tine.
    return next((s["step"] for s in steps
                 if s["position"][0] <= 0.0 and tine_of(s["position"])), None)


def got_through(site: str, arm: str, post: List[Dict[str, Any]]) -> bool:
    """§9 label 3: did the agent get through the route that is open now?"""
    xs = [s["position"][0] for s in post]
    if not xs:
        return False
    if site == "s01":
        return min(xs) < S01_CUBE_X
    if site.startswith("s02"):
        # With B shut, crossing the wall at all means through the new door.
        return min(xs) < S02_WALL_FAR_X
    if arm == "dynamic":
        # s03: the committed tine is closed, so "through" = entered the other.
        tines = [tine_of(s["position"]) for s in post]
        first = next((t for t in tines if t), None)
        return any(t not in (None, first) for t in tines)
    return min(xs) < S03_EXIT_X


def label_run(site: str, arm: str, run_dir: Path) -> Dict[str, Any]:
    metrics = read_json(run_dir / "metrics.json")
    steps = read_jsonl(run_dir / "steps.jsonl")
    events = read_jsonl(run_dir / "events.jsonl")
    decisions = sorted(read_jsonl(run_dir / "decisions.jsonl"), key=lambda d: d["step"])

    split = split_step(site, arm, run_dir, steps, events)
    # Move k is chosen by decision k-1, so decisions from `split` on are the
    # ones made with the change already on screen.
    post_steps = [s for s in steps if split is None or s["step"] > split]
    post_decisions = [d for d in decisions if split is None or d["step"] >= split]

    ack = next((d for d in post_decisions if acknowledges(d.get("reason") or "")), None)
    ack_step = ack["step"] if ack else None
    window = post_decisions[:ACK_WINDOW]
    acked_in_window = ack is not None and ack in window

    toward = 0
    for d in window:
        manifest = d.get("manifest") or {}
        actions = {a["index"]: a for a in manifest.get("actions", [])}
        action = actions.get(d.get("index"))
        bearing = (manifest.get("goal") or {}).get("bearing_deg")
        if action and bearing is not None and not action.get("turn_around") \
                and abs(action["theta_deg"] - bearing) <= TOWARD_GOAL_DEG:
            toward += 1

    through = got_through(site, arm, post_steps)
    collided = sum(1 for s in post_steps if s.get("collided"))
    share = collided / len(post_steps) if post_steps else 0.0

    # First match wins, in the order §9 lists them.
    acknowledged = arm != "dynamic" or ack is not None
    if metrics.get("goal_reached"):
        label = "success"
    elif arm == "dynamic" and split is None:
        label = "pre_change_failure"
    elif arm == "dynamic" and not acked_in_window and toward >= TOWARD_GOAL_MIN:
        label = "ignore_change"
    elif acknowledged and not through:
        label = "replan_failure"
    elif acknowledged and share >= COLLISION_SHARE:
        label = "collision"
    elif through:
        label = "timeout"
    else:
        label = "unclassified"

    return {"auto_label": label, "ack_step": ack_step, "evidence": {
        "split_step": split, "post_steps": len(post_steps),
        "post_collisions": collided, "collision_share": round(share, 3),
        "acknowledged": ack is not None, "acked_in_first_5": acked_in_window,
        "toward_goal_in_first_5": toward, "got_through": through,
        "min_x": round(min((s["position"][0] for s in steps), default=0.0), 2),
        "goal_reached": metrics.get("goal_reached"),
        "final_goal_distance_m": metrics.get("final_goal_distance_m"),
        "end_reason": metrics.get("end_reason"),
    }}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mini-phase", required=True)
    args = parser.parse_args()
    mp = args.mini_phase
    folder = phase_dir(mp)
    labels_path = folder / "labels.csv"

    existing: Dict[str, Dict[str, str]] = {}
    if labels_path.is_file():
        with labels_path.open(newline="") as handle:
            existing = {r["run_id"]: r for r in csv.DictReader(handle)}

    rows: List[Dict[str, Any]] = []
    evidence: Dict[str, Any] = {}
    skipped = 0
    matrix = load_matrix()
    for site, arm, seed in order_of(mp):
        row = latest_row(matrix, mp, site, arm, seed)
        if row["status"] != "valid":
            skipped += 1
            continue
        result = label_run(site, arm, run_dir_for(mp, site, arm, seed))
        manual = existing.get(row["run_id"], {})
        rows.append({
            "run_id": row["run_id"], "site": site, "arm": arm, "seed": seed,
            "auto_label": result["auto_label"],
            "label": manual.get("label", ""),
            "ack_step": "" if result["ack_step"] is None else result["ack_step"],
            "tags": manual.get("tags", ""), "override_note": manual.get("override_note", ""),
            "reviewer": manual.get("reviewer", ""), "date": manual.get("date", ""),
        })
        evidence[row["run_id"]] = result["evidence"]
        print("{0:<34} {1:<18} {2}".format(row["run_id"], result["auto_label"],
                                          json.dumps(result["evidence"])))

    rows.sort(key=lambda r: (r["site"], r["arm"], int(r["seed"])))
    with labels_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (folder / "auto_labels.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("{0} labelled, {1} skipped (not valid)".format(len(rows), skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
