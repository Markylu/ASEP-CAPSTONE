"""R16 goal-confirmer probe: c01 on every recorded goal report (live model).

Every recorded step where the perceiver reported the goal in a strip is asked
again with c01 on its clean frame and the reported strip and range. Each
report is scored against the site model (eval/r12_probe.in_view: the goal
within the camera's field and in line of sight): genuine or false. The gate
(R16 README) wants most false reports refused and almost no genuine one.

    VLM_PROFILE=remote python eval/r16_confirm_probe.py run RUNS... --out c01.jsonl
    python eval/r16_confirm_probe.py score c01.jsonl RUNS...

The frames must be on disk (the flight host keeps them). Evaluation reads the
manifest's goal to score; the confirmer never sees it.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

from server.decider import prompt as prompts, schema, spatial, vlm  # noqa: E402
from server.decider.orchestrator import PERCEIVER_MAX_TOKENS, _confirmed  # noqa: E402
from r12_probe import in_view  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402


def reports(roots: List[str]) -> List[Tuple[str, Path, Dict[str, Any]]]:
    out = []
    for root in roots:
        for run in runs_under(Path(root).resolve()):
            for r in load(run):
                res = (r.get("perceiver") or {}).get("result") or {}
                strip = res.get("goal_reported") or res.get("goal")
                if strip in spatial.STRIPS and r.get("clean_frame"):
                    out.append((Path(root).resolve().parent.name, run, r))
    return out


def key(rnd: str, run: Path, r: Dict[str, Any]) -> str:
    return "{0}/{1}/{2}".format(rnd, label(run), r["step"])


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {json.loads(line)["key"] for line in out.read_text().splitlines() if line.strip()}
    todo = [c for c in reports(args.roots) if key(*c) not in done
            and (c[1] / c[2]["clean_frame"]).is_file()]
    p = prompts.get(args.prompt)
    print("{0} reports to ask".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, case) -> None:
        rnd, run, r = case
        res = r["perceiver"]["result"]
        report = {"strip": res.get("goal_reported") or res["goal"],
                  "range": spatial.WORDS["range"].get(res.get("goal_range"))}
        async with sem:
            b64 = base64.b64encode((run / r["clean_frame"]).read_bytes()).decode()
            call = await vlm.call_structured(schema.CONFIRMER_SCHEMA_NAME, p.system,
                                             p.render(p, report), b64,
                                             schema.confirmer_schema(), _confirmed,
                                             PERCEIVER_MAX_TOKENS)
        with out.open("a") as handle:
            handle.write(json.dumps({"key": key(rnd, run, r), "prompt": p.version,
                                     "strip": report["strip"], "result": call.result,
                                     "error": call.error}) + "\n")
        print("{0}/{1} {2}: {3}".format(n + 1, len(todo), key(rnd, run, r),
                                        (call.result or {}).get("present", call.error)),
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
    answers = {}
    for line in Path(args.answers).read_text().splitlines():
        j = json.loads(line) if line.strip() else {}
        if j.get("result"):
            answers[j["key"]] = j["result"]["present"]
    tally: Counter = Counter()
    for rnd, run, r in reports(args.roots):
        a = answers.get(key(rnd, run, r))
        if a is None:
            continue
        tally[("genuine" if in_view(r) else "false", a)] += 1
    g = tally[("genuine", "yes")] + tally[("genuine", "no")]
    f = tally[("false", "yes")] + tally[("false", "no")]
    print("goal reports asked: {0} genuine, {1} false".format(g, f))
    print("  genuine kept   {0}/{1} = {2:.1%}".format(tally[("genuine", "yes")], g,
                                                     tally[("genuine", "yes")] / max(1, g)))
    print("  false refused  {0}/{1} = {2:.1%}".format(tally[("false", "no")], f,
                                                     tally[("false", "no")] / max(1, f)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
    run.add_argument("--prompt", default="c01")
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
