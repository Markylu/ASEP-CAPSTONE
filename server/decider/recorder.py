"""Owner of the run directory.

Godot writes nothing to disk. This side knows the model tag, the prompt hash and
the git SHA, so it is the only writer, and a run directory is therefore never
half-written by two processes.

    eval/runs/run_2026-09-14_1830/
    |- run.json          what produced the run
    |- frames/f000000.png   the literal image each decision was made from
    |- decisions.jsonl   one line per decision
    |- steps.jsonl       one line per executed step
    |- events.jsonl      one line per thing the site did on its own
    `- metrics.json      the scientific record; small, and committed
"""
from __future__ import annotations

import base64
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config, prompt


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _append(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


#: Events that mean "the route or the sightline just changed under the agent".
#: `_occlusion_summary()` dates `occlusion_step` from the first of these.
OCCLUSION_EVENTS = frozenset({"occluder_deployed", "doors_switched"})


class Run:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.dir = config.RUNS_DIR / run_id
        self.frames = self.dir / "frames"
        self.decisions = self.dir / "decisions.jsonl"
        self.steps = self.dir / "steps.jsonl"
        self.events = self.dir / "events.jsonl"

    def start(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        self.frames.mkdir(parents=True, exist_ok=True)
        # Opening a run means opening it, not adding to whatever was here. The
        # append-only writers below would otherwise stack a second flight on top
        # of the first — which is exactly what re-running `eval/replay.py` does,
        # since it writes <run_id>_replay every time. The result was a replay
        # that reported twice the steps and two deploy events, and read as
        # non-reproducible when nothing had changed.
        for path in (self.decisions, self.steps, self.events):
            if path.is_file():
                path.unlink()
        record = {
            "run_id": self.run_id,
            "started": _now(),
            "model": config.VLM_MODEL,
            # Which provider answered. A `local` run's token counts are not
            # comparable with a `remote` one's; the profile is how a reader of
            # metrics.json finds that out.
            "vlm_profile": config.VLM_PROFILE,
            "litellm_base_url": config.LITELLM_BASE_URL,
            "prompt_version": prompt.PROMPT_VERSION,
            "prompt_sha": prompt.prompt_sha(),
            "git_sha": config.git_sha(),
            "git_dirty": config.git_dirty(),
            "temperature": config.TEMPERATURE,
        }
        record.update(meta)
        (self.dir / "run.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    def ensure(self) -> None:
        """A run that posted a decision without a /run/start still gets a home."""
        if not self.frames.is_dir():
            self.start({"note": "started implicitly by first decision"})

    def save_frame(self, step: int, frame_b64: str) -> str:
        self.ensure()
        name = "f{0:06d}.png".format(step)
        (self.frames / name).write_bytes(base64.b64decode(frame_b64))
        return "frames/" + name

    def record_decision(self, record: Dict[str, Any]) -> None:
        self.ensure()
        record["t"] = _now()
        _append(self.decisions, record)

    def record_step(self, pose: Dict[str, Any],
                    goal: Optional[Dict[str, Any]] = None) -> None:
        self.ensure()
        record = {"t": _now()}
        record.update(pose)
        if goal:
            record["goal"] = goal
        _append(self.steps, record)

    def record_event(self, name: str, step: Optional[int] = None,
                     data: Optional[Dict[str, Any]] = None) -> None:
        """A site prop firing: the occluder deploying, a door opening.

        `step` is the 1-based move the event belongs to, the same numbering
        steps.jsonl uses, so "deployed at step 3" and the step 3 record describe
        the same move.
        """
        self.ensure()
        _append(self.events, {"t": _now(), "name": name, "step": step,
                              "data": data or {}})

    # ------------------------------------------------------------------ metrics

    def finish(self, reason: str, steps: Optional[int] = None) -> Dict[str, Any]:
        self.ensure()
        decisions = _read_jsonl(self.decisions)
        step_records = _read_jsonl(self.steps)
        run_json = json.loads((self.dir / "run.json").read_text())

        latencies = [d["latency_ms"] for d in decisions if d.get("latency_ms") is not None]
        prompt_tokens = [d["prompt_tokens"] for d in decisions if d.get("prompt_tokens")]
        completion_tokens = [d["completion_tokens"] for d in decisions if d.get("completion_tokens")]
        collisions = sum(1 for s in step_records if s.get("collided"))
        timings = [d["timing"] for d in decisions if d.get("timing")]
        rungs: Dict[str, int] = {}
        for d in decisions:
            rung = d.get("rung", "unknown")
            rungs[rung] = rungs.get(rung, 0) + 1

        # Steps first: a scripted run or a replay has no decisions at all, and
        # its metrics should still say whether it arrived.
        goal = None
        for record in reversed(step_records):
            goal = record.get("goal")
            if goal:
                break
        if not goal:
            for d in reversed(decisions):
                goal = (d.get("manifest") or {}).get("goal")
                if goal:
                    break

        events = _read_jsonl(self.events)
        occlusion = self._occlusion_summary(step_records, events)

        metrics = {
            "run_id": self.run_id,
            "ended": _now(),
            "end_reason": reason,
            "steps": steps if steps is not None else len(step_records),
            "decisions": len(decisions),
            "collisions": collisions,
            "goal_reached": bool(goal.get("reached")) if goal else None,
            "final_goal_distance_m": round(float(goal["distance"]), 3) if goal else None,
            "latency_ms": {
                "p50": round(_pct(latencies, 50), 1) if latencies else None,
                "p95": round(_pct(latencies, 95), 1) if latencies else None,
                "mean": round(statistics.fmean(latencies), 1) if latencies else None,
            },
            # Where the wall time went, not just how much there was. See
            # vlm.Timing: rtt+upload is transport, prefill+decode is the model.
            # A run whose network share dominates is a link problem; one whose
            # prefill dominates is an image-size problem. Null throughout for a
            # run recorded before this existed, or flown without streaming.
            "latency_breakdown_ms": _breakdown(timings),
            "tokens_per_frame": {
                "prompt_mean": round(statistics.fmean(prompt_tokens), 1) if prompt_tokens else None,
                "completion_mean": round(statistics.fmean(completion_tokens), 1) if completion_tokens else None,
            },
            "tokens_total": {
                "prompt": sum(prompt_tokens) or None,
                "completion": sum(completion_tokens) or None,
            },
            "rungs_used": rungs,
            "events": [{"name": e.get("name"), "step": e.get("step"), "t": e.get("t")}
                       for e in events],
            # Copied so metrics.json stands alone as a citation.
            "site_id": run_json.get("site_id"),
            "site_version": run_json.get("site_version"),
            "scene": run_json.get("scene"),
            "physics_ticks_per_second": run_json.get("physics_ticks_per_second"),
            "freeze_world": run_json.get("freeze_world"),
            "static_doors": run_json.get("static_doors"),
            "model": run_json.get("model"),
            "prompt_version": run_json.get("prompt_version"),
            "prompt_sha": run_json.get("prompt_sha"),
            "git_sha": run_json.get("git_sha"),
            "frame_size": run_json.get("frame_size"),
            "config": run_json.get("config"),
        }
        metrics.update(occlusion)
        (self.dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

        run_json["ended"] = metrics["ended"]
        run_json["end_reason"] = reason
        (self.dir / "run.json").write_text(json.dumps(run_json, indent=2) + "\n")
        return metrics


    @staticmethod
    def _occlusion_summary(step_records: List[Dict[str, Any]],
                           events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Turn the raycast trace into the sentence the site is asking for:
        "goal occluded at step 3, re-acquired 7 steps later".

        Every field is None rather than 0 when the run cannot answer — an older
        run with no `line_of_sight` recorded, or a site with no occluder. A zero
        here would read as a real measurement.

        `occlusion_step` is the step the world changed under the agent, whoever
        changed it: s01's cube rising, s02's doors switching. Any future prop
        that hides the goal joins `OCCLUSION_EVENTS`.
        """
        summary: Dict[str, Any] = {
            "occlusion_step": None,
            "goal_visible_steps": None,
            "goal_first_hidden_step": None,
            "steps_to_reacquire": None,
        }

        change = next((e for e in events if e.get("name") in OCCLUSION_EVENTS), None)
        if change is not None:
            summary["occlusion_step"] = change.get("step")

        visibility = [((s.get("goal") or {}).get("line_of_sight"), s.get("step"))
                      for s in step_records]
        seen = [(v, n) for v, n in visibility if v is not None]
        if not seen:
            return summary

        summary["goal_visible_steps"] = sum(1 for v, _ in seen if v)
        summary["goal_first_hidden_step"] = next((n for v, n in seen if not v), None)

        hidden_at = summary["goal_first_hidden_step"]
        if hidden_at is not None:
            regained = next((n for v, n in seen if v and n > hidden_at), None)
            if regained is not None:
                summary["steps_to_reacquire"] = regained - hidden_at
        return summary


#: Segments summarised in metrics.json, in the order they happen.
_TIMING_FIELDS = ("rtt_ms", "upload_ms", "ttft_ms", "prefill_ms", "decode_ms",
                  "unaccounted_ms", "network_ms", "compute_ms", "total_ms",
                  "decode_tok_s")


def _breakdown(timings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """p50/p95 per segment, skipping decisions that could not measure one.

    Each segment is summarised over the decisions that actually have it rather
    than over all of them, so one unstreamed fallback step does not silently
    drag the prefill median toward zero. `n` says how many backed each figure.
    """
    summary: Dict[str, Any] = {}
    for field_name in _TIMING_FIELDS:
        values = [t[field_name] for t in timings if t.get(field_name) is not None]
        summary[field_name] = {
            "p50": round(_pct(values, 50), 1) if values else None,
            "p95": round(_pct(values, 95), 1) if values else None,
            "n": len(values),
        }
    streamed = [t for t in timings if t.get("streamed")]
    summary["streamed_decisions"] = len(streamed)
    frame_bytes = [t["request_bytes"] for t in timings if t.get("request_bytes")]
    summary["request_bytes_mean"] = (
        round(statistics.fmean(frame_bytes)) if frame_bytes else None)
    return summary


def _pct(values: List[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
