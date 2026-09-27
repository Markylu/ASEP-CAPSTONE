"""Load a recorded run from disk into objects the UI and the analysis share.

A run directory is written by four different producers (the decider, the Godot
session, git-tracked vs gitignored paths), so any given file may be missing: a
run cloned from git has no `frames/` and no `steps.jsonl`, and a scripted run
has no `decisions.jsonl` at all. Loading therefore never raises on absence — it
records what is missing and lets the caller decide whether that matters.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "eval" / "runs"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Tolerant of a truncated final line, which a killed run leaves behind."""
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


@dataclass
class Decision:
    """One model call. `index` is absent when every rung of the ladder failed."""
    step: int
    index: Optional[int]
    reason: str
    rung: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    attempts: List[Dict[str, Any]]
    error: Optional[str]
    frame: Optional[str]
    manifest: Dict[str, Any]
    raw: Dict[str, Any]

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Decision":
        index = row.get("index")
        return cls(
            step=int(row.get("step", -1)),
            index=None if index is None else int(index),
            reason=row.get("reason") or "",
            rung=row.get("rung") or "",
            latency_ms=float(row.get("latency_ms") or 0.0),
            prompt_tokens=int(row.get("prompt_tokens") or 0),
            completion_tokens=int(row.get("completion_tokens") or 0),
            attempts=list(row.get("attempts") or []),
            error=row.get("error"),
            frame=row.get("frame"),
            manifest=dict(row.get("manifest") or {}),
            raw=row,
        )

    @property
    def failed(self) -> bool:
        return self.index is None

    @property
    def goal(self) -> Dict[str, Any]:
        """The goal as the model was shown it, from the manifest it was sent.

        Not looked up in steps.jsonl: the manifest describes the state the
        decision was made *from*, steps.jsonl row n describes the state after
        move n, and decision 0 has no step row at all. The manifest is also
        git-tracked, while steps.jsonl is not.
        """
        return dict(self.manifest.get("goal") or {})


@dataclass
class Step:
    """One executed step. Numbered from 1, while decisions are numbered from 0:
    decision n is what produced step n+1."""
    step: int
    t: float
    position: List[float]
    yaw: float
    pitch: float
    action: Dict[str, Any]
    collided: bool
    goal: Dict[str, Any]
    raw: Dict[str, Any]

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Step":
        action = row.get("action")
        if not isinstance(action, dict):
            action = {"index": action}
        return cls(
            step=int(row.get("step", -1)),
            t=float(row.get("t") or 0.0),
            position=[float(v) for v in (row.get("position") or [])],
            yaw=float(row.get("yaw") or 0.0),
            pitch=float(row.get("pitch") or 0.0),
            action=action,
            collided=bool(row.get("collided")),
            goal=dict(row.get("goal") or {}),
            raw=row,
        )


@dataclass
class Run:
    path: Path
    meta: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Decision] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    frames: List[Path] = field(default_factory=list)

    @property
    def run_id(self) -> str:
        """The directory name, not run.json's field. A copied or renamed run
        directory keeps the old id inside run.json, and the directory is what
        actually holds the frames and the steps."""
        return self.path.name

    @property
    def recorded_run_id(self) -> Optional[str]:
        """run.json's own id, surfaced only when it disagrees with the directory."""
        recorded = self.meta.get("run_id") or self.metrics.get("run_id")
        if recorded and recorded != self.path.name:
            return str(recorded)
        return None

    @property
    def started(self) -> str:
        return self.meta.get("started") or ""

    @property
    def sort_key(self) -> float:
        """ISO timestamps sort lexically, but a run with no run.json still has
        to land somewhere, so fall back to the directory's mtime."""
        if self.started:
            return self.started
        try:
            return "0000 " + str(os.path.getmtime(self.path))
        except OSError:
            return "0000"

    @property
    def model(self) -> str:
        return self.meta.get("model") or self.metrics.get("model") or "?"

    @property
    def scene(self) -> Optional[str]:
        """The res:// scene the run was flown on, as recorded at /run/start.

        Watching or re-recording a run has to launch the same map, and the run
        itself is the only thing that knows which one that was. Runs from before
        sites existed carry res://main.tscn; a run with nothing recorded falls
        back to the project's main_scene.
        """
        scene = self.meta.get("scene") or self.metrics.get("scene")
        return str(scene) if scene else None

    @property
    def site_id(self) -> Optional[str]:
        """Which site, or None for a run flown on the unmigrated sandbox."""
        site = self.meta.get("site_id") or self.metrics.get("site_id")
        return str(site) if site else None

    @property
    def site_citation(self) -> Optional[str]:
        """`s01_occluder_dropin@v1` — the form a write-up cites (PLAN §6)."""
        if not self.site_id:
            return None
        version = self.meta.get("site_version") or self.metrics.get("site_version")
        return "{0}@v{1}".format(self.site_id, version) if version else self.site_id

    @property
    def n_steps(self) -> int:
        value = self.metrics.get("steps")
        return int(value) if value is not None else len(self.steps)

    @property
    def collisions(self) -> int:
        value = self.metrics.get("collisions")
        if value is not None:
            return int(value)
        return sum(1 for s in self.steps if s.collided)

    @property
    def goal_reached(self) -> Optional[bool]:
        value = self.metrics.get("goal_reached")
        if value is not None:
            return bool(value)
        if self.steps:
            return bool(self.steps[-1].goal.get("reached"))
        return None

    @property
    def end_reason(self) -> str:
        return self.meta.get("end_reason") or self.metrics.get("end_reason") or "?"

    @property
    def config(self) -> Dict[str, Any]:
        return self.meta.get("config") or self.metrics.get("config") or {}

    @property
    def static_doors(self) -> bool:
        """Door banks were disarmed for the live run; a replay must match."""
        return bool(self.meta.get("static_doors") or self.metrics.get("static_doors"))

    @property
    def frame_size(self) -> List[int]:
        size = self.meta.get("frame_size") or self.metrics.get("frame_size") or [768, 768]
        return [int(size[0]), int(size[1])]

    @property
    def is_replay(self) -> bool:
        return self.path.name.endswith("_replay")

    @property
    def failed_steps(self) -> List[int]:
        return [d.step for d in self.decisions if d.failed]

    @property
    def unreplayable_reason(self) -> Optional[str]:
        """None means the run can be re-flown from its recorded index list."""
        if not self.decisions:
            return "no decisions.jsonl — nothing records which action was chosen"
        failed = self.failed_steps
        if failed:
            return "failed decision(s) at step {0} — the index was never chosen".format(
                ", ".join(str(s) for s in failed))
        return None

    @property
    def replayable(self) -> bool:
        return self.unreplayable_reason is None

    @property
    def indices(self) -> List[int]:
        """The scripted index list, in step order. Empty when unreplayable."""
        if not self.replayable:
            return []
        ordered = sorted(self.decisions, key=lambda d: d.step)
        return [int(d.index) for d in ordered]

    def frame_for(self, decision: Decision) -> Optional[Path]:
        """`frames/` is gitignored, so a cloned run has decisions but no images."""
        if decision.frame:
            candidate = self.path / decision.frame
            if candidate.is_file():
                return candidate
        ordered = sorted(self.decisions, key=lambda d: d.step)
        try:
            position = ordered.index(decision)
        except ValueError:
            return None
        if position < len(self.frames):
            return self.frames[position]
        return None

    def result_step(self, decision: Decision) -> Optional[Step]:
        """What executing this decision produced. Decisions count from 0 and
        executed steps from 1, so decision n produced step n+1."""
        for step in self.steps:
            if step.step == decision.step + 1:
                return step
        return None


def load_run(path: Path) -> Run:
    path = Path(path).resolve()
    frames_dir = path / "frames"
    frames = sorted(frames_dir.glob("f*.png")) if frames_dir.is_dir() else []
    return Run(
        path=path,
        meta=read_json(path / "run.json"),
        metrics=read_json(path / "metrics.json"),
        decisions=[Decision.from_row(r) for r in read_jsonl(path / "decisions.jsonl")],
        steps=[Step.from_row(r) for r in read_jsonl(path / "steps.jsonl")],
        frames=frames,
    )


def list_runs(runs_dir: Optional[Path] = None) -> List[Run]:
    """Newest first. A directory counts as a run if it holds any of the four."""
    runs_dir = Path(runs_dir or RUNS_DIR)
    if not runs_dir.is_dir():
        return []
    found = []
    for child in sorted(runs_dir.iterdir()):
        if not child.is_dir():
            continue
        if not any((child / name).exists() for name in
                   ("run.json", "metrics.json", "decisions.jsonl", "steps.jsonl")):
            continue
        found.append(load_run(child))
    return sorted(found, key=lambda r: r.sort_key, reverse=True)
