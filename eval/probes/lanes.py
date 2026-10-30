"""Batch 0: index every flown run on the lane checkouts (docs/research/probe-plan.md).

Each round flew on several lane checkouts (~/asep-rNN-lK); its frames stayed
there (gitignored) while decisions.jsonl was merged into the repo. This walks
the given roots for eval/phase2/<round>/runs/<site>/<arm>/<seed>/decisions.jsonl
and writes one row per run to eval/phase2/_probes/lanes.jsonl, pointing at the
copy that has frames. Later probes load runs through this index.

    python3 eval/probes/lanes.py ~/asep-*

Check (probe plan, batch 0): every R15-R26N run in the repo is found, and every
run from R6 on has frames.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INDEX, PROBES, REPO_ROOT, round_id, round_number, write_jsonl  # noqa: E402

PATTERN = "eval/phase2/R*/runs/*/*/seed*/decisions.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def frames_in(run: Path) -> int:
    try:
        return sum(1 for n in os.listdir(run / "frames") if n.endswith(".png"))
    except OSError:
        return 0


def key_of(run: Path):
    return run.parts[-5], run.parts[-3], run.parts[-2], run.parts[-1]


def number(folder: str) -> int:
    return round_number(round_id(folder)) or 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    args = ap.parse_args()

    found = defaultdict(list)
    for root in args.roots:
        root = Path(root).expanduser().resolve()
        if not root.is_dir() or root == REPO_ROOT:
            continue
        for d in glob.glob(str(root / PATTERN)):
            run = Path(d).parent
            if "_attempts" in run.parts:
                continue
            with open(d) as f:
                n_dec = sum(1 for _ in f)
            found[key_of(run)].append({
                "dir": str(run), "lane": root.name, "frames": frames_in(run),
                "decisions": n_dec, "sha": sha(Path(d)),
                "complete": (run / "metrics.json").exists(),
            })

    rows = []
    for (folder, site, arm, seed), copies in sorted(found.items()):
        best = max(copies, key=lambda c: (c["complete"], c["frames"], c["decisions"]))
        repo = REPO_ROOT / "eval" / "phase2" / folder / "runs" / site / arm / seed / "decisions.jsonl"
        rows.append({
            "folder": folder, "round": round_id(folder), "site": site, "arm": arm, "seed": seed,
            "decisions_dir": best["dir"], "lane": best["lane"], "frames": best["frames"],
            "decisions": best["decisions"], "copies": len(copies),
            "repo_match": (sha(repo) == best["sha"]) if repo.exists() else None,
        })
    write_jsonl(INDEX, rows)

    have = {(r["folder"], r["site"], r["arm"], r["seed"]): r for r in rows}
    repo_runs = sorted(Path(p).parent for p in glob.glob(str(REPO_ROOT / PATTERN))
                       if "_attempts" not in p)
    missing, no_frames, differ = [], [], []
    for run in repo_runs:
        key = key_of(run)
        r = have.get(key)
        if r is None:
            missing.append("/".join(key))
            continue
        if number(key[0]) >= 6 and r["frames"] == 0:
            no_frames.append("/".join(key))
        if r["repo_match"] is False:
            differ.append("/".join(key))
    in_scope = [r for r in repo_runs if 15 <= number(r.parts[-5]) <= 26]
    missing_scope = [m for m in missing if 15 <= number(m.split("/")[0]) <= 26]

    out = [
        "lane index: {0} runs from {1} roots -> {2}".format(len(rows), len(args.roots), INDEX),
        "repo runs: {0}; R15-R26N in repo: {1}".format(len(repo_runs), len(in_scope)),
        "R15-R26N missing from the lanes: {0}".format(len(missing_scope)),
        "any round missing from the lanes: {0}".format(len(missing)),
        "R6+ indexed runs without frames: {0}".format(len(no_frames)),
        "decisions.jsonl differs from the repo copy: {0}".format(len(differ)),
        "check: {0}".format("PASS" if not missing_scope and not no_frames else "FAIL"),
    ]
    for name, items in (("missing", missing), ("no frames", no_frames), ("differs", differ)):
        out += ["  {0}: {1}".format(name, i) for i in items[:60]]
    text = "\n".join(out) + "\n"
    (PROBES / "lanes_check.txt").write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
