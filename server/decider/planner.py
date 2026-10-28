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

from dataclasses import dataclass, field
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


# --- a17 (R12): staged search, no goal truth ------------------------------------
#
# Two stages, set by code from what the agent itself has seen:
# - explore: search. The target is an edge of unsearched ground a known path
#   reaches, a doorway, or a way back, chosen by q04. The evaluator scores each
#   step by what the look newly searched and how much nearer the target the
#   drone got; four unproductive steps in a row blacklist the target.
# - goal: head for where the goal was seen (spatial.goal_belief, from the rays
#   since `rays_since`). One sighting is enough to enter. A look whose cone
#   covers the believed point without seeing the goal, twice in a row, or
#   reaching the point with no sighting in the last three looks, disproves the
#   sightings: their rays are dropped and the stage is explore again. Inside
#   goal, a16's walled/blocked rule asks q04 for a detour off the search menu.
# The manifest's goal block is never read here (the orchestrator strips it).

A = spatial.PARAMS_A17

#: a17's evaluator and stage thresholds. Part of a17's sha (agent.py).
STAGE_PARAMS: Dict[str, Any] = {
    "unproductive_new_cells": 3,
    "unproductive_gain_m": 0.5,
    "unproductive_steps": 4,
    # One look that should have shown the goal and did not disproves it. R11
    # and R11C open-loop (eval/r12_probe.py line 5): false sightings disproved
    # 39 of 46 (2 looks: 28), genuine ones lost in sight 12 of 285 (2 looks: 9).
    "miss_looks": 1,
    "reached_quiet_looks": 3,
    "detour_max_steps": 12,
    "explore_hold_steps": 3,
}

#: Why q04 is asked, in words.
ASKED_A17: Dict[str, str] = {
    "start": "the run is starting and the goal has not been seen",
    "reached": "the drone has reached the target you chose",
    "closed": "the doorway you chose is closed or already passed",
    "unproductive": "your target has shown no new ground and come no nearer for four steps",
    "exhausted": "no unsearched ground is reachable from here; only doorways or a way back",
    "lost": "the goal was not where it was seen, so the search goes on",
    "walled": "the way toward the goal you saw is walled",
    "blocked": "a move toward the goal you saw was blocked",
}


#: Every other sentence q04 is shown (search_situation).
SITUATION_A17: Dict[str, str] = {
    "asked": "Step {step}. You are asked now because {why}.",
    "dropped": "The goal was not where it was seen; that sighting is dropped.",
    "unseen": "The goal has not been seen yet.",
    "seen": "The goal was seen at step {step}: {where}.",
    "blocked": "Moves from here that were blocked before: {dirs}.",
    "menu": "Places you can choose from:",
    "explore": "  explore: no fixed target, go where the image shows open floor",
}


def stage_sha_blob() -> Dict[str, Any]:
    return {"stage_params": STAGE_PARAMS, "asked_a17": ASKED_A17,
            "situation_a17": SITUATION_A17}


@dataclass
class StageState:
    """The stage machine's state, carried from step to step in the decision
    record (`stage`), so a run directory replays to it."""
    stage: str = "explore"
    rays_since: int = -1
    miss: int = 0
    unproductive: int = 0
    blacklist: List[List[float]] = field(default_factory=list)
    target_dist_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"stage": self.stage, "rays_since": self.rays_since, "miss": self.miss,
                "unproductive": self.unproductive,
                "blacklist": [[round(x, 2), round(y, 2)] for x, y in self.blacklist],
                "target_dist_m": self.target_dist_m}

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "StageState":
        if not d:
            return cls()
        return cls(d.get("stage", "explore"), int(d.get("rays_since", -1)), int(d.get("miss", 0)),
                   int(d.get("unproductive", 0)), [list(p) for p in d.get("blacklist") or []],
                   d.get("target_dist_m"))


@dataclass
class Staged:
    """What a17's planner decided this step. `ask` is an ASKED_A17 key when q04
    must choose now; `menu` is what it chooses from."""
    state: StageState
    target: Optional[spatial.Target]
    mode: Optional[str]
    ask: Optional[str]
    menu: List[spatial.Target]
    evaluator: Dict[str, Any]
    events: List[str]


def belief_target(mem: spatial.SpatialMemory, state: StageState,
                  step: int) -> Optional[spatial.Target]:
    b = mem.goal_belief(since=state.rays_since)
    if b is None:
        return None
    return spatial.Target("goal", "goal", b[0], b[1],
                          "the goal (seen at step {0})".format(b[2]), step)


def search_menu(mem: spatial.SpatialMemory, here: spatial.Pose, step: int,
                blacklist: List[List[float]]) -> List[spatial.Target]:
    """q04's menu: reachable edges of unsearched ground (best first), doorways a
    known path reaches, and the way back. Distances are path metres."""
    reach = mem.reach(here[:2])
    black = [(b[0], b[1]) for b in blacklist]
    out: List[spatial.Target] = []
    for k, (p, cells, path) in enumerate(mem.search_frontiers(here[:2], black)):
        out.append(spatial.Target("unexplored_{0}".format(k + 1), "frontier", p[0], p[1],
                                  spatial.WORDS_A17["frontier"].format(cells=cells, path=path),
                                  step))
    for o in mem.listed_openings(step):
        path = mem.reachable((o.x, o.y), reach)
        if path is None or any(spatial.dist((o.x, o.y), b) < A["blacklist_near_m"]
                               for b in black):
            continue
        out.append(spatial.Target("doorway_" + o.label, "opening", o.x, o.y,
                                  spatial.WORDS_A17["doorway"].format(
                                      label=o.label, step=o.step, path=path), step))
    back = spatial._backtrack_point(mem, here)
    if back is not None:
        s, p = back
        out.append(spatial.Target("back_to_step_{0}".format(s), "backtrack", p[0], p[1],
                                  "where you were at step {0}".format(s), step))
    return out


def evaluate(mem: spatial.SpatialMemory, here: Optional[spatial.Pose],
             perception: Optional[Dict[str, Any]], state: StageState,
             target: Optional[spatial.Target]) -> Dict[str, Any]:
    """The move-productivity record: what this look newly searched, how much of
    its cone had been searched before ("seen this view before"), and how much
    nearer the standing target the drone got since the last step."""
    look = mem.last_look()
    dist_now = (round(spatial.dist(here[:2], (target.x, target.y)), 2)
                if here is not None and target is not None else None)
    gain = (round(state.target_dist_m - dist_now, 2)
            if dist_now is not None and state.target_dist_m is not None else None)
    last_move = mem.trail[-2][0] if len(mem.trail) > 1 else None
    return {"new_seen": look.new if look else 0,
            "view_revisit": round(look.revisit, 2) if look else None,
            "target_dist_m": dist_now, "target_gain_m": gain,
            "stopped_short": any(b.step == last_move for b in mem.blocks),
            "goal_sighted": (perception or {}).get("goal") in spatial.STRIPS}


def staged(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
           perception: Optional[Dict[str, Any]], prev: StageState,
           standing: Optional[spatial.Target], mode: Optional[str],
           last_called: Optional[int]) -> Staged:
    """a17's target for this step, and whether q04 must be asked."""
    step = int(manifest.get("step", 0))
    here = spatial.pose_xyh(manifest.get("pose"))
    st = StageState.from_dict(prev.to_dict())
    events: List[str] = []
    ev = evaluate(mem, here, perception, st, standing)
    sighted = ev["goal_sighted"]

    # Stage transitions, on what the agent itself has seen.
    if st.stage == "explore" and sighted:
        st.stage, st.miss, st.unproductive = "goal", 0, 0
        standing, mode = None, None
        events.append("goal_sighted")
    elif st.stage == "goal":
        belief = mem.goal_belief(since=st.rays_since)
        lost = belief is None
        if belief is not None and here is not None:
            if sighted:
                st.miss = 0
            elif mem.covered(belief[:2], step) or mem.faces_unseen(belief[:2], here,
                                                                    perception):
                st.miss += 1
            if st.miss >= STAGE_PARAMS["miss_looks"]:
                lost = True
                events.append("belief_disproved")
            elif (spatial.dist(here[:2], belief[:2]) < spatial.TARGET_REACHED_M
                  and step - belief[2] >= STAGE_PARAMS["reached_quiet_looks"]):
                lost = True
                events.append("belief_reached_empty")
        if lost:
            st.stage, st.miss, st.rays_since = "explore", 0, step + 1
            standing, mode, last_called = None, None, None
            events.append("lost")

    ask: Optional[str] = None
    target, out_mode = standing, mode
    if here is None:
        return Staged(st, target, out_mode, None, [], ev, events)

    if st.stage == "goal":
        goal = belief_target(mem, st, step)
        assert goal is not None
        way = goal_way(mem, manifest, perception, (goal.x, goal.y))
        if standing is not None and standing.kind != "goal":
            # A detour stands until reached or closed, too long, or the goal
            # in view with the way open.
            state = spatial.target_state(mem, standing, here[:2])
            if (state != "open" or (sighted and way == "open")
                    or step - standing.step > STAGE_PARAMS["detour_max_steps"]):
                target, out_mode = goal, "approach"
                events.append("detour_" + ("done" if state != "open" else "ended"))
            else:
                target = standing
        else:
            target, out_mode = goal, "approach"
            if way != "open":
                ask = way
    else:
        if standing is not None:
            # The evaluator scores the standing search target.
            productive = (ev["new_seen"] >= STAGE_PARAMS["unproductive_new_cells"]
                          or (ev["target_gain_m"] or 0.0) >= STAGE_PARAMS["unproductive_gain_m"])
            st.unproductive = 0 if productive else st.unproductive + 1
            state = spatial.target_state(mem, standing, here[:2])
            if st.unproductive >= STAGE_PARAMS["unproductive_steps"]:
                st.blacklist.append([standing.x, standing.y])
                events.append("blacklisted")
                ask = "unproductive"
            elif state != "open":
                ask = state
        elif "lost" in events:
            ask = "lost"
        elif last_called is None:
            ask = "start"
        elif step - last_called >= STAGE_PARAMS["explore_hold_steps"]:
            ask = "reached"
        if ask is not None:
            target, out_mode, st.unproductive = None, None, 0

    menu: List[spatial.Target] = []
    if ask is not None:
        menu = search_menu(mem, here, step, st.blacklist)
        if st.stage == "explore" and not any(t.kind == "frontier" for t in menu):
            ask = "exhausted"
    st.target_dist_m = (round(spatial.dist(here[:2], (target.x, target.y)), 2)
                        if target is not None else None)
    return Staged(st, target, out_mode, ask, menu, ev, events)


def search_situation(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
                     state: StageState, menu: List[spatial.Target], ask: str) -> str:
    """What q04 is told: why it is asked, whether and where the goal was seen
    (the agent's own sightings), moves from here blocked before, and the menu
    with path distances."""
    here = spatial.pose_xyh(manifest.get("pose"))
    step = int(manifest.get("step", 0))
    w = SITUATION_A17
    lines = [w["asked"].format(step=step, why=ASKED_A17[ask])]
    if here is not None:
        b = mem.goal_belief(since=state.rays_since) if state.stage == "goal" else None
        if b is None:
            lines.append(w["dropped"] if ask == "lost" else w["unseen"])
        else:
            lines.append(w["seen"].format(step=b[2], where=spatial.where_words(here, b[:2])))
        blocked = sorted({spatial.relative_word(bl.heading - here[2]) for bl in mem.blocks
                          if spatial.dist(here[:2], (bl.x, bl.y)) < spatial.BLOCK_NEAR_M})
        if blocked:
            lines.append(w["blocked"].format(dirs=", ".join(blocked)))
    lines.append(w["menu"])
    for t in menu:
        lines.append("  {0}: {1}".format(t.id, t.words(here) if here is not None else t.label))
    lines.append(w["explore"])
    return "\n".join(lines)
