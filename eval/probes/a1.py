"""Probe A1: does the strategist's pick follow the item or the list position? (model calls)

Recorded q03 strategist calls re-asked with only the menu lines reordered.
Method and gate: eval/phase2/_probes/a1/README.md (committed before the first call).

    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/a1.py run --shard 0 --of 2
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/a1.py run --shard 1 --of 2
    python eval/probes/a1.py score
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROBES, agents, load, runs, write_jsonl  # noqa: E402

N_CALLS = 300
FIRST, LAST = 19, 26
FIRST_AGENT = "a49"
EXPLORE = "explore"
ORDERS = ("rec", "rec2", "rev", "shuf")
CONCURRENCY = 8
OUT = PROBES / "a1"


def sample():
    calls = []
    for run in runs(FIRST, LAST):
        for r in load(run["path"]):
            s = r.get("strategist") or {}
            menu = s.get("menu") or []
            v = r.get("agent_version")
            if len(menu) < 2 or not s.get("text") or not v:
                continue
            if agents.get(v).features.get("orchestrator", {}).get("strategist") != "q03":
                continue
            key = "{0}/{1}/{2}/{3}".format(run["round"], run["site"], run["arm"], r["step"])
            calls.append({"key": key, "agent": v, "text": s["text"],
                          "ids": [m["id"] for m in menu],
                          "recorded": (s.get("result") or {}).get("target")})

    def h(c):
        return hashlib.sha256(c["key"].encode()).hexdigest()

    calls.sort(key=lambda c: (c["agent"] != FIRST_AGENT, h(c)))
    return calls[:N_CALLS]


def orders(c):
    ids = c["ids"]
    rev = list(reversed(ids))
    shuf = list(ids)
    rng = random.Random(c["key"])
    for _ in range(20):
        rng.shuffle(shuf)
        if shuf != ids and shuf != rev:
            break
    if shuf == ids:
        shuf = rev
    return {"rec": list(ids), "rec2": list(ids), "rev": rev, "shuf": shuf}


def reorder(text: str, ids, new) -> str:
    lines = text.splitlines()
    at = {i: next(k for k, x in enumerate(lines) if x.startswith("  " + i + ":")) for i in ids}
    block = sorted(at.values())
    assert block == list(range(block[0], block[0] + len(ids))), "menu lines not contiguous"
    moved = [lines[at[i]] for i in new]
    return "\n".join(lines[:block[0]] + moved + lines[block[-1] + 1:])


async def run_probe(shard: int, of: int) -> None:
    from server.decider import config, orchestrator, prompt as prompts, schema, vlm
    q03 = prompts.get("q03")
    sem = asyncio.Semaphore(CONCURRENCY)
    todo = sample()[shard::of]

    async def ask(c, name, ids):
        options = ids + [EXPLORE]
        text = reorder(c["text"], c["ids"], ids)
        async with sem:
            sub = await vlm.call_structured(
                schema.STRATEGIST_SCHEMA_NAME, q03.system, text, None,
                schema.strategist_schema(options), orchestrator._strategy(options),
                orchestrator.STRATEGIST_MAX_TOKENS)
        picked = (sub.result or {}).get("target")
        return {"key": c["key"], "agent": c["agent"], "order": name, "ids": ids,
                "picked": picked, "pos": options.index(picked) + 1 if picked in options else None,
                "recorded": c["recorded"], "instance": config.LITELLM_BASE_URL,
                "rung": sub.rung, "raw": sub.raw}

    rows = await asyncio.gather(*(ask(c, name, ids) for c in todo
                                  for name, ids in orders(c).items()))
    write_jsonl(OUT / "calls_{0}of{1}.jsonl".format(shard, of), list(rows))
    print("shard {0}/{1}: {2} calls on {3}".format(shard, of, len(rows), config.LITELLM_BASE_URL))


def score() -> int:
    rows = []
    for f in sorted(OUT.glob("calls_*of*.jsonl")):
        rows += [json.loads(l) for l in f.read_text().splitlines()]
    by = {}
    for r in rows:
        by.setdefault(r["key"], {})[r["order"]] = r
    full = {k: v for k, v in by.items() if all(o in v and v[o]["picked"] for o in ORDERS)}

    def same(a, b, keys):
        return sum(full[k][a]["picked"] == full[k][b]["picked"] for k in keys) / len(keys)

    def gap_of(keys):
        nn = same("rec", "rec2", keys)
        no = (same("rec", "rev", keys) + same("rec", "shuf", keys)) / 2
        return nn, no

    lines = ["A1: {0} calls x 4 orders; {1} with all four answered".format(len(by), len(full))]
    groups = (("all", list(full)),
              ("not all-explore", [k for k in full
                                   if any(full[k][o]["picked"] != EXPLORE for o in ORDERS)]))
    for label, keys in groups:
        if not keys:
            continue
        nn, no = gap_of(keys)
        lines += ["\n## {0} ({1} calls)".format(label, len(keys)),
                  "  Nn (rec vs rec2, noise): {0:.1%}".format(nn),
                  "  No (rec vs rev {0:.1%}, rec vs shuf {1:.1%}): {2:.1%}".format(
                      same("rec", "rev", keys), same("rec", "shuf", keys), no),
                  "  Nn - No: {0:+.1f} pts".format((nn - no) * 100)]
        for o in ORDERS:
            first = sum(full[k][o]["pos"] == 1 for k in keys) / len(keys)
            expl = sum(full[k][o]["picked"] == EXPLORE for k in keys) / len(keys)
            lines.append("  {0:4s}: first-listed picked {1:.1%}, explore {2:.1%}".format(
                o, first, expl))
        diff = [k for k in keys if full[k]["rec"]["picked"] != full[k]["rev"]["picked"]]
        if diff:
            pos_same = sum(full[k]["rec"]["pos"] == full[k]["rev"]["pos"] for k in diff) / len(diff)
            lines.append("  rec != rev on {0} calls; rev pick at the same list position: "
                         "{1:.1%}".format(len(diff), pos_same))
        fid = sum(full[k]["rec"]["picked"] == full[k]["rec"]["recorded"] for k in keys) / len(keys)
        lines.append("  replay fidelity (rec = originally recorded pick): {0:.1%}".format(fid))
    lines.append("\n## By instance")
    for inst in sorted({r["instance"] for r in rows}):
        keys = [k for k in full if full[k]["rec"]["instance"] == inst]
        if keys:
            nn, no = gap_of(keys)
            lines.append("  {0}: {1} calls, Nn {2:.1%}, No {3:.1%}".format(inst, len(keys), nn, no))
    nn, no = gap_of(list(full))
    gap = (nn - no) * 100
    verdict = "HOLDS" if gap >= 15 else ("REFUTED" if gap <= 5 else "no call")
    lines += ["\n## Gate (all calls)", "  Nn - No = {0:+.1f} pts -> {1}".format(gap, verdict)]
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "score", "count"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "run":
        asyncio.run(run_probe(args.shard, args.of))
        return 0
    if args.cmd == "count":
        s = sample()
        print(len(s), "calls;", sum(c["agent"] == FIRST_AGENT for c in s), "from", FIRST_AGENT)
        if s:
            print(reorder(s[0]["text"], s[0]["ids"], orders(s[0])["shuf"]))
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
