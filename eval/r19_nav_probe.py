"""R19 navigator probe: recorded turn-arounds against a forward "toward" (live model).

Each recorded step is asked again with its recorded navigator text and
annotated frame under each prompt's system text (p16 against p17 change only
the system text). Sets:
- `ta`: the navigator turned around (picked 0) while "toward your target" was on
  a forward move (R15/R15N failure analysis: 50 a round, R11 3). Want: the
  forward "toward" taken.
- `kept`: "toward" on a forward move and followed; capped. Want: still followed.
- `back`: "toward" on marker 0; capped. Want: still turned around.

    VLM_PROFILE=remote python eval/r19_nav_probe.py run RUNS... --out nav.jsonl
    python eval/r19_nav_probe.py score nav.jsonl

The frames must be on disk (the flight host keeps them). No ground truth is read.
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
KEPT_CAP = 80
BACK_CAP = 60


def cases(roots: List[str]) -> List[Tuple[str, str, Path, Dict[str, Any], int]]:
    ta, kept, back = [], [], []
    for root in roots:
        rnd = Path(root).resolve().parent.name
        for run in runs_under(Path(root).resolve()):
            for r in load(run):
                tags = r.get("tags") or {}
                if not r.get("navigator_text") or not r.get("frame"):
                    continue
                if not (run / r["frame"]).is_file():
                    continue
                toward = [int(k) for k, notes in tags.items() if TOWARD in notes]
                if not toward:
                    continue
                case = (rnd, run, r, toward[0])
                if toward[0] == 0:
                    back.append(case)
                elif r.get("index") == 0:
                    ta.append(case)
                elif r.get("index") == toward[0]:
                    kept.append(case)
    random.Random(19).shuffle(kept)
    random.Random(19).shuffle(back)
    return ([("ta",) + c for c in ta] + [("kept",) + c for c in kept[:KEPT_CAP]]
            + [("back",) + c for c in back[:BACK_CAP]])


def key(rnd: str, run: Path, r: Dict[str, Any]) -> str:
    return "{0}/{1}/{2}".format(rnd, label(run), r["step"])


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {(j["key"], j["prompt"]) for j in map(json.loads, out.read_text().splitlines())}
    todo = [(p, c) for c in cases(args.roots) for p in args.prompts
            if (key(c[1], c[2], c[3]), p) not in done]
    print("{0} calls to make".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, version: str, case) -> None:
        kind, rnd, run, r, toward = case
        indices = sorted(int(k) for k in (r.get("tags") or {}))
        p = prompts.get(version)
        async with sem:
            b64 = base64.b64encode((run / r["frame"]).read_bytes()).decode()
            call = await vlm.call_structured(schema.SCHEMA_NAME, p.system, r["navigator_text"],
                                             b64, schema.action_schema(indices),
                                             _action(indices), config.MAX_TOKENS)
        pick = call.result["index"] if call.result else None
        with out.open("a") as handle:
            handle.write(json.dumps({"key": key(rnd, run, r), "prompt": version, "set": kind,
                                     "toward": toward, "pick": pick,
                                     "recorded": r.get("index"), "error": call.error}) + "\n")
        print("{0}/{1} {2} {3} {4}: toward {5} pick {6}".format(
            n + 1, len(todo), version, kind, key(rnd, run, r), toward, pick), flush=True)

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
        k = (j["prompt"], j["set"])
        n[k] += 1
        followed[k] += j["pick"] == j["toward"]
        turned[k] += j["pick"] == 0
    print("prompt  set     asked  followed 'toward'   picked 0")
    for k in sorted(n):
        print("{0:<7} {1:<7} {2:>5}  {3:>5} ({4:5.1%})   {5:>5} ({6:5.1%})".format(
            k[0], k[1], n[k], followed[k], followed[k] / n[k], turned[k], turned[k] / n[k]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
    run.add_argument("--prompts", nargs="+", default=["p16", "p17"])
    run.add_argument("--concurrency", type=int, default=4)
    run.set_defaults(fn=cmd_run)
    score = sub.add_parser("score")
    score.add_argument("answers")
    score.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
