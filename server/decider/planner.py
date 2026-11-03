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

import heapq
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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


def detour_stalled(mem: spatial.SpatialMemory, target: spatial.Target,
                   stall: Dict[str, float]) -> bool:
    """a33: the last `steps` moves, all on this detour, brought the drone less
    than `gain_m` nearer it. R15 s01 final: 12 steps circling a frontier 3-4 m
    abeam ("sharp right: toward your target" every step)."""
    k = int(stall["steps"])
    if len(mem.trail) <= k or mem.trail[-1 - k][0] < target.step:
        return False
    _, x0, y0, _ = mem.trail[-1 - k]
    _, x1, y1, _ = mem.trail[-1]
    t = (target.x, target.y)
    return spatial.dist((x0, y0), t) - spatial.dist((x1, y1), t) < float(stall["gain_m"])


def failed_detours(records: List[Dict[str, Any]]) -> List[List[float]]:
    """Where the detours handed back stalled or too long stood: a33 leaves them
    off later menus (R11 failure analysis Q6, fix 1d)."""
    rows = {r["step"]: r for r in records if "step" in r}
    out = []
    for step, r in rows.items():
        if (r.get("planner") or {}).get("hand_back") in ("detour_stalled", "detour_too_long"):
            t = (rows.get(step - 1) or {}).get("target") or {}
            if t.get("x") is not None and t.get("kind") != "goal":
                out.append([t["x"], t["y"]])
    return out


def route(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
          perception: Optional[Dict[str, Any]], records: List[Dict[str, Any]],
          standing: Optional[spatial.Target], mode: Optional[str],
          last_called: Optional[int], goal: spatial.Point,
          stall: Optional[Dict[str, float]] = None,
          along: Optional[Dict[str, Any]] = None,
          other: Optional[Dict[str, Any]] = None) -> Route:
    """The target for this step, and whether q03 must be asked for a detour."""
    step = int(manifest.get("step", 0))
    here = spatial.pose_xyh(manifest.get("pose"))
    way = goal_way(mem, manifest, perception, goal)
    gained = progress(mem, goal)
    hand_back = None
    if standing is not None and standing.kind != "goal" and here is not None:
        state = spatial.target_state(mem, standing, here[:2], goal)
        if state == "reached" and standing.kind == "through" and standing.via:
            # a46: in front of the gap; now square through it.
            beyond = spatial.Target(standing.id, "through_beyond", standing.via[0],
                                    standing.via[1], standing.label, step)
            return Route(beyond, mode, way, gained)
        if state != "open":
            hand_back = "detour_" + state
        elif stall is not None and detour_stalled(mem, standing, stall):
            hand_back = "detour_stalled"
        elif (along is not None and standing.kind == "along" and way == "open"
              and step - standing.step >= along["hand_back_after"]
              and abs(spatial.wrap(spatial.bearing(here[:2], goal) - here[2]))
              <= along["hand_back_within_deg"]):
            # a39: the way toward the goal opened ahead while following the
            # wall. A goal off to the side counts as open in goal_way (the
            # turn faces it), which along a wall it always is.
            hand_back = "along_way_open"
        elif step - standing.step > (other["max_steps"]
                                     if other is not None and standing.kind == "other_way"
                                     else P["detour_max_steps"]):
            # a50: the way back to the fork is longer than a detour.
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


# --- a39: along-the-wall detours ------------------------------------------------
#
# R15 failure analysis, change 2. Mode B, no search along the wall that stops
# the drone, was primary in 7 of R15/R15N's 17 failures (about 368 steps); R11's
# wins came from a goal-side phantom that slid the drone along that wall. Code
# offers the two ways along it; the strategist (q08) chooses. The parameters
# and wording are the agent's features["along_wall"] (agent.ALONG_WALL_A39), so
# part of its sha.


def wall_axis(mem: spatial.SpatialMemory, here: spatial.Pose, want: float,
              p: Dict[str, Any]) -> float:
    """Heading along the wall between the drone and the goal, pointing to the
    drone's left of the goal: the main axis of the wall cells within `look_m`
    toward the goal, or square to the goal when the map has too few."""
    return _wall_fit(mem, here, want, p)[0]


def _wall_fit(mem: spatial.SpatialMemory, here: spatial.Pose, want: float,
              p: Dict[str, Any]) -> Tuple[float, Optional[spatial.Point]]:
    """wall_axis, and the centre of the wall cells it was fitted to (None when
    the map has too few)."""
    cells = set(mem.wall) | set(mem.stop_wall)
    pts = []
    for c in cells:
        q = ((c[0] + 0.5) * spatial.CELL_M, (c[1] + 0.5) * spatial.CELL_M)
        if (spatial.dist(here[:2], q) <= p["look_m"]
                and abs(spatial.wrap(spatial.bearing(here[:2], q) - want))
                <= p["look_within_deg"]):
            pts.append(q)
    axis = (want + 90.0) % 360.0
    centre = None
    if len(pts) >= p["min_wall_cells"]:
        mx = sum(q[0] for q in pts) / len(pts)
        my = sum(q[1] for q in pts) / len(pts)
        sxx = sum((q[0] - mx) ** 2 for q in pts)
        syy = sum((q[1] - my) ** 2 for q in pts)
        sxy = sum((q[0] - mx) * (q[1] - my) for q in pts)
        axis = math.degrees(0.5 * math.atan2(2.0 * sxy, sxx - syy)) % 360.0
        centre = (mx, my)
    if spatial.wrap(axis - want) < 0:
        axis = (axis + 180.0) % 360.0
    return axis, centre


def along_room(mem: spatial.SpatialMemory, here: spatial.Pose, heading: float,
               p: Dict[str, Any]) -> float:
    """Metres the drone can go along `heading` before the map shows a wall."""
    room, d = 0.0, p["step_m"]
    while d <= p["max_m"] + 1e-9:
        q = (here[0] + d * math.cos(math.radians(heading)),
             here[1] + d * math.sin(math.radians(heading)))
        if mem._blocked_cell(spatial.cell(q)):
            break
        room, d = d, d + p["step_m"]
    return room


def along_followed(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """How many times each along-the-wall side was chosen so far."""
    n = {"left": 0, "right": 0}
    for r in records:
        t = ((r.get("strategist") or {}).get("result") or {}).get("target") or ""
        if t.startswith("along_") and t[6:] in n:
            n[t[6:]] += 1
    return n


def along_wall(mem: spatial.SpatialMemory, here: spatial.Pose, step: int, goal: spatial.Point,
               records: List[Dict[str, Any]], p: Dict[str, Any]) -> List[spatial.Target]:
    """a39: the two along-the-wall detours, left then right of the goal's
    direction, each worded with how often that way was followed. A side with
    less than `min_m` of room is left off, and the other says so."""
    want = spatial.bearing(here[:2], goal)
    axis = wall_axis(mem, here, want, p)
    followed = along_followed(records)
    w = p["words"]
    sides = {}
    for side, heading in (("left", axis), ("right", (axis + 180.0) % 360.0)):
        room = along_room(mem, here, heading, p)
        if room >= p["min_m"]:
            sides[side] = (heading, room)
    out = []
    for side, (heading, room) in sides.items():
        notes = [w["followed"].format(n=followed[side]) if followed[side] else w["fresh"]]
        other = "right" if side == "left" else "left"
        if other not in sides:
            notes.append(w["other_ended"].format(side=other))
        x = here[0] + room * math.cos(math.radians(heading))
        y = here[1] + room * math.sin(math.radians(heading))
        out.append(spatial.Target("along_" + side, "along", x, y,
                                  "{0} ({1})".format(w["item"].format(side=side, d=room),
                                                     "; ".join(notes)), step))
    return out


# --- a50: the other way at the fork --------------------------------------------
#
# s03 analysis (eval/phase2/R22K_open_near_unwalled_goal_confirmer/
# s03_tines_analysis.md): the failed drones took the tine whose door was shut and
# stayed in it 34-46 steps; the menu never offered the other tine. The along-the-
# wall item not taken at the crossbar ended in its mouth on 20 of 20 calls. So
# each detour call also lists the newest along-the-wall end offered at an
# earlier call far from here that the drone never came near, and the situation
# says when a closed door was seen in the last few steps. q10 decides.
# Parameters in the agent's features["other_way"].


def other_way(mem: spatial.SpatialMemory, here: spatial.Pose, step: int,
              records: List[Dict[str, Any]], blacklist: List[List[float]],
              p: Dict[str, Any]) -> List[spatial.Target]:
    """a50: the newest along-the-wall end, offered at a call at least `from_m`
    from here, that the drone never came within `reached_m` of and a known path
    reaches; at most one item."""
    reach = None
    for r in sorted((r for r in records if "step" in r and r["step"] < step),
                    key=lambda r: r["step"], reverse=True):
        menu = (r.get("strategist") or {}).get("menu") or []
        at = spatial.pose_xyh((r.get("manifest") or {}).get("pose"))
        if not menu or at is None or spatial.dist(here[:2], at[:2]) < p["from_m"]:
            continue
        for t in menu:
            if t.get("kind") != "along":
                continue
            end = (t["x"], t["y"])
            if any(spatial.dist(end, (x, y)) < p["reached_m"] for _, x, y, _ in mem.trail):
                continue
            if any(spatial.dist(end, (b[0], b[1])) < p["reached_m"] for b in blacklist):
                continue
            if reach is None:
                reach = mem.reach(here[:2])
            path = mem.reachable(end, reach, p["reach_within_m"])
            if path is None:
                continue
            return [spatial.Target("other_way_{0}".format(r["step"]), "other_way", end[0],
                                   end[1], p["words"]["item"].format(step=r["step"],
                                                                     path=path), step)]
    return []


def dead_end(records: List[Dict[str, Any]], step: int, menu: List[spatial.Target],
             p: Dict[str, Any]) -> bool:
    """a52: a closed door seen in the last `recent_steps` and at most
    `dead_end_max_along` along-the-wall items on the menu."""
    return (closed_door_line(records, step, p) is not None
            and sum(t.kind == "along" for t in menu) <= p["dead_end_max_along"])


def closed_door_line(records: List[Dict[str, Any]], step: int,
                     p: Dict[str, Any]) -> Optional[str]:
    """a50: the steps, within the last `recent_steps`, on which the doorway
    confirmer called a reported doorway closed; None when there were none."""
    seen = sorted({r["step"] for r in records
                   if "step" in r and step - p["recent_steps"] <= r["step"] <= step
                   and "closed" in (((r.get("door_confirmer") or {}).get("result")
                                     or {}).values())})
    if not seen:
        return None
    return p["words"]["closed"].format(steps=", ".join(str(n) for n in seen))


# --- a46: through the doorway in the blocking wall ------------------------------
#
# R19/R19K s02 failure analysis (mode K): from the side of the open door nearer
# closed door B, the straight line to the goal clips the door frame on 197 of
# 202 steps, and a doorway target placed 5 m down a sighting ray sits off the
# gap. Code places the gap where the open-doorway sighting rays (after the
# doorway confirmer) meet the wall that stopped the drone, and offers a detour
# square through it: a point in front of the gap, then one beyond. The
# strategist (q09) chooses. Parameters in the agent's features["through"].


def through_doorways(mem: spatial.SpatialMemory, here: spatial.Pose, step: int,
                     goal: spatial.Point, along: Dict[str, Any],
                     p: Dict[str, Any]) -> List[spatial.Target]:
    """Detours square through a gap in the wall between the drone and the goal
    that at least `min_rays` recent open-doorway sightings, from `min_steps`
    different steps, point at."""
    want = spatial.bearing(here[:2], goal)
    axis, centre = _wall_fit(mem, here, want, along)
    if centre is None:
        return []
    ux, uy = math.cos(math.radians(axis)), math.sin(math.radians(axis))
    # The wall's normal, pointing from the drone's side to the far side.
    nx, ny = -uy, ux
    if (centre[0] - here[0]) * nx + (centre[1] - here[1]) * ny < 0:
        nx, ny = -nx, -ny
    hits = []
    for r in mem.door_rays:
        if r.step < step - p["recent_steps"] or spatial.dist(here[:2], (r.x, r.y)) > p["from_m"]:
            continue
        dx, dy = math.cos(math.radians(r.heading)), math.sin(math.radians(r.heading))
        den = dx * nx + dy * ny
        if den < 0.2:
            continue  # along the wall or away from it
        t = ((centre[0] - r.x) * nx + (centre[1] - r.y) * ny) / den
        if 0.0 < t <= p["ray_m"]:
            hits.append((r.x + t * dx, r.y + t * dy, r.step))
    out: List[spatial.Target] = []
    used: set = set()
    for i, h in enumerate(hits):
        if i in used:
            continue
        group = [j for j, g in enumerate(hits)
                 if j not in used and spatial.dist(h[:2], g[:2]) <= p["merge_m"]]
        if len(group) < p["min_rays"] or len({hits[j][2] for j in group}) < p["min_steps"]:
            continue
        used.update(group)
        gx = sum(hits[j][0] for j in group) / len(group)
        gy = sum(hits[j][1] for j in group) / len(group)
        # A move into the wall that a wall stopped near the gap: it is shut.
        into = math.degrees(math.atan2(ny, nx))
        if any(spatial.dist((b.x, b.y), (gx, gy)) <= p["blocked_near_m"]
               and abs(spatial.wrap(b.heading - into)) <= 60.0 for b in mem.blocks):
            continue
        front = (gx - p["front_m"] * nx, gy - p["front_m"] * ny)
        beyond = [gx + p["beyond_m"] * nx, gy + p["beyond_m"] * ny]
        k = len(out) + 1
        out.append(spatial.Target("through_{0}".format(k), "through", front[0], front[1],
                                  p["words"]["item"].format(n=len(group)), step, beyond))
    return out[:2]


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
                     menu: List[spatial.Target], ask: str, goal: spatial.Point,
                     extra: Optional[str] = None) -> str:
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
    if extra:
        lines.append(extra)
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
        target, out_mode, ask = _goal_stage(mem, manifest, perception, st, standing, mode,
                                            here, step, sighted, events)
    else:
        target, out_mode, ask = _explore_stage(mem, st, ev, standing, mode, here, step,
                                               last_called, events)
    return _finish(mem, st, target, out_mode, ask, here, step, ev, events)


def _goal_stage(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
                perception: Optional[Dict[str, Any]], st: StageState,
                standing: Optional[spatial.Target], mode: Optional[str],
                here: spatial.Pose, step: int, sighted: bool, events: List[str]):
    """a17's goal stage: head for the belief; a walled or blocked way asks for
    a detour, which stands until reached or closed, too long, or the goal in
    view with the way open. Returns (target, mode, ask)."""
    goal = belief_target(mem, st, step)
    assert goal is not None
    way = goal_way(mem, manifest, perception, (goal.x, goal.y))
    if standing is not None and standing.kind != "goal":
        state = spatial.target_state(mem, standing, here[:2])
        if (state != "open" or (sighted and way == "open")
                or step - standing.step > STAGE_PARAMS["detour_max_steps"]):
            events.append("detour_" + ("done" if state != "open" else "ended"))
            return goal, "approach", None
        return standing, mode, None
    return goal, "approach", (way if way != "open" else None)


def _explore_stage(mem: spatial.SpatialMemory, st: StageState, ev: Dict[str, Any],
                   standing: Optional[spatial.Target], mode: Optional[str],
                   here: spatial.Pose, step: int, last_called: Optional[int],
                   events: List[str]):
    """a17's explore stage: the evaluator scores the standing search target;
    q04 is asked when it is unproductive, reached or closed, after the goal was
    lost, at the start, or when "explore" has stood its hold. Returns
    (target, mode, ask)."""
    ask: Optional[str] = None
    target, out_mode = standing, mode
    if standing is not None:
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
    return target, out_mode, ask


def _finish(mem: spatial.SpatialMemory, st: StageState, target: Optional[spatial.Target],
            mode: Optional[str], ask: Optional[str], here: spatial.Pose, step: int,
            ev: Dict[str, Any], events: List[str]) -> Staged:
    """The menu when q04 is asked ("exhausted" when explore has no unsearched
    ground to offer), and the target's distance for the next step's evaluator."""
    menu: List[spatial.Target] = []
    if ask is not None:
        menu = search_menu(mem, here, step, st.blacklist)
        if st.stage == "explore" and not any(t.kind == "frontier" for t in menu):
            ask = "exhausted"
    st.target_dist_m = (round(spatial.dist(here[:2], (target.x, target.y)), 2)
                        if target is not None else None)
    return Staged(st, target, mode, ask, menu, ev, events)


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


# --- a20 (R13): explore, goal, verify --------------------------------------------
#
# a17's stages with a third (operator, 2026-10-28). R12: in `dynamic` the goal
# was reported at step 0 in 5 of 6 runs, then dropped by a cone or "faces it"
# check, or chased to a point 10 m out, and not found again. In a20:
# - goal: while the goal is reported on this look, head for the belief (a17).
#   The first look without it goes to verify, unless a detour stands (the drone
#   left the goal's view on purpose); a17's disproof rules are not used.
# - verify: go back to where the goal was last seen from, face the way it was
#   seen, and look again. Seen there or on the way: goal, and if the new
#   sighting disagrees with the old belief, the old rays are dropped. Not seen
#   on that check look, no path back, or too long: the sighting is dropped and
#   the stage is explore.
# a21 is a20 with the goal's true position in the strategist's text alone.

#: a20's verify thresholds. Part of a20's sha (agent.py).
STAGE_PARAMS_A20: Dict[str, Any] = {
    "vantage_reached_m": spatial.TARGET_REACHED_M,
    # The check look faces the seen bearing within the frame, as faces_unseen.
    "check_within_deg": spatial.FOV_DEG / 2.0 - 4.0,
    "look_point_m": 3.0,
    "moved_off_ray_m": 2.0,
    "moved_bearing_deg": 15.0,
    "verify_max_steps": 8,
}

#: Why the strategist is asked after a verify, in words (beside ASKED_A17).
ASKED_A20: Dict[str, str] = {
    "verify_failed": "the drone went back to where it saw the goal and it was not there",
    "verify_timeout": "the drone could not get back to where it saw the goal in time",
    "verify_unreachable": "no known path leads back to where the goal was seen",
}

#: Every other sentence a20's strategist and navigator are shown.
SITUATION_A20: Dict[str, str] = {
    "vantage": "where you last saw the goal from (step {step})",
    "look": "the way you last saw the goal (step {step})",
}


def verify_sha_blob() -> Dict[str, Any]:
    return {"stage_params_a20": STAGE_PARAMS_A20, "asked_a20": ASKED_A20,
            "situation_a20": SITUATION_A20}


def asked(key: str) -> str:
    return ASKED_A20.get(key) or ASKED_A17[key]


@dataclass
class VerifyState(StageState):
    """a17's state, plus where the goal was last seen from (x, y, heading of
    the sighting, step) and the step verify began."""
    vantage: Optional[List[float]] = None
    verify_since: int = -1
    # a22: steps allowed for this verify, set from the distance back when it
    # began (agent feature `verify_budget`); -1 is a20's fixed limit.
    verify_budget: int = -1

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["vantage"] = [round(v, 2) for v in self.vantage] if self.vantage else None
        d["verify_since"] = self.verify_since
        if self.verify_budget >= 0:
            d["verify_budget"] = self.verify_budget
        return d

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "VerifyState":
        base = StageState.from_dict(d)
        d = d or {}
        return cls(base.stage, base.rays_since, base.miss, base.unproductive, base.blacklist,
                   base.target_dist_m, list(d["vantage"]) if d.get("vantage") else None,
                   int(d.get("verify_since", -1)), int(d.get("verify_budget", -1)))


def _last_ray(mem: spatial.SpatialMemory, since: int):
    rays = [r for r in mem.goal_rays if r.step >= since]
    return rays[-1] if rays else None


def _moved(old: Tuple[float, float, int], ray: Any, vantage: Optional[List[float]]) -> bool:
    """Whether a new sighting disagrees with the belief it would join: the
    believed point lies off the new ray, or the bearing from the same place
    has turned."""
    V = STAGE_PARAMS_A20
    rel = spatial.wrap(spatial.bearing((ray.x, ray.y), old[:2]) - ray.heading)
    off = spatial.dist((ray.x, ray.y), old[:2]) * math.sin(math.radians(abs(rel)))
    if abs(rel) > 90.0 or off > V["moved_off_ray_m"]:
        return True
    return (vantage is not None
            and spatial.dist((ray.x, ray.y), (vantage[0], vantage[1])) < V["vantage_reached_m"]
            and abs(spatial.wrap(ray.heading - vantage[2])) > V["moved_bearing_deg"])


def verify_target(st: VerifyState, here: spatial.Pose, step: int) -> spatial.Target:
    """The vantage; once there, a point along the seen bearing, so "toward
    your target" turns the drone to face it."""
    vx, vy, vh, vs = st.vantage
    if spatial.dist(here[:2], (vx, vy)) < STAGE_PARAMS_A20["vantage_reached_m"]:
        p = spatial.ahead((vx, vy), vh, STAGE_PARAMS_A20["look_point_m"])
        return spatial.Target("verify_look", "verify", p[0], p[1],
                              SITUATION_A20["look"].format(step=int(vs)), step)
    return spatial.Target("verify_vantage", "verify", vx, vy,
                          SITUATION_A20["vantage"].format(step=int(vs)), step)


def _to_explore(st: VerifyState, step: int, why: str, events: List[str]) -> None:
    st.stage, st.rays_since, st.vantage, st.verify_since = "explore", step + 1, None, -1
    if st.verify_budget >= 0:
        st.verify_budget = 0
    events.extend([why, "lost"])


def verify_steps(budget: Dict[str, float], here: Optional[spatial.Pose],
                 vantage: List[float]) -> int:
    """a22: steps allowed to get back to the vantage and look, from the
    straight-line distance back when verify began. Shakedown: three of six
    a20 timeouts were honest trips of 5-9 m that ran past 8 steps."""
    d = spatial.dist(here[:2], (vantage[0], vantage[1])) if here is not None else 0.0
    return max(int(budget["min_steps"]),
               int(math.ceil(budget["extra_steps"] + d * budget["steps_per_m"])))


def staged_verify(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
                  perception: Optional[Dict[str, Any]], prev: VerifyState,
                  standing: Optional[spatial.Target], mode: Optional[str],
                  last_called: Optional[int],
                  budget: Optional[Dict[str, float]] = None) -> Staged:
    """a20's target for this step, and whether the strategist must be asked.
    a22 (`budget`): the step limit scales with the distance back."""
    V = STAGE_PARAMS_A20
    step = int(manifest.get("step", 0))
    here = spatial.pose_xyh(manifest.get("pose"))
    st = VerifyState.from_dict(prev.to_dict())
    events: List[str] = []
    ev = evaluate(mem, here, perception, st, standing)
    sighted = ev["goal_sighted"]
    why: Optional[str] = None

    if st.stage == "explore" and sighted:
        st.stage, st.unproductive = "goal", 0
        standing, mode = None, None
        events.append("goal_sighted")
    elif st.stage == "goal" and not sighted:
        detour = (standing is not None and standing.kind not in ("goal", "verify")
                  and here is not None
                  and spatial.target_state(mem, standing, here[:2]) == "open"
                  and step - standing.step <= STAGE_PARAMS["detour_max_steps"])
        ray = _last_ray(mem, st.rays_since)
        if ray is None:
            _to_explore(st, step, "verify_unreachable", events)
            why = "verify_unreachable"
        elif not detour:
            st.stage, st.verify_since = "verify", step
            st.vantage = [ray.x, ray.y, ray.heading, ray.step]
            if budget is not None:
                st.verify_budget = verify_steps(budget, here, st.vantage)
            standing, mode = None, None
            events.append("goal_lost")
    elif st.stage == "verify":
        if sighted:
            ray = _last_ray(mem, st.rays_since)
            old = mem.goal_belief(since=st.rays_since, until=step - 1)
            if old is None or _moved(old, ray, st.vantage):
                st.rays_since = step
                events.append("reacquired_moved")
            else:
                events.append("reacquired")
            st.stage, st.vantage, st.verify_since = "goal", None, -1
            standing, mode = None, None
        elif here is not None:
            vx, vy, vh = st.vantage[:3]
            at = spatial.dist(here[:2], (vx, vy)) < V["vantage_reached_m"]
            # a27: a check look counts this far from the vantage. Turning to face
            # the seen bearing takes a 1.7 m move, which leaves a 1.5 m circle:
            # R13, 5 of 8 timeouts reached the vantage and never checked.
            near = (spatial.dist(here[:2], (vx, vy))
                    < (budget or {}).get("check_within_m", V["vantage_reached_m"]))
            if (step > st.verify_since and near
                    and abs(spatial.wrap(here[2] - vh)) <= V["check_within_deg"]):
                why = "verify_failed"
            elif step - st.verify_since > (st.verify_budget if st.verify_budget > 0
                                           else V["verify_max_steps"]):
                why = "verify_timeout"
            elif not at and mem.reachable((vx, vy), mem.reach(here[:2])) is None:
                why = "verify_unreachable"
            if why is not None:
                _to_explore(st, step, why, events)
    if "lost" in events:
        standing, mode, last_called = None, None, None

    if here is None:
        return Staged(st, standing, mode, None, [], ev, events)
    if st.stage == "goal":
        target, out_mode, ask = _goal_stage(mem, manifest, perception, st, standing, mode,
                                            here, step, sighted, events)
    elif st.stage == "verify":
        target, out_mode, ask = verify_target(st, here, step), "verify", None
    else:
        target, out_mode, ask = _explore_stage(mem, st, ev, standing, mode, here, step,
                                               last_called, events)
        if ask == "lost" and why is not None:
            ask = why
    return _finish(mem, st, target, out_mode, ask, here, step, ev, events)


# --- a63 (R30): the route planner ------------------------------------------------
#
# docs/research/pathfinder-plan.md. a49's planner asks one local question (is a
# forward move within 55 degrees of the goal open?) and hands a menu to q03 when
# it is not. In the s03 shut tine that read `open` on 78% of decisions (probe
# B0), because a goal behind the drone counts as open; every a17b s03
# final/dynamic failure stayed in the shut tine 34-46 steps (s03_tines_analysis).
# a63 searches a route over the memory's cost map (spatial.CostMap) every step
# and steers the drone at the next point on it. No strategist call. Unknown
# cells are passable at a cost, so there is always a route unless the drone is
# boxed in; then the perceiver's walls are softened, and failing that the
# nearest unsearched edge is the target. Parameters: agent.PATHFINDER_A63.


@dataclass
class PathPlan:
    """What the route planner decided this step: the target to steer at, the
    route it lies on, and the stall cells added this step (recorded, so the
    memory rebuilt from decisions.jsonl carries them)."""
    target: Optional[spatial.Target]
    waypoint: Optional[spatial.Point]
    path: List[Tuple[int, int]]
    path_m: Optional[float]
    unknown_on_path: int
    fallback: str
    stall: List[List[int]]
    costs: Dict[str, int]
    sealed: List[List[int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        out = {"way": "path", "path_m": self.path_m,
               "path_cells": [[c[0], c[1]] for c in self.path],
               "waypoint": ([round(self.waypoint[0], 2), round(self.waypoint[1], 2)]
                            if self.waypoint else None),
               "unknown_on_path": self.unknown_on_path, "fallback": self.fallback,
               "stall": self.stall, "costs": self.costs}
        if self.sealed:
            out["sealed"] = self.sealed
        return out


def astar(cm: spatial.CostMap, start: Tuple[int, int], goal: Tuple[int, int],
          max_nodes: int = 40000) -> Optional[List[Tuple[int, int]]]:
    """Cheapest 8-connected route from start to goal over the cost map, as a
    list of cells from start to goal, or None. The start and goal cells are
    always passable (the drone is on the one and the goal on the other)."""
    diag = math.sqrt(2.0)

    def h(c: Tuple[int, int]) -> float:
        return math.hypot(c[0] - goal[0], c[1] - goal[1])

    best: Dict[Tuple[int, int], float] = {start: 0.0}
    parent: Dict[Tuple[int, int], Tuple[int, int]] = {}
    todo = [(h(start), 0.0, start)]
    seen = 0
    while todo:
        _, g, c = heapq.heappop(todo)
        if g > best.get(c, math.inf):
            continue
        if c == goal:
            out = [c]
            while c in parent:
                c = parent[c]
                out.append(c)
            return out[::-1]
        seen += 1
        if seen > max_nodes:
            return None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                n = (c[0] + dx, c[1] + dy)
                if not cm.inside(n):
                    continue
                cost = 1.0 if n == goal else cm.cost(n)
                if cost is None:
                    continue
                step = (diag if dx and dy else 1.0) * cost
                if dx and dy:
                    # No cutting a corner between two impassable cells.
                    if cm.cost((c[0] + dx, c[1])) is None and cm.cost((c[0], c[1] + dy)) is None:
                        continue
                ng = g + step
                if ng < best.get(n, math.inf) - 1e-9:
                    best[n] = ng
                    parent[n] = c
                    heapq.heappush(todo, (ng + h(n), ng, n))
    return None


def _centre(c: Tuple[int, int]) -> spatial.Point:
    return (c[0] + 0.5) * spatial.CELL_M, (c[1] + 0.5) * spatial.CELL_M


def waypoint_on(cm: spatial.CostMap, here: spatial.Point, path: List[Tuple[int, int]],
                goal: spatial.Point, p: Dict[str, Any]) -> spatial.Point:
    """The farthest point on the route within lookahead_m that a straight
    flight from here reaches over passable cells, and at least min_m away
    unless the goal itself is nearer (string pulling, so the bearing near a
    door runs through the gap)."""
    look, near = float(p["lookahead_m"]), float(p.get("waypoint_min_m", 1.0))
    if spatial.dist(here, goal) <= look and cm.passable_segment(here, goal):
        return goal
    pick: Optional[spatial.Point] = None
    for c in path[1:]:
        q = _centre(c)
        if spatial.dist(here, q) > look:
            break
        if cm.passable_segment(here, q):
            pick = q
    if pick is None:
        pick = _centre(path[1]) if len(path) > 1 else goal
    if spatial.dist(here, pick) < near:
        # Too close to steer by: push along the same bearing to min_m.
        pick = spatial.ahead(here, spatial.bearing(here, pick), near)
    return pick


def stall_cells_from(records: List[Dict[str, Any]], step: int) -> List[Tuple[int, int]]:
    """Every stall cell and dead-end seal earlier planner records added
    (replayable from the record alone, as the memory is)."""
    out = []
    for r in records:
        if "step" in r and r["step"] < step:
            plan = r.get("planner") or {}
            for c in (plan.get("stall") or []) + (plan.get("sealed") or []):
                out.append((int(c[0]), int(c[1])))
    return out


def dead_end_seal(mem: spatial.SpatialMemory, here: spatial.Pose,
                  p: Dict[str, Any]) -> List[List[int]]:
    """a67: at a confirmed closed door within door_within_m, the corridor the
    trail came down is a dead end. Walk the trail back; at each point the
    cells out to lateral_cells either side that are not known ground are
    sealed, until a point where known ground reaches past open_lateral_m
    on a side (a junction, as the s03 crossbar), or max_back_m of trail.
    In an open room (the s02 hall at door B) the first point already opens
    sideways, so nothing is sealed. s03_tines_analysis: the fix is "back to
    the fork"; R26 tried it as a strategist's item and the stall hand-back
    ended it; this makes the map say it."""
    d = p.get("dead_end")
    if not d:
        return []
    near_door = any(spatial.dist(here[:2], ((c[0] + 0.5) * spatial.CELL_M,
                                              (c[1] + 0.5) * spatial.CELL_M)) <= d["door_within_m"]
                    for c in mem.door_wall)
    # a68: a closed door read from 3-8 m out counts too (at 1 m a door leaf
    # reads as plain wall); the point is kept at the strip's range estimate.
    if not near_door and d.get("closed_read_within_m"):
        near_door = any(spatial.dist(here[:2], (x, y)) <= d["closed_read_within_m"]
                        for x, y, _ in mem.closed_doors)
    if not near_door:
        return []
    strong = set(mem.visits) | (set(mem.free_near) if mem.cfg.near_free_m is not None
                                else set(mem.free))
    hardset = (set(mem.wall) | set(mem.near_wall) | set(mem.firm_wall) | set(mem.stop_wall)
               | set(mem.door_wall))
    trail = [(x, y) for _, x, y, _ in mem.trail]
    if len(trail) < 2:
        return []
    # One corridor axis for the walk: from the trail point axis_m back (by
    # path) to the newest point. a68: at the wall the trail zig-zags, and a
    # per-segment "sideways" there pointed along the corridor, so the walk
    # saw an opening at once and sealed nothing (a67 s03 dynamic replay).
    back = 0.0
    j = len(trail) - 1
    while j > 0 and back < d.get("axis_m", 8.0):
        back += spatial.dist(trail[j - 1], trail[j])
        j -= 1
    span = spatial.dist(trail[j], trail[-1])
    if span < 3.0:
        return []
    ux, uy = (trail[-1][0] - trail[j][0]) / span, (trail[-1][1] - trail[j][1]) / span
    nx, ny = -uy, ux
    L = d["lateral_cells"]

    def lateral(b: spatial.Point, side: float, k: int) -> Tuple[int, int]:
        return spatial.cell((b[0] + side * nx * k * spatial.CELL_M,
                             b[1] + side * ny * k * spatial.CELL_M))

    # The window: trail points back to the junction, the first point where
    # known ground reaches open_cells sideways (the crossbar's own trail from
    # a tine mouth; never inside a 3 m tine), or max_back_m of trail.
    window: List[spatial.Point] = []
    back = 0.0
    for i in range(len(trail) - 1, 0, -1):
        a, b = trail[i - 1], trail[i]
        seg = spatial.dist(a, b)
        if seg < 0.3:
            continue
        back += seg
        if back > d["max_back_m"]:
            break
        opening = any(all(lateral(b, side, k) in strong for k in range(1, d["open_cells"] + 1))
                      for side in (1.0, -1.0))
        if opening:
            break
        window.append(b)
    if not window:
        return []
    # a68: a side is a corridor wall when a seen wall lies within L cells of
    # any window point on that side (the side strips read the tine's walls
    # no_floor on the way in; the s02 hall at door B shows none): the gaps
    # on that side, cells that are not known ground, are sealed along the
    # whole window. Known floor alone cannot tell a 3 m corridor from a hall.
    # The seal runs seal_cells deep: a band the route could skirt for less
    # than the way back is no seal (a66 s03 dynamic replay: 4 deep, the
    # route went round the band's end through the solid, 21 m against 40).
    out: List[List[int]] = []
    deep = int(d.get("seal_cells", L))
    walled = {side: any(lateral(b, side, k) in hardset for b in window
                        for k in range(1, L + 1)) for side in (1.0, -1.0)}
    if not (walled[1.0] or walled[-1.0]):
        return []
    # A corridor walled on one seen side is walled on both: the far floor
    # the perceiver reads through the other side is the route's way round
    # otherwise (a66 s03 dynamic replay: the divider side showed no wall
    # within four cells and the route cut through it for 24 m). Sealed
    # cells yield to known floor seen later (spatial.CostMap).
    for side in (1.0, -1.0):
        for b in window:
            for k in range(1, deep + 1):
                c = lateral(b, side, k)
                if c not in strong and c not in hardset and [c[0], c[1]] not in out:
                    out.append([c[0], c[1]])
    return out


def _stalled(records: List[Dict[str, Any]], step: int, p: Dict[str, Any]) -> bool:
    """Whether the route has not shortened by stall_gain_m over the last
    stall_steps planner records, with no stall cells added in that window."""
    k = int(p["stall_steps"])
    rows = sorted((r for r in records if "step" in r and r["step"] < step
                   and (r.get("planner") or {}).get("path_m") is not None),
                  key=lambda r: r["step"])[-k:]
    if len(rows) < k or rows[-1]["step"] != step - 1:
        return False
    if any((r.get("planner") or {}).get("stall") for r in rows):
        return False
    gained = rows[0]["planner"]["path_m"] - rows[-1]["planner"]["path_m"]
    return gained < float(p["stall_gain_m"])


def _last_move(records: List[Dict[str, Any]], step: int) -> Optional[Tuple[float, bool]]:
    """(heading of the last chosen move, whether it was a turn-around)."""
    rows = sorted((r for r in records if "step" in r and r["step"] < step),
                  key=lambda r: r["step"])
    if not rows or rows[-1].get("index") is None:
        return None
    r = rows[-1]
    here = spatial.pose_xyh((r.get("manifest") or {}).get("pose"))
    chosen = next((a for a in (r.get("manifest") or {}).get("actions") or []
                   if a.get("index") == r["index"]), None)
    if here is None or chosen is None:
        return None
    return spatial.action_heading(chosen, here[2]), bool(chosen.get("turn_around"))


def pathfind(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
             records: List[Dict[str, Any]], goal: spatial.Point,
             p: Dict[str, Any]) -> PathPlan:
    """a63's target for this step: the next point on the cheapest route to the
    goal over the memory's cost map."""
    step = int(manifest.get("step", 0))
    here = spatial.pose_xyh(manifest.get("pose"))
    if here is None:
        return PathPlan(goal_target(goal, step), None, [], None, 0, "no_pose", [], {})
    stall = stall_cells_from(records, step)
    added: List[List[int]] = []
    if _stalled(records, step, p):
        last = _last_move(records, step)
        blocked = any(b.step == step - 1 for b in mem.blocks)
        if last is not None and not last[1] and not blocked:
            heading = last[0]
            for d in (spatial.CELL_M, 2.0 * spatial.CELL_M):
                q = spatial.ahead(here[:2], heading, d)
                for side in (None, heading + 90.0, heading - 90.0):
                    c = spatial.cell(q if side is None
                                     else spatial.ahead(q, side % 360.0, spatial.CELL_M))
                    if c not in mem.visits and c != spatial.cell(goal):
                        added.append([c[0], c[1]])
            stall = stall + [(c[0], c[1]) for c in added]
    sealed_now = [c for c in dead_end_seal(mem, here, p) if (c[0], c[1]) not in stall]
    stall = stall + [(c[0], c[1]) for c in sealed_now]
    start, end = spatial.cell(here[:2]), spatial.cell(goal)
    fallback = "none"
    cm = spatial.CostMap(mem, stall, p, include=(start, end), start=start)
    path = astar(cm, start, end)
    if path is None:
        fallback = "soft"
        cm = spatial.CostMap(mem, stall, p, soft=True, include=(start, end), start=start)
        path = astar(cm, start, end)
    if path is None:
        fallback = "frontier"
        fronts = mem.search_frontiers(here[:2])
        if fronts:
            fp = fronts[0][0]
            path = astar(cm, start, spatial.cell(fp)) or [start, spatial.cell(fp)]
            target_point = fp
        else:
            path = [start, end]
            target_point = goal
        wp = waypoint_on(cm, here[:2], path, target_point, p)
    else:
        wp = waypoint_on(cm, here[:2], path, goal, p)
    path_m = round(sum(spatial.dist(_centre(a), _centre(b)) for a, b in zip(path, path[1:])), 2)
    unknown = sum(1 for c in path[1:-1] if c not in cm.known)
    target = spatial.Target("path", "path", wp[0], wp[1], p["words"]["path"], step)
    return PathPlan(target, wp, path, path_m, unknown, fallback, added, cm.counts(), sealed_now)


def search_situation_a20(mem: spatial.SpatialMemory, manifest: Dict[str, Any],
                         state: VerifyState, menu: List[spatial.Target], ask: str,
                         goal: Optional[spatial.Point] = None) -> str:
    """a20's strategist text: a17's (search_situation) with the verify reasons.
    a21 (`goal`, the true position): also where the goal is, and each place
    worded with how much nearer the goal it lies (a16's wording)."""
    here = spatial.pose_xyh(manifest.get("pose"))
    step = int(manifest.get("step", 0))
    w = SITUATION_A17
    lines = [w["asked"].format(step=step, why=asked(ask))]
    if here is not None:
        b = (mem.goal_belief(since=state.rays_since) if state.stage in ("goal", "verify")
             else None)
        if b is None:
            lines.append(w["dropped"] if ask in ("lost",) + tuple(ASKED_A20) else w["unseen"])
        else:
            lines.append(w["seen"].format(step=b[2], where=spatial.where_words(here, b[:2])))
        if goal is not None:
            lines.append(spatial.WORDS_A14["goal_known"].format(
                where=spatial.where_words(here, goal)))
        blocked = sorted({spatial.relative_word(bl.heading - here[2]) for bl in mem.blocks
                          if spatial.dist(here[:2], (bl.x, bl.y)) < spatial.BLOCK_NEAR_M})
        if blocked:
            lines.append(w["blocked"].format(dirs=", ".join(blocked)))
    lines.append(w["menu"])
    for t in menu:
        if here is None:
            lines.append("  {0}: {1}".format(t.id, t.label))
        elif goal is not None:
            lines.append("  {0}: {1}; {2}".format(t.id, t.words(here), gain_words(here, t, goal)))
        else:
            lines.append("  {0}: {1}".format(t.id, t.words(here)))
    lines.append(w["explore"])
    return "\n".join(lines)
