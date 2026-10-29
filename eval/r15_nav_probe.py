"""R15 navigator probe: p14 against p15 on recorded steps (live model).

Each recorded step whose notes put "toward your target" on a visible action is
asked again, with the recorded navigator text and annotated frame, under each
prompt's system text; the pick is compared with the action carrying "toward".
Set `back`: "toward" on marker 0 (the target behind; R11, p14: 43 of 181
followed). Set `ahead`: "toward" on a forward move (R11: 71% followed), capped,
to check p15 does not turn the drone around when it should fly on.

    VLM_PROFILE=remote python eval/r15_nav_probe.py run RUNS --out nav.jsonl
    python eval/r15_nav_probe.py score nav.jsonl

The frames must be on disk (the flight host keeps them). Model calls only; no
ground truth is read.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

from server.decider import config, prompt as prompts, schema, spatial, vlm  # noqa: E402
from server.decider.orchestrator import _action  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402

TOWARD = spatial.WORDS["toward_target"]
AHEAD_CAP = 150


def cases(root: Path) -> List[Tuple[str, Path, Dict[str, Any], int]]:
    back, ahead = [], []
    for run in runs_under(root):
        for r in load(run):
            tags = r.get("tags") or {}
            if not r.get("navigator_text") or not r.get("frame"):
                continue
            if not (run / r["frame"]).is_file():
                continue
            toward = [int(k) for k, notes in tags.items() if TOWARD in notes]
            if not toward:
                continue
            (back if toward[0] == 0 else ahead).append((run, r, toward[0]))
    random.Random(15).shuffle(ahead)
    return ([("back", run, r, t) for run, r, t in back]
            + [("ahead", run, r, t) for run, r, t in ahead[:AHEAD_CAP]])


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        for line in out.read_text().splitlines():
            j = json.loads(line)
            done.add((j["run"], j["step"], j["prompt"]))
    todo = [(p, c) for c in cases(Path(args.root).resolve()) for p in args.prompts
            if (label(c[1]), c[2]["step"], p) not in done]
    print("{0} calls to make".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, version: str, case) -> None:
        kind, run, r, toward = case
        indices = sorted(int(k) for k in (r.get("tags") or {}))
        p = prompts.get(version)
        async with sem:
            b64 = base64.b64encode((run / r["frame"]).read_bytes()).decode()
            call = await vlm.call_structured(schema.SCHEMA_NAME, p.system, r["navigator_text"],
                                             b64, schema.action_schema(indices),
                                             _action(indices), config.MAX_TOKENS)
        pick = call.result["index"] if call.result else None
        with out.open("a") as handle:
            handle.write(json.dumps({"run": label(run), "step": r["step"], "prompt": version,
                                     "set": kind, "toward": toward, "pick": pick,
                                     "recorded": r.get("index"), "error": call.error}) + "\n")
        print("{0}/{1} {2} {3} step {4}: toward {5} pick {6}".format(
            n + 1, len(todo), version, label(run), r["step"], toward, pick), flush=True)

    async def go() -> None:
        sem = asyncio.Semaphore(args.concurrency)
        try:
            await asyncio.gather(*(one(sem, n, v, c) for n, (v, c) in enumerate(todo)))
        finally:
            await vlm.aclose()

    asyncio.run(go())
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    rows = [json.loads(line) for line in Path(args.answers).read_text().splitlines()
            if line.strip()]
    n: Counter = Counter()
    followed: Counter = Counter()
    turned: Counter = Counter()
    for j in rows:
        if j.get("pick") is None:
            continue
        key = (j["prompt"], j["set"])
        n[key] += 1
        followed[key] += j["pick"] == j["toward"]
        turned[key] += j["pick"] == 0
    print("prompt  set     asked  followed 'toward'   picked 0")
    for key in sorted(n):
        print("{0:<7} {1:<7} {2:>5}  {3:>5} ({4:5.1%})   {5:>5} ({6:5.1%})".format(
            key[0], key[1], n[key], followed[key], followed[key] / n[key],
            turned[key], turned[key] / n[key]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("root")
    run.add_argument("--out", required=True)
    run.add_argument("--prompts", nargs="+", default=["p14", "p15"])
    run.add_argument("--concurrency", type=int, default=3)
    run.set_defaults(fn=cmd_run)
    score = sub.add_parser("score")
    score.add_argument("answers")
    score.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
