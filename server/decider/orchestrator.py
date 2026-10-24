"""One step of the orchestrated agent (a13 on): several model calls, each with
one job, and code that does the spatial work between them.

    perceiver  (g03, clean frame)        where the goal is, open floor, doorways
    mapper     (spatial.rebuild)         the run's map, rebuilt from decisions.jsonl
    strategist (q01, text, on a trigger) a target from a list code builds
    projector  (spatial.project)         notes against each action
    navigator  (p14, annotated frame)    the action
    critic     (spatial.critique)        one retry when the map disagrees

Every call is the frozen model at temperature 0 on the shared ladder
(vlm.call_structured). A failed perceiver or strategist never fails the step:
the navigator goes on with what there is. A failed navigator fails the step,
as in app.decide.

The strategist's target and the step it was last asked are read back from
decisions.jsonl, like the map, so a run replays from its record alone.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Callable, Dict, List, Optional

from fastapi.responses import JSONResponse

from . import agent, config, prompt as prompts, schema, spatial, vlm
from .recorder import Run, _read_jsonl

log = logging.getLogger("decider")

PERCEIVER_MAX_TOKENS = 768
STRATEGIST_MAX_TOKENS = 512

#: The perceiver's strip as the old left/ahead/right report, so agent_evidence.py,
#: the labeller's goal facets and the probe read `goal` where they always have.
LEGACY_GOAL = {"far_left": "left", "left": "left", "centre": "ahead", "right": "right",
               "far_right": "right", "not_visible": "not_visible"}

EXPLORE = "explore"


# --- validators: the cleaned reply, or VLMError (a failed rung) ------------------

def perception_from(parsed: Dict[str, Any]) -> Dict[str, Any]:
    goal = parsed.get("goal")
    if goal not in schema.STRIPS + ["not_visible"]:
        raise vlm.VLMError("perceiver gave no valid goal: {0!r}".format(goal))
    lanes = []
    for strip in schema.STRIPS:
        lane = parsed.get(strip) or {}
        if lane.get("floor") not in schema.FLOOR_CLASSES:
            raise vlm.VLMError("perceiver gave no valid floor for {0}".format(strip))
        lanes.append({"strip": strip, "floor": lane["floor"],
                      "doorway": bool(lane.get("doorway"))})
    goal_range = parsed.get("goal_range")
    if goal == "not_visible":
        goal_range = None
    elif goal_range not in ("touching", "near", "mid", "far"):
        goal_range = "mid"
    return {"reason": str(parsed.get("reason", "")), "goal": goal,
            "goal_range": goal_range, "lanes": lanes}


def _strategy(ids: List[str]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def check(parsed: Dict[str, Any]) -> Dict[str, Any]:
        if parsed.get("target") not in ids:
            raise vlm.VLMError("strategist named no listed target: {0!r}".format(
                parsed.get("target")))
        mode = parsed.get("mode") if parsed.get("mode") in schema.MODES else "explore"
        return {"reason": str(parsed.get("reason", "")), "mode": mode,
                "target": parsed["target"]}
    return check


def _action(indices: List[int]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def check(parsed: Dict[str, Any]) -> Dict[str, Any]:
        try:
            index = int(parsed["action"])
        except (KeyError, TypeError, ValueError):
            raise vlm.VLMError("no action in reply")
        if index not in indices:
            raise vlm.VLMError("model chose {0}, not on this frame ({1})".format(index, indices))
        return {"index": index, "reason": str(parsed.get("reason", ""))}
    return check


# --- words for the navigator ------------------------------------------------------

def perceiver_line(perception: Optional[Dict[str, Any]]) -> str:
    if not perception:
        return "no answer this step."
    if perception["goal"] == "not_visible":
        return "the goal is not visible."
    return "the goal is in the {0} part of the image, {1}.".format(
        perception["goal"].replace("_", " "),
        spatial.WORDS["range"].get(perception.get("goal_range"), "distance unknown"))


def plan_line(target: Optional[spatial.Target], mode: Optional[str],
              here: Optional[spatial.Pose]) -> str:
    if target is None or here is None:
        return "no fixed target; explore where the image shows open floor."
    return "head for {0} ({1}).".format(target.words(here), mode or "explore")


def recent_moves(records: List[Dict[str, Any]], manifest: Dict[str, Any], n: int = 3) -> str:
    """The last n moves in words, each with what it did. No positions."""
    step_now = int(manifest.get("step", 0))
    rows = sorted((r for r in records if "step" in r and r["step"] < step_now),
                  key=lambda r: r["step"])
    poses = [spatial.pose_xyh((r.get("manifest") or {}).get("pose")) for r in rows]
    poses.append(spatial.pose_xyh(manifest.get("pose")))
    out = []
    for k, r in enumerate(rows):
        if r.get("error") or r.get("index") is None:
            continue
        actions = (r.get("manifest") or {}).get("actions") or []
        chosen = next((a for a in actions if a.get("index") == r["index"]), {})
        move = prompts._move({"turn_around": chosen.get("turn_around"),
                              "theta_deg": chosen.get("theta_deg")})
        before = poses[k]
        after = next((p for p in poses[k + 1:] if p is not None), None)
        what = ""
        if before is not None and after is not None and not chosen.get("turn_around"):
            moved = math.hypot(after[0] - before[0], after[1] - before[1])
            if moved < spatial.BLOCKED_BELOW_M:
                what = ", did not move (blocked)"
            elif moved < spatial.SHORT_BELOW_M:
                what = ", stopped short (blocked)"
            else:
                what = ", moved {0:.1f} m".format(moved)
        out.append("step {0} {1}{2}".format(r["step"], move, what))
    if not out:
        return "none yet, this is the first step."
    return "; ".join(out[-n:]) + "."


# --- the step -------------------------------------------------------------------

def previous(records: List[Dict[str, Any]], step: int):
    """The strategist's standing target and mode, the step it was last asked, and
    the perceiver's report on the previous step, all from decisions.jsonl."""
    rows = sorted((r for r in records if "step" in r and r["step"] < step),
                  key=lambda r: r["step"])
    target, mode, last_called, last_perception = None, None, None, None
    for r in rows:
        if r.get("strategist") is not None:
            last_called = r["step"]
        if "target" in r:
            target = spatial.Target.from_dict(r.get("target"))
            mode = r.get("mode")
    if rows:
        last_perception = (rows[-1].get("perceiver") or {}).get("result")
    return target, mode, last_called, last_perception


def _error(run: Run, record: Dict[str, Any], message: str):
    record["error"] = message
    run.record_decision(record)
    log.error("step %d decision failed: %s", record.get("step", -1), message)
    # 200 with an error body, as app.decide: the client fails the run.
    return JSONResponse({"error": message}, status_code=200)


async def decide(request: Any, run: Run, frame_path: str):
    """The /decide body for an orchestrated agent. Writes the decision record."""
    features = agent.current().features["orchestrator"]
    manifest = request.manifest
    step = int(request.step)
    record: Dict[str, Any] = {"step": step, "frame": frame_path, "manifest": manifest,
                              "frame_size": request.frame_size, **agent.record()}
    # Never fall back to the annotated frame for the perceiver (app.decide, a06).
    if not request.clean_frame_png_b64:
        return _error(run, record, "agent wants the clean frame and the request has none")
    record["clean_frame"] = run.save_clean_frame(step, request.clean_frame_png_b64)
    records = _read_jsonl(run.decisions)
    latency = 0.0

    # 1. Perceiver: the clean frame and nothing else.
    perceiver_prompt = prompts.get(features["perceiver"])
    seen = await vlm.call_structured(
        schema.PERCEIVER_SCHEMA_NAME, perceiver_prompt.system,
        perceiver_prompt.render(perceiver_prompt, manifest), request.clean_frame_png_b64,
        schema.perceiver_schema(), perception_from, PERCEIVER_MAX_TOKENS)
    latency += seen.latency_ms
    perception = seen.result
    record["perceiver"] = seen.to_dict()
    record["goal"] = LEGACY_GOAL[perception["goal"]] if perception else None

    # 2. Mapper.
    mem = spatial.rebuild(records, manifest, perception)
    here = spatial.pose_xyh(manifest.get("pose"))

    # 3. Strategist, only when something has changed.
    target, mode, last_called, last_perception = previous(records, step)
    why = spatial.trigger(mem, manifest, perception, target, last_called, last_perception)
    if target is not None and here is not None and not spatial.target_still_valid(
            mem, target, here[:2]):
        target = None
    if why is not None and here is not None:
        menu = spatial.targets(mem, here, step)
        ids = [t.id for t in menu] + [EXPLORE]
        strategist_prompt = prompts.get(features["strategist"])
        text = strategist_prompt.render(strategist_prompt, spatial.situation(
            mem, manifest, perception, target, menu, why))
        plan = await vlm.call_structured(
            schema.STRATEGIST_SCHEMA_NAME, strategist_prompt.system, text, None,
            schema.strategist_schema(ids), _strategy(ids), STRATEGIST_MAX_TOKENS)
        latency += plan.latency_ms
        record["strategist"] = dict(plan.to_dict(), trigger=why, text=text,
                                    menu=[t.to_dict() for t in menu])
        if plan.result is not None:
            mode = plan.result["mode"]
            target = next((t for t in menu if t.id == plan.result["target"]), None)
    record["target"] = target.to_dict() if target is not None else None
    record["mode"] = mode

    # 4. Projector.
    tags = spatial.project(mem, manifest, perception, target)
    record["tags"] = {str(k): v for k, v in tags.items()}

    # 5. Navigator.
    indices = schema.visible_indices(manifest)
    if not indices:
        return _error(run, record, "manifest offers no actions")
    navigator_prompt = agent.current().prompt
    text = navigator_prompt.render(navigator_prompt, manifest, tags,
                                   plan_line(target, mode, here), perceiver_line(perception),
                                   recent_moves(records, manifest))
    record["navigator_text"] = text
    action_schema = schema.action_schema(indices)
    nav = await vlm.call_structured(
        schema.SCHEMA_NAME, navigator_prompt.system, text, request.frame_png_b64,
        action_schema, _action(indices), config.MAX_TOKENS)
    latency += nav.latency_ms
    if nav.result is None:
        record["navigator"] = nav.to_dict()
        record["step_latency_ms"] = round(latency, 1)
        return _error(run, record, "VLMError: " + (nav.error or "navigator failed"))

    # 6. Critic: ask once more when the map disagrees; the second answer stands.
    final = nav
    why_not = None
    if features.get("critic") == "retry":
        why_not = spatial.critique(mem, manifest, tags, nav.result["index"])
    record["critic"] = None
    if why_not is not None:
        note = spatial.WORDS["critic_tail"].format(why=why_not, i=nav.result["index"])
        retry = await vlm.call_structured(
            schema.SCHEMA_NAME, navigator_prompt.system, text, request.frame_png_b64,
            action_schema, _action(indices), config.MAX_TOKENS,
            follow_up=[{"role": "assistant", "content": nav.raw},
                       {"role": "user", "content": note}])
        latency += retry.latency_ms
        record["critic"] = {"why": why_not, "note": note, "first": nav.to_dict(),
                            "retry": retry.to_dict(),
                            "changed": (retry.result is not None
                                        and retry.result["index"] != nav.result["index"])}
        if retry.result is not None:
            final = retry
    assert final.result is not None

    record.update({
        "index": final.result["index"],
        "reason": final.result["reason"],
        "rung": final.rung,
        "latency_ms": round(final.latency_ms, 1),
        "model": final.model,
        "prompt_tokens": final.prompt_tokens,
        "completion_tokens": final.completion_tokens,
        "attempts": final.attempts,
        "raw": final.raw,
        "timing": final.timing.to_dict() if final.timing else None,
        "spatial": mem.snapshot(),
        "step_latency_ms": round(latency, 1),
    })
    run.record_decision(record)
    log.info("step %-3d -> [%d] %-6s %6.0fms  goal=%s target=%s%s  %s",
             step, final.result["index"], final.rung, latency, record["goal"],
             target.id if target else "-", " critic" if why_not else "",
             final.result["reason"][:70].replace("\n", " "))
    return {"index": final.result["index"], "reason": final.result["reason"],
            "rung": final.rung, "latency_ms": round(latency, 1)}
