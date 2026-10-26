"""R11 probe for a15 and a16 (the agent VLM_AGENT names, a15 by default), on recorded runs (eval/phase2/R11_goal_default/README.md).

Code-only lines, no model (`offline`):
1. Block memory: the near-repeat collisions of R9, R10C and R10 (a stopped-short
   pick within 2 m and 45 degrees of an earlier block; 36 of 37 had no note),
   rebuilt with a15's memory: does the pick now carry "blocked here before" or
   "stopped short here before"?
2. Route planner: on R10's steps, with the goal standing, how often a15's
   planner keeps it (the way toward it open on a15's map, and no stall).
3. Wall-aware toward: R10's steps re-tagged with a15's memory; "toward your
   target" on an action with a wall, blocked or stopped-short note must not occur.
4. Leaks: no R10 navigator text words the goal's true distance and direction
   (views.goal_leaks), and none in the smoke run below.
Not gated: `smoke` drives a15's real step (orchestrator.decide) over R10's
recorded manifests with stub replies (perceiver as recorded, navigator R10's
pick where offered, q03 the first doorway), so every stage and record field is
exercised; it says nothing about how a15 flies.

Live lines (`sample-*` build the sets from records alone; `run-*` need the
model and, for the navigator, R10's frames on sctsvr6):
- q03 on R10's steps where a15's planner would ask for a detour;
- p14 on R10's steps where "toward" sat on a walled action and a move ahead
  was open, re-tagged as a15 tags them.

    python eval/r11_probe.py offline --r9 eval/phase2/R9_hail_mary/runs \\
        --r10c eval/phase2/R10C_a13_control/runs --r10 eval/phase2/R10_goal_planner/runs
    python eval/r11_probe.py smoke eval/phase2/R10_goal_planner/runs
    python eval/r11_probe.py sample-detour eval/phase2/R10_goal_planner/runs --out detour_set.jsonl
    VLM_AGENT=a15 python eval/r11_probe.py run-detour detour_set.jsonl --out detour_a15.jsonl
    python eval/r11_probe.py sample-toward <R10 runs with frames> --out toward_set.jsonl
    VLM_AGENT=a15 python eval/r11_probe.py run-toward toward_set.jsonl --out toward_a15.jsonl
    python eval/r11_probe.py report detour_a15.jsonl toward_a15.jsonl

Evaluation only: the probe reads the manifest's goal ground truth to score.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

from server.decider import orchestrator, planner, prompt as prompts, spatial, views  # noqa: E402
from spatial_replay import (REPEAT_NEAR_M, REPEAT_WITHIN_DEG, GOALWARD_M, goal_gain,  # noqa: E402
                            label, load, memory_at, runs_under)

#: The gate (README, "Probe gate"). A probe that misses any of these stops R11.
GATE = {
    "block_noted_min": 30,        # of the 37 near-repeat collisions in R9, R10C, R10
    "planner_goal_min": 0.50,     # R10 steps where a15's planner keeps the goal
    "toward_not_open_max": 0,     # a15 tags: "toward" on a walled or blocked action
    "leaks_max": 0,               # navigator texts wording the goal's true position
    "detour_goalward_min": 0.60,  # q03's detour >= 3 m nearer the goal than the drone
    "detour_explore_max": 0.10,   # q03 chooses "explore"
    "toward_open_min": 0.80,      # p14's pick carries no not-open note
}

#: The notes that say a forward move is not open; the first two are memory's.
NOT_OPEN = spatial._NOT_OPEN
BLOCK_NOTES = NOT_OPEN[:2]


def _read(path: str) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def _agent() -> str:
    return os.environ.get("VLM_AGENT", "a15").strip() or "a15"


def _cfg() -> spatial.SpatialConfig:
    from server.decider import agent
    cfg = agent.get(_agent()).spatial_config
    assert cfg is not None and cfg.name in ("a15", "a16"), _agent()
    return cfg


def _a15(rows: List[Dict[str, Any]], k: int) -> spatial.SpatialMemory:
    """The probed agent's memory (a15 or a16) as of decision k."""
    r = rows[k]
    return spatial.rebuild(rows[:k], r["manifest"], (r.get("perceiver") or {}).get("result"),
                           _cfg())


def _moved(rows: List[Dict[str, Any]], k: int) -> Optional[float]:
    if k + 1 >= len(rows):
        return None
    a = spatial.pose_xyh(rows[k]["manifest"].get("pose"))
    b = spatial.pose_xyh(rows[k + 1]["manifest"].get("pose"))
    return None if a is None or b is None else spatial.dist(a[:2], b[:2])


def _chosen(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next((a for a in r["manifest"].get("actions") or [] if a["index"] == r.get("index")),
                None)


# --- 1. block memory --------------------------------------------------------------

def near_repeats(roots: List[str]) -> List[Dict[str, Any]]:
    """Every near-repeat collision under the roots, with a13's and a15's notes
    on the pick (the definition is spatial_replay.audit's)."""
    out = []
    for root in roots:
        for run in runs_under(Path(root).resolve()):
            rows = load(run)
            for k, r in enumerate(rows):
                chosen = _chosen(r)
                moved = _moved(rows, k)
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                if (chosen is None or chosen.get("turn_around") or moved is None
                        or here is None or moved >= spatial.SHORT_BELOW_M):
                    continue
                heading = spatial.action_heading(chosen, here[2])
                mem = memory_at(rows, k)
                if not any(b.step < r["step"] and spatial.dist(here[:2], (b.x, b.y)) < REPEAT_NEAR_M
                           and abs(spatial.wrap(b.heading - heading)) < REPEAT_WITHIN_DEG
                           for b in mem.blocks):
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                target = spatial.Target.from_dict(r.get("target"))
                tags15 = spatial.project(_a15(rows, k), r["manifest"], perception, target)
                notes = tags15.get(int(r["index"]), [])
                out.append({"run": label(run), "step": r["step"], "pick": r["index"],
                            "a13": (r.get("tags") or {}).get(str(r["index"]), []),
                            "a15": notes,
                            "noted": any(n.startswith(BLOCK_NOTES) for n in notes)})
    return out


# --- 2-4. planner, toward, leaks on R10 -------------------------------------------

def r10_lines(root: str) -> Dict[str, Any]:
    kept = steps = toward_bad = toward_moved = leaks = 0
    ways: Counter = Counter()
    for run in runs_under(Path(root).resolve()):
        rows = load(run)
        for k, r in enumerate(rows):
            if r.get("index") is None:
                continue
            man = r["manifest"]
            goal = orchestrator.goal_at(man)
            perception = (r.get("perceiver") or {}).get("result")
            mem = _a15(rows, k)
            steps += 1
            if goal is not None:
                way = planner.goal_way(mem, man, perception, goal)
                gained = planner.progress(mem, goal)
                stalled = gained is not None and gained < planner.P["stall_gain_m"]
                ways["stall" if way == "open" and stalled else way] += 1
                kept += way == "open" and not stalled
            target = spatial.Target.from_dict(r.get("target"))
            tags = spatial.project(mem, man, perception, target)
            for notes in tags.values():
                if spatial.WORDS["toward_target"] in notes and any(
                        n.startswith(NOT_OPEN) for n in notes):
                    toward_bad += 1
            old = sorted(int(i) for i, n in (r.get("tags") or {}).items()
                         if spatial.WORDS["toward_target"] in n)
            new = sorted(i for i, n in tags.items() if spatial.WORDS["toward_target"] in n)
            toward_moved += old != new
            leaks += len(views.goal_leaks("navigator", r.get("navigator_text") or "", man))
    return {"steps": steps, "planner_kept": kept, "ways": dict(ways),
            "toward_not_open": toward_bad, "toward_moved": toward_moved, "leaks": leaks}


# --- smoke: a15's real step over R10's manifests -----------------------------------

def smoke_run(run: Path, work: Path) -> Dict[str, Any]:
    from server.decider import recorder, schema, vlm
    rows = load(run)
    replay: Dict[str, Any] = {"q03": [], "navigator": []}

    async def stub(name, system, text, image_b64, json_schema, validate, max_tokens,
                   follow_up=None):
        rec = replay["rec"]
        if name == schema.PERCEIVER_SCHEMA_NAME:
            return vlm.SubCall(name, (rec.get("perceiver") or {}).get("result"), "stub")
        if name == schema.STRATEGIST_SCHEMA_NAME:
            ids = json_schema["properties"]["target"]["enum"]
            pick = next((i for i in ids if i.startswith("doorway_")), ids[0])
            replay["q03"].append({"step": rec["step"], "text": text, "target": pick})
            return vlm.SubCall(name, validate({"reason": "stub", "mode": "explore",
                                               "target": pick}), "stub")
        enum = json_schema["properties"]["action"]["enum"]
        pick = rec["index"] if rec.get("index") in enum else enum[0]
        replay["navigator"].append((text, rec["manifest"]))
        return vlm.SubCall(name, validate({"action": pick, "reason": "stub"}), "stub")

    real = vlm.call_structured
    vlm.call_structured = stub
    errors = []
    try:
        r = recorder.Run("smoke-" + "-".join(run.parts[-3:]), work / label(run))
        r.ensure()
        for rec in rows:
            replay["rec"] = rec
            request = types.SimpleNamespace(
                manifest=rec["manifest"], step=rec["step"], frame_size=rec.get("frame_size"),
                frame_png_b64="AA==", clean_frame_png_b64="AA==")
            answer = asyncio.run(orchestrator.decide(request, r, rec.get("frame")))
            if not isinstance(answer, dict):
                errors.append(rec["step"])
        out = recorder._read_jsonl(r.decisions)
    finally:
        vlm.call_structured = real
    leaks = sum(len(views.goal_leaks("navigator", t, m)) for t, m in replay["navigator"])
    toward_bad = sum(1 for d in out for notes in (d.get("tags") or {}).values()
                     if spatial.WORDS["toward_target"] in notes
                     and any(n.startswith(NOT_OPEN) for n in notes))
    return {"run": label(run), "decisions": len(out), "errors": errors,
            "standing": Counter((d.get("target") or {}).get("kind", "none") for d in out),
            "asked": Counter((d.get("planner") or {}).get("ask") for d in out
                             if (d.get("planner") or {}).get("ask")),
            "hand_back": Counter((d.get("planner") or {}).get("hand_back") for d in out
                                 if (d.get("planner") or {}).get("hand_back")),
            "q03_calls": len(replay["q03"]), "hidden": sum(1 for d in out if d.get("hidden")),
            "toward_not_open": toward_bad, "leaks": leaks,
            "fields": sorted({k for d in out for k in d}),
            "q03_example": replay["q03"][0]["text"] if replay["q03"] else None}


def cmd_smoke(args: argparse.Namespace) -> int:
    os.environ["VLM_AGENT"] = _agent()
    total: Counter = Counter()
    asked: Counter = Counter()
    back: Counter = Counter()
    errors = leaks = q03 = hidden = toward_bad = 0
    example = None
    fields: set = set()
    with tempfile.TemporaryDirectory() as tmp:
        for run in runs_under(Path(args.root).resolve()):
            row = smoke_run(run, Path(tmp))
            total.update(row["standing"])
            asked.update(row["asked"])
            back.update(row["hand_back"])
            errors += len(row["errors"])
            leaks += row["leaks"]
            q03 += row["q03_calls"]
            hidden += row["hidden"]
            toward_bad += row["toward_not_open"]
            fields |= set(row["fields"])
            example = example or row["q03_example"]
            print(json.dumps({k: v for k, v in row.items() if k not in ("fields", "q03_example")}))
    n = sum(total.values())
    print("\ndecisions {0}, failed steps {1}, leaks {2}, 'toward' on a not-open action {3}"
          .format(n, errors, leaks, toward_bad))
    print("standing target: " + ", ".join("{0} {1}".format(k, v) for k, v in total.most_common()))
    print("q03 calls {0} ({1:.0%} of steps): {2}".format(q03, q03 / n if n else 0, dict(asked)))
    print("detours handed back: {0}; [0] hidden on {1} steps".format(dict(back), hidden))
    print("record fields: " + ", ".join(sorted(fields)))
    print("\nfirst q03 text:\n" + (example or "(none)"))
    return 1 if errors or leaks or toward_bad else 0


# --- live sets ---------------------------------------------------------------------

def cmd_sample_detour(args: argparse.Namespace) -> int:
    """R10 steps where a15's planner, with the goal standing, would ask q03."""
    q03 = prompts.get("q03")
    n = 0
    with open(args.out, "w") as out:
        for run in runs_under(Path(args.root).resolve()):
            rows = load(run)
            for k, r in enumerate(rows):
                man = r["manifest"]
                goal = orchestrator.goal_at(man)
                here = spatial.pose_xyh(man.get("pose"))
                if r.get("index") is None or goal is None or here is None:
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                mem = _a15(rows, k)
                way = planner.goal_way(mem, man, perception, goal)
                gained = planner.progress(mem, goal)
                # As route(): a stall only once the goal has stood for stall_steps.
                stalled = (gained is not None and gained < planner.P["stall_gain_m"]
                           and planner.goal_run(rows, r["step"]) >= planner.P["stall_steps"])
                ask = way if way != "open" else ("stall" if stalled else None)
                if ask is None:
                    continue
                menu = planner.detours(mem, here, r["step"], goal)
                text = q03.render(q03, planner.detour_situation(mem, man, menu, ask, goal))
                out.write(json.dumps({
                    "run": label(run), "arm": run.parts[-2], "step": r["step"], "ask": ask,
                    "text": text, "ids": [t.id for t in menu] + [orchestrator.EXPLORE],
                    "menu": [t.to_dict() for t in menu], "here": list(here[:2]),
                    "goal": list(goal)}) + "\n")
                n += 1
    print("{0} detour calls -> {1}".format(n, args.out))
    return 0


def cmd_sample_toward(args: argparse.Namespace) -> int:
    """R10 steps where "toward" sat on a walled or blocked action and some move
    ahead was open: the navigator text rebuilt with a15's notes."""
    p14 = prompts.get("p14")
    n = 0
    with open(args.out, "w") as out:
        for run in runs_under(Path(args.root).resolve()):
            rows = load(run)
            for k, r in enumerate(rows):
                tags = {int(i): v for i, v in (r.get("tags") or {}).items()}
                hidden = set((r.get("hidden") or {}).get("indices") or [])
                if r.get("index") is None or not any(
                        spatial.WORDS["toward_target"] in v and any(
                            w.startswith(NOT_OPEN) for w in v) for v in tags.values()):
                    continue
                man = r["manifest"]
                forward = [a for a in man.get("actions") or [] if not a.get("turn_around")]
                if all(any(w.startswith(NOT_OPEN) for w in tags.get(int(a["index"]), []))
                       for a in forward):
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                target = spatial.Target.from_dict(r.get("target"))
                here = spatial.pose_xyh(man.get("pose"))
                tags15 = spatial.project(_a15(rows, k), man, perception, target)
                offered = dict(man, actions=[a for a in man.get("actions") or []
                                             if int(a["index"]) not in hidden])
                text = p14.render(p14, offered, tags15,
                                  orchestrator.plan_line(target, r.get("mode"), here, True),
                                  orchestrator.perceiver_line(perception),
                                  orchestrator.recent_moves(rows[:k], man))
                out.write(json.dumps({
                    "run": label(run), "step": r["step"], "text": text,
                    "frame": str(run / r["frame"]),
                    "tags": {str(i): v for i, v in tags15.items()},
                    "indices": [int(a["index"]) for a in offered["actions"]],
                    "r10_pick": r["index"]}) + "\n")
                n += 1
    print("{0} toward steps -> {1}".format(n, args.out))
    return 0


async def _ask_all(items: List[Dict[str, Any]], out: Path, kind: str) -> None:
    from server.decider import agent, config, schema, vlm
    try:
        for n, item in enumerate(items):
            if kind == "detour":
                q = prompts.get(agent.current().features["orchestrator"]["strategist"])
                call = await vlm.call_structured(
                    schema.STRATEGIST_SCHEMA_NAME, q.system, item["text"], None,
                    schema.strategist_schema(item["ids"]), orchestrator._strategy(item["ids"]),
                    orchestrator.STRATEGIST_MAX_TOKENS)
            else:
                p = agent.current().prompt
                frame = base64.b64encode(Path(item["frame"]).read_bytes()).decode()
                call = await vlm.call_structured(
                    schema.SCHEMA_NAME, p.system, item["text"], frame,
                    schema.action_schema(item["indices"]), orchestrator._action(item["indices"]),
                    config.MAX_TOKENS)
            rec = dict(item, agent=agent.current().version, answer=call.result,
                       error=call.error, latency_ms=round(call.latency_ms, 1))
            with out.open("a") as handle:
                handle.write(json.dumps(rec) + "\n")
            print("{0}/{1} {2} step {3}: {4}".format(n + 1, len(items), item["run"],
                                                      item["step"], call.result), flush=True)
    finally:
        await vlm.aclose()


def _run_live(args: argparse.Namespace, kind: str) -> int:
    out = Path(args.out)
    done = {(r["run"], r["step"]) for r in _read(args.out)} if out.is_file() else set()
    asyncio.run(_ask_all([i for i in _read(args.set) if (i["run"], i["step"]) not in done],
                         out, kind))
    return 0


# --- report ------------------------------------------------------------------------

def _row(name: str, value: str, ok: bool, threshold: str) -> str:
    return "| {0} | {1} | {2} | {3} |".format(name, value, threshold, "yes" if ok else "**no**")


def cmd_offline(args: argparse.Namespace) -> int:
    repeats = near_repeats([args.r9, args.r10c, args.r10])
    noted = sum(r["noted"] for r in repeats)
    r10 = r10_lines(args.r10)
    share = r10["planner_kept"] / r10["steps"] if r10["steps"] else 0.0
    print("agent {0}".format(_agent()))
    lines = [
        _row("near-repeat collisions noted by the agent's memory", "{0}/{1}".format(noted, len(repeats)),
             noted >= GATE["block_noted_min"], ">= {0}".format(GATE["block_noted_min"])),
        _row("R10 steps where the planner keeps the goal", "{0}/{1} ({2:.0%})".format(
            r10["planner_kept"], r10["steps"], share), share >= GATE["planner_goal_min"],
            ">= {0:.0%}".format(GATE["planner_goal_min"])),
        _row("'toward' on a not-open action, the agent's tags on R10", str(r10["toward_not_open"]),
             r10["toward_not_open"] <= GATE["toward_not_open_max"],
             "<= {0}".format(GATE["toward_not_open_max"])),
        _row("R10 navigator lines wording the goal's position", str(r10["leaks"]),
             r10["leaks"] <= GATE["leaks_max"], "<= {0}".format(GATE["leaks_max"])),
    ]
    print("| Check | Value | Threshold | Pass |\n|---|---|---|---|\n" + "\n".join(lines))
    print("\nplanner on R10's steps: {0}".format(r10["ways"]))
    print("steps whose 'toward' note moved under a15: {0}".format(r10["toward_moved"]))
    print("near-repeats still un-noted: " + ("; ".join(
        "{0} {1} [{2}] {3}".format(r["run"], r["step"], r["pick"], r["a15"])
        for r in repeats if not r["noted"]) or "none"))
    ok = all("**no**" not in l for l in lines)
    print("\nOFFLINE LINES {0}".format("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def cmd_report(args: argparse.Namespace) -> int:
    detour = [r for r in _read(args.detour) if r.get("answer")]
    toward = [r for r in _read(args.toward) if r.get("answer")]

    def goalward(r: Dict[str, Any]) -> bool:
        t = next((m for m in r["menu"] if m["id"] == r["answer"]["target"]), None)
        return t is not None and goal_gain(tuple(r["here"]), (t["x"], t["y"]),
                                           tuple(r["goal"])) >= GOALWARD_M

    def opened(r: Dict[str, Any]) -> bool:
        i = r["answer"].get("index")
        return not any(w.startswith(NOT_OPEN) for w in r["tags"].get(str(i), []))

    gw = sum(goalward(r) for r in detour) / len(detour) if detour else 0.0
    ex = sum(r["answer"]["target"] == orchestrator.EXPLORE for r in detour) / len(detour) \
        if detour else 0.0
    op = sum(opened(r) for r in toward) / len(toward) if toward else 0.0
    lines = [
        _row("q03 detour >= 3 m nearer the goal", "{0:.0%}".format(gw),
             gw >= GATE["detour_goalward_min"], ">= {0:.0%}".format(GATE["detour_goalward_min"])),
        _row("q03 chooses explore", "{0:.0%}".format(ex), ex <= GATE["detour_explore_max"],
             "<= {0:.0%}".format(GATE["detour_explore_max"])),
        _row("p14 pick open with a15's notes", "{0:.0%}".format(op),
             op >= GATE["toward_open_min"], ">= {0:.0%}".format(GATE["toward_open_min"])),
    ]
    print("| Check | Value | Threshold | Pass |\n|---|---|---|---|\n" + "\n".join(lines))
    print("\ndetour calls answered {0}; toward steps answered {1}".format(len(detour), len(toward)))
    ok = all("**no**" not in l for l in lines)
    print("\nLIVE LINES {0}".format("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("offline", help="the code-only gate lines")
    o.add_argument("--r9", required=True)
    o.add_argument("--r10c", required=True)
    o.add_argument("--r10", required=True)
    o.set_defaults(func=cmd_offline)
    s = sub.add_parser("smoke", help="a15's real step over R10's manifests, stub replies")
    s.add_argument("root")
    s.set_defaults(func=cmd_smoke)
    sd = sub.add_parser("sample-detour", help="R10 steps where a15 would ask q03")
    sd.add_argument("root")
    sd.add_argument("--out", required=True)
    sd.set_defaults(func=cmd_sample_detour)
    rd = sub.add_parser("run-detour", help="ask the current agent's strategist (live)")
    rd.add_argument("set")
    rd.add_argument("--out", required=True)
    rd.set_defaults(func=lambda a: _run_live(a, "detour"))
    st = sub.add_parser("sample-toward", help="R10 steps where 'toward' sat on a wall")
    st.add_argument("root")
    st.add_argument("--out", required=True)
    st.set_defaults(func=cmd_sample_toward)
    rt = sub.add_parser("run-toward", help="ask the navigator with a15's notes (live, frames)")
    rt.add_argument("set")
    rt.add_argument("--out", required=True)
    rt.set_defaults(func=lambda a: _run_live(a, "toward"))
    p = sub.add_parser("report", help="score the live lines")
    p.add_argument("detour")
    p.add_argument("toward")
    p.set_defaults(func=cmd_report)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
