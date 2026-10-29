"""R17 detour-strategist probe: recorded strategist calls asked again (live model).

Every recorded step with a strategist call is asked again with its recorded text
(the situation and its menu, as the strategist saw it) under each prompt's
system text. Text only: the strategist gets no image. Scored by the kind of
place picked: a doorway when the menu held one, the way back when moves from
here were blocked on two or more sides (the dead-end case), and how often the
pick lies nearer the goal than the drone (from the recorded menu wording).

    VLM_PROFILE=remote python eval/r17_strategist_probe.py run RUNS... --prompts q03 q06 --out ans.jsonl
    python eval/r17_strategist_probe.py score ans.jsonl RUNS...
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

from server.decider import prompt as prompts, schema, vlm  # noqa: E402
from server.decider.orchestrator import STRATEGIST_MAX_TOKENS, _strategy  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402


def calls(roots: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    out = []
    for root in roots:
        rnd = Path(root).resolve().parent.name
        for run in runs_under(Path(root).resolve()):
            for r in load(run):
                s = r.get("strategist") or {}
                if s.get("text") and s.get("menu") is not None:
                    out.append(("{0}/{1}/{2}".format(rnd, label(run), r["step"]), s))
    return out


def ids(s: Dict[str, Any]) -> List[str]:
    return [m["id"] for m in s["menu"]] + ["explore"]


def kind(s: Dict[str, Any], target: str) -> str:
    return next((m["kind"] for m in s["menu"] if m["id"] == target), "explore")


def blocked_sides(s: Dict[str, Any]) -> int:
    for line in s["text"].splitlines():
        if line.startswith("Moves from here that were blocked before:"):
            return len(line.split(":", 1)[1].strip(" .").split(", "))
    return 0


def nearer(s: Dict[str, Any], target: str) -> bool:
    for line in s["text"].splitlines():
        if line.strip().startswith(target + ":"):
            return "nearer the goal" in line
    return False


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {(j["key"], j["prompt"]) for j in map(json.loads, out.read_text().splitlines())}
    todo = [(k, s, p) for k, s in calls(args.roots) for p in args.prompts if (k, p) not in done]
    print("{0} calls to ask".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, case) -> None:
        k, s, version = case
        p = prompts.get(version)
        async with sem:
            call = await vlm.call_structured(schema.STRATEGIST_SCHEMA_NAME, p.system, s["text"],
                                             None, schema.strategist_schema(ids(s)),
                                             _strategy(ids(s)), STRATEGIST_MAX_TOKENS)
        with out.open("a") as handle:
            handle.write(json.dumps({"key": k, "prompt": version, "result": call.result,
                                     "error": call.error}) + "\n")
        print("{0}/{1} {2} {3}: {4}".format(n + 1, len(todo), k, version,
                                            (call.result or {}).get("target", call.error)),
              flush=True)

    async def go() -> None:
        sem = asyncio.Semaphore(args.concurrency)
        try:
            await asyncio.gather(*(one(sem, n, c) for n, c in enumerate(todo)))
        finally:
            await vlm.aclose()

    asyncio.run(go())
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    answers: Dict[Tuple[str, str], str] = {}
    for line in Path(args.answers).read_text().splitlines():
        j = json.loads(line) if line.strip() else {}
        if j.get("result"):
            answers[(j["key"], j["prompt"])] = j["result"]["target"]
    prompts_seen = sorted({p for _, p in answers})
    rows: Dict[str, Counter] = defaultdict(Counter)
    for k, s in calls(args.roots):
        picks = {"recorded": (s.get("result") or {}).get("target")}
        picks.update({p: answers.get((k, p)) for p in prompts_seen})
        door = any(m["kind"] == "opening" for m in s["menu"])
        back = any(m["kind"] == "backtrack" for m in s["menu"])
        dead = blocked_sides(s) >= 2
        for name, t in picks.items():
            if t is None:
                continue
            c = rows[name]
            c["calls"] += 1
            c["kind_" + kind(s, t)] += 1
            c["nearer"] += nearer(s, t)
            if door:
                c["door_menus"] += 1
                c["door_picked"] += kind(s, t) == "opening"
            if dead and back:
                c["dead_menus"] += 1
                c["back_picked"] += kind(s, t) == "backtrack"
    for name, c in rows.items():
        print("{0:9s} calls {1:3d} | doorway when listed {2}/{3} | way back in a dead end "
              "{4}/{5} | pick nearer the goal {6}/{1} | kinds {7}".format(
                  name, c["calls"], c["door_picked"], c["door_menus"], c["back_picked"],
                  c["dead_menus"], c["nearer"],
                  {k[5:]: v for k, v in sorted(c.items()) if k.startswith("kind_")}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
    run.add_argument("--prompts", nargs="+", default=["q03", "q06"])
    run.add_argument("--concurrency", type=int, default=3)
    run.set_defaults(fn=cmd_run)
    score = sub.add_parser("score")
    score.add_argument("answers")
    score.add_argument("roots", nargs="+")
    score.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
