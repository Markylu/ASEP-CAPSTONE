"""One step of the orchestrated agent (a13 on): several model calls, each with
one job, and code that does the spatial work between them.

A step is a list of stages (`pipeline()`), each reading what the ones before it
left on the Step and writing its part of the decision record:

    perceiver  (g03, clean frame)        where the goal is, open floor, doorways
    mapper     (spatial.rebuild)         the run's map, rebuilt from decisions.jsonl
    strategist (q01/q02, text, trigger)  a target from a list code builds (a13, a14)
      or route (planner.py + q03)        the goal unless its way is shut, then a detour (a15)
    projector  (spatial.project)         notes against each action
    turn_rule  (spatial.hide_turn_around) a14 on
    navigator  (p14, annotated frame)    the action
    critic     (spatial.critique)        one retry when the map disagrees (a13)

Every model stage is shown a views.View, and views.check() refuses one that
shows its role more than it may see. The memory's parameters and wording are
the agent's spatial.SpatialConfig.

a14 (R10) changes three things by feature flag: the strategist (q02) is given
the goal's true position (`goal_truth: planner`), a turn-around right after a
turn-around is not offered while a move ahead is open (`turn_rule`), and the
critic is off. a15 (R11) sets the target by code (`target_policy:
goal_default_llm_detour`) and has a15's memory (`memory: a15`).

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
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi.responses import JSONResponse

from . import agent, config, planner, prompt as prompts, schema, spatial, views, vlm
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

def perception_from(parsed: Dict[str, Any], version: str = "g03",
                    floor_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """The perceiver's reply, checked. g03 gives a doorway as a bool; g04 and
    g05 as "open", "closed" or "none", kept as "open"/"closed" or False. g05
    says where the floor ends in the image; `floor_map` (the agent's) turns
    that into the floor class the map reads, the answer kept as floor_end."""
    goal = parsed.get("goal")
    if goal not in schema.STRIPS + ["not_visible"]:
        raise vlm.VLMError("perceiver gave no valid goal: {0!r}".format(goal))
    lanes = []
    for strip in schema.STRIPS:
        lane = parsed.get(strip) or {}
        if lane.get("floor") not in schema.floor_classes(version):
            raise vlm.VLMError("perceiver gave no valid floor for {0}".format(strip))
        door = lane.get("doorway")
        if version in ("g04", "g05"):
            door = door if door in ("open", "closed") else False
        else:
            door = bool(door)
        if version == "g05":
            lanes.append({"strip": strip, "floor": (floor_map or {})[lane["floor"]],
                          "floor_end": lane["floor"], "doorway": door})
        else:
            lanes.append({"strip": strip, "floor": lane["floor"], "doorway": door})
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
              here: Optional[spatial.Pose], goal_known: bool = False) -> str:
    if target is None or here is None:
        return "no fixed target; explore where the image shows open floor."
    if goal_known and target.kind == "goal":
        # a14: the goal's true position stays with the planner; the navigator
        # gets no distance or direction for it, only "toward your target".
        return spatial.WORDS_A14["plan_goal"].format(mode=mode or "approach")
    return "head for {0} ({1}).".format(target.words(here), mode or "explore")


def without_goal(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """The manifest with its goal ground truth removed (a17)."""
    return {k: v for k, v in manifest.items() if k != "goal"}


def goal_at(manifest: Dict[str, Any]) -> Optional[spatial.Point]:
    """The goal's true position on the map (a14's planner only): x, minus z."""
    position = (manifest.get("goal") or {}).get("position")
    if not position:
        return None
    return float(position[0]), -float(position[2])


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


# --- the step as stages ---------------------------------------------------------

@dataclass
class Step:
    """What one decision knows as its stages build it. Each stage reads what
    the stages before it left here and writes its part of `record`, in the
    order a decision record has always had its fields."""
    features: Dict[str, Any]
    cfg: spatial.SpatialConfig
    manifest: Dict[str, Any]
    step: int
    records: List[Dict[str, Any]]
    record: Dict[str, Any]
    frame_b64: str
    clean_b64: str
    latency: float = 0.0
    perception: Optional[Dict[str, Any]] = None
    mem: Optional[spatial.SpatialMemory] = None
    here: Optional[spatial.Pose] = None
    goal: Optional[spatial.Point] = None
    target: Optional[spatial.Target] = None
    mode: Optional[str] = None
    true_goal: Optional[spatial.Point] = None
    tags: Dict[int, List[str]] = field(default_factory=dict)
    offered: Dict[str, Any] = field(default_factory=dict)
    nav_text: str = ""
    nav: Any = None
    final: Any = None
    why_not: Optional[str] = None


#: A stage returns None to go on, or an error message that fails the step.
StageFn = Callable[[Step], Awaitable[Optional[str]]]


@dataclass(frozen=True)
class Stage:
    """One part of a step. `model` names the subagent prompt a model stage
    calls (None for code); `when` is when it runs."""
    name: str
    run: StageFn
    model: Optional[str] = None
    when: str = "every step"


async def ask(s: Step, view: views.View, schema_name: str, json_schema: Dict[str, Any],
              validate: Callable[[Dict[str, Any]], Dict[str, Any]], max_tokens: int,
              follow_up: Optional[List[Dict[str, Any]]] = None):
    """One model call from a view, after checking the view shows its role only
    what it may see."""
    views.check(view, s.manifest, s.goal is not None)
    if follow_up is None:
        reply = await vlm.call_structured(schema_name, view.system, view.text, view.image_b64,
                                          json_schema, validate, max_tokens)
    else:
        reply = await vlm.call_structured(schema_name, view.system, view.text, view.image_b64,
                                          json_schema, validate, max_tokens,
                                          follow_up=follow_up)
    s.latency += reply.latency_ms
    return reply


async def perceive(s: Step) -> Optional[str]:
    """The clean frame and nothing else."""
    p = prompts.get(s.features["perceiver"])
    seen = await ask(s, views.perceiver(p, s.manifest, s.clean_b64),
                     schema.PERCEIVER_SCHEMA_NAME, schema.perceiver_schema(p.version),
                     lambda parsed: perception_from(parsed, p.version,
                                                    s.features.get("floor_map")),
                     PERCEIVER_MAX_TOKENS)
    s.perception = seen.result
    s.record["perceiver"] = seen.to_dict()
    s.record["goal"] = LEGACY_GOAL[s.perception["goal"]] if s.perception else None
    return None


async def build_map(s: Step) -> Optional[str]:
    s.mem = spatial.rebuild(s.records, s.manifest, s.perception, s.cfg)
    s.here = spatial.pose_xyh(s.manifest.get("pose"))
    # a14 on: the planner side alone is given where the goal truly is. a21:
    # the strategist alone, from the manifest before its goal block was removed.
    truth = s.features.get("goal_truth")
    s.goal = (goal_at(s.manifest) if truth == "planner"
              else s.true_goal if truth == "strategist" else None)
    return None


def _set_target(s: Step) -> None:
    s.record["target"] = s.target.to_dict() if s.target is not None else None
    s.record["mode"] = s.mode


async def strategize(s: Step) -> Optional[str]:
    """a13, a14: the strategist chooses a target on a trigger, else the
    standing target holds while it is still open."""
    assert s.mem is not None
    target, mode, last_called, last_perception = previous(s.records, s.step)
    why = spatial.trigger(s.mem, s.manifest, s.perception, target, last_called, last_perception,
                          goal_at=s.goal, words=s.cfg.triggers if s.goal is not None else None)
    if target is not None and s.here is not None and not spatial.target_still_valid(
            s.mem, target, s.here[:2], s.goal):
        target = None
    if why is not None and s.here is not None:
        menu = spatial.targets(s.mem, s.here, s.step, s.goal)
        ids = [t.id for t in menu] + [EXPLORE]
        view = views.strategist(prompts.get(s.features["strategist"]), spatial.situation(
            s.mem, s.manifest, s.perception, target, menu, why, s.goal))
        plan = await ask(s, view, schema.STRATEGIST_SCHEMA_NAME, schema.strategist_schema(ids),
                         _strategy(ids), STRATEGIST_MAX_TOKENS)
        s.record["strategist"] = dict(plan.to_dict(), trigger=why, text=view.text,
                                      menu=[t.to_dict() for t in menu])
        if plan.result is not None:
            mode = plan.result["mode"]
            target = next((t for t in menu if t.id == plan.result["target"]), None)
    s.target, s.mode = target, mode
    _set_target(s)
    return None


async def route(s: Step) -> Optional[str]:
    """a15: code keeps the goal as the target (planner.py) and asks the detour
    strategist (q03) only when the way toward it is shut."""
    assert s.mem is not None and s.goal is not None
    standing, mode, last_called, _ = previous(s.records, s.step)
    r = planner.route(s.mem, s.manifest, s.perception, s.records, standing, mode, last_called,
                      s.goal)
    s.record["planner"] = r.to_dict()
    s.target, s.mode = r.target, r.mode
    if r.ask is not None and s.here is not None:
        menu = planner.detours(s.mem, s.here, s.step, s.goal)
        ids = [t.id for t in menu] + [EXPLORE]
        view = views.strategist(prompts.get(s.features["strategist"]),
                                planner.detour_situation(s.mem, s.manifest, menu, r.ask, s.goal))
        plan = await ask(s, view, schema.STRATEGIST_SCHEMA_NAME, schema.strategist_schema(ids),
                         _strategy(ids), STRATEGIST_MAX_TOKENS)
        s.record["strategist"] = dict(plan.to_dict(), trigger=spatial.WORDS_A15["asked"][r.ask],
                                      text=view.text, menu=[t.to_dict() for t in menu])
        # A failed call keeps the goal; "explore" is no target for a few steps.
        if plan.result is not None:
            s.mode = plan.result["mode"]
            s.target = next((t for t in menu if t.id == plan.result["target"]), None)
    _set_target(s)
    return None


async def stage_plan(s: Step) -> Optional[str]:
    """a17: the stage machine (planner.staged) sets the target from what the
    agent has seen, and asks q04 for a search target or a detour when it must.
    The evaluator's record of this step is kept beside the stage."""
    assert s.mem is not None
    standing, mode, last_called, _ = previous(s.records, s.step)
    prev = next((r.get("stage") for r in sorted(
        (r for r in s.records if "step" in r and r["step"] < s.step),
        key=lambda r: r["step"], reverse=True) if r.get("stage")), None)
    r = planner.staged(s.mem, s.manifest, s.perception, planner.StageState.from_dict(prev),
                       standing, mode, last_called)
    s.target, s.mode = r.target, r.mode
    if r.ask is not None and s.here is not None:
        ids = [t.id for t in r.menu] + [EXPLORE]
        view = views.strategist(prompts.get(s.features["strategist"]),
                                planner.search_situation(s.mem, s.manifest, r.state, r.menu,
                                                         r.ask))
        plan = await ask(s, view, schema.STRATEGIST_SCHEMA_NAME, schema.strategist_schema(ids),
                         _strategy(ids), STRATEGIST_MAX_TOKENS)
        s.record["strategist"] = dict(plan.to_dict(), trigger=planner.ASKED_A17[r.ask],
                                      text=view.text, menu=[t.to_dict() for t in r.menu])
        # A failed call keeps what the planner had; "explore" is no target.
        if plan.result is not None:
            s.mode = plan.result["mode"]
            s.target = next((t for t in r.menu if t.id == plan.result["target"]), None)
            r.state.target_dist_m = (
                round(spatial.dist(s.here[:2], (s.target.x, s.target.y)), 2)
                if s.target is not None else None)
    s.record["stage"] = r.state.to_dict()
    s.record["evaluator"] = dict(r.evaluator, events=r.events, ask=r.ask)
    _set_target(s)
    return None


async def verify_plan(s: Step) -> Optional[str]:
    """a20: a17's stages with verify (planner.staged_verify). a21: the
    strategist's text also carries the goal's true position (s.goal)."""
    assert s.mem is not None
    standing, mode, last_called, _ = previous(s.records, s.step)
    prev = next((r.get("stage") for r in sorted(
        (r for r in s.records if "step" in r and r["step"] < s.step),
        key=lambda r: r["step"], reverse=True) if r.get("stage")), None)
    r = planner.staged_verify(s.mem, s.manifest, s.perception,
                              planner.VerifyState.from_dict(prev), standing, mode, last_called)
    s.target, s.mode = r.target, r.mode
    if r.ask is not None and s.here is not None:
        ids = [t.id for t in r.menu] + [EXPLORE]
        view = views.strategist(prompts.get(s.features["strategist"]),
                                planner.search_situation_a20(s.mem, s.manifest, r.state,
                                                             r.menu, r.ask, s.goal))
        plan = await ask(s, view, schema.STRATEGIST_SCHEMA_NAME, schema.strategist_schema(ids),
                         _strategy(ids), STRATEGIST_MAX_TOKENS)
        s.record["strategist"] = dict(plan.to_dict(), trigger=planner.asked(r.ask),
                                      text=view.text, menu=[t.to_dict() for t in r.menu])
        if plan.result is not None:
            s.mode = plan.result["mode"]
            s.target = next((t for t in r.menu if t.id == plan.result["target"]), None)
            r.state.target_dist_m = (
                round(spatial.dist(s.here[:2], (s.target.x, s.target.y)), 2)
                if s.target is not None else None)
    s.record["stage"] = r.state.to_dict()
    s.record["evaluator"] = dict(r.evaluator, events=r.events, ask=r.ask)
    _set_target(s)
    return None


async def project(s: Step) -> Optional[str]:
    assert s.mem is not None
    s.tags = spatial.project(s.mem, s.manifest, s.perception, s.target)
    s.record["tags"] = {str(k): v for k, v in s.tags.items()}
    s.offered = s.manifest
    return None


async def turn_rule(s: Step) -> Optional[str]:
    """a14 on: a turn-around right after a turn-around is not offered while a
    move ahead is open (operator, 2026-10-24). Left off the list and the schema;
    the frame still shows its marker."""
    assert s.mem is not None
    hidden = spatial.hide_turn_around(s.mem, s.manifest, s.tags)
    if hidden:
        s.record["hidden"] = {"indices": hidden, "why": spatial.WORDS_A14["turn_rule"]}
        s.offered = dict(s.manifest, actions=[a for a in s.manifest.get("actions") or []
                                              if int(a["index"]) not in hidden])
    return None


async def navigate(s: Step) -> Optional[str]:
    indices = schema.visible_indices(s.offered)
    if not indices:
        return "manifest offers no actions"
    p = agent.current().prompt
    view = views.navigator(p, s.offered, s.tags,
                           plan_line(s.target, s.mode, s.here,
                                     s.features.get("goal_truth") == "planner"),
                           perceiver_line(s.perception), recent_moves(s.records, s.manifest),
                           s.frame_b64)
    s.nav_text = view.text
    s.record["navigator_text"] = view.text
    s.nav = await ask(s, view, schema.SCHEMA_NAME, schema.action_schema(indices),
                      _action(indices), config.MAX_TOKENS)
    if s.nav.result is None:
        s.record["navigator"] = s.nav.to_dict()
        s.record["step_latency_ms"] = round(s.latency, 1)
        return "VLMError: " + (s.nav.error or "navigator failed")
    s.final = s.nav
    return None


async def critic(s: Step) -> Optional[str]:
    """a13: ask once more when the map disagrees; the second answer stands."""
    assert s.mem is not None
    if s.features.get("critic") == "retry":
        s.why_not = spatial.critique(s.mem, s.manifest, s.tags, s.nav.result["index"])
    s.record["critic"] = None
    if s.why_not is not None:
        indices = schema.visible_indices(s.offered)
        note = spatial.WORDS["critic_tail"].format(why=s.why_not, i=s.nav.result["index"])
        p = agent.current().prompt
        view = views.View("navigator", p.system, s.nav_text, s.frame_b64)
        retry = await ask(s, view, schema.SCHEMA_NAME, schema.action_schema(indices),
                          _action(indices), config.MAX_TOKENS,
                          follow_up=[{"role": "assistant", "content": s.nav.raw},
                                     {"role": "user", "content": note}])
        s.record["critic"] = {"why": s.why_not, "note": note, "first": s.nav.to_dict(),
                              "retry": retry.to_dict(),
                              "changed": (retry.result is not None
                                          and retry.result["index"] != s.nav.result["index"])}
        if retry.result is not None:
            s.final = retry
    return None


def pipeline(features: Dict[str, Any]) -> List[Stage]:
    """The stages an orchestrated agent's features name, in order."""
    policy = features.get("target_policy", "llm_strategist")
    if policy == "llm_strategist":
        planning = Stage("strategist", strategize, features.get("strategist"), "on a trigger")
    elif policy == "goal_default_llm_detour":
        planning = Stage("route", route, features.get("strategist"),
                         "every step; q03 only when the way to the goal is shut")
    elif policy == "staged_search":
        planning = Stage("stages", stage_plan, features.get("strategist"),
                         "every step; q04 when a search target or a detour is needed")
    elif policy == "staged_verify":
        planning = Stage("stages", verify_plan, features.get("strategist"),
                         "every step; the strategist when a search target or a detour "
                         "is needed")
    else:
        raise ValueError("unknown target_policy {0!r}".format(policy))
    stages = [Stage("perceiver", perceive, features.get("perceiver")),
              Stage("mapper", build_map),
              planning,
              Stage("projector", project)]
    if features.get("turn_rule") == "no_repeat_when_open":
        stages.append(Stage("turn_rule", turn_rule))
    stages += [Stage("navigator", navigate, agent.current().prompt_version),
               Stage("critic", critic, None, "when the map disagrees (a13)")]
    return stages


async def decide(request: Any, run: Run, frame_path: str):
    """The /decide body for an orchestrated agent. Writes the decision record."""
    current = agent.current()
    features = current.features["orchestrator"]
    manifest = request.manifest
    step = int(request.step)
    record: Dict[str, Any] = {"step": step, "frame": frame_path, "manifest": manifest,
                              "frame_size": request.frame_size, **agent.record()}
    # Never fall back to the annotated frame for the perceiver (app.decide, a06).
    if not request.clean_frame_png_b64:
        return _error(run, record, "agent wants the clean frame and the request has none")
    record["clean_frame"] = run.save_clean_frame(step, request.clean_frame_png_b64)
    # a17 (R12, operator 2026-10-28): no goal truth anywhere in the agent. Its
    # stages see the manifest without the goal block; the record keeps it for
    # evaluation.
    # a21 (R13G): the same, the goal's position kept apart for the strategist.
    true_goal = goal_at(manifest)
    if features.get("goal_truth") in ("none", "strategist"):
        manifest = without_goal(manifest)
    s = Step(features=features, cfg=spatial.config_for(features), manifest=manifest, step=step,
             records=_read_jsonl(run.decisions), record=record,
             frame_b64=request.frame_png_b64, clean_b64=request.clean_frame_png_b64,
             true_goal=true_goal)
    for stage in pipeline(features):
        try:
            failed = await stage.run(s)
        except views.LeakError as exc:
            failed = "{0}: {1}".format(stage.name, exc)
        if failed is not None:
            return _error(run, record, failed)
    final = s.final
    assert final is not None and final.result is not None and s.mem is not None
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
        "spatial": s.mem.snapshot(),
        "step_latency_ms": round(s.latency, 1),
    })
    run.record_decision(record)
    log.info("step %-3d -> [%d] %-6s %6.0fms  goal=%s target=%s%s  %s",
             step, final.result["index"], final.rung, s.latency, record["goal"],
             s.target.id if s.target else "-", " critic" if s.why_not else "",
             final.result["reason"][:70].replace("\n", " "))
    return {"index": final.result["index"], "reason": final.result["reason"],
            "rung": final.rung, "latency_ms": round(s.latency, 1)}
