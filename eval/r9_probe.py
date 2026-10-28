"""R9 probe for the orchestrated agent a13, offline, on recorded frames.

Two parts, both run against the live model before R9 may fly
(eval/phase2/R9_hail_mary/README.md, probe gate):

1. Perceiver (g03) on recorded clean frames, scored against ground truth from
   the manifest (evaluation only; the agent never reads it):
   - goal strip, from the goal's bearing and line of sight;
   - phantom goals on frames where the goal is not in view;
   - the floor in the strip of the move the drone then made, against what
     that move did (blocked or short means a wall within 1.5 m);
   - the old left/ahead/right report against g02's in-flight answer on the
     same frame, so a regression against the identifier R5-R8 flew shows.

2. Trap replay: steps where an earlier agent stood where it had already been
   blocked. Each is replayed through the real a13 step (orchestrator.decide)
   on a scratch copy of the run up to that step, and scored on whether the
   pick goes into the known-blocked heading again.

    python eval/r9_probe.py sample ROOT [ROOT ...] --out set.jsonl
    VLM_AGENT=a13 python eval/r9_probe.py run set.jsonl --out perceiver_a13.jsonl
    python eval/r9_probe.py report perceiver_a13.jsonl
    python eval/r9_probe.py sample-trap ROOT [ROOT ...] --out trap_set.jsonl
    VLM_AGENT=a13 python eval/r9_probe.py run-trap trap_set.jsonl --out trap_a13.jsonl
    python eval/r9_probe.py report-trap trap_a13.jsonl

ROOT is any directory holding recorded runs with frames (frames are not
committed; they live in the checkout or host that flew the round). Set paths
are absolute for that reason.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from server.decider import spatial  # noqa: E402

HALF_FOV = spatial.FOV_DEG / 2.0

#: The pre-registered gate (README). A probe that misses any of these stops R9.
GATE = {
    "strip_within_one_min": 0.90,     # goal in view: reported strip within one of truth
    "phantom_max": 0.05,              # goal not in view: reported as visible
    "legacy_drop_max": 0.05,          # left/ahead/right accuracy may not fall below g02's by more
    "false_wall_max": 0.20,           # completed moves whose strip was called blocked_near
    "trap_repeat_max": 0.25,          # trap steps where a13 picks the known-blocked heading
}


def _rows(run: Path) -> List[Dict[str, Any]]:
    path = run / "decisions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return sorted((r for r in rows if "step" in r), key=lambda r: r["step"])


def _runs(roots: List[str]) -> List[Path]:
    seen, out = set(), []
    for root in roots:
        for p in sorted(Path(root).resolve().rglob("decisions.jsonl")):
            if "_attempts" in p.parts or "replay" in p.parts:
                continue
            key = "/".join(p.parts[-6:-1])  # round/runs/site/arm/seed
            if key not in seen:
                seen.add(key)
                out.append(p.parent)
    return out


def true_strip(bearing_deg: float) -> str:
    """The strip a point at this bearing (positive left) falls in."""
    u = math.tan(math.radians(bearing_deg)) / math.tan(math.radians(HALF_FOV))
    for strip, edge in zip(spatial.STRIPS, (0.6, 0.2, -0.2, -0.6)):
        if u > edge:
            return strip
    return spatial.STRIPS[-1]


def true_range(distance: float) -> str:
    for name, top in (("touching", 2.0), ("near", 6.0), ("mid", 15.0)):
        if distance < top:
            return name
    return "far"


def truth_of(row: Dict[str, Any]) -> Dict[str, Any]:
    goal = (row.get("manifest") or {}).get("goal") or {}
    b = float(goal.get("bearing_deg", 180.0))
    d = float(goal.get("distance", 0.0))
    in_view = bool(goal.get("line_of_sight")) and abs(b) <= HALF_FOV
    return {"in_view": in_view, "bearing_deg": round(b, 1), "distance": round(d, 1),
            "strip": true_strip(b) if in_view else "not_visible",
            "range": true_range(d) if in_view else None}


def move_of(rows: List[Dict[str, Any]], k: int) -> Optional[Dict[str, Any]]:
    r = rows[k]
    if r.get("index") is None or k + 1 >= len(rows):
        return None
    chosen = next((a for a in r["manifest"]["actions"] if a["index"] == r["index"]), None)
    a = spatial.pose_xyh(r["manifest"].get("pose"))
    b = spatial.pose_xyh(rows[k + 1]["manifest"].get("pose"))
    if chosen is None or chosen.get("turn_around") or a is None or b is None:
        return None
    moved = spatial.dist(a[:2], b[:2])
    return {"theta_deg": float(chosen["theta_deg"]),
            "strip": spatial.strip_for(float(chosen["theta_deg"])),
            "moved": round(moved, 2), "blocked": moved < spatial.SHORT_BELOW_M}


def _read(path: str) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


# --- perceiver -------------------------------------------------------------------

def cmd_sample(args: argparse.Namespace) -> int:
    rng = random.Random("r9-perceiver")
    view: List[Dict[str, Any]] = []
    out_view: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    completed: List[Dict[str, Any]] = []
    for run in _runs(args.roots):
        rows = _rows(run)
        for k, r in enumerate(rows):
            if not r.get("clean_frame") or not (run / r["clean_frame"]).is_file():
                continue
            item = {"run": "/".join(run.parts[-5:]), "step": r["step"],
                    "clean": str(run / r["clean_frame"]), "truth": truth_of(r),
                    "move": move_of(rows, k),
                    "g02": (r.get("goal_identifier") or {}).get("goal")}
            (view if item["truth"]["in_view"] else out_view).append(item)
            if item["move"]:
                (blocked if item["move"]["blocked"] else completed).append(item)
    picked: Dict[str, Dict[str, Any]] = {}
    for pool in (view, out_view, blocked, completed):
        for item in rng.sample(pool, min(args.n, len(pool))):
            picked[item["clean"]] = item
    rows_out = sorted(picked.values(), key=lambda i: (i["run"], i["step"]))
    Path(args.out).write_text("".join(json.dumps(i) + "\n" for i in rows_out))
    print("{0} frames from pools: in view {1}, out of view {2}, blocked moves {3}, "
          "completed {4}".format(len(rows_out), len(view), len(out_view), len(blocked),
                                 len(completed)))
    return 0


async def _perceive(items: List[Dict[str, Any]], out: Path) -> None:
    from server.decider import agent, prompt as prompts, schema, vlm
    from server.decider.orchestrator import PERCEIVER_MAX_TOKENS, perception_from
    p = prompts.get(agent.current().features["orchestrator"]["perceiver"])
    try:
        for n, item in enumerate(items):
            frame = base64.b64encode(Path(item["clean"]).read_bytes()).decode()
            call = await vlm.call_structured(schema.PERCEIVER_SCHEMA_NAME, p.system,
                                             p.render(p, {}), frame, schema.perceiver_schema(),
                                             perception_from, PERCEIVER_MAX_TOKENS)
            rec = dict(item, agent=agent.current().version, perceiver=call.result,
                       error=call.error, latency_ms=round(call.latency_ms, 1))
            with out.open("a") as handle:
                handle.write(json.dumps(rec) + "\n")
            print("{0}/{1} {2} step {3}: {4} (truth {5})".format(
                n + 1, len(items), item["run"], item["step"],
                (call.result or {}).get("goal"), item["truth"]["strip"]), flush=True)
    finally:
        await vlm.aclose()


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = {r["clean"] for r in _read(args.out)} if out.is_file() else set()
    asyncio.run(_perceive([i for i in _read(args.set) if i["clean"] not in done], out))
    return 0


LEGACY = {"far_left": "left", "left": "left", "centre": "ahead", "right": "right",
          "far_right": "right", "not_visible": "not_visible"}


def _frac(xs: List[Dict[str, Any]], cond: Callable[[Dict[str, Any]], bool]) -> Optional[float]:
    return round(sum(1 for x in xs if cond(x)) / len(xs), 3) if xs else None


def perceiver_scores(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok = [r for r in rows if r.get("perceiver")]
    view = [r for r in ok if r["truth"]["in_view"]]
    out_view = [r for r in ok if not r["truth"]["in_view"]]
    idx = {s: i for i, s in enumerate(spatial.STRIPS)}

    def within_one(r: Dict[str, Any]) -> bool:
        got = r["perceiver"]["goal"]
        return got in idx and abs(idx[got] - idx[r["truth"]["strip"]]) <= 1

    def floor(r: Dict[str, Any]) -> str:
        return next(l["floor"] for l in r["perceiver"]["lanes"]
                    if l["strip"] == r["move"]["strip"])

    legacy = [r for r in ok if r.get("g02")]
    moves = [r for r in ok if r.get("move")]
    blocked = [r for r in moves if r["move"]["blocked"]]
    completed = [r for r in moves if not r["move"]["blocked"]]
    seen = [r for r in view if r["perceiver"]["goal"] != "not_visible"]
    return {
        "frames": len(rows), "answered": len(ok),
        "in_view": len(view), "out_of_view": len(out_view),
        "strip_exact": _frac(view, lambda r: r["perceiver"]["goal"] == r["truth"]["strip"]),
        "strip_within_one": _frac(view, within_one),
        "missed": _frac(view, lambda r: r["perceiver"]["goal"] == "not_visible"),
        "phantom": _frac(out_view, lambda r: r["perceiver"]["goal"] != "not_visible"),
        "range_exact": _frac(seen, lambda r: r["perceiver"]["goal_range"] == r["truth"]["range"]),
        "legacy_g03": _frac(legacy, lambda r: LEGACY[r["perceiver"]["goal"]]
                            == LEGACY[r["truth"]["strip"]]),
        "legacy_g02": _frac(legacy, lambda r: r["g02"] == LEGACY[r["truth"]["strip"]]),
        "blocked_moves": len(blocked), "completed_moves": len(completed),
        "wall_recall": _frac(blocked, lambda r: floor(r) == "blocked_near"),
        "false_wall": _frac(completed, lambda r: floor(r) == "blocked_near"),
        "doorway_rate": _frac(ok, lambda r: any(l["doorway"] for l in r["perceiver"]["lanes"])),
        "latency_ms_mean": round(sum(r["latency_ms"] for r in ok) / len(ok), 1) if ok else None,
    }


def cmd_report(args: argparse.Namespace) -> int:
    s = perceiver_scores(_read(args.results))
    print(json.dumps(s, indent=1))
    verdict = {
        "strip_within_one": (s["strip_within_one"] is not None
                             and s["strip_within_one"] >= GATE["strip_within_one_min"]),
        "phantom": s["phantom"] is not None and s["phantom"] <= GATE["phantom_max"],
        "legacy": (s["legacy_g03"] is not None and s["legacy_g02"] is not None
                   and s["legacy_g03"] >= s["legacy_g02"] - GATE["legacy_drop_max"]),
        "false_wall": s["false_wall"] is not None and s["false_wall"] <= GATE["false_wall_max"],
    }
    print("gate:", json.dumps(verdict), "->", "PASS" if all(verdict.values()) else "FAIL")
    return 0 if all(verdict.values()) else 1


# --- trap replay -------------------------------------------------------------------

def cmd_sample_trap(args: argparse.Namespace) -> int:
    """Steps where the drone stands within reach of an earlier blocked move,
    with both frames on disk. `recorded_repeat` marks the recorded pick going
    into that blocked heading again."""
    items = []
    for run in _runs(args.roots):
        rows = _rows(run)
        for k, r in enumerate(rows):
            if r.get("index") is None or not r.get("clean_frame") or not r.get("frame"):
                continue
            if not (run / r["clean_frame"]).is_file() or not (run / r["frame"]).is_file():
                continue
            here = spatial.pose_xyh(r["manifest"].get("pose"))
            if here is None:
                continue
            mem = spatial.rebuild(rows[:k], r["manifest"])
            if not any(b.kind == "blocked" and spatial.dist(here[:2], (b.x, b.y)) < spatial.BLOCK_NEAR_M
                       for b in mem.blocks):
                continue
            chosen = next((a for a in r["manifest"]["actions"] if a["index"] == r["index"]), {})
            hit = (None if chosen.get("turn_around")
                   else mem.block_for(here[:2], spatial.action_heading(chosen, here[2])))
            items.append({"run_dir": str(run), "run": "/".join(run.parts[-5:]), "k": k,
                          "step": r["step"], "recorded_pick": r["index"],
                          "recorded_repeat": hit is not None and hit.kind == "blocked"})
    Path(args.out).write_text("".join(json.dumps(i) + "\n" for i in items))
    print("{0} trap steps, {1} where the recorded agent repeated the blocked heading".format(
        len(items), sum(i["recorded_repeat"] for i in items)))
    return 0


async def _trap(items: List[Dict[str, Any]], out: Path) -> None:
    from server.decider import agent, orchestrator, vlm
    from server.decider.recorder import Run
    scratch = Path(tempfile.mkdtemp(prefix="r9_trap_"))
    try:
        for n, item in enumerate(items):
            run_dir = Path(item["run_dir"])
            rows = _rows(run_dir)
            k = item["k"]
            target = rows[k]
            work = scratch / "run_{0}".format(n)
            (work / "frames").mkdir(parents=True)
            # The run up to this step, as the a13 step reads it. The strategist
            # is marked as asked 8 steps ago, so its triggers fire as they would
            # mid-run rather than as at the start.
            prior = [dict(r) for r in rows[:k]]
            mark = max(0, target["step"] - 8)
            for r in prior:
                if r["step"] == mark:
                    r["strategist"] = {"replay": True}
                    r["target"] = None
            (work / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in prior))
            request = SimpleNamespace(
                step=target["step"], manifest=target["manifest"], frame_size=None,
                frame_png_b64=base64.b64encode((run_dir / target["frame"]).read_bytes()).decode(),
                clean_frame_png_b64=base64.b64encode(
                    (run_dir / target["clean_frame"]).read_bytes()).decode())
            await orchestrator.decide(request, Run("r9_trap_{0}".format(n), work), "frames/f.png")
            rec = _rows(work)[-1]
            here = spatial.pose_xyh(target["manifest"].get("pose"))
            chosen = next((a for a in target["manifest"]["actions"]
                           if a["index"] == rec.get("index")), {})
            mem = spatial.rebuild(rows[:k], target["manifest"])
            hit = (None if not chosen or chosen.get("turn_around") or here is None
                   else mem.block_for(here[:2], spatial.action_heading(chosen, here[2])))
            critic = rec.get("critic") or {}
            result = dict(item, agent=agent.current().version, pick=rec.get("index"),
                          error=rec.get("error"),
                          repeat=hit is not None and hit.kind == "blocked",
                          turn_around=bool(chosen.get("turn_around")),
                          tags=rec.get("tags"), target=rec.get("target"),
                          critic=critic.get("why"), critic_changed=critic.get("changed"),
                          strategist_trigger=(rec.get("strategist") or {}).get("trigger"),
                          reason=rec.get("reason"), navigator_text=rec.get("navigator_text"),
                          step_latency_ms=rec.get("step_latency_ms"))
            with out.open("a") as handle:
                handle.write(json.dumps(result) + "\n")
            print("{0}/{1} {2} step {3}: recorded [{4}]{5} -> a13 [{6}]{7}{8}".format(
                n + 1, len(items), item["run"], item["step"], item["recorded_pick"],
                " repeat" if item["recorded_repeat"] else "", result["pick"],
                " repeat" if result["repeat"] else "",
                " (critic)" if result["critic"] else ""), flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        await vlm.aclose()


def cmd_run_trap(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = {(d["run"], d["step"]) for d in _read(args.out)} if out.is_file() else set()
    asyncio.run(_trap([i for i in _read(args.set) if (i["run"], i["step"]) not in done], out))
    return 0


def cmd_report_trap(args: argparse.Namespace) -> int:
    rows = _read(args.results)
    ok = [r for r in rows if not r.get("error")]
    n = len(ok) or 1
    s = {
        "steps": len(rows), "answered": len(ok),
        "recorded_repeat": round(sum(r["recorded_repeat"] for r in ok) / n, 3),
        "a13_repeat": round(sum(r["repeat"] for r in ok) / n, 3),
        "a13_turn_around": round(sum(r["turn_around"] for r in ok) / n, 3),
        "critic_fired": sum(1 for r in ok if r["critic"]),
        "critic_changed": sum(1 for r in ok if r["critic_changed"]),
        "strategist_called": sum(1 for r in ok if r["strategist_trigger"]),
        "step_latency_ms_mean": round(sum(r["step_latency_ms"] or 0 for r in ok) / n, 1),
    }
    print(json.dumps(s, indent=1))
    passed = s["a13_repeat"] <= GATE["trap_repeat_max"]
    print("gate: trap_repeat", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="build the perceiver set from recorded runs")
    s.add_argument("roots", nargs="+")
    s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=40, help="frames per pool (in view, out of "
                   "view, blocked move, completed move)")
    r = sub.add_parser("run", help="ask a13's perceiver about every frame in the set")
    r.add_argument("set")
    r.add_argument("--out", required=True)
    p = sub.add_parser("report", help="score the perceiver and apply the gate")
    p.add_argument("results")
    st = sub.add_parser("sample-trap", help="build the trap set from recorded runs")
    st.add_argument("roots", nargs="+")
    st.add_argument("--out", required=True)
    rt = sub.add_parser("run-trap", help="replay every trap step through the a13 step")
    rt.add_argument("set")
    rt.add_argument("--out", required=True)
    pt = sub.add_parser("report-trap", help="score the trap replay and apply the gate")
    pt.add_argument("results")
    args = parser.parse_args()
    if args.cmd in ("run", "run-trap") and os.environ.get("VLM_AGENT") != "a13":
        raise SystemExit("set VLM_AGENT=a13")
    return {"sample": cmd_sample, "run": cmd_run, "report": cmd_report,
            "sample-trap": cmd_sample_trap, "run-trap": cmd_run_trap,
            "report-trap": cmd_report_trap}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
