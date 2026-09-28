#!/usr/bin/env python3
"""Phase 1 runner: fly a mini-phase under the frozen spec, then check it.

The spec is docs/phase1-test-plan.md. Section numbers below point into it.

    python eval/phase1.py init                       # lay out eval/phase1/ (idempotent)
    python eval/phase1.py run --mini-phase 1.0       # fly order.txt, skip valid runs
    python eval/phase1.py run --mini-phase 1A --only s01/dynamic/3
    python eval/phase1.py validate --mini-phase 1A   # re-check without flying
    python eval/phase1.py status
    python eval/phase1.py demo --mini-phase 1A --limit 3   # try a host; records nothing

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
import random
import shutil
import subprocess
import sys
import time
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

def front_app(field: str = "bundleid") -> str:
    """A field of the app in front (macOS), or "" when it cannot be read.

    Godot launched as a bare binary has no bundle id, so it is spotted by name.
    """
    asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True).stdout.strip()
    if not asn:
        return ""
    out = subprocess.run(["lsappinfo", "info", "-only", field, asn],
                         capture_output=True, text=True).stdout
    parts = out.split('"')
    return parts[3] if len(parts) > 3 else ""


def hand_focus_back(process: "subprocess.Popen[str]", bundle_id: str) -> None:
    """Godot activates itself once on launch, whatever the window mode (`open -g`,
    LSUIElement and the no_focus flag were all tried). Give the front back to
    whoever had it as soon as Godot takes it; it does not take it again."""
    if not bundle_id or "godot" in bundle_id.lower():
        return
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and process.poll() is None:
        if "godot" in front_app("name").lower():
            subprocess.run(["osascript", "-e",
                            'tell application id "{0}" to activate'.format(bundle_id)],
                           capture_output=True)
            return
        time.sleep(0.05)


def fly(site: str, arm: str, seed: int, run_id: str, run_dir: Path,
        decider_url: str, godot: str, background: bool = True) -> int:
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
    # Background: the window is minimized and focus goes back to the operator.
    # Frames are byte-identical to a visible window's, so this is not a config
    # change (§3); it only keeps a sweep from taking over the machine.
    background = background and sys.platform == "darwin"
    if background:
        command.append("--window-mode=minimized")
    run_dir.mkdir(parents=True, exist_ok=True)
    previous = front_app() if background else ""
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    if background:
        hand_focus_back(process, previous)
    try:
        # Godot enforces the 900 s wall clock itself; this is the backstop.
        output, _ = process.communicate(timeout=LOCK["wall_clock_s"] + 120)
        code = process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
        code, output = 124, "subprocess timeout\n{0}".format(output or "")
    (run_dir / "godot.log").write_text(output)
    ended = [line for line in output.splitlines() if "RUN ENDED" in line]
    print("    " + (ended[-1].strip()[:140] if ended
                    else "no RUN ENDED line (exit {0})".format(code)))
    return code


def replay(run_dir: Path, decider_url: str, godot: str,
           headless: bool = True) -> Dict[str, Any]:
    verdict_path = run_dir / "replay.json"
    subprocess.run([sys.executable, str(REPLAY_CLI), str(run_dir),
                    "--decider-url", decider_url, "--godot", godot,
                    "--json", str(verdict_path)] + (["--headless"] if headless else []),
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
    # run.json holds the size asked for; the decider logs the size captured.
    # They differed under Xvfb (768x432), and only the second is what the model saw.
    captured = {tuple(d.get("frame_size") or ()) for d in read_jsonl(run_dir / "decisions.jsonl")}
    if captured - {tuple(LOCK["frame_size"])}:
        reasons.append("captured frame size {0}, want {1}".format(
            sorted(captured), LOCK["frame_size"]))
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
            fly(site, arm, seed, row["run_id"], run_dir, args.decider_url, args.godot,
                background=not args.foreground)
            if read_json(run_dir / "run.json") and read_jsonl(run_dir / "decisions.jsonl"):
                verdict = replay(run_dir, args.decider_url, args.godot,
                                 headless=not args.foreground)
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


def cmd_demo(args: argparse.Namespace) -> int:
    """Fly a mini-phase's order outside eval/phase1/, for trying a new host.

    Nothing goes into matrix.csv or phase.json, so a complete or planned
    mini-phase is untouched. Each run is replayed and put through §10 and the
    verdict printed. Never cite these runs.
    """
    mp = args.mini_phase
    health = decider_health(args.decider_url)
    if not health.get("ok"):
        print("decider not healthy at {0}: {1}".format(args.decider_url, health))
        return 1
    print("decider: profile {0}, model {1}".format(health.get("profile"), health.get("model")))
    cells = order_of(mp)
    if args.only:
        site, arm, seed = args.only.split("/")
        cells = [c for c in cells if c == (site, arm, int(seed))]
    if args.limit:
        cells = cells[:args.limit]
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    root = REPO_ROOT / "eval" / "runs" / "demo_{0}_{1}".format(mp, stamp)
    valid = reached = 0
    for index, (site, arm, seed) in enumerate(cells, 1):
        run_dir = root / site / arm / "seed{0}".format(seed)
        run_id = "demo_{0}_{1}_{2}_{3}_seed{4}".format(stamp, mp, site, arm, seed)
        print("[{0}/{1}] {2}".format(index, len(cells), run_id))
        fly(site, arm, seed, run_id, run_dir, args.decider_url, args.godot,
            background=not args.foreground)
        if read_json(run_dir / "run.json") and read_jsonl(run_dir / "decisions.jsonl"):
            verdict = replay(run_dir, args.decider_url, args.godot, headless=not args.foreground)
            print("    replay {0}".format("ok" if verdict.get("ok") else "FAILED"))
        reasons = validate(mp, site, arm, seed, run_dir, None)
        print("    would be valid" if not reasons else "    would be INVALID: " + "; ".join(reasons))
        valid += not reasons
        reached += read_json(run_dir / "metrics.json").get("end_reason") == "goal_reached"
    print("{0}: {1}/{2} would be valid, {3} reached the goal; runs in {4}".format(
        mp, valid, len(cells), reached, root.relative_to(REPO_ROOT)))
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
    for name, func in (("run", cmd_run), ("validate", cmd_validate), ("demo", cmd_demo)):
        p = sub.add_parser(name)
        p.add_argument("--mini-phase", required=True, choices=list(MINI_PHASES))
        p.set_defaults(func=func)
        if name == "demo":
            p.add_argument("--limit", type=int, default=0,
                           help="fly only the first N runs of the order")
        if name in ("run", "demo"):
            p.add_argument("--only", help="site/arm/seed, e.g. s01/dynamic/3")
            p.add_argument("--decider-url", default="http://127.0.0.1:8000")
            p.add_argument("--godot", default=shutil.which("godot") or "godot")
            p.add_argument("--max-attempts", type=int, default=3)
            p.add_argument("--foreground", action="store_true",
                           help="visible, focused flight window and windowed replay. "
                                "Default: minimized flight, focus handed back, headless "
                                "replay (same frames and trajectories)")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
