"""Probe A0 (no model): do recorded picks follow list position, or content?

Belief under test (docs/research/probe-plan.md, A): the model favours some list
positions, so menu order is a hidden lever. Strategist menus are ordered by code
(frontiers, doorways, backtrack, then explore), so position can be compared
with content: an item is "good" when its ground-truth path to the goal is at
least 1 m shorter than the drone's (geo, the run's own door state). Navigator
actions are ordered by angle, so there only a left/right lean can be read: the
same note on mirrored slots (1<->5, 2<->4) should be picked equally often.

    python3 eval/probes/a0.py [--first 11] [--last 26]

Gate: eval/phase2/_probes/a0/README.md (committed before this ran).
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PROBES, load, metrics, path_to_goal, pct, runs, s03_region,  # noqa: E402
                    s03_shut_side, switch_step, true_goal, world, world_key, write_jsonl, xy)

GOOD_GAIN_M = 1.0
MIRROR = {1: 5, 2: 4, 4: 2, 5: 1}
TOWARD = "toward your target"
OUT = PROBES / "a0"


def strategist_items(run, rows, met, goal):
    """One row per menu item of every strategist call with a menu."""
    out = []
    for r in rows:
        s = r.get("strategist") or {}
        menu = s.get("menu") or []
        picked = (s.get("result") or {}).get("target")
        here = xy(r)
        if not menu or picked is None or here is None or goal is None:
            continue
        key = world_key(run["site"], run["arm"], r["step"], rows, met)
        free = world(run["site"], run["arm"], r["step"], rows, met)
        d_here = path_to_goal(key, free, goal, here[:2])
        shut = None
        if run["site"] == "s03":
            side = s03_shut_side(run["arm"], rows, switch_step(met))
            shut = side is not None and s03_region(here[:2]) == "tine_" + side
        for pos, item in enumerate(menu, start=1):
            d_item = path_to_goal(key, free, goal, (item["x"], item["y"]))
            out.append({
                "run": "{0}/{1}/{2}".format(run["round"], run["site"], run["arm"]),
                "step": r["step"], "n": len(menu), "pos": pos, "id": item["id"],
                "kind": item["kind"],
                "good": math.isfinite(d_item) and (d_here - d_item) >= GOOD_GAIN_M,
                "picked": item["id"] == picked, "explore_picked": picked == "explore",
                "in_shut_tine": shut,
            })
    return out


def navigator_calls(run, rows):
    out = []
    for r in rows:
        tags = r.get("tags") or {}
        if r.get("index") is None or not tags:
            continue
        out.append({"picked": int(r["index"]),
                    "notes": {int(k): tuple(sorted(v)) for k, v in tags.items()}})
    return out


def rate(c: Counter) -> float:
    return c["k"] / c["n"] if c["n"] else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=11)
    ap.add_argument("--last", type=int, default=26)
    args = ap.parse_args()

    items, calls = [], []
    for run in runs(args.first, args.last):
        rows = load(run["path"])
        met = metrics(run["path"])
        items += strategist_items(run, rows, met, true_goal(rows))
        calls += navigator_calls(run, rows)
    write_jsonl(OUT / "items.jsonl", items)

    lines = ["A0 over R{0}-R{1}: {2} strategist menu items in {3} calls; {4} navigator calls".format(
        args.first, args.last, len(items), len({(i["run"], i["step"]) for i in items}), len(calls))]

    # 1. Strategist: pick rate by position, within good and within not-good items.
    lines.append("\n## Strategist: pick rate by list position (menus with 2+ items)")
    by = defaultdict(Counter)
    for i in items:
        if i["n"] < 2:
            continue
        grp = "pos1" if i["pos"] == 1 else "pos2+"
        by[(i["good"], grp)]["n"] += 1
        by[(i["good"], grp)]["k"] += i["picked"]
    eff = {}
    for good in (True, False):
        a, b = by[(good, "pos1")], by[(good, "pos2+")]
        eff[good] = (rate(a) - rate(b)) * 100
        lines.append("  {0:9s} first listed {1}; listed 2nd or later {2}; position effect "
                     "{3:+.0f} pts".format("good" if good else "not good", pct(a["k"], a["n"]),
                                           pct(b["k"], b["n"]), eff[good]))
    content = {}
    for grp in ("pos1", "pos2+"):
        content[grp] = (rate(by[(True, grp)]) - rate(by[(False, grp)])) * 100
        lines.append("  content effect at {0}: good minus not-good {1:+.0f} pts".format(
            grp, content[grp]))
    first = [i for i in items if i["pos"] == 1]
    lines.append("  explore picked on " + pct(sum(i["explore_picked"] for i in first), len(first))
                 + " of calls")

    # 2. By kind; backtrack "listed but ignored".
    lines.append("\n## Strategist: pick rate when listed, by kind")
    kinds = defaultdict(Counter)
    for i in items:
        kinds[i["kind"]]["n"] += 1
        kinds[i["kind"]]["k"] += i["picked"]
        if i["kind"] == "backtrack" and i["in_shut_tine"]:
            kinds["backtrack, in s03 shut tine"]["n"] += 1
            kinds["backtrack, in s03 shut tine"]["k"] += i["picked"]
    for k, c in sorted(kinds.items()):
        lines.append("  {0:30s} {1}".format(k, pct(c["k"], c["n"])))

    # 3. Navigator: left/right lean.
    lines.append("\n## Navigator: left/right lean (slots 1,2 left; 4,5 right)")
    toward = defaultdict(Counter)
    tie = Counter()
    for c in calls:
        with_toward = [i for i, n in c["notes"].items() if any(TOWARD in x for x in n)]
        if len(with_toward) == 1 and with_toward[0] in MIRROR:
            slot = with_toward[0]
            toward[slot]["n"] += 1
            toward[slot]["k"] += c["picked"] == slot
        for left in (1, 2):
            right = MIRROR[left]
            if (left in c["notes"] and right in c["notes"]
                    and c["notes"][left] == c["notes"][right] and c["picked"] in (left, right)):
                tie["n"] += 1
                tie["k"] += c["picked"] == left
    leans = []
    for left in (1, 2):
        right = MIRROR[left]
        a, b = toward[left], toward[right]
        if a["n"] and b["n"]:
            leans.append((rate(a) - rate(b)) * 100)
        lines.append("  'toward' on slot {0}: followed {1}; on slot {2}: followed {3}".format(
            left, pct(a["k"], a["n"]), right, pct(b["k"], b["n"])))
    lean = sum(leans) / len(leans) if leans else float("nan")
    lines.append("  lean (left minus right, mean of the two pairs): {0:+.0f} pts".format(lean))
    lines.append("  same notes on mirrored slots, one of them picked: left " + pct(tie["k"], tie["n"]))

    # Gate readout (thresholds from the README).
    lines.append("\n## Gate")
    pos_sig = any(v >= 15 for v in eff.values() if not math.isnan(v))
    lines.append("  position signal (pos1 minus pos2+ >= 15 pts, good or not-good): "
                 + ("YES" if pos_sig else "no"))
    lines.append("  content signal (good minus not-good >= 15 pts at both positions): "
                 + ("YES" if all(v >= 15 for v in content.values()) else "no"))
    share = rate(tie) if tie["n"] else 0.5
    lean_flag = (not math.isnan(lean) and abs(lean) >= 10) or (
        tie["n"] >= 50 and not 0.40 <= share <= 0.60)
    lines.append("  left/right lean (|lean| >= 10 pts, or tie share outside 40-60% with n >= 50): "
                 + ("YES" if lean_flag else "no"))
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
