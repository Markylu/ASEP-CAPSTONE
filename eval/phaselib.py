"""The run engine shared by every phase: lay out, fly, check, aggregate.

A phase is a set of units (Phase 1's mini-phases, Phase 2's rounds). A unit
is a set of cells, site × arm × seed, flown in a fixed order, at one git SHA,
under one lock. What differs between phases is configuration, so each phase
script builds one `Phase` and hands it its CLI:

    eval/phase1.py   docs/phase1-test-plan.md
    eval/phase2.py   docs/phase2-test-plan.md

Section numbers (§) point into docs/phase1-test-plan.md, whose validity rules
(§10) and rubric (§9) every phase inherits. Standard library only.
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
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
GODOT_PROJECT = REPO_ROOT / "first-project"
REPLAY_CLI = REPO_ROOT / "eval" / "replay.py"

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
VALID_END_REASONS = ("goal_reached", "max_steps")

#: Recorded data, not code: never makes the tree dirty. Same list as the
#: decider's config._DATA_PATHS.
DATA_PATHS = ("eval/runs", "eval/phase1", "eval/phase2")

#: run.json keys every phase checks against its lock (§10).
RUN_KEYS = ("model", "vlm_profile", "temperature", "prompt_version", "prompt_sha",
            "frame_size", "freeze_world", "physics_ticks_per_second", "godot_version",
            "max_steps")
#: Checked as well when the lock names an agent (Phase 2 onward).
AGENT_KEYS = ("agent_version", "agent_sha")


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


# ------------------------------------------------------------------ geometry

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


# ------------------------------------------------------------------ preflight helpers

def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO_ROOT)] + list(args),
                          capture_output=True, text=True).stdout.strip()


def git_clean() -> bool:
    """Same rule as the decider's `git_dirty`: recorded data does not count."""
    excludes = [":(exclude){0}".format(p) for p in DATA_PATHS]
    return not git("status", "--porcelain", "--", ".", *excludes)


def decider_health(url: str) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure means "do not fly"
        return {"ok": False, "error": str(exc)}


# ------------------------------------------------------------------ statistics (§8, §11)

#: §9 terminal labels, in rubric order, as the §11 table columns.
LABEL_COLUMNS = (("success", "success"), ("ignore", "ignore_change"),
                 ("replan", "replan_failure"), ("collision", "collision"),
                 ("timeout", "timeout"), ("pre-change", "pre_change_failure"))
#: §4 layouts: (title, sites). The two door layouts pool their mirror pair.
LAYOUTS = (("L1 Object Appearance", ["s01"]),
           ("L2a Door Switch, out of view", ["s02a", "s02c"]),
           ("L2b Door Switch, in view", ["s02va", "s02vc"]),
           ("L3 Split Path", ["s03"]))
ALL_SITES = [s for _, sites in LAYOUTS for s in sites]
RUN_FIELDS = ["site", "arm", "seed", "run_id", "goal_reached", "label", "reviewer",
              "steps", "collisions", "final_goal_distance_m", "end_reason",
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


def pick(runs: List[Dict[str, Any]], sites: List[str], arm: Optional[str] = None,
         seeds: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    return [r for r in runs if r["site"] in sites and (arm is None or r["arm"] == arm)
            and (seeds is None or r["seed"] in seeds)]


def s11_tables(runs: List[Dict[str, Any]]) -> List[str]:
    """§11: main table per layout + pooled rows, then the planned contrasts."""
    header = ("| Site | Arm | n | SR | 95% CI | " + " | ".join(c for c, _ in LABEL_COLUMNS)
              + " | latency p50 / p95 |")
    rule = "|---" * (6 + len(LABEL_COLUMNS)) + "|"
    lines = ["## Main table (§11)", ""]
    for title, sites in LAYOUTS:
        lines += ["### " + title, "", header, rule]
        for site in sites:
            for arm in ARMS:
                lines.append(table_row(site, arm, pick(runs, [site], arm)))
        if len(sites) > 1:
            for arm in ARMS:
                lines.append(table_row("pooled", arm, pick(runs, sites, arm)))
        lines.append("")
    lines += ["### Pooled, all six sites", "", header, rule]
    for arm in ARMS:
        lines.append(table_row("all", arm, pick(runs, ALL_SITES, arm)))
    lines.append("")

    lines += ["## Planned contrasts (§11)", "",
              "Fisher's exact test, two-sided. Seeds are near-replicates at temperature 0 "
              "(§7.3), so p is a robustness check across start poses, not sampling "
              "inference.", "",
              "| # | Scope | Contrast | Successes | ΔSR | p |", "|---|---|---|---|---|---|"]
    scopes = [(site, [site]) for site in ALL_SITES]
    scopes += [(title.split(" ")[0] + " pooled", sites) for title, sites in LAYOUTS
               if len(sites) > 1]
    scopes.append(("all sites", ALL_SITES))
    for tag, other in (("a", "initial"), ("b", "final")):
        for scope, sites in scopes:
            lines.append(contrast_line(tag, scope, "dynamic", pick(runs, sites, "dynamic"),
                                       other, pick(runs, sites, other)))
    lines.append(contrast_line("c", "dynamic arm", "L2b",
                               pick(runs, ["s02va", "s02vc"], "dynamic"),
                               "L2a", pick(runs, ["s02a", "s02c"], "dynamic")))
    for a_site, c_site in (("s02a", "s02c"), ("s02va", "s02vc")):
        for arm in ("final", "dynamic"):
            lines.append(contrast_line("d", arm, a_site + " (A)", pick(runs, [a_site], arm),
                                       c_site + " (C)", pick(runs, [c_site], arm)))
    # s03 final: the closed exit is L on odd seeds and R on even seeds (§5).
    lines.append(contrast_line("d", "s03 final", "L closed (odd seeds)",
                               pick(runs, ["s03"], "final", [1, 3, 5]),
                               "R closed (even seeds)", pick(runs, ["s03"], "final", [2, 4])))
    lines.append("")
    return lines


def write_runs_csv(path: Path, runs: List[Dict[str, Any]], unit_key: str) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[unit_key] + RUN_FIELDS,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(runs, key=lambda r: (ALL_SITES.index(r["site"]),
                                                     ARMS.index(r["arm"]), r["seed"])))


# ------------------------------------------------------------------ the phase

class Phase:
    """One phase's layout, lock and units.

    `units` maps a unit id to {"folder", "title", "sites", "seeds", "citable"},
    plus optionally "arms" (default all three) and "agent" (an agent version;
    `agent_lock(version)` then adds its version, sha and prompt to the unit's
    lock). `lock` is the frozen config for the whole phase;
    `lock["overrides"][unit]` patches it per unit (Phase 1's shakedown flies
    the stub model).
    """

    def __init__(self, *, number: int, root: Path, unit_key: str, unit_label: str,
                 units: Dict[str, Dict[str, Any]], lock: Dict[str, Any], script: str,
                 spec: str, orders: Optional[Dict[str, str]] = None,
                 agent_lock: Optional[Callable[[str], Dict[str, Any]]] = None,
                 unit_readme: Optional[Callable[[str], str]] = None) -> None:
        self.number = number
        self.root = root
        self.unit_key = unit_key
        self.unit_label = unit_label
        self.units = units
        self.lock = lock
        self.script = script
        self.spec = spec
        self.orders = orders or {}
        self.agent_lock = agent_lock
        self.unit_readme = unit_readme
        self.lock_path = root / "config.lock.json"
        self.matrix_path = root / "matrix.csv"
        self.results_dir = root / "results"
        self.matrix_fields = [unit_key, "site", "site_version", "arm", "seed", "run_id",
                              "attempt", "status", "end_reason", "invalid_reason"]

    # -------------------------------------------------------------- layout

    def arms(self, unit: str) -> Sequence[str]:
        return self.units[unit].get("arms", ARMS)

    def order_of(self, unit: str) -> List[Tuple[str, str, int]]:
        if unit in self.orders:
            out = []
            for token in self.orders[unit].replace("\n", " ").split(","):
                site, arm, seed = token.strip().split("/")
                out.append((site, arm, int(seed)))
            return out
        spec = self.units[unit]
        cells = [(str(site), str(arm), int(seed)) for site, arm, seed
                 in itertools.product(spec["sites"], self.arms(unit), spec["seeds"])]
        random.Random("phase{0}-{1}".format(self.number, unit)).shuffle(cells)
        return cells

    def phase_dir(self, unit: str) -> Path:
        return self.root / self.units[unit]["folder"]

    def run_id_for(self, unit: str, site: str, arm: str, seed: int, attempt: int) -> str:
        return "p{0}_{1}_{2}_{3}_seed{4}_a{5:02d}".format(
            self.number, unit, site, arm, seed, attempt)

    def run_dir_for(self, unit: str, site: str, arm: str, seed: int) -> Path:
        return self.phase_dir(unit) / "runs" / site / arm / "seed{0}".format(seed)

    def unit_lock(self, unit: str) -> Dict[str, Any]:
        """The lock as it applies to one unit: overrides and agent folded in."""
        merged = {k: v for k, v in self.lock.items() if k != "overrides"}
        merged.update(self.lock.get("overrides", {}).get(unit, {}))
        agent = self.units[unit].get("agent")
        if agent and self.agent_lock:
            merged.update(self.agent_lock(agent))
        return merged

    def load_matrix(self) -> List[Dict[str, Any]]:
        if not self.matrix_path.is_file():
            return []
        with self.matrix_path.open(newline="") as handle:
            return list(csv.DictReader(handle))

    def save_matrix(self, rows: List[Dict[str, Any]]) -> None:
        with self.matrix_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.matrix_fields)
            writer.writeheader()
            writer.writerows(rows)

    def latest_row(self, rows: List[Dict[str, Any]], unit: str, site: str, arm: str,
                   seed: int) -> Dict[str, Any]:
        """The current attempt for a cell: the highest attempt number."""
        cell = [r for r in rows if r[self.unit_key] == unit and r["site"] == site
                and r["arm"] == arm and int(r["seed"]) == seed]
        return max(cell, key=lambda r: int(r["attempt"]))

    def cmd_init(self, _args: argparse.Namespace) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        if self.lock_path.is_file() and read_json(self.lock_path) != self.lock:
            print("config.lock.json differs from the lock in {0}. The spec changed: "
                  "restart the affected {1}s and replace the lock by hand. "
                  "Not overwriting.".format(self.script, self.unit_label.lower()))
            return 1
        write_json(self.lock_path, self.lock)

        rows: List[Dict[str, Any]] = list(self.load_matrix())
        have = {(r[self.unit_key], r["site"], r["arm"], str(r["seed"])) for r in rows}
        for unit, spec in self.units.items():
            folder = self.phase_dir(unit)
            (folder / "runs").mkdir(parents=True, exist_ok=True)
            order = self.order_of(unit)
            cells = len(spec["sites"]) * len(self.arms(unit)) * len(spec["seeds"])
            if len(order) != cells or len(set(order)) != cells:
                raise SystemExit("order for {0} is not the full design ({1} cells)".format(
                    unit, cells))
            (folder / "order.txt").write_text(
                "".join("{0}/{1}/{2}\n".format(*cell) for cell in order))
            if spec.get("agent"):
                # The unit's own lock: phase lock + agent. A round flown under a
                # different agent sha is a different round.
                unit_lock = self.unit_lock(unit)
                lock_file = folder / "config.lock.json"
                if lock_file.is_file() and read_json(lock_file) != unit_lock:
                    raise SystemExit("{0}: config.lock.json no longer matches agent {1}. "
                                     "Agents are never edited; add a new version and a "
                                     "new {2}.".format(unit, spec["agent"],
                                                       self.unit_label.lower()))
                write_json(lock_file, unit_lock)
            if not (folder / "phase.json").is_file():
                phase = {self.unit_key: unit, "title": spec["title"],
                         "citable": spec["citable"]}
                if spec.get("agent"):
                    phase["agent_version"] = spec["agent"]
                phase.update({"status": "planned", "git_sha": None, "started": None,
                              "finished": None, "operator": None, "notes": ""})
                write_json(folder / "phase.json", phase)
            # The unit's write-up, written before it flies. Only a stub, only
            # once, and never for a unit already flown: a hypothesis written
            # after the result is not one.
            readme = folder / "README.md"
            if (self.unit_readme and not readme.is_file()
                    and read_json(folder / "phase.json").get("status") == "planned"):
                readme.write_text(self.unit_readme(unit))
            for site, arm, seed in sorted(order):
                if (unit, site, arm, str(seed)) in have:
                    continue
                rows.append({self.unit_key: unit, "site": site,
                             "site_version": SITES[site][1], "arm": arm, "seed": seed,
                             "run_id": self.run_id_for(unit, site, arm, seed, 1),
                             "attempt": 1, "status": "planned", "end_reason": "",
                             "invalid_reason": ""})
        self.save_matrix(rows)
        self.write_readme()
        print("{0} laid out: {1} matrix rows".format(
            self.root.relative_to(REPO_ROOT), len(rows)))
        return 0

    def write_readme(self) -> None:
        rows = self.load_matrix()
        with_agent = any(spec.get("agent") for spec in self.units.values())
        lines = ["# Phase {0} data".format(self.number), "",
                 "Flown under `{0}`. Regenerated by `{1}`; do not edit by hand.".format(
                     self.spec, self.script), "",
                 "| {0} | Title |{1} Citable | Status | Valid / planned | Git SHA | "
                 "Summary |".format(self.unit_label, " Agent |" if with_agent else ""),
                 "|---|---|---|---|---|---|---|" + ("---|" if with_agent else "")]
        for unit, spec in self.units.items():
            folder = self.phase_dir(unit)
            phase = read_json(folder / "phase.json")
            current = ([self.latest_row(rows, unit, s, a, sd)
                        for s, a, sd in self.order_of(unit)] if rows else [])
            valid = sum(1 for r in current if r["status"] == "valid")
            summary = " · ".join(
                "[{0}]({1}/{2})".format(name, spec["folder"], file)
                for name, file in (("write-up", "README.md"), ("summary", "summary.md"))
                if (folder / file).is_file())
            agent_cell = " {0} |".format(spec.get("agent", "")) if with_agent else ""
            lines.append("| {0} | {1} |{2} {3} | {4} | {5} / {6} | {7} | {8} |".format(
                unit, spec["title"], agent_cell, "yes" if spec["citable"] else "no",
                phase.get("status", "planned"), valid, len(current),
                phase.get("git_sha") or "", summary))
        if (self.results_dir / "results.md").is_file():
            lines += ["", "Aggregate tables and contrasts (§11): [results/results.md]"
                      "(results/results.md), built by `{0} results`.".format(self.script)]
        (self.root / "README.md").write_text("\n".join(lines) + "\n")

    # -------------------------------------------------------------- preflight

    def preflight(self, unit: str, decider_url: str) -> List[str]:
        """§7.2 step 1. The scripted probe per site is done by hand."""
        problems = []
        if read_json(self.lock_path) != self.lock:
            problems.append("config.lock.json missing or stale: run `init`")
        if not git_clean():
            problems.append("git tree has uncommitted changes outside {0}".format(
                ", ".join(DATA_PATHS)))
        lock = self.unit_lock(unit)
        health = decider_health(decider_url)
        if not health.get("ok"):
            problems.append("decider not healthy at {0}: {1}".format(decider_url, health))
        else:
            checks = [("model", lock["model"]), ("prompt_sha", lock["prompt_sha"]),
                      ("profile", lock["vlm_profile"])]
            checks += [(key, lock[key]) for key in AGENT_KEYS if key in lock]
            for key, want in checks:
                if health.get(key) != want:
                    problems.append("decider {0} is {1!r}, lock wants {2!r}".format(
                        key, health.get(key), want))
        for short in self.units[unit]["sites"]:
            site_id, version = SITES[short]
            manifest = read_json(GODOT_PROJECT / "sites" / site_id / "site.json")
            if manifest.get("version") != version or manifest.get("status") != "active":
                problems.append("{0} is v{1} {2}, lock wants v{3} active".format(
                    site_id, manifest.get("version"), manifest.get("status"), version))
        return problems

    # -------------------------------------------------------------- flying

    def fly(self, site: str, arm: str, seed: int, run_id: str, run_dir: Path,
            decider_url: str, godot: str) -> int:
        command = [
            godot, "--path", str(GODOT_PROJECT),
            "res://sites/{0}/site.tscn".format(SITES[site][0]), "--",
            "--run-id=" + run_id,
            "--run-dir=" + str(run_dir.relative_to(REPO_ROOT)),
            "--decider-url=" + decider_url,
            "--max-steps={0}".format(self.lock["max_steps"]),
            "--max-collisions={0}".format(self.lock["max_collisions"]),
            "--frame-size={0}x{1}".format(*self.lock["frame_size"]),
            "--world=" + arm,
            "--spawn-seed={0}".format(seed),
        ]
        run_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Godot enforces the 900 s wall clock itself; this is the backstop.
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=self.lock["wall_clock_s"] + 120)
            code, output = result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired as exc:
            code, output = 124, "subprocess timeout\n{0}".format(exc.stdout or "")
        (run_dir / "godot.log").write_text(output)
        ended = [line for line in output.splitlines() if "RUN ENDED" in line]
        print("    " + (ended[-1].strip()[:140] if ended
                        else "no RUN ENDED line (exit {0})".format(code)))
        return code

    def replay(self, run_dir: Path, decider_url: str, godot: str) -> Dict[str, Any]:
        verdict_path = run_dir / "replay.json"
        subprocess.run([sys.executable, str(REPLAY_CLI), str(run_dir),
                        "--decider-url", decider_url, "--godot", godot,
                        "--json", str(verdict_path)],
                       capture_output=True, text=True, timeout=self.lock["wall_clock_s"])
        return read_json(verdict_path) or {"ok": False, "error": "replay wrote no verdict"}

    # -------------------------------------------------------------- validity (§10)

    def validate(self, unit: str, site: str, arm: str, seed: int, run_dir: Path,
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

        lock = self.unit_lock(unit)
        wanted = {key: lock[key] for key in RUN_KEYS}
        wanted.update({key: lock[key] for key in AGENT_KEYS if key in lock})
        wanted.update({
            "site_id": SITES[site][0], "site_version": SITES[site][1],
            "world": arm, "spawn_seed": seed, "git_dirty": False,
        })
        for key, value in wanted.items():
            if meta.get(key) != value:
                reasons.append("run.json {0}={1!r}, want {2!r}".format(key, meta.get(key), value))
        config = meta.get("config") or {}
        for key, value in self.lock["config"].items():
            if config.get(key) != value:
                reasons.append("config {0}={1!r}, want {2!r}".format(key, config.get(key), value))
        if phase_sha and meta.get("git_sha") != phase_sha:
            reasons.append("git_sha {0} != {1} {2}".format(
                meta.get("git_sha"), self.unit_label.lower(), phase_sha))

        changes = [e for e in read_jsonl(run_dir / "events.jsonl")
                   if e.get("name") in CHANGE_EVENTS]
        trigger_x = TRIGGER_X[site]
        crossed = crossing_step(site, run_dir)
        if arm != "dynamic":
            if changes:
                reasons.append("change event in a {0} arm".format(arm))
        elif changes:
            if trigger_x is not None and not change_step_ok(site, run_dir,
                                                            changes[0].get("step")):
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

    def retire(self, unit: str, site: str, arm: str, seed: int, label: str) -> None:
        """Invalid or crashed attempts are moved, never deleted (§10)."""
        source = self.run_dir_for(unit, site, arm, seed)
        target = (self.phase_dir(unit) / "_attempts" / site / arm /
                  "seed{0}".format(seed) / label)
        if target.exists():
            target = target.with_name(label + "_" + datetime.now().strftime("%Y%m%d%H%M%S"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.move(str(source), str(target))

    def cmd_run(self, args: argparse.Namespace) -> int:
        unit = args.unit
        folder = self.phase_dir(unit)
        phase = read_json(folder / "phase.json")
        if not phase:
            raise SystemExit("run `init` first")
        if phase.get("status") in ("complete", "superseded"):
            raise SystemExit("{0} is {1}".format(unit, phase["status"]))

        problems = self.preflight(unit, args.decider_url)
        head = git("rev-parse", "--short", "HEAD")
        if phase.get("git_sha") and phase["git_sha"] != head:
            problems.append("HEAD {0} != {1} SHA {2}: one SHA per {1} (§7.1); restart "
                            "the {1} to change it".format(head, self.unit_label.lower(),
                                                          phase["git_sha"]))
        if problems:
            print("PREFLIGHT FAILED:\n  " + "\n  ".join(problems))
            return 1
        if not phase.get("git_sha"):
            phase.update({"git_sha": head, "started": now(), "status": "running",
                          "operator": git("config", "user.name") or getpass.getuser()})
            write_json(folder / "phase.json", phase)

        cells = self.order_of(unit)
        if args.only:
            site, arm, seed = args.only.split("/")
            cells = [c for c in cells if c == (site, arm, int(seed))]
            if not cells:
                raise SystemExit("{0} is not in {1}'s order".format(args.only, unit))

        for index, (site, arm, seed) in enumerate(cells, 1):
            for _ in range(args.max_attempts):
                rows = self.load_matrix()
                row = self.latest_row(rows, unit, site, arm, seed)
                if row["status"] == "valid":
                    break
                attempt = int(row["attempt"])
                run_dir = self.run_dir_for(unit, site, arm, seed)
                print("[{0}/{1}] {2}".format(index, len(cells), row["run_id"]))
                if run_dir.exists():
                    # Left by an interrupted flight of this same attempt.
                    self.retire(unit, site, arm, seed, "a{0:02d}_interrupted".format(attempt))
                self.fly(site, arm, seed, row["run_id"], run_dir, args.decider_url, args.godot)
                if read_json(run_dir / "run.json") and read_jsonl(run_dir / "decisions.jsonl"):
                    verdict = self.replay(run_dir, args.decider_url, args.godot)
                    print("    replay {0}".format("ok" if verdict.get("ok") else "FAILED"))
                reasons = self.validate(unit, site, arm, seed, run_dir, phase["git_sha"])
                row["end_reason"] = read_json(run_dir / "metrics.json").get("end_reason", "")
                if not reasons:
                    row["status"] = "valid"
                    self.save_matrix(rows)
                    print("    valid")
                    break
                row["status"], row["invalid_reason"] = "invalid", "; ".join(reasons)
                print("    INVALID: " + row["invalid_reason"])
                self.retire(unit, site, arm, seed, "a{0:02d}".format(attempt))
                rows.append(dict(row, run_id=self.run_id_for(unit, site, arm, seed, attempt + 1),
                                 attempt=attempt + 1, status="planned", end_reason="",
                                 invalid_reason=""))
                self.save_matrix(rows)
            else:
                print("giving up on {0}/{1}/{2} after {3} attempts".format(
                    site, arm, seed, args.max_attempts))
                self.write_readme()
                return 1
        self.write_readme()
        return self.report(unit)

    def cmd_validate(self, args: argparse.Namespace) -> int:
        unit = args.unit
        phase = read_json(self.phase_dir(unit) / "phase.json")
        bad = 0
        for site, arm, seed in self.order_of(unit):
            reasons = self.validate(unit, site, arm, seed,
                                    self.run_dir_for(unit, site, arm, seed),
                                    phase.get("git_sha"))
            if reasons:
                bad += 1
                print("{0}/{1}/{2}: {3}".format(site, arm, seed, "; ".join(reasons)))
        print("{0} invalid".format(bad))
        return 1 if bad else 0

    def report(self, unit: str) -> int:
        rows = self.load_matrix()
        current = [self.latest_row(rows, unit, s, a, sd) for s, a, sd in self.order_of(unit)]
        valid = sum(1 for r in current if r["status"] == "valid")
        print("{0}: {1} / {2} valid".format(unit, valid, len(current)))
        return 0 if valid == len(current) else 1

    def cmd_status(self, _args: argparse.Namespace) -> int:
        self.write_readme()
        print((self.root / "README.md").read_text())
        return 0

    # -------------------------------------------------------------- results

    def complete_units(self, citable_only: bool) -> List[str]:
        return [unit for unit, spec in self.units.items()
                if (spec["citable"] or not citable_only)
                and read_json(self.phase_dir(unit) / "phase.json").get("status") == "complete"]

    def collect_runs(self, units: Sequence[str]) -> List[Dict[str, Any]]:
        """The current valid run of every cell in the given units."""
        rows = self.load_matrix()
        runs = []  # type: List[Dict[str, Any]]
        for unit in units:
            labels = {}  # type: Dict[str, Dict[str, str]]
            labels_path = self.phase_dir(unit) / "labels.csv"
            if labels_path.is_file():
                with labels_path.open(newline="") as handle:
                    labels = {r["run_id"]: r for r in csv.DictReader(handle)}
            for site, arm, seed in sorted(self.order_of(unit)):
                row = self.latest_row(rows, unit, site, arm, seed)
                if row["status"] != "valid":
                    raise SystemExit("{0} {1}/{2}/{3} is not valid; a complete {4} "
                                     "must be".format(unit, site, arm, seed,
                                                      self.unit_label.lower()))
                run_dir = self.run_dir_for(unit, site, arm, seed)
                metrics = read_json(run_dir / "metrics.json")
                latencies = [float(d["latency_ms"])
                             for d in read_jsonl(run_dir / "decisions.jsonl")
                             if d.get("latency_ms") is not None]
                label = labels.get(row["run_id"], {})
                runs.append({
                    self.unit_key: unit, "unit": unit, "site": site, "arm": arm,
                    "seed": seed, "run_id": row["run_id"],
                    "goal_reached": bool(metrics.get("goal_reached")),
                    "label": label.get("label", ""), "reviewer": label.get("reviewer", ""),
                    "steps": metrics.get("steps"), "collisions": metrics.get("collisions"),
                    "final_goal_distance_m": metrics.get("final_goal_distance_m"),
                    "end_reason": metrics.get("end_reason"),
                    "latency_p50_ms": (metrics.get("latency_ms") or {}).get("p50"),
                    "latency_p95_ms": (metrics.get("latency_ms") or {}).get("p95"),
                    "git_sha": metrics.get("git_sha"), "_latencies": latencies,
                })
        return runs

    # -------------------------------------------------------------- CLI

    def main(self, description: str,
             extra: Optional[Callable[[Any], None]] = None) -> int:
        parser = argparse.ArgumentParser(description=description,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
        sub = parser.add_subparsers(dest="command", required=True)
        sub.add_parser("init").set_defaults(func=self.cmd_init)
        sub.add_parser("status").set_defaults(func=self.cmd_status)
        flag = "--" + self.unit_key.replace("_", "-")
        for name, func in (("run", self.cmd_run), ("validate", self.cmd_validate)):
            p = sub.add_parser(name)
            p.add_argument(flag, dest="unit", required=True, choices=list(self.units))
            p.set_defaults(func=func)
            if name == "run":
                p.add_argument("--only", help="site/arm/seed, e.g. s01/dynamic/3")
                p.add_argument("--decider-url", default="http://127.0.0.1:8000")
                p.add_argument("--godot", default=shutil.which("godot") or "godot")
                p.add_argument("--max-attempts", type=int, default=3)
        if extra:
            extra(sub)
        args = parser.parse_args()
        return args.func(args)
