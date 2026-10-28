"""R10 probe for a14, offline, on R9's recorded runs.

Two parts, both run against the live model before R10 may fly
(eval/phase2/R10_goal_planner/README.md, probe gate):

1. Strategist (q02), text only. Every strategist call R9 made is rebuilt as
   a14 would word it: the same memory (spatial.rebuild), the goal listed at its
   true position, a14's trigger sentence. q02 answers it; each answer is scored
   on whether the chosen target's point is at least 3 m nearer the true goal
   than the drone (spatial_replay.goalward), against q01's recorded answer on
   the same call.
   History is R9's (the target standing before each call is q01's), so this
   asks how q02 chooses from the same situations, not how an a14 run unfolds.

2. Turn rule. The R9 steps where a14 would leave [0] off and R9 picked [0]: the
   recorded navigator text and annotated frame, re-asked with [0] off the list
   and out of the schema. Scored on whether the pick carries no blocked,
   stopped-short or wall note.

    python eval/r10_probe.py sample-strategist ROOT --out strat_set.jsonl
    VLM_AGENT=a14 python eval/r10_probe.py run-strategist strat_set.jsonl --out strat_a14.jsonl
    python eval/r10_probe.py sample-turn ROOT --out turn_set.jsonl
    VLM_AGENT=a14 python eval/r10_probe.py run-turn turn_set.jsonl --out turn_a14.jsonl
    python eval/r10_probe.py report strat_a14.jsonl turn_a14.jsonl

ROOT is R9's runs folder. The strategist set needs only decisions.jsonl; the
turn set needs the frames, which live on the host that flew R9.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

from server.decider import orchestrator, spatial  # noqa: E402
from spatial_replay import GOALWARD_M, goal_gain, goalward  # noqa: E402

#: The pre-registered gate (README). A probe that misses any of these stops R10.
GATE = {
    "goalward_min": 0.55,          # q02 picks a target >= 3 m nearer the goal than the drone
    "goalward_gain_min": 0.20,     # ... at least this far above q01 (R9: 35%) on the same calls
    "explore_max": 0.20,           # q02 picks "explore" (no target)
    "turn_open_min": 0.80,         # [0] hidden: the pick carries no blocked/wall note
}

#: a13's trigger sentences back to their keys; the one sentence two keys share
#: is split by the target's state (spatial.target_state).
_KEY_OF = {v: k for k, v in spatial.TRIGGERS_A13.items() if not k.startswith("target_")}


def _rows(run: Path) -> List[Dict[str, Any]]:
    rows = [json.loads(l) for l in (run / "decisions.jsonl").read_text().splitlines()
            if l.strip()]
    return sorted((r for r in rows if "step" in r), key=lambda r: r["step"])


def _runs(root: str) -> List[Path]:
    return sorted(p.parent for p in Path(root).resolve().rglob("decisions.jsonl")
                  if "_attempts" not in p.parts)


def _read(path: str) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def _label(run: Path) -> str:
    return "/".join(run.parts[-3:])


# --- strategist ------------------------------------------------------------------

def cmd_sample_strategist(args: argparse.Namespace) -> int:
    from server.decider import prompt as prompts
    q02 = prompts.get("q02")
    words = spatial.WORDS_A14["triggers"]
    out = []
    for run in _runs(args.root):
        rows = _rows(run)
        for k, r in enumerate(rows):
            if not r.get("strategist"):
                continue
            before, man = rows[:k], r["manifest"]
            perception = (r.get("perceiver") or {}).get("result")
            mem = spatial.rebuild(before, man, perception)
            here = spatial.pose_xyh(man.get("pose"))
            goal = orchestrator.goal_at(man)
            if here is None or goal is None:
                continue
            target, _, last_called, last_perception = orchestrator.previous(before, r["step"])
            key = spatial.trigger_key(mem, man, perception, target, last_called,
                                      last_perception, goal_at=goal)
            if key is None:
                key = _KEY_OF.get(r["strategist"]["trigger"])
            if key is None:
                state = spatial.target_state(mem, target, here[:2], goal)
                key = "target_closed" if state == "closed" else "target_reached"
            if target is not None and not spatial.target_still_valid(mem, target, here[:2],
                                                                     goal):
                target = None
            menu = spatial.targets(mem, here, r["step"], goal)
            text = q02.render(q02, spatial.situation(mem, man, perception, target, menu,
                                                     words[key], goal))
            out.append({"run": _label(run), "step": r["step"], "arm": run.parts[-2],
                        "text": text, "menu": [t.to_dict() for t in menu],
                        "ids": [t.id for t in menu] + [orchestrator.EXPLORE],
                        "here": list(here), "goal": list(goal),
                        "q01_target": (r["strategist"].get("result") or {}).get("target"),
                        "q01_goalward": goalward(r)})
    Path(args.out).write_text("".join(json.dumps(i) + "\n" for i in out))
    print("{0} strategist calls from {1} runs".format(len(out), len(_runs(args.root))))
    return 0


async def _strategise(items: List[Dict[str, Any]], out: Path) -> None:
    from server.decider import agent, prompt as prompts, schema, vlm
    q = prompts.get(agent.current().features["orchestrator"]["strategist"])
    try:
        for n, item in enumerate(items):
            call = await vlm.call_structured(
                schema.STRATEGIST_SCHEMA_NAME, q.system, item["text"], None,
                schema.strategist_schema(item["ids"]), orchestrator._strategy(item["ids"]),
                orchestrator.STRATEGIST_MAX_TOKENS)
            rec = dict(item, agent=agent.current().version, answer=call.result,
                       error=call.error, latency_ms=round(call.latency_ms, 1))
            with out.open("a") as handle:
                handle.write(json.dumps(rec) + "\n")
            print("{0}/{1} {2} step {3}: {4} (q01 {5})".format(
                n + 1, len(items), item["run"], item["step"],
                (call.result or {}).get("target"), item["q01_target"]), flush=True)
    finally:
        await vlm.aclose()


def cmd_run_strategist(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = {(r["run"], r["step"]) for r in _read(args.out)} if out.is_file() else set()
    asyncio.run(_strategise([i for i in _read(args.set)
                             if (i["run"], i["step"]) not in done], out))
    return 0


def _q02_goalward(rec: Dict[str, Any]) -> bool:
    """The answer's target at least GOALWARD_M nearer the goal than the drone,
    as goalward() scores q01's recorded answer."""
    chosen = (rec.get("answer") or {}).get("target")
    t = next((m for m in rec["menu"] if m["id"] == chosen), None)
    if t is None:
        return False
    return goal_gain(tuple(rec["here"][:2]), (t["x"], t["y"]),
                     tuple(rec["goal"])) >= GOALWARD_M


# --- turn rule -------------------------------------------------------------------

def cmd_sample_turn(args: argparse.Namespace) -> int:
    out = []
    for run in _runs(args.root):
        rows = _rows(run)
        for k, r in enumerate(rows):
            if r.get("index") is None:
                continue
            mem = spatial.rebuild(rows[:k], r["manifest"],
                                  (r.get("perceiver") or {}).get("result"))
            tags = {int(i): v for i, v in (r.get("tags") or {}).items()}
            hidden = spatial.hide_turn_around(mem, r["manifest"], tags)
            if not hidden or r["index"] not in hidden:
                continue
            text = "\n".join(l for l in r["navigator_text"].splitlines()
                             if not any(l.startswith("  [{0}]".format(i)) for i in hidden))
            out.append({"run": _label(run), "step": r["step"],
                        "frame": str(run / r["frame"]), "text": text,
                        "indices": [int(a["index"]) for a in r["manifest"]["actions"]
                                    if int(a["index"]) not in hidden],
                        "tags": {str(i): v for i, v in tags.items()}})
    Path(args.out).write_text("".join(json.dumps(i) + "\n" for i in out))
    print("{0} steps where a14 hides [0] and R9 turned around".format(len(out)))
    return 0


async def _navigate(items: List[Dict[str, Any]], out: Path) -> None:
    from server.decider import agent, config, schema, vlm
    p = agent.current().prompt
    try:
        for n, item in enumerate(items):
            frame = base64.b64encode(Path(item["frame"]).read_bytes()).decode()
            call = await vlm.call_structured(
                schema.SCHEMA_NAME, p.system, item["text"], frame,
                schema.action_schema(item["indices"]), orchestrator._action(item["indices"]),
                config.MAX_TOKENS)
            rec = dict(item, agent=agent.current().version, answer=call.result,
                       error=call.error, latency_ms=round(call.latency_ms, 1))
            with out.open("a") as handle:
                handle.write(json.dumps(rec) + "\n")
            print("{0}/{1} {2} step {3}: [{4}]".format(
                n + 1, len(items), item["run"], item["step"],
                (call.result or {}).get("index")), flush=True)
    finally:
        await vlm.aclose()


def cmd_run_turn(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = {(r["run"], r["step"]) for r in _read(args.out)} if out.is_file() else set()
    asyncio.run(_navigate([i for i in _read(args.set)
                           if (i["run"], i["step"]) not in done], out))
    return 0


def _open(rec: Dict[str, Any]) -> bool:
    i = (rec.get("answer") or {}).get("index")
    words = rec["tags"].get(str(i), [])
    return i is not None and not any(w.startswith(spatial._NOT_OPEN) for w in words)


# --- report ----------------------------------------------------------------------

def cmd_report(args: argparse.Namespace) -> int:
    strat = [r for r in _read(args.strategist) if r.get("answer")]
    turn = [r for r in _read(args.turn) if r.get("answer")]
    n = len(strat)
    q01 = sum(1 for r in strat if r["q01_goalward"]) / n if n else 0.0
    q02 = sum(1 for r in strat if _q02_goalward(r)) / n if n else 0.0
    explore = sum(1 for r in strat if r["answer"]["target"] == orchestrator.EXPLORE) / n \
        if n else 0.0
    opened = sum(1 for r in turn if _open(r)) / len(turn) if turn else 0.0
    lines = [
        ("strategist goal-ward, q02", q02, q02 >= GATE["goalward_min"],
         ">= {0:.0%}".format(GATE["goalward_min"])),
        ("strategist goal-ward, q02 - q01 (q01 {0:.0%})".format(q01), q02 - q01,
         q02 - q01 >= GATE["goalward_gain_min"],
         ">= {0:.0%}".format(GATE["goalward_gain_min"])),
        ("strategist explore, q02", explore, explore <= GATE["explore_max"],
         "<= {0:.0%}".format(GATE["explore_max"])),
        ("[0] hidden, pick open", opened, opened >= GATE["turn_open_min"],
         ">= {0:.0%}".format(GATE["turn_open_min"])),
    ]
    print("| Check | Value | Threshold | Pass |\n|---|---|---|---|")
    for name, value, ok, thr in lines:
        print("| {0} | {1:.1%} | {2} | {3} |".format(name, value, thr, "yes" if ok else "**no**"))
    print("\nstrategist calls answered {0}; turn steps answered {1}".format(n, len(turn)))
    by_arm: Dict[str, List[bool]] = {}
    for r in strat:
        by_arm.setdefault(r["arm"], []).append(_q02_goalward(r))
    print("q02 goal-ward by arm: " + ", ".join(
        "{0} {1}/{2}".format(a, sum(v), len(v)) for a, v in sorted(by_arm.items())))
    print("\nGATE {0}".format("PASSED" if all(ok for _, _, ok, _ in lines) else "FAILED"))
    return 0 if all(ok for _, _, ok, _ in lines) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample-strategist", help="rebuild R9's strategist calls as a14")
    s.add_argument("root")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_sample_strategist)
    r = sub.add_parser("run-strategist", help="ask the current agent's strategist")
    r.add_argument("set")
    r.add_argument("--out", required=True)
    r.set_defaults(func=cmd_run_strategist)
    st = sub.add_parser("sample-turn", help="R9 steps where a14 hides [0] and R9 turned")
    st.add_argument("root")
    st.add_argument("--out", required=True)
    st.set_defaults(func=cmd_sample_turn)
    rt = sub.add_parser("run-turn", help="re-ask the navigator with [0] off the list")
    rt.add_argument("set")
    rt.add_argument("--out", required=True)
    rt.set_defaults(func=cmd_run_turn)
    p = sub.add_parser("report", help="score both parts and apply the gate")
    p.add_argument("strategist")
    p.add_argument("turn")
    p.set_defaults(func=cmd_report)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
