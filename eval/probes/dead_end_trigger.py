"""Where a closed-door read could trigger a dead-end latch, on flown records. No model.

R38 asks whether a66 can be told "this corridor ends at a closed door" by code.
The trigger named in the brief is a closed-door read. Every recorded step
holds the perceiver's lanes, `doorway` per strip as it stood after the door
confirmer. Three candidate triggers are counted per run, on the change arms of
Round F, R32P and R35, against where the drone stood (evaluation only):

  asked   a closed-door read in the centre three strips. These are the steps
          probe DE's confirmer (e01) would be asked on.
  strict  the centre strip reads a closed door within 5 m (the memory's range
          for that strip's floor end), the goal lies within 35 degrees of the
          heading, and the same held on an earlier step no more than 3 back.
  trail   an asked step that ends a straight run of 5 m or more of trail begun
          at a turn of 60 degrees or more (a corridor turned into, by trail
          shape alone).

A trigger is right in s03 when the drone stands in the tine whose door is shut,
facing that door, after the door shut. It is wrong anywhere in s02: the hall is
not a dead end, and a68's seal boxed the drone there (R30 shakedown).

    python eval/probes/dead_end_trigger.py [--folders final,R32P_repeat_a66,R35_wall_turn_only]
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
import common  # noqa: E402
from common import REPO_ROOT, load, metrics, spatial, switch_step, xy  # noqa: E402

FOLDERS = "final,R32P_repeat_a66,R35_wall_turn_only"
CENTRAL = spatial.CENTRAL_STRIPS  # the strips a78's confirmer is asked on
#: Metres the memory places a closed door at, by the strip's floor end (a17d).
DOOR_RANGE_M = dict(spatial.PARAMS_A17D["door_suspect_m"], **spatial.PARAMS_A17D["door_wall_m"])
STRICT = {"range_m": 5.0, "goal_deg": 35.0, "within_steps": 3}
TRAIL = {"run_m": 5.0, "turn_deg": 60.0, "axis_m": 4.0, "off_axis_deg": 45.0, "min_seg_m": 0.3}
FACING_DEG = 60.0  # of the exit wall (-x), for "facing the shut door"


def run_dirs(folder: str) -> List[Path]:
    return [d.parent for d in sorted(
        (REPO_ROOT / "eval" / "phase2" / folder).glob("runs/*/*/seed*/decisions.jsonl"))]


def turn(a: float, b: float) -> float:
    return abs(spatial.wrap(a - b))


def straight_run(trail: List[spatial.Point]) -> Tuple[float, Optional[float]]:
    """(metres of straight trail ending at the newest point, degrees turned
    where that run began), the turn None when the run reaches the spawn."""
    pts = [trail[0]]
    for p in trail[1:]:
        if spatial.dist(p, pts[-1]) >= TRAIL["min_seg_m"]:
            pts.append(p)
    if len(pts) < 3:
        return 0.0, None

    def back_from(i: int) -> int:
        j, gone = i, 0.0
        while j > 0 and gone < TRAIL["axis_m"]:
            gone += spatial.dist(pts[j - 1], pts[j])
            j -= 1
        return j

    axis = spatial.bearing(pts[back_from(len(pts) - 1)], pts[-1])
    run, i = 0.0, len(pts) - 1
    while i > 0 and turn(spatial.bearing(pts[i - 1], pts[i]), axis) <= TRAIL["off_axis_deg"]:
        run += spatial.dist(pts[i - 1], pts[i])
        i -= 1
    if i <= 0:
        return run, None
    return run, turn(spatial.bearing(pts[back_from(i)], pts[i]), axis)


def shut_tine(arm: str, run: Path, rows: List[Dict[str, Any]], sw: Optional[int]) -> Optional[str]:
    """s03: 'tine_L' or 'tine_R', the one whose exit door is shut."""
    if arm == "final":
        closed = json.loads((run / "run.json").read_text()).get("final_closed") or []
        return {"BranchL": "tine_L", "BranchR": "tine_R"}.get(closed[0]) if closed else None
    if sw is None:
        return None
    at = next((xy(r) for r in rows if r["step"] >= sw and xy(r)), None)
    return ("tine_L" if at[1] < 0 else "tine_R") if at else None


def where(site: str, arm: str, shut: Optional[str], sw: Optional[int], here: spatial.Pose,
          step: int) -> str:
    """Where an asked step stood: 'shut_tine' (in the tine whose door is shut,
    after it shut, facing the exit wall), 's03_other' or 's02'."""
    if site != "s03":
        return "s02"
    if (shut is not None and common.s03_region(here[:2]) == shut
            and (arm == "final" or (sw is not None and step >= sw))
            and turn(here[2], 180.0) <= FACING_DEG):
        return "shut_tine"
    return "s03_other"


def closed_door_places(rows: List[Dict[str, Any]], radius_m: float = 4.0) -> Dict[int, int]:
    """Per step, how many distinct places a closed door has been read at so far
    in the run (this step included): the points the memory keeps for closed
    doors (SpatialMemory.closed_doors: along the strip, at the range its floor
    end stands for), counted as one place when within radius_m of an earlier
    one. Everything in it is the agent's own: its pose and its perceiver's
    reads. A hall whose wall has several doors collects places; a corridor
    with one door at its end does not."""
    places: List[spatial.Point] = []
    out: Dict[int, int] = {}
    for r in rows:
        here = xy(r)
        if here is not None:
            for lane in ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []:
                rng = DOOR_RANGE_M.get(lane.get("floor_end"))
                if lane.get("doorway") == "closed" and rng is not None:
                    at = spatial.ahead(here[:2], (here[2] + spatial.strip_offset(lane["strip"]))
                                       % 360.0, rng)
                    if all(spatial.dist(at, q) > radius_m for q in places):
                        places.append(at)
        out[r["step"]] = len(places)
    return out


def read_run(run: Path) -> Dict[str, Any]:
    site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
    rows = [r for r in load(run) if r.get("manifest")]
    met = metrics(run)
    sw = switch_step(met)
    shut = shut_tine(arm, run, rows, sw) if site == "s03" else None
    out: Dict[str, Any] = {
        "site": site, "arm": arm, "seed": seed, "won": bool(met.get("goal_reached")),
        "steps": len(rows), "switch": sw, "crossed": None, "closed_reads": 0,
        "first_closed": None, "asked": [], "asked_right": [], "strict": None, "trail": None}
    trail: List[spatial.Point] = []
    hits: List[int] = []
    for r in rows:
        here = xy(r)
        if here is None:
            continue
        trail.append(here[:2])
        step = r["step"]
        if out["crossed"] is None and here[0] < (-7.0 if site == "s03" else 0.0):
            out["crossed"] = step
        lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
        closed = {l["strip"]: l.get("floor_end") for l in lanes if l.get("doorway") == "closed"}
        if not closed:
            continue
        out["closed_reads"] += 1
        if out["first_closed"] is None:
            out["first_closed"] = step
        if not any(s in closed for s in CENTRAL):
            continue
        out["asked"].append(step)
        if where(site, arm, shut, sw, here, step) == "shut_tine":
            out["asked_right"].append(step)
        rng = DOOR_RANGE_M.get(closed.get("centre")) if "centre" in closed else None
        goal_deg = ((r["manifest"].get("goal") or {}).get("bearing_deg"))
        if (rng is not None and rng <= STRICT["range_m"] and goal_deg is not None
                and abs(goal_deg) <= STRICT["goal_deg"]):
            if out["strict"] is None and hits and step - hits[-1] <= STRICT["within_steps"]:
                out["strict"] = step
            hits.append(step)
        if out["trail"] is None:
            run_m, turned = straight_run(trail)
            if run_m >= TRAIL["run_m"] and turned is not None and turned >= TRAIL["turn_deg"]:
                out["trail"] = step
    return out


def before_crossing(r: Dict[str, Any], key: str) -> bool:
    """Whether the trigger fired while the drone was still on the near side."""
    return r[key] is not None and (r["crossed"] is None or r[key] < r["crossed"])


def med(xs: List[int]) -> str:
    return str(int(statistics.median(xs))) if xs else "-"


def show(v: Any) -> str:
    return "-" if v is None else str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", default=FOLDERS)
    ap.add_argument("--out", default=str(REPO_ROOT / "eval/phase2/_probes/dead_end/trigger.txt"))
    args = ap.parse_args()
    runs: List[Dict[str, Any]] = []
    for folder in args.folders.split(","):
        for run in run_dirs(folder):
            if run.parts[-2] == "initial":
                continue
            runs.append(dict(read_run(run), folder=folder.split("_", 1)[0]))

    lines = ["Closed-door reads as a dead-end trigger: {0} change-arm runs of {1}".format(
        len(runs), args.folders), ""]
    lines.append("1. Runs a trigger fired in, before the drone crossed (s02: x < 0; s03: x < -7)")
    row = "{0:<22}{1:>5}{2:>9}{3:>9}{4:>9}{5:>14}{6:>14}"
    lines.append(row.format("group", "runs", "asked", "strict", "trail", "closed reads",
                            "asked steps"))
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = collections.defaultdict(list)
    for r in runs:
        groups[("s03" if r["site"] == "s03" else "s02", r["arm"],
                "won" if r["won"] else "lost")].append(r)
    for key in sorted(groups):
        g = groups[key]
        lines.append(row.format(
            " ".join(key), len(g),
            sum(1 for r in g if r["asked"]
                and (r["crossed"] is None or r["asked"][0] < r["crossed"])),
            sum(before_crossing(r, "strict") for r in g),
            sum(before_crossing(r, "trail") for r in g),
            "{0}-{1}".format(min(r["closed_reads"] for r in g), max(r["closed_reads"] for r in g)),
            "{0}-{1}".format(min(len(r["asked"]) for r in g), max(len(r["asked"]) for r in g))))
    s02 = [r for r in runs if r["site"] != "s03"]
    s03d = [r for r in runs if r["site"] == "s03" and r["arm"] == "dynamic"]
    lines += ["", "s02 change arms, {0} runs: strict fired in {1}, trail in {2}".format(
        len(s02), sum(before_crossing(r, "strict") for r in s02),
        sum(before_crossing(r, "trail") for r in s02)),
        "s03 dynamic, {0} runs: strict fired in {1}, trail in {2}".format(
            len(s03d), sum(r["strict"] is not None for r in s03d),
            sum(r["trail"] is not None for r in s03d))]

    lines += ["", "2. Asked steps (probe DE's frame set) by where the drone stood"]
    right = sum(len(r["asked_right"]) for r in runs if r["site"] == "s03")
    other = sum(len(r["asked"]) - len(r["asked_right"]) for r in runs if r["site"] == "s03")
    lines.append("s03, in the shut tine facing its door: {0}".format(right))
    lines.append("s03, anywhere else: {0}".format(other))
    lines.append("s02: {0}".format(sum(len(r["asked"]) for r in s02)))

    row = "{0:<8}{1:<9}{2:<7}{3:<6}{4:>7}{5:>8}{6:>8}{7:>8}{8:>8}{9:>8}{10:>8}{11:>11}"
    lines += ["", "3. s03 run by run (steps; '-' never)",
              row.format("round", "arm", "seed", "won", "switch", "closed", "asked", "right",
                         "n right", "strict", "trail", "left@right")]
    for r in sorted((r for r in runs if r["site"] == "s03"),
                    key=lambda r: (r["arm"], r["folder"], r["seed"])):
        first_right = r["asked_right"][0] if r["asked_right"] else None
        lines.append(row.format(
            r["folder"], r["arm"], r["seed"], "yes" if r["won"] else "no", show(r["switch"]),
            show(r["first_closed"]), show(r["asked"][0] if r["asked"] else None),
            show(first_right), len(r["asked_right"]), show(r["strict"]), show(r["trail"]),
            show(None if first_right is None else 60 - first_right)))
    lost = [r for r in s03d if not r["won"]]
    firsts = [r["asked_right"][0] for r in lost if r["asked_right"]]
    lines += ["", "s03 dynamic losses: a right asked step in {0} of {1}, first at median step {2}; "
              "{3} with 25 or more steps left".format(
                  len(firsts), len(lost), med(firsts), sum(1 for s in firsts if 60 - s >= 25))]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
