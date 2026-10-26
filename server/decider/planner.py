"""The route planner and progress monitor of a15 (R11): code, not a model.

R10 told the strategist (q02) where the goal is on every call, and it chose the
goal on 70 of 229. Standing on the goal or a doorway gained about 0.9 m a step
toward it; unexplored ground, backtrack and explore gained nothing or lost
ground, and took 47% of the steps (eval/phase2/R11_goal_default/evidence.md).

So in a15 the goal is the standing target by default, and the detour
strategist (q03) is asked only when the way toward it is shut:
- walled: no forward move within 55 degrees of the goal is open on the map;
- blocked: a move toward the goal was blocked here in the last 3 steps;
- stall (the progress monitor): the goal has been the target for 6 steps and
  the drone is not 0.5 m nearer it.
A detour stands until it is reached or closed, until 12 steps have passed, or
until the goal is in view with the way to it open; then the goal is the target
again. "explore" stands for 3 steps.

Planner-side code may read the goal's true position (operator, 2026-10-26); no
navigator or perceiver text may carry it (views.py checks every one). Every
parameter is spatial.PARAMS_A15, hashed into a15's sha.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import spatial

P = spatial.PARAMS_A15


@dataclass
class Route:
    """What the planner decided this step. `ask` names why q03 must choose a
    detour now (WORDS_A15["asked"] key), or None."""
    target: Optional[spatial.Target]
    mode: Optional[str]
    way: str
    progress_m: Optional[float]
    ask: Optional[str] = None
    hand_back: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"way": self.way, "progress_m": self.progress_m, "ask": self.ask,
                "hand_back": self.hand_back}


def goal_target(goal: spatial.Point, step: int) -> spatial.Target:
    return spatial.Target("goal", "goal", goal[0], goal[1], spatial.WORDS_A14["goal_label"], step)


def goal_way(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
             perception: Optional[Dict[str, Any]], goal: spatial.Point) -> str:
    """'open', 'walled' or 'blocked': whether the map lets the drone head for
    the goal from here. A goal behind is open (the turn-around faces it)."""
    here = spatial.pose_xyh(manifest.get("pose"))
    if here is None:
        return "open"
    step = int(manifest.get("step", 0))
    want = spatial.bearing(here[:2], goal)
    for b in mem.blocks:
        if (b.step >= step - P["recent_block_steps"]
                and spatial.dist(here[:2], (b.x, b.y)) < P["recent_block_near_m"]
                and abs(spatial.wrap(b.heading - want)) <= P["goal_way_within_deg"]):
            return "blocked"
    if abs(spatial.wrap(want - here[2])) > 90.0:
        return "open"
    lanes = {l.get("strip"): l for l in (perception or {}).get("lanes") or []}
    for a in manifest.get("actions") or []:
        if a.get("turn_around"):
            continue
        if (abs(spatial.wrap(spatial.action_heading(a, here[2]) - want))
                <= P["goal_way_within_deg"] and not spatial.not_open(mem, here, a, lanes)):
            return "open"
    return "walled"


def goal_run(records: List[Dict[str, Any]], step: int) -> int:
    """How many decisions in a row, up to this one, stood on the goal."""
    rows = sorted((r for r in records if "step" in r and r["step"] < step),
                  key=lambda r: r["step"])
    n = 0
    for r in reversed(rows):
        if (r.get("target") or {}).get("id") != "goal":
            break
        n += 1
    return n


def progress(mem: spatial.SpatialMemory, goal: spatial.Point) -> Optional[float]:
    """Metres nearer the goal than `stall_steps` decisions ago, or None."""
    k = P["stall_steps"]
    if len(mem.trail) <= k:
        return None
    _, x0, y0, _ = mem.trail[-1 - k]
    _, x1, y1, _ = mem.trail[-1]
    return round(spatial.dist((x0, y0), goal) - spatial.dist((x1, y1), goal), 2)


def route(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
          perception: Optional[Dict[str, Any]], records: List[Dict[str, Any]],
          standing: Optional[spatial.Target], mode: Optional[str],
          last_called: Optional[int], goal: spatial.Point) -> Route:
    """The target for this step, and whether q03 must be asked for a detour."""
    step = int(manifest.get("step", 0))
    here = spatial.pose_xyh(manifest.get("pose"))
    way = goal_way(mem, manifest, perception, goal)
    gained = progress(mem, goal)
    hand_back = None
    if standing is not None and standing.kind != "goal" and here is not None:
        state = spatial.target_state(mem, standing, here[:2], goal)
        if state != "open":
            hand_back = "detour_" + state
        elif step - standing.step > P["detour_max_steps"]:
            hand_back = "detour_too_long"
        elif (perception or {}).get("goal") in spatial.STRIPS and way == "open":
            hand_back = "goal_in_view"
        else:
            return Route(standing, mode, way, gained)
    elif (standing is None and last_called is not None
          and step - last_called < P["explore_hold_steps"]):
        return Route(None, mode, way, gained)
    stalled = (gained is not None and goal_run(records, step) >= P["stall_steps"]
               and gained < P["stall_gain_m"])
    ask = None
    if way != "open":
        ask = way
    elif stalled:
        ask = "stall"
    return Route(goal_target(goal, step), "approach", way, gained, ask, hand_back)


def gain_words(here: spatial.Pose, target: spatial.Target, goal: spatial.Point) -> str:
    gain = spatial.dist(here[:2], goal) - spatial.dist((target.x, target.y), goal)
    if abs(gain) < P["same_distance_m"]:
        return spatial.WORDS_A15["same"]
    return spatial.WORDS_A15["nearer" if gain > 0 else "farther"].format(d=abs(gain))


def detours(mem: spatial.SpatialMemory, here: spatial.Pose, step: int,
            goal: spatial.Point) -> List[spatial.Target]:
    """q03's menu: the strategist's list without the goal."""
    return [t for t in spatial.targets(mem, here, step, goal) if t.kind != "goal"]


def detour_situation(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
                     menu: List[spatial.Target], ask: str, goal: spatial.Point) -> str:
    """What q03 is told, in words: why it is asked, where the goal is, which
    moves from here were blocked, and each detour with how much nearer the
    goal it lies. Not whether the goal is in the image, nor how long the drone
    has stayed near this spot: R10's strategist read both as "a wall is in the
    way" (evidence §2)."""
    here = spatial.pose_xyh(manifest.get("pose"))
    step = int(manifest.get("step", 0))
    lines = ["Step {0}. You are asked now because {1}.".format(
        step, spatial.WORDS_A15["asked"][ask])]
    if here is not None:
        lines.append(spatial.WORDS_A14["goal_known"].format(
            where=spatial.where_words(here, goal)))
        blocked = sorted({spatial.relative_word(b.heading - here[2]) for b in mem.blocks
                          if spatial.dist(here[:2], (b.x, b.y)) < spatial.BLOCK_NEAR_M})
        if blocked:
            lines.append("Moves from here that were blocked before: {0}.".format(
                ", ".join(blocked)))
    lines.append(spatial.WORDS_A15["menu"])
    for t in menu:
        if here is None:
            lines.append("  {0}: {1}".format(t.id, t.label))
        else:
            lines.append("  {0}: {1}; {2}".format(t.id, t.words(here),
                                                  gain_words(here, t, goal)))
    lines.append("  explore: no fixed target, go where the image shows open floor")
    return "\n".join(lines)
