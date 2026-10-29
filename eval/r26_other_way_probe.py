"""R26 other-way probe: a50's "other way at the fork" item at every recorded detour call.

At each recorded strategist call of the along-the-wall rounds (R21-R22K: q08's
menus), the memory is rebuilt from the records up to that step, and
planner.other_way adds its item to the recorded menu; planner.closed_door_line
words the closed doors of the last steps. Scored against the site model (R11's
analysis/geo.py):
- s03 dead end (`final`/`dynamic`, drone in a tine, x < -3): is the item listed,
  on free floor, in the other tine (|y| >= 3.5, opposite side)?
- s02: is the item listed, and does it bring the drone nearer a door open at
  that step (0.5 m or more)?

`run` asks a strategist prompt (live, text only) at those calls; `score` counts
other-way picks on s03 dead-end calls, misleading other-way picks on s02, and
along-the-wall picks at the s02 divider against the recorded q08 answer.

    python3 eval/r26_other_way_probe.py items RUNS...      (R26_AGENT=a52 for a52's listing)
    VLM_PROFILE=remote python eval/r26_other_way_probe.py run RUNS... --out q10.jsonl
    python3 eval/r26_other_way_probe.py score q10.jsonl RUNS...
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))

from server.decider import agent, planner, prompt as prompts, schema, spatial, vlm  # noqa: E402
from server.decider.orchestrator import STRATEGIST_MAX_TOKENS, _strategy, goal_at  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402
import geo  # noqa: E402


import os  # noqa: E402

A50 = agent.get(os.environ.get("R26_AGENT", "a50"))
CFG = A50.spatial_config
P = A50.features["orchestrator"]["other_way"]


def place(site: str, arm: str, here: spatial.Pose) -> str:
    """s03_dead (in a tine past the crossbar, final/dynamic), s02_divider, or the site."""
    if site == "s03" and arm != "initial" and here[0] < -3.0:
        return "s03_dead"
    if site.startswith("s02") and abs(here[0]) < 3.0:
        return "s02_divider"
    return site[:3]


def good(site: str, arm: str, step: int, here: spatial.Pose, it: spatial.Target) -> bool:
    free = geo.world(site, arm, step)
    if not free(it.x, it.y):
        return False
    if site == "s03":
        return abs(it.y) >= 3.5 and it.y * here[1] < 0
    if site.startswith("s02"):
        doors = geo.open_doors(site, arm, step)
        if not doors:
            return False
        dy = min(abs(here[1] - geo.S02_DOORS[d]) for d in doors)
        return min(abs(it.y - geo.S02_DOORS[d]) for d in doors) < dy - 0.5
    return True


def cases(roots: List[str]):
    """(key, site, arm, step, here, menu, text, recorded pick) at every recorded
    strategist call, a50's item added to the recorded menu."""
    for root in roots:
        rnd = Path(root).resolve().parent.name
        for run in runs_under(Path(root).resolve()):
            site, arm = run.parts[-3], run.parts[-2]
            rows = load(run)
            for i, r in enumerate(rows):
                s = r.get("strategist") or {}
                ask = (r.get("planner") or {}).get("ask")
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                goal = goal_at(r["manifest"])
                if s.get("menu") is None or not s.get("text"):
                    continue
                if ask is None or here is None or goal is None:
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                mem = spatial.rebuild(rows[:i], r["manifest"], perception, CFG)
                black = planner.failed_detours(rows[:i])
                menu = [spatial.Target.from_dict(m) for m in s["menu"]]
                if not P.get("only_dead_end") or planner.dead_end(rows[:i + 1], r["step"],
                                                                  menu, P):
                    menu = menu + planner.other_way(mem, here, r["step"], rows[:i], black, P)
                text = planner.detour_situation(mem, r["manifest"], menu, ask, goal,
                                                planner.closed_door_line(rows[:i + 1],
                                                                         r["step"], P))
                pick = (s.get("result") or {}).get("target")
                yield ("{0}/{1}/{2}".format(rnd, label(run), r["step"]), site, arm, r["step"],
                       here, menu, text, pick)


def cmd_items(args: argparse.Namespace) -> int:
    t: Counter = Counter()
    for _, site, arm, step, here, menu, text, _ in cases(args.roots):
        where = place(site, arm, here)
        it = next((m for m in menu if m.kind == "other_way"), None)
        n_along = sum(m.kind == "along" for m in menu)
        closed = "closed door was seen" in text
        t[where, "calls"] += 1
        t[where, "closed_line"] += closed
        if it is not None:
            t[where, "item"] += 1
            t[where, "item_good"] += good(site, arm, step, here, it)
            if closed and n_along <= 1:
                t[where, "item_dead_end_cue"] += 1
                t[where, "item_dead_end_cue_good"] += good(site, arm, step, here, it)
    for k in sorted(t):
        print("  {0}: {1}".format("/".join(k), t[k]))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {json.loads(l)["key"] for l in out.read_text().splitlines() if l.strip()}
    todo = [c for c in cases(args.roots) if c[0] not in done
            and (any(m.kind == "other_way" for m in c[5])
                 or place(c[1], c[2], c[4]) == "s02_divider")]
    p = prompts.get(args.prompt)
    print("{0} calls to ask".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, case) -> None:
        key, menu, text = case[0], case[5], case[6]
        ids = [t.id for t in menu] + ["explore"]
        async with sem:
            call = await vlm.call_structured(schema.STRATEGIST_SCHEMA_NAME, p.system, text, None,
                                             schema.strategist_schema(ids), _strategy(ids),
                                             STRATEGIST_MAX_TOKENS)
        with out.open("a") as handle:
            handle.write(json.dumps({"key": key, "prompt": p.version, "text": text,
                                     "result": call.result, "error": call.error}) + "\n")
        print("{0}/{1} {2}: {3}".format(n + 1, len(todo), key,
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
    answers: Dict[str, Any] = {}
    for line in Path(args.answers).read_text().splitlines():
        j = json.loads(line) if line.strip() else {}
        if j.get("result"):
            answers[j["key"]] = j["result"]["target"]
    t: Counter = Counter()
    for key, site, arm, step, here, menu, _, old in cases(args.roots):
        pick = answers.get(key)
        if pick is None:
            continue
        where = place(site, arm, here)
        it = next((m for m in menu if m.kind == "other_way"), None)
        chosen = next((m for m in menu if m.id == pick), None)
        kind = chosen.kind if chosen is not None else "explore"
        t[where, "asked"] += 1
        t[where, "pick_" + kind] += 1
        if it is not None:
            t[where, "item_listed"] += 1
            if kind == "other_way":
                t[where, "other_way_good" if good(site, arm, step, here, it)
                  else "other_way_misleading"] += 1
        if where == "s02_divider":
            t[where, "q08_along"] += (old or "").startswith("along_")
            t[where, "new_along"] += kind == "along"
    for k in sorted(t):
        print("  {0}: {1}".format("/".join(k), t[k]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    items = sub.add_parser("items")
    items.add_argument("roots", nargs="+")
    items.set_defaults(fn=cmd_items)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
    run.add_argument("--prompt", default="q10")
    run.add_argument("--concurrency", type=int, default=4)
    run.set_defaults(fn=cmd_run)
    score = sub.add_parser("score")
    score.add_argument("answers")
    score.add_argument("roots", nargs="+")
    score.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
