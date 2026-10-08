#!/usr/bin/env python3
"""Phase 1 runner: fly a mini-phase under the frozen spec, then check it.

The spec is docs/phase1-test-plan.md. Section numbers below point into it.

    python eval/phase1.py init                       # lay out eval/phase1/ (idempotent)
    python eval/phase1.py run --mini-phase 1.0       # fly order.txt, skip valid runs
    python eval/phase1.py run --mini-phase 1A --only s01/dynamic/3
    python eval/phase1.py validate --mini-phase 1A   # re-check without flying
    python eval/phase1.py status
    python eval/phase1.py results                    # §11 tables -> eval/phase1/results/

One Godot at a time, always (§7.1): parallel runs would inflate decision
latency, which is a dependent variable. A decider must already be running.
Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import itertools
import json
import math
import random
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE_DIR = REPO_ROOT / "eval" / "phase1"
GODOT_PROJECT = REPO_ROOT / "first-project"
REPLAY_CLI = REPO_ROOT / "eval" / "replay.py"
LOCK_PATH = PHASE_DIR / "config.lock.json"
MATRIX_PATH = PHASE_DIR / "matrix.csv"

ARMS = ("initial", "final", "dynamic")
SEEDS = (1, 2, 3, 4, 5)

#: Short name (used in run ids, folders and order.txt) -> site id at the frozen
#: version (§3).
SITES: Dict[str, Tuple[str, int]] = {
    "s01": ("s01_occluder_dropin", 1),
    "s02a": ("s02a_doors_open_a", 2),
    "s02c": ("s02c_doors_open_c", 2),
    "s02va": ("s02va_doors_visible_a", 1),
    "s02vc": ("s02vc_doors_visible_c", 1),
    "s03": ("s03_fork_deadend", 2),
}

#: x of each site's change trigger (§4). A dynamic run must carry the change
#: event on the move that first reached it: step 3 flying straight, later if
#: the agent turned. s03's trigger is inside whichever tine the agent enters,
#: so there is no single line to check.
TRIGGER_X: Dict[str, Optional[float]] = {
    "s01": 6.5, "s02a": 6.5, "s02c": 6.5, "s02va": 14.5, "s02vc": 14.5, "s03": None,
}
#: The agent touches a trigger box before its centre crosses TRIGGER_X: half
#: the box depth (1.0 m, every site.json) plus the agent's sphere (r = 0.2 m,
#: vlmnav_controller.tscn).
TRIGGER_REACH_M = 0.5 + 0.2
#: How far the agent travels in the ~2 physics ticks before an overlap is
#: reported (a move is 1.7 m in ~13-17 ticks).
SIGNAL_LAG_M = 0.3
CHANGE_EVENTS = ("occluder_deployed", "doors_switched")

#: §7 table. seeds: which replicates the mini-phase flies.
MINI_PHASES: Dict[str, Dict[str, Any]] = {
    "1.0": {"folder": "1.0_shakedown", "title": "Shakedown (fake decider)",
            "sites": list(SITES), "seeds": [1], "citable": False},
    "1A": {"folder": "1A_s01", "title": "Object Appearance",
           "sites": ["s01"], "seeds": list(SEEDS), "citable": True},
    "1Ba": {"folder": "1Ba_s02a", "title": "Door Switch, out of view, A opens",
            "sites": ["s02a"], "seeds": list(SEEDS), "citable": True},
    "1Bc": {"folder": "1Bc_s02c", "title": "Door Switch, out of view, C opens",
            "sites": ["s02c"], "seeds": list(SEEDS), "citable": True},
    "1Ca": {"folder": "1Ca_s02va", "title": "Door Switch, in view, A opens",
            "sites": ["s02va"], "seeds": list(SEEDS), "citable": True},
    "1Cc": {"folder": "1Cc_s02vc", "title": "Door Switch, in view, C opens",
            "sites": ["s02vc"], "seeds": list(SEEDS), "citable": True},
    "1D": {"folder": "1D_s03", "title": "Split Path",
           "sites": ["s03"], "seeds": list(SEEDS), "citable": True},
}

#: §7.4, verbatim. 1.0 is not in the spec's list; it is generated the same way.
ORDERS: Dict[str, str] = {
    "1A": """s01/final/1, s01/initial/4, s01/dynamic/4, s01/final/4, s01/final/3, s01/initial/1,
s01/final/2, s01/initial/2, s01/dynamic/1, s01/dynamic/5, s01/initial/5, s01/final/5,
s01/dynamic/2, s01/initial/3, s01/dynamic/3""",
    "1Ba": """s02a/initial/3, s02a/dynamic/5, s02a/dynamic/4, s02a/initial/4, s02a/final/2,
s02a/final/5, s02a/final/1, s02a/initial/5, s02a/initial/1, s02a/final/3, s02a/final/4,
s02a/dynamic/3, s02a/initial/2, s02a/dynamic/1, s02a/dynamic/2""",
    "1Bc": """s02c/initial/1, s02c/initial/5, s02c/initial/2, s02c/dynamic/5, s02c/final/3,
s02c/final/1, s02c/dynamic/1, s02c/dynamic/4, s02c/initial/4, s02c/dynamic/2, s02c/final/2,
s02c/dynamic/3, s02c/final/5, s02c/final/4, s02c/initial/3""",
    "1Ca": """s02va/dynamic/3, s02va/dynamic/2, s02va/final/2, s02va/final/5, s02va/final/4,
s02va/dynamic/1, s02va/initial/2, s02va/dynamic/4, s02va/initial/3, s02va/initial/5,
s02va/initial/1, s02va/dynamic/5, s02va/final/1, s02va/final/3, s02va/initial/4""",
    "1Cc": """s02vc/dynamic/3, s02vc/final/3, s02vc/initial/5, s02vc/initial/2, s02vc/dynamic/2,
s02vc/initial/3, s02vc/final/4, s02vc/initial/1, s02vc/final/1, s02vc/dynamic/1,
s02vc/final/5, s02vc/dynamic/5, s02vc/final/2, s02vc/dynamic/4, s02vc/initial/4""",
    "1D": """s03/final/2, s03/dynamic/4, s03/initial/4, s03/initial/2, s03/dynamic/5, s03/final/3,
s03/initial/3, s03/dynamic/2, s03/final/4, s03/initial/1, s03/dynamic/1, s03/initial/5,
s03/final/1, s03/final/5, s03/dynamic/3""",
}

#: §3 and §6, as recorded per run. `run.json` must agree with every entry.
LOCK: Dict[str, Any] = {
    "spec": "docs/phase1-test-plan.md",
    "model": "Qwen3-VL-30B-A3B",
    "vlm_profile": "remote",
    "temperature": 0.0,
    "prompt_version": "p02",
    "prompt_sha": "26260774b60e",
    "frame_size": [768, 768],
    "freeze_world": True,
    "physics_ticks_per_second": 60,
    "godot_version": "4.7.2-stable (official)",
    "config": {"fov_deg": 87.0, "camera_pitch": 0.0, "num_actions": 5,
               "include_turn_around": True, "fan_spread": 1.0,
               "action_dist": 1.7, "annotation_distance": 6.0},
    "max_steps": 60,
    "max_collisions": -1,
    "stop_on_goal": True,
    "wall_clock_s": 900,
    "seeds": list(SEEDS),
    "spawn_jitter": {"dz_m": 0.5, "dyaw_deg": 5.0},
    "sites": {site_id: version for site_id, version in SITES.values()},
    # 1.0 flies the stand-in router (server/decider/fake_litellm.py) so it
    # spends no H100 time. Everything else is checked as for a citable phase.
    "overrides": {"1.0": {"model": "stub"}},
}

MATRIX_FIELDS = ["mini_phase", "site", "site_version", "arm", "seed", "run_id",
                 "attempt", "status", "end_reason", "invalid_reason"]
VALID_END_REASONS = ("goal_reached", "max_steps")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text()) if path.is_file() else {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ------------------------------------------------------------------ layout

def order_of(mp: str) -> List[Tuple[str, str, int]]:
    if mp in ORDERS:
        out = []
        for token in ORDERS[mp].replace("\n", " ").split(","):
            site, arm, seed = token.strip().split("/")
            out.append((site, arm, int(seed)))
        return out
    spec = MINI_PHASES[mp]
    cells = [(str(site), str(arm), int(seed))
             for site, arm, seed in itertools.product(spec["sites"], ARMS, spec["seeds"])]
    random.Random("phase1-" + mp).shuffle(cells)
    return cells


def move_ends(run_dir: Path) -> List[Tuple[int, float]]:
    """(step, x where that move ended), in order.

    Step k in steps.jsonl is where move k ended. steps.jsonl is git-ignored,
    so fall back to decisions.jsonl: decision k's pose is where move k ended.
    """
    ends = [(s["step"], s["position"][0]) for s in read_jsonl(run_dir / "steps.jsonl")]
    if not ends:
        ends = [(d["step"], d["manifest"]["pose"]["position"][0])
                for d in read_jsonl(run_dir / "decisions.jsonl") if d["step"] > 0]
    return sorted(ends)


def crossing_step(site: str, run_dir: Path) -> Optional[int]:
    """The first move that ended touching the trigger box, else None."""
    trigger_x = TRIGGER_X[site]
    if trigger_x is None:
        return None
    reach = trigger_x + TRIGGER_REACH_M
    return next((step for step, x in move_ends(run_dir) if x <= reach), None)


def change_step_ok(site: str, run_dir: Path, event_step: Optional[int]) -> bool:
    """§10: the change fired on the move that reached the trigger.

    The next move is also accepted when the agent only just reached it: the
    overlap is reported a couple of physics ticks late, and if those fall
    after the move ends, the frozen world delivers it on the next one.
    """
    crossed = crossing_step(site, run_dir)
    if crossed is None or event_step is None:
        return False
    if event_step == crossed:
        return True
    end_x = dict(move_ends(run_dir))[crossed]
    reach = TRIGGER_X[site] + TRIGGER_REACH_M  # type: ignore[operator]
    return event_step == crossed + 1 and end_x > reach - SIGNAL_LAG_M


def phase_dir(mp: str) -> Path:
    return PHASE_DIR / MINI_PHASES[mp]["folder"]


def run_id_for(mp: str, site: str, arm: str, seed: int, attempt: int) -> str:
    return "p1_{0}_{1}_{2}_seed{3}_a{4:02d}".format(mp, site, arm, seed, attempt)


def run_dir_for(mp: str, site: str, arm: str, seed: int) -> Path:
    return phase_dir(mp) / "runs" / site / arm / "seed{0}".format(seed)


def load_matrix() -> List[Dict[str, Any]]:
    if not MATRIX_PATH.is_file():
        return []
    with MATRIX_PATH.open(newline="") as handle:
        return list(csv.DictReader(handle))


def save_matrix(rows: List[Dict[str, Any]]) -> None:
    with MATRIX_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def latest_row(rows: List[Dict[str, Any]], mp: str, site: str, arm: str,
               seed: int) -> Dict[str, Any]:
    """The current attempt for a cell: the highest attempt number."""
    cell = [r for r in rows if r["mini_phase"] == mp and r["site"] == site
            and r["arm"] == arm and int(r["seed"]) == seed]
    return max(cell, key=lambda r: int(r["attempt"]))


def cmd_init(_args: argparse.Namespace) -> int:
    PHASE_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.is_file() and read_json(LOCK_PATH) != LOCK:
        print("config.lock.json differs from the lock in eval/phase1.py. The spec "
              "changed: restart the affected mini-phases (§7.1) and replace the "
              "lock by hand. Not overwriting.")
        return 1
    write_json(LOCK_PATH, LOCK)

    rows: List[Dict[str, Any]] = list(load_matrix())
    have = {(r["mini_phase"], r["site"], r["arm"], str(r["seed"])) for r in rows}
    for mp, spec in MINI_PHASES.items():
        folder = phase_dir(mp)
        (folder / "runs").mkdir(parents=True, exist_ok=True)
        order = order_of(mp)
        cells = len(spec["sites"]) * len(ARMS) * len(spec["seeds"])
        if len(order) != cells or len(set(order)) != cells:
            raise SystemExit("order for {0} is not the full design ({1} cells)".format(mp, cells))
        (folder / "order.txt").write_text(
            "".join("{0}/{1}/{2}\n".format(*cell) for cell in order))
        if not (folder / "phase.json").is_file():
            write_json(folder / "phase.json", {
                "mini_phase": mp, "title": spec["title"], "citable": spec["citable"],
                "status": "planned", "git_sha": None, "started": None, "finished": None,
                "operator": None, "notes": ""})
        for site, arm, seed in sorted(order):
            if (mp, site, arm, str(seed)) in have:
                continue
            rows.append({"mini_phase": mp, "site": site, "site_version": SITES[site][1],
                         "arm": arm, "seed": seed,
                         "run_id": run_id_for(mp, site, arm, seed, 1), "attempt": 1,
                         "status": "planned", "end_reason": "", "invalid_reason": ""})
    save_matrix(rows)
    write_readme()
    print("eval/phase1 laid out: {0} matrix rows".format(len(rows)))
    return 0


def write_readme() -> None:
    rows = load_matrix()
    lines = ["# Phase 1 data", "",
             "Flown under `docs/phase1-test-plan.md`. Regenerated by `eval/phase1.py`; "
             "do not edit by hand.", "",
             "| Mini-phase | Title | Citable | Status | Valid / planned | Git SHA | Summary |",
             "|---|---|---|---|---|---|---|"]
    for mp, spec in MINI_PHASES.items():
        folder = phase_dir(mp)
        phase = read_json(folder / "phase.json")
        current = [latest_row(rows, mp, s, a, sd) for s, a, sd in order_of(mp)] if rows else []
        valid = sum(1 for r in current if r["status"] == "valid")
        summary = ("[summary]({0}/summary.md)".format(spec["folder"])
                   if (folder / "summary.md").is_file() else "")
        lines.append("| {0} | {1} | {2} | {3} | {4} / {5} | {6} | {7} |".format(
            mp, spec["title"], "yes" if spec["citable"] else "no",
            phase.get("status", "planned"), valid, len(current),
            phase.get("git_sha") or "", summary))
    if (PHASE_DIR / "results" / "results.md").is_file():
        lines += ["", "Aggregate tables and contrasts (§11): [results/results.md](results/results.md), "
                  "built by `eval/phase1.py results`."]
    (PHASE_DIR / "README.md").write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------ preflight

def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO_ROOT)] + list(args),
                          capture_output=True, text=True).stdout.strip()


def git_clean() -> bool:
    """Same rule as the decider's `git_dirty`: recorded data does not count."""
    return not git("status", "--porcelain", "--", ".", ":(exclude)eval/runs",
                   ":(exclude)eval/phase1")


def expected(mp: str, key: str) -> Any:
    return LOCK["overrides"].get(mp, {}).get(key, LOCK[key])


def decider_health(url: str) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure means "do not fly"
        return {"ok": False, "error": str(exc)}


def preflight(mp: str, decider_url: str) -> List[str]:
    """§7.2 step 1. The scripted probe per site is done by hand."""
    problems = []
    if read_json(LOCK_PATH) != LOCK:
        problems.append("config.lock.json missing or stale: run `init`")
    if not git_clean():
        problems.append("git tree has uncommitted changes outside eval/runs and eval/phase1")
    health = decider_health(decider_url)
    if not health.get("ok"):
        problems.append("decider not healthy at {0}: {1}".format(decider_url, health))
    else:
        for key, want in (("model", expected(mp, "model")), ("prompt_sha", LOCK["prompt_sha"]),
                          ("profile", LOCK["vlm_profile"])):
            if health.get(key) != want:
                problems.append("decider {0} is {1!r}, lock wants {2!r}".format(
                    key, health.get(key), want))
    for short in MINI_PHASES[mp]["sites"]:
        site_id, version = SITES[short]
        manifest = read_json(GODOT_PROJECT / "sites" / site_id / "site.json")
        if manifest.get("version") != version or manifest.get("status") != "active":
            problems.append("{0} is v{1} {2}, lock wants v{3} active".format(
                site_id, manifest.get("version"), manifest.get("status"), version))
    return problems


# ------------------------------------------------------------------ flying

def fly(site: str, arm: str, seed: int, run_id: str, run_dir: Path,
        decider_url: str, godot: str) -> int:
    command = [
        godot, "--path", str(GODOT_PROJECT),
        "res://sites/{0}/site.tscn".format(SITES[site][0]), "--",
        "--run-id=" + run_id,
        "--run-dir=" + str(run_dir.relative_to(REPO_ROOT)),
        "--decider-url=" + decider_url,
        "--max-steps={0}".format(LOCK["max_steps"]),
        "--max-collisions={0}".format(LOCK["max_collisions"]),
        "--frame-size={0}x{1}".format(*LOCK["frame_size"]),
        "--world=" + arm,
        "--spawn-seed={0}".format(seed),
    ]
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Godot enforces the 900 s wall clock itself; this is the backstop.
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=LOCK["wall_clock_s"] + 120)
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        code, output = 124, "subprocess timeout\n{0}".format(exc.stdout or "")
    (run_dir / "godot.log").write_text(output)
    ended = [line for line in output.splitlines() if "RUN ENDED" in line]
    print("    " + (ended[-1].strip()[:140] if ended
                    else "no RUN ENDED line (exit {0})".format(code)))
    return code


def replay(run_dir: Path, decider_url: str, godot: str) -> Dict[str, Any]:
    verdict_path = run_dir / "replay.json"
    subprocess.run([sys.executable, str(REPLAY_CLI), str(run_dir),
                    "--decider-url", decider_url, "--godot", godot,
                    "--json", str(verdict_path)],
                   capture_output=True, text=True, timeout=LOCK["wall_clock_s"])
    return read_json(verdict_path) or {"ok": False, "error": "replay wrote no verdict"}


# ------------------------------------------------------------------ validity (§10)

def validate(mp: str, site: str, arm: str, seed: int, run_dir: Path,
             phase_sha: Optional[str]) -> List[str]:
    meta = read_json(run_dir / "run.json")
    metrics = read_json(run_dir / "metrics.json")
    if not meta or not metrics:
        return ["run.json or metrics.json missing"]
    reasons = []

    if metrics.get("end_reason") not in VALID_END_REASONS:
        reasons.append("end reason {0}".format(str(metrics.get("end_reason"))[:80]))
    if any("error" in d for d in read_jsonl(run_dir / "decisions.jsonl")):
        reasons.append("decision_error in decisions.jsonl")
    rungs = metrics.get("rungs_used") or {}
    total = sum(rungs.values())
    if not total or rungs.get("json_schema", 0) / total < 0.9:
        reasons.append("json_schema rung below 90%: {0}".format(rungs))

    wanted = {
        "model": expected(mp, "model"), "vlm_profile": LOCK["vlm_profile"],
        "temperature": LOCK["temperature"], "prompt_version": LOCK["prompt_version"],
        "prompt_sha": LOCK["prompt_sha"], "frame_size": LOCK["frame_size"],
        "freeze_world": LOCK["freeze_world"],
        "physics_ticks_per_second": LOCK["physics_ticks_per_second"],
        "godot_version": LOCK["godot_version"], "max_steps": LOCK["max_steps"],
        "site_id": SITES[site][0], "site_version": SITES[site][1],
        "world": arm, "spawn_seed": seed, "git_dirty": False,
    }
    for key, value in wanted.items():
        if meta.get(key) != value:
            reasons.append("run.json {0}={1!r}, want {2!r}".format(key, meta.get(key), value))
    config = meta.get("config") or {}
    for key, value in LOCK["config"].items():
        if config.get(key) != value:
            reasons.append("config {0}={1!r}, want {2!r}".format(key, config.get(key), value))
    if phase_sha and meta.get("git_sha") != phase_sha:
        reasons.append("git_sha {0} != mini-phase {1}".format(meta.get("git_sha"), phase_sha))

    changes = [e for e in read_jsonl(run_dir / "events.jsonl") if e.get("name") in CHANGE_EVENTS]
    trigger_x = TRIGGER_X[site]
    crossed = crossing_step(site, run_dir)
    if arm != "dynamic":
        if changes:
            reasons.append("change event in a {0} arm".format(arm))
    elif changes:
        if trigger_x is not None and not change_step_ok(site, run_dir, changes[0].get("step")):
            reasons.append("change at step {0}, but the trigger was reached at step {1}"
                           .format(changes[0].get("step"), crossed))
    elif crossed is not None:
        # Absent is only legitimate if the agent never reached the trigger
        # (-> pre_change_failure).
        reasons.append("crossed trigger x={0} at step {1} but no change event".format(
            trigger_x, crossed))

    verdict = read_json(run_dir / "replay.json")
    if not verdict.get("ok"):
        reasons.append("replay not ok: {0}".format(
            {k: verdict.get(k) for k in ("problems", "max_pos_drift", "events_match",
                                         "error", "godot_exit") if k in verdict}))
    return reasons


def retire(mp: str, site: str, arm: str, seed: int, label: str) -> None:
    """Invalid or crashed attempts are moved, never deleted (§10)."""
    source = run_dir_for(mp, site, arm, seed)
    target = phase_dir(mp) / "_attempts" / site / arm / "seed{0}".format(seed) / label
    if target.exists():
        target = target.with_name(label + "_" + datetime.now().strftime("%Y%m%d%H%M%S"))
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.move(str(source), str(target))


def cmd_run(args: argparse.Namespace) -> int:
    mp = args.mini_phase
    folder = phase_dir(mp)
    phase = read_json(folder / "phase.json")
    if not phase:
        raise SystemExit("run `init` first")
    if phase.get("status") in ("complete", "superseded"):
        raise SystemExit("{0} is {1}".format(mp, phase["status"]))

    problems = preflight(mp, args.decider_url)
    head = git("rev-parse", "--short", "HEAD")
    if phase.get("git_sha") and phase["git_sha"] != head:
        problems.append("HEAD {0} != mini-phase SHA {1}: one SHA per mini-phase (§7.1); "
                        "restart the mini-phase to change it".format(head, phase["git_sha"]))
    if problems:
        print("PREFLIGHT FAILED:\n  " + "\n  ".join(problems))
        return 1
    if not phase.get("git_sha"):
        phase.update({"git_sha": head, "started": now(), "status": "running",
                      "operator": git("config", "user.name") or getpass.getuser()})
        write_json(folder / "phase.json", phase)

    cells = order_of(mp)
    if args.only:
        site, arm, seed = args.only.split("/")
        cells = [c for c in cells if c == (site, arm, int(seed))]
        if not cells:
            raise SystemExit("{0} is not in {1}'s order".format(args.only, mp))

    for index, (site, arm, seed) in enumerate(cells, 1):
        for _ in range(args.max_attempts):
            rows = load_matrix()
            row = latest_row(rows, mp, site, arm, seed)
            if row["status"] == "valid":
                break
            attempt = int(row["attempt"])
            run_dir = run_dir_for(mp, site, arm, seed)
            print("[{0}/{1}] {2}".format(index, len(cells), row["run_id"]))
            if run_dir.exists():
                # Left by an interrupted flight of this same attempt.
                retire(mp, site, arm, seed, "a{0:02d}_interrupted".format(attempt))
            fly(site, arm, seed, row["run_id"], run_dir, args.decider_url, args.godot)
            if read_json(run_dir / "run.json") and read_jsonl(run_dir / "decisions.jsonl"):
                verdict = replay(run_dir, args.decider_url, args.godot)
                print("    replay {0}".format("ok" if verdict.get("ok") else "FAILED"))
            reasons = validate(mp, site, arm, seed, run_dir, phase["git_sha"])
            row["end_reason"] = read_json(run_dir / "metrics.json").get("end_reason", "")
            if not reasons:
                row["status"] = "valid"
                save_matrix(rows)
                print("    valid")
                break
            row["status"], row["invalid_reason"] = "invalid", "; ".join(reasons)
            print("    INVALID: " + row["invalid_reason"])
            retire(mp, site, arm, seed, "a{0:02d}".format(attempt))
            rows.append(dict(row, run_id=run_id_for(mp, site, arm, seed, attempt + 1),
                             attempt=attempt + 1, status="planned", end_reason="",
                             invalid_reason=""))
            save_matrix(rows)
        else:
            print("giving up on {0}/{1}/{2} after {3} attempts".format(
                site, arm, seed, args.max_attempts))
            write_readme()
            return 1
    write_readme()
    return report(mp)


def cmd_validate(args: argparse.Namespace) -> int:
    mp = args.mini_phase
    phase = read_json(phase_dir(mp) / "phase.json")
    bad = 0
    for site, arm, seed in order_of(mp):
        reasons = validate(mp, site, arm, seed, run_dir_for(mp, site, arm, seed),
                           phase.get("git_sha"))
        if reasons:
            bad += 1
            print("{0}/{1}/{2}: {3}".format(site, arm, seed, "; ".join(reasons)))
    print("{0} invalid".format(bad))
    return 1 if bad else 0


# ------------------------------------------------------------------ results

RESULTS_DIR = PHASE_DIR / "results"
#: §9 terminal labels, in rubric order, as the §11 table columns.
LABEL_COLUMNS = (("success", "success"), ("ignore", "ignore_change"),
                 ("replan", "replan_failure"), ("collision", "collision"),
                 ("timeout", "timeout"), ("pre-change", "pre_change_failure"))
#: §4 layouts: (title, sites). The two door layouts pool their mirror pair.
LAYOUTS = (("L1 Object Appearance", ["s01"]),
           ("L2a Door Switch, out of view", ["s02a", "s02c"]),
           ("L2b Door Switch, in view", ["s02va", "s02vc"]),
           ("L3 Split Path", ["s03"]))
RUN_FIELDS = ["mini_phase", "site", "arm", "seed", "run_id", "goal_reached", "label",
              "reviewer", "steps", "collisions", "final_goal_distance_m", "end_reason",
              "latency_p50_ms", "latency_p95_ms", "git_sha"]


def wilson(k: int, n: int, z: float = 1.959964) -> Tuple[float, float]:
    """Wilson score 95% interval for k successes in n (§8)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def fisher(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher's exact p for k1/n1 vs k2/n2 (§11).

    Sums every table with the same margins that is no more likely than the
    observed one, the usual two-sided definition.
    """
    total, hits = n1 + n2, k1 + k2

    def prob(a: int) -> float:
        return math.comb(n1, a) * math.comb(n2, hits - a) / math.comb(total, hits)

    observed = prob(k1)
    low, high = max(0, hits - n2), min(hits, n1)
    return min(1.0, sum(prob(a) for a in range(low, high + 1)
                        if prob(a) <= observed * (1 + 1e-9)))


def pct(values: List[float], percentile: float) -> Optional[float]:
    """Linear interpolation, the same rule as the recorder's per-run p50/p95."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def collect_runs() -> List[Dict[str, Any]]:
    """The current valid run of every cell in every complete, citable mini-phase."""
    rows = load_matrix()
    runs = []  # type: List[Dict[str, Any]]
    for mp, spec in MINI_PHASES.items():
        if not spec["citable"]:
            continue
        if read_json(phase_dir(mp) / "phase.json").get("status") != "complete":
            continue
        labels = {}  # type: Dict[str, Dict[str, str]]
        labels_path = phase_dir(mp) / "labels.csv"
        if labels_path.is_file():
            with labels_path.open(newline="") as handle:
                labels = {r["run_id"]: r for r in csv.DictReader(handle)}
        for site, arm, seed in sorted(order_of(mp)):
            row = latest_row(rows, mp, site, arm, seed)
            if row["status"] != "valid":
                raise SystemExit("{0} {1}/{2}/{3} is not valid; a complete mini-phase "
                                 "must be".format(mp, site, arm, seed))
            run_dir = run_dir_for(mp, site, arm, seed)
            metrics = read_json(run_dir / "metrics.json")
            latencies = [float(d["latency_ms"]) for d in read_jsonl(run_dir / "decisions.jsonl")
                         if d.get("latency_ms") is not None]
            label = labels.get(row["run_id"], {})
            runs.append({
                "mini_phase": mp, "site": site, "arm": arm, "seed": seed,
                "run_id": row["run_id"], "goal_reached": bool(metrics.get("goal_reached")),
                "label": label.get("label", ""), "reviewer": label.get("reviewer", ""),
                "steps": metrics.get("steps"), "collisions": metrics.get("collisions"),
                "final_goal_distance_m": metrics.get("final_goal_distance_m"),
                "end_reason": metrics.get("end_reason"),
                "latency_p50_ms": (metrics.get("latency_ms") or {}).get("p50"),
                "latency_p95_ms": (metrics.get("latency_ms") or {}).get("p95"),
                "git_sha": metrics.get("git_sha"), "_latencies": latencies,
            })
    return runs


def table_row(name: str, arm: str, cell: List[Dict[str, Any]]) -> str:
    n = len(cell)
    k = sum(1 for r in cell if r["goal_reached"])
    low, high = wilson(k, n)
    counts = [str(sum(1 for r in cell if r["label"] == label)) for _, label in LABEL_COLUMNS]
    latencies = [x for r in cell for x in r["_latencies"]]
    p50, p95 = pct(latencies, 50), pct(latencies, 95)
    latency = ("{0:.2f} / {1:.2f} s".format(p50 / 1000, p95 / 1000)
               if p50 is not None and p95 is not None else "")
    return "| {0} | {1} | {2} | **{3:.2f}** | {4:.2f}–{5:.2f} | {6} | {7} |".format(
        name, arm, n, k / n if n else 0.0, low, high, " | ".join(counts), latency)


def contrast_line(tag: str, scope: str, left: str, a: List[Dict[str, Any]],
                  right: str, b: List[Dict[str, Any]]) -> str:
    k1, n1 = sum(1 for r in a if r["goal_reached"]), len(a)
    k2, n2 = sum(1 for r in b if r["goal_reached"]), len(b)
    if not n1 or not n2:
        return "| {0} | {1} | {2} vs {3} | n/a | | |".format(tag, scope, left, right)
    return "| {0} | {1} | {2} vs {3} | {4}/{5} vs {6}/{7} | {8:+.2f} | {9:.3g} |".format(
        tag, scope, left, right, k1, n1, k2, n2, k1 / n1 - k2 / n2, fisher(k1, n1, k2, n2))


def cmd_results(_args: argparse.Namespace) -> int:
    """§11 tables and contrasts over every complete citable mini-phase.

    Deterministic: no timestamps, sorted inputs, so a rerun on the same data
    gives byte-identical files.
    """
    runs = collect_runs()
    if not runs:
        print("no complete citable mini-phases")
        return 1

    def pick(sites: List[str], arm: Optional[str] = None,
             seeds: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        return [r for r in runs if r["site"] in sites and (arm is None or r["arm"] == arm)
                and (seeds is None or r["seed"] in seeds)]

    all_sites = [s for _, sites in LAYOUTS for s in sites]
    header = ("| Site | Arm | n | SR | 95% CI | " + " | ".join(c for c, _ in LABEL_COLUMNS)
              + " | latency p50 / p95 |")
    rule = "|---" * (6 + len(LABEL_COLUMNS)) + "|"
    pending = sum(1 for r in runs if "pending" in r["reviewer"].lower())
    mps = sorted({r["mini_phase"] for r in runs}, key=list(MINI_PHASES).index)

    lines = ["# Phase 1 results", "",
             "Generated by `python eval/phase1.py results` from every complete, citable "
             "mini-phase ({0}). Do not edit by hand.".format(", ".join(mps)), "",
             "Spec: `docs/phase1-test-plan.md`. SR CI is Wilson 95% (§8). Latency is "
             "pooled over every decision in the cell, linear-interpolated percentiles. "
             "Label counts come from each mini-phase's `labels.csv` (§9).", ""]
    if pending:
        lines += ["> **{0} of {1} labels are still pending operator confirmation.** "
                  "Rerun this after confirming them.".format(pending, len(runs)), ""]

    lines += ["## Main table (§11)", ""]
    for title, sites in LAYOUTS:
        lines += ["### " + title, "", header, rule]
        for site in sites:
            for arm in ARMS:
                lines.append(table_row(site, arm, pick([site], arm)))
        if len(sites) > 1:
            for arm in ARMS:
                lines.append(table_row("pooled", arm, pick(sites, arm)))
        lines.append("")
    lines += ["### Pooled, all six sites", "", header, rule]
    for arm in ARMS:
        lines.append(table_row("all", arm, pick(all_sites, arm)))
    lines.append("")

    lines += ["## Planned contrasts (§11)", "",
              "Fisher's exact test, two-sided. Seeds are near-replicates at temperature 0 "
              "(§7.3), so p is a robustness check across start poses, not sampling "
              "inference.", "",
              "| # | Scope | Contrast | Successes | ΔSR | p |", "|---|---|---|---|---|---|"]
    scopes = [(site, [site]) for site in all_sites]
    scopes += [(title.split(" ")[0] + " pooled", sites) for title, sites in LAYOUTS
               if len(sites) > 1]
    scopes.append(("all sites", all_sites))
    for tag, other in (("a", "initial"), ("b", "final")):
        for scope, sites in scopes:
            lines.append(contrast_line(tag, scope, "dynamic", pick(sites, "dynamic"),
                                       other, pick(sites, other)))
    lines.append(contrast_line("c", "dynamic arm", "L2b", pick(["s02va", "s02vc"], "dynamic"),
                               "L2a", pick(["s02a", "s02c"], "dynamic")))
    for a_site, c_site in (("s02a", "s02c"), ("s02va", "s02vc")):
        for arm in ("final", "dynamic"):
            lines.append(contrast_line("d", arm, a_site + " (A)", pick([a_site], arm),
                                       c_site + " (C)", pick([c_site], arm)))
    # s03 final: the closed exit is L on odd seeds and R on even seeds (§5).
    lines.append(contrast_line("d", "s03 final", "L closed (odd seeds)",
                               pick(["s03"], "final", [1, 3, 5]),
                               "R closed (even seeds)", pick(["s03"], "final", [2, 4])))
    lines.append("")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "results.md").write_text("\n".join(lines))
    with (RESULTS_DIR / "runs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(runs, key=lambda r: (all_sites.index(r["site"]),
                                                     ARMS.index(r["arm"]), r["seed"])))
    print("{0} runs from {1} -> {2}".format(len(runs), ", ".join(mps),
                                             RESULTS_DIR.relative_to(REPO_ROOT)))
    return 0


def report(mp: str) -> int:
    rows = load_matrix()
    current = [latest_row(rows, mp, s, a, sd) for s, a, sd in order_of(mp)]
    valid = sum(1 for r in current if r["status"] == "valid")
    print("{0}: {1} / {2} valid".format(mp, valid, len(current)))
    return 0 if valid == len(current) else 1


def cmd_status(_args: argparse.Namespace) -> int:
    write_readme()
    print((PHASE_DIR / "README.md").read_text())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("results").set_defaults(func=cmd_results)
    for name, func in (("run", cmd_run), ("validate", cmd_validate)):
        p = sub.add_parser(name)
        p.add_argument("--mini-phase", required=True, choices=list(MINI_PHASES))
        p.set_defaults(func=func)
        if name == "run":
            p.add_argument("--only", help="site/arm/seed, e.g. s01/dynamic/3")
            p.add_argument("--decider-url", default="http://127.0.0.1:8000")
            p.add_argument("--godot", default=shutil.which("godot") or "godot")
            p.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
