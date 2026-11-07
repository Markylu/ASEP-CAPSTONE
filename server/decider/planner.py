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
    #: a72 (`commit`): whether this step kept the previous step's route, and
    #: the fresh route's length it was held against (None: no previous route
    #: to keep, or commitment off).
    kept: Optional[bool] = None
    fresh_m: Optional[float] = None
    #: a76 (`door_approach`): the remembered opening this step's waypoint was
    #: laid on, {label, phase, x, y}; None when the rule did not fire.
    door: Optional[Dict[str, Any]] = None
    #: a78 (`dead_end_latch`): the corridor latched as a dead end, carried on
    #: every step from the one it fired on: {step, origin, axis_deg, lane_m,
    #: half_width_m, ahead_m, reach_m, out}. None before it fires.
    latch: Optional[Dict[str, Any]] = None
    #: a80 (`survey`): the wall survey's state, carried on every step from the
    #: one it starts on (planner.wall_survey). None before it starts.
    survey: Optional[Dict[str, Any]] = None
    #: a90 (`way_in`): True while the drone is on its first way in: before
    #: step `steps`, no survey started, no latch, and never yet more than the
    #: survey's line_m off the direct line from the spawn to the goal (so a
    #: survey can still start). None for agents without the setting.
    way_in: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {"way": "path", "path_m": self.path_m,
               "path_cells": [[c[0], c[1]] for c in self.path],
               "waypoint": ([round(self.waypoint[0], 2), round(self.waypoint[1], 2)]
                            if self.waypoint else None),
               "unknown_on_path": self.unknown_on_path, "fallback": self.fallback,
               "stall": self.stall, "costs": self.costs}
        if self.sealed:
            out["sealed"] = self.sealed
        if self.kept is not None:
            out["kept"] = self.kept
            out["fresh_m"] = self.fresh_m
        if self.door is not None:
            out["door"] = self.door
        if self.latch is not None:
            out["latch"] = self.latch
        if self.survey is not None:
            out["survey"] = self.survey
        if self.way_in is not None:
            out["way_in"] = self.way_in
        return out


def path_cost(cm: spatial.CostMap, path: List[Tuple[int, int]]) -> Optional[float]:
    """What astar charges for this route on this map (the first cell is free,
    the last is the goal and always passable), or None if a cell is impassable."""
    total = 0.0
    for a, b in zip(path, path[1:]):
        c = 1.0 if b == path[-1] else cm.cost(b)
        if c is None:
            return None
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        total += (math.sqrt(2.0) if dx and dy else 1.0) * max(dx, dy, 1) * c
    return total


def _previous_route(records: List[Dict[str, Any]], step: int) -> Optional[List[Tuple[int, int]]]:
    """The route the previous step's planner record steered by, if that step
    is step - 1 and had a route of its own (fallback none)."""
    rows = sorted((r for r in records if "step" in r and r["step"] < step),
                  key=lambda r: r["step"])
    if not rows or rows[-1]["step"] != step - 1:
        return None
    plan = rows[-1].get("planner") or {}
    cells = plan.get("path_cells") or []
    if plan.get("fallback") != "none" or len(cells) < 2:
        return None
    return [(int(c[0]), int(c[1])) for c in cells]


def committed_route(cm: spatial.CostMap, start: Tuple[int, int], prev: List[Tuple[int, int]],
                    goal: Tuple[int, int], p: Dict[str, Any]) -> Optional[List[Tuple[int, int]]]:
    """a72: the previous route from where the drone now is, if the drone is
    still on or beside it (within leave_cells) and the rest of it is passable
    on this step's map; else None."""
    if prev[-1] != goal:
        return None
    # Where the drone is along the route: the nearest route cell (the later
    # one on a tie, so the drone is not sent back along it).
    best = None
    for i, c in enumerate(prev):
        d = math.hypot(c[0] - start[0], c[1] - start[1])
        if best is None or d <= best[0] + 1e-9:
            best = (d, i)
    i = best[1]
    if max(abs(prev[i][0] - start[0]), abs(prev[i][1] - start[1])) > int(p["leave_cells"]):
        return None
    rest = prev[i:] if prev[i] == start else [start] + prev[i + 1:]
    if len(rest) < 2:
        return None
    if prev[i] != start and not cm.passable_segment(_centre(start), _centre(rest[1])):
        return None
    return rest if path_cost(cm, rest) is not None else None


def astar(cm: spatial.CostMap, start: Tuple[int, int], goal: Tuple[int, int],
          max_nodes: int = 40000, strict_corners: bool = False) -> Optional[List[Tuple[int, int]]]:
    """Cheapest 8-connected route from start to goal over the cost map, as a
    list of cells from start to goal, or None. The start and goal cells are
    always passable (the drone is on the one and the goal on the other).
    `strict_corners` (a73): a diagonal move needs both cells it passes between
    passable, not one; a 1.7 m flight cannot thread a 0.85 m diagonal gap."""
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
                    # No cutting a corner between two impassable cells (a73
                    # strict_corners: past one impassable cell either).
                    side_a = cm.cost((c[0] + dx, c[1])) is None
                    side_b = cm.cost((c[0], c[1] + dy)) is None
                    if (side_a and side_b) or (strict_corners and (side_a or side_b)):
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
    # a69: a corridor is a window with a wall seen on each side somewhere
    # (the tine's side strips read no_floor on both sides on the way in):
    # then both sides are sealed seal_cells deep, because the far floor the
    # perceiver reads through a side is the route's way round otherwise
    # (a66 s03 dynamic replay: 24 m through the divider against 40). A
    # window walled on one side only is the s02 hall along the divider:
    # that side alone is sealed, one_side_cells deep (a68 s02a and s02vc
    # dynamic: sealing the hall boxed the drone, route on 53% of steps).
    # Sealed cells yield to known floor seen later (spatial.CostMap).
    both = walled[1.0] and walled[-1.0]
    for side in (1.0, -1.0):
        if not both and not walled[side]:
            continue
        depth = deep if both else int(d.get("one_side_cells", L))
        for b in window:
            for k in range(1, depth + 1):
                c = lateral(b, side, k)
                if c not in strong and c not in hardset and [c[0], c[1]] not in out:
                    out.append([c[0], c[1]])
    return out


# --- a78 (R38): the dead-end latch ----------------------------------------------
#
# s03 dynamic, 0/52 in Phase 2: the drone reads the tine's door closed and
# stays in the tine. a68's seal (dead_end_seal above) took it out in flight;
# it lost the cell to a seal that yielded to floor seen later (the drone flew
# back in) and lost s02 to a trigger that fired in the hall (a69: g05's reads
# cannot tell a corridor from a hall). The latch differs in three ways:
#   - the trigger is the dead-end confirmer's own answer (e01, asked on a
#     closed-door read in the centre three strips), twice in three asked steps;
#   - the corridor is the straight run of trail the drone had flown when the
#     confirmer said yes, not a walk over wall reads; it is shut as one
#     rectangle, whatever the perceiver painted inside it, except a lane back
#     along the run;
#   - it holds for the rest of the run, and once the drone is out past the
#     run's start the lane is shut too.
# The latch is carried in the planner record, so a memory and a route rebuilt
# from decisions.jsonl have it. eval/phase2/R38_dead_end_latch/README.md.


def latch_from(records: List[Dict[str, Any]], step: int) -> Optional[Dict[str, Any]]:
    """The latch the newest earlier planner record carries, or None."""
    best: Optional[Dict[str, Any]] = None
    at = -1
    for r in records:
        if "step" in r and at < r["step"] < step:
            latch = (r.get("planner") or {}).get("latch")
            if latch:
                best, at = latch, r["step"]
    return dict(best) if best else None


def latch_frame(latch: Dict[str, Any], at: spatial.Point) -> Tuple[float, float]:
    """(metres along the latched corridor from its mouth, metres left of its
    axis) for a point on the map."""
    rad = math.radians(float(latch["axis_deg"]))
    ux, uy = math.cos(rad), math.sin(rad)
    rx, ry = at[0] - float(latch["origin"][0]), at[1] - float(latch["origin"][1])
    return rx * ux + ry * uy, -rx * uy + ry * ux


def latch_cells(latch: Dict[str, Any]) -> List[Tuple[int, int]]:
    """The cells the latch shuts: the rectangle from the corridor's mouth to
    ahead_m beyond the farthest the drone has been down it (reach_m),
    half_width_m either side of its axis. While the drone is in it, the lane
    (lane_m either side of the axis, as far as the drone has been) is left
    open as the way back, so the only route is back down the lane; once the
    drone is out, nothing is left open."""
    rad = math.radians(float(latch["axis_deg"]))
    ux, uy = math.cos(rad), math.sin(rad)
    ox, oy = float(latch["origin"][0]), float(latch["origin"][1])
    reach, half = float(latch["reach_m"]), float(latch["half_width_m"])
    length = reach + float(latch["ahead_m"])
    corners = [(ox + a * ux - b * uy, oy + a * uy + b * ux)
               for a in (0.0, length) for b in (-half, half)]
    lo = spatial.cell((min(c[0] for c in corners), min(c[1] for c in corners)))
    hi = spatial.cell((max(c[0] for c in corners), max(c[1] for c in corners)))
    out = []
    for cx in range(lo[0], hi[0] + 1):
        for cy in range(lo[1], hi[1] + 1):
            along, left = latch_frame(latch, _centre((cx, cy)))
            if not (0.0 <= along <= length and abs(left) <= half):
                continue
            if (not latch.get("out") and along <= reach + spatial.CELL_M / 2.0
                    and abs(left) <= float(latch["lane_m"])):
                continue
            out.append((cx, cy))
    return out


def latch_yes_steps(reads: List[Tuple[int, str]], step: int, d: Dict[str, Any]) -> List[int]:
    """The steps of the yes answers that call a dead end at this step, or []:
    the dead-end confirmer [(step, "yes" or "no")] said yes on this step, and
    yes on `yes_reads` of its last `of_reads` answers, none of them older
    than `recent_steps`."""
    if not reads or tuple(reads[-1]) != (step, "yes"):
        return []
    recent = [r for r in reads[-int(d["of_reads"]):] if step - r[0] <= int(d["recent_steps"])]
    yes = [r[0] for r in recent if r[1] == "yes"]
    return yes if len(yes) >= int(d["yes_reads"]) else []


def latch_reads_agree(reads: List[Tuple[int, str]], step: int, d: Dict[str, Any]) -> bool:
    return bool(latch_yes_steps(reads, step, d))


def straight_run(trail: List[Tuple[int, float, float, float]], upto: int,
                 d: Dict[str, Any]) -> Optional[Tuple[spatial.Point, int, float, float]]:
    """The straight run of trail that ends at step `upto`: (where it began,
    the step it began at, its axis in degrees, its length in metres), or None
    when it is shorter
    than min_run_m. Segments within off_axis_deg of the axis, at most
    max_back_m. The axis is first taken over the last axis_m of trail (two
    moves), then over the run that axis finds, until the run stops changing:
    one long window (a68's 8 m) reaches back round the corner the corridor was
    turned into from and skews the axis of a run shorter than it."""
    pts: List[spatial.Point] = []
    steps: List[int] = []
    for step, x, y, _ in trail:
        if step > upto:
            break
        if not pts or spatial.dist(pts[-1], (x, y)) >= 0.3:
            pts.append((x, y))
            steps.append(step)
    if len(pts) < 2:
        return None
    j, back = len(pts) - 1, 0.0
    while j > 0 and back < float(d["axis_m"]):
        back += spatial.dist(pts[j - 1], pts[j])
        j -= 1
    i, run, axis = j, 0.0, 0.0
    for _ in range(4):
        if spatial.dist(pts[j], pts[-1]) < 1e-6:
            return None
        axis = spatial.bearing(pts[j], pts[-1])
        i, run = len(pts) - 1, 0.0
        while (i > 0 and run < float(d["max_back_m"])
               and abs(spatial.wrap(spatial.bearing(pts[i - 1], pts[i]) - axis))
               <= float(d["off_axis_deg"])):
            run += spatial.dist(pts[i - 1], pts[i])
            i -= 1
        if i == j or i == len(pts) - 1:
            break
        j = i
    if run < float(d["min_run_m"]):
        return None
    return pts[i], steps[i], axis, run


def _turned_into(trail: List[Tuple[int, float, float, float]], began: spatial.Point,
                 since: int, axis: float, off_axis_deg: float) -> bool:
    """Whether the straight run that began at `began` (step `since`) was turned
    into: the last move of 0.3 m or more before it ran more than off_axis_deg
    off the run's axis. False for a run that reaches back to the spawn."""
    for s, x, y, _ in reversed(trail):
        if s < since and spatial.dist((x, y), began) >= 0.3:
            return abs(spatial.wrap(spatial.bearing((x, y), began) - axis)) > off_axis_deg
    return False


def _from_line(trail: List[Tuple[int, float, float, float]], upto: int,
               goal: spatial.Point, d: Dict[str, Any], c: Dict[str, Any]
               ) -> Optional[Tuple[spatial.Point, int, float, float]]:
    """a94: the corridor a drone flew into without a turn, as the trail tells
    it: (where it left the direct line from the spawn to the goal, the step it
    left it at, the bearing from there to where it is now, the metres), or
    None. A straight run that reaches back to the spawn is not a corridor
    turned into (its mouth would be the spawn), but a drone that drifted from
    the stem into a tine within off_axis_deg of its line made no turn either,
    and the straight run found reaches the spawn until the drone turns about
    (R54 s03 final seed 1: closed reads from step 13, latch at 35; R49 s03
    final seed 2: 17 and 44). Where the trail was last within off_line_m of
    the direct line is the mouth, the line's bearing the axis; the drone must
    now be more than off_line_m off it, min_run_m or more from there."""
    pts = [(s, x, y) for s, x, y, _ in trail if s <= upto]
    if len(pts) < 2:
        return None
    line = {"origin": trail[0][1:3], "axis_deg": spatial.bearing(trail[0][1:3], goal)}
    here = pts[-1]
    if abs(latch_frame(line, here[1:3])[1]) <= float(c["off_line_m"]):
        return None
    left = None
    for i, (s, x, y) in enumerate(pts[:-1]):
        if abs(latch_frame(line, (x, y))[1]) <= float(c["off_line_m"]):
            left = i
    if left is None:
        return None
    # The mouth is the first point beyond the line's band, not the last within
    # it: measured from a point on the line the lane's span takes in the
    # diagonal the drone drifted in on (R56 shakedown s03 final seed 1: 4.1 m,
    # read at 13, latched at 31).
    began = pts[left + 1]
    run = spatial.dist(began[1:3], here[1:3])
    if run < float(d["min_run_m"]):
        return None
    # The axis is the direct line's: a corridor drifted into without a turn
    # runs the way the drone was going (the bearing from the mouth to the
    # drone swings as it turns about at the door, and the lane's span with it).
    return (began[1], began[2]), began[0], float(line["axis_deg"]), run


def confined_run(trail: List[Tuple[int, float, float, float]], closed: List[int],
                 here: spatial.Pose, step: int, d: Dict[str, Any],
                 goal: Optional[spatial.Point] = None
                 ) -> Optional[Tuple[spatial.Point, int, float, float]]:
    """a79: the straight run of trail the drone has been confined to, as
    straight_run gives it (where it began, the step it began at, its axis, its
    length), or None. The trigger of the dead-end latch, from the trail alone.

    A corridor confines the drone and a hall does not. A run qualifies when
    every position since it began lies within half_m of its axis and no more
    than back_m behind where it began (the drone never left the lane, however
    often it turned about in it); in the last dwell_steps it has got no more
    than advance_m farther down the lane than it had been before them (it is
    not still flying down it); and a closed door was read in the centre three
    strips (`closed`, the steps) on `reads` steps since the run began, with the
    drone looking along the run (within facing_deg of its axis: the door is at
    the lane's end, not beside it). The drone has never stood beside the lane
    (between half_m and beside_m off its axis, from mouth_m down the run to
    ahead_m beyond the farthest it has been): a corridor has walls there. The
    run must begin at a turn (the move
    before it more than off_axis_deg off its axis): a run that reaches back to
    the spawn is not a corridor the drone turned into, its mouth is where the
    flight started and there is nothing behind it to go back to. The longest
    qualifying run ending at any step from look_back_steps before the first
    closed read to now is the corridor.

    Round F, R32P and R35 (eval/probes/confined_trigger.py): in the shut s03
    tine the drone stays within about a metre of its line for 30-40 steps; at
    the s02 divider it leaves the line of its approach within a few steps."""
    c = d.get("confined")
    if not c or not closed:
        return None
    half, back = float(c["half_m"]), float(c["back_m"])
    head: Dict[int, float] = {s: h for s, _, _, h in trail}
    best: Optional[Tuple[spatial.Point, int, float, float]] = None
    tried = set()
    cands: List[Tuple[Tuple[spatial.Point, int, float, float], bool]] = []
    for upto in range(max(0, min(closed) - int(d["look_back_steps"])), step + 1):
        found = straight_run(trail, upto, d)
        if found is None:
            continue
        if not _turned_into(trail, found[0], found[1], found[2], float(d["off_axis_deg"])):
            continue  # the run from the spawn, or one cut short by max_back_m
        cands.append((found, False))
    if c.get("from_line") and goal is not None:
        # a94: the corridor the drone drifted into without a turn, its mouth
        # where the trail left the direct line (_from_line).
        found = _from_line(trail, step, goal, d, c)
        if found is not None:
            cands.append((found, True))
    for found, from_line in cands:
        began, since, axis, run = found
        if c.get("off_line_m") and goal is not None and trail and not from_line:
            # a86: a lane along the direct line from the spawn to the goal is
            # the drone's way in, not a corridor it turned into, however it
            # wobbled on it (R44 s02va dynamic seed 2: a sidestep at x = 10 on
            # the way to the shut door made the rest of the approach a "run
            # turned into", and the latch shut the hall in front of the door).
            direct = spatial.bearing(trail[0][1:3], goal)
            line = {"origin": trail[0][1:3], "axis_deg": direct}
            if (abs(spatial.wrap(axis - direct)) <= float(d["off_axis_deg"])
                    and abs(latch_frame(line, began)[1]) < float(c["off_line_m"])):
                continue
        key = (since, round(axis, 1))
        if key in tried:
            if best is not None and best[1] == since and run > best[3]:
                best = found
            continue
        tried.add(key)
        frame = {"origin": began, "axis_deg": axis}
        inside = True
        before = now = None  # farthest down the lane: dwell_steps ago, and to date
        lo = hi = 0.0        # a84 (span_m): how far either side of the axis it has been
        span = c.get("span_m")
        if from_line and c.get("from_line_span_m") is not None:
            # a94: measured off the direct line's bearing, not the run's own
            # axis, the lane is the corridor's full width (the 3 m s03 tine:
            # R56 shakedown s03 final seed 1 stood 2.9 m across it).
            span = c["from_line_span_m"]
        for s, x, y, _ in trail:
            if s < since:
                continue
            along, left = latch_frame(frame, (x, y))
            lo, hi = min(lo, left), max(hi, left)
            # a84: the lane is span_m wide wherever the run's axis lies in it
            # (R39 and R43's shakedown: a run flown along one wall of the 3 m
            # tine has its axis there, and the drone turning about by the
            # other wall stood 1.5-2.3 m off it); a79: half_m either side.
            off = (hi - lo > float(span)) if span else (abs(left) > half)
            if along < -back or off:
                inside = False
                break
            now = along if now is None else max(now, along)
            if s <= step - int(c["dwell_steps"]):
                before = along if before is None else max(before, along)
        if not inside or before is None or now - before > float(c["advance_m"]):
            continue  # left the lane, or still getting farther down it
        # A corridor has walls. Ground the drone has stood on beside the lane
        # says there is none there.
        wide = float(c["beside_m"])
        mid, reach = ((lo + hi) / 2.0, float(span) / 2.0) if span else (0.0, half)
        beside = False
        for s, x, y, _ in trail:
            if from_line and s < since:
                continue  # a94: the way in along the line lies behind this mouth
            along, left = latch_frame(frame, (x, y))
            if (float(d["mouth_m"]) <= along <= now + float(d["ahead_m"])
                    and reach < abs(left - mid) <= wide):
                beside = True
                break
        if beside:
            continue
        facing = [s for s in closed if s >= since and s in head
                  and abs(spatial.wrap(head[s] - axis)) <= float(c["facing_deg"])]
        if len(facing) < int(c["reads"]):
            continue
        if best is None or run >= best[3]:
            best = found
    return best


def dead_end_latch(mem: spatial.SpatialMemory, here: spatial.Pose, step: int,
                   p: Dict[str, Any], goal: Optional[spatial.Point] = None
                   ) -> Optional[Dict[str, Any]]:
    """a78: the latch this step fires, or None. Fires when the dead-end
    confirmer's answers agree (latch_yes_steps) and the trail holds a straight
    run of at least min_run_m whose lane the drone is still in.

    The corridor is the longest such run ending at any step from look_back_steps
    before the first agreeing yes to now. The confirmer is asked only on a
    closed-door read, and in the shut tine those come late and steps apart: by
    then the drone has turned about at the door, and the run that brought it
    down the tine ended up to 12 steps before the first yes (Round F s03
    dynamic: seed 1 yes at 20 and 25, run ended at 20; seed 2 first yes at 29,
    run ended at 17; seed 5 yes at 23 and 35, run ended at 18). A run the drone
    is no longer in the lane of (the stem, flown before the tine and longer
    than it) is not the corridor. It starts mouth_m down the run."""
    d = p.get("dead_end_latch")
    if not d:
        return None
    if d.get("confined"):
        # a79: the trail is the trigger (confined_run); no confirmer.
        found = confined_run(mem.trail, mem.closed_reads, here, step, d, goal)
        if found is None:
            return None
        began, since, axis, _ = found
        origin = spatial.ahead(began, axis, float(d["mouth_m"]))
        latch = {
            "step": step, "origin": [round(origin[0], 2), round(origin[1], 2)],
            "axis_deg": round(axis, 1), "lane_m": float(d["lane_m"]),
            "half_width_m": round(int(d["seal_cells"]) * spatial.CELL_M, 2),
            "ahead_m": float(d["ahead_m"]), "reach_m": 0.0, "out": False}
        if latch_frame(latch, here[:2])[0] <= 0.0:
            return None  # the drone is at the lane's mouth: nothing to shut behind it
        inside = [latch_frame(latch, (x, y)) for s, x, y, _ in mem.trail if s >= since]
        latch["reach_m"] = round(max(a for a, _ in inside), 2)
        if d.get("exit"):
            # a82: the middle of where the drone has flown in the corridor,
            # metres left of the run's axis (a run flown along one wall has
            # its axis there; the way out is down the corridor's middle).
            lefts = sorted(l for a, l in inside if a >= 0.0)
            latch["mid_m"] = round(lefts[len(lefts) // 2], 2) if lefts else 0.0
        return latch
    yes = latch_yes_steps(mem.dead_end_reads, step, d)
    if not yes:
        return None
    best: Optional[Tuple[float, Dict[str, Any], int]] = None
    for upto in range(max(0, min(yes) - int(d["look_back_steps"])), step + 1):
        found = straight_run(mem.trail, upto, d)
        if found is None:
            continue
        began, since, axis, run = found
        origin = spatial.ahead(began, axis, float(d["mouth_m"]))
        latch: Dict[str, Any] = {
            "step": step, "origin": [round(origin[0], 2), round(origin[1], 2)],
            "axis_deg": round(axis, 1), "lane_m": float(d["lane_m"]),
            "half_width_m": round(int(d["seal_cells"]) * spatial.CELL_M, 2),
            "ahead_m": float(d["ahead_m"]), "reach_m": 0.0, "out": False}
        along, left = latch_frame(latch, here[:2])
        if along <= 0.0 or abs(left) > float(d["lane_m"]) + spatial.CELL_M:
            continue  # the drone is not in this run's corridor
        if best is None or run >= best[0]:
            best = (run, latch, since)
    if best is None:
        return None
    _, latch, since = best
    latch["reach_m"] = round(max(latch_frame(latch, (x, y))[0]
                                 for s, x, y, _ in mem.trail if s >= since), 2)
    return latch


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


def _door_steps(records: List[Dict[str, Any]], step: int, look: bool = False) -> Dict[str, int]:
    """Steps earlier planner records spent approaching each opening, by label
    (`look`: the steps spent turning to look at it instead)."""
    out: Dict[str, int] = {}
    for r in records:
        if "step" in r and r["step"] < step:
            door = (r.get("planner") or {}).get("door") or {}
            label = door.get("label")
            if label and (door.get("phase") == "look") == look:
                out[label] = out.get(label, 0) + 1
    return out


def _route_gap(at: spatial.Point, pts: List[spatial.Point]) -> Optional[Tuple[float, int]]:
    """Metres from `at` to the route, and the index of the nearest segment."""
    near = None
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        vx, vy = b[0] - a[0], b[1] - a[1]
        n2 = vx * vx + vy * vy
        t = max(0.0, min(1.0, ((at[0] - a[0]) * vx + (at[1] - a[1]) * vy) / n2)) if n2 > 1e-9 else 0.0
        gap = spatial.dist(at, (a[0] + t * vx, a[1] + t * vy))
        if near is None or gap < near[0]:
            near = (gap, i)
    return near


def door_look(mem: spatial.SpatialMemory, here: spatial.Pose, path: List[Tuple[int, int]],
              records: List[Dict[str, Any]], step: int,
              p: Dict[str, Any]) -> Optional[Tuple[spatial.Point, Dict[str, Any]]]:
    """a77: the waypoint that turns the drone to face a doorway known from weak
    reads only (never read on a square look), so the next frame holds it in the
    centre strip; None when none qualifies. `budget_steps` looks per doorway."""
    spent = _door_steps(records, step, look=True)
    pts = [_centre(c) for c in path]
    best = None
    for o in mem.openings:
        if o.passed or o.closed or o.dead or o.strong or o.seen < int(p["min_seen"]):
            continue
        if spent.get(o.label, 0) >= int(p["budget_steps"]):
            continue
        at = (o.x, o.y)
        d = spatial.dist(here[:2], at)
        if not float(p["min_m"]) <= d <= float(p["range_m"]):
            continue
        near = _route_gap(at, pts)
        if near is None or near[0] > float(p["route_m"]):
            continue
        if best is None or d < best[0]:
            best = (d, o)
    if best is None:
        return None
    o = best[1]
    return (o.x, o.y), {"label": o.label, "phase": "look", "x": round(o.x, 2), "y": round(o.y, 2)}


def door_approach(mem: spatial.SpatialMemory, cm: spatial.CostMap, here: spatial.Pose,
                  path: List[Tuple[int, int]], records: List[Dict[str, Any]], step: int,
                  p: Dict[str, Any]) -> Optional[Tuple[spatial.Point, Dict[str, Any]]]:
    """a76: the waypoint that squares the drone up on a remembered open doorway
    the route runs past, and its record; None when no doorway qualifies.

    Round F, R32P and R35 (s02 change arms, near side): within 4 m of the
    true open door the drone stood more than 30
    degrees off the door's line on 309 of 381 steps, the door was in view on
    162 and the route's waypoint pointed at it on 102. The doorway's line is
    taken from the route itself (its direction where it passes the doorway:
    the map holds no wall there to fit, the wall is painted as floor). Off
    the line the waypoint is `pre_m` out on it; on the line (within `align_m`)
    it is `through_m` beyond the doorway. A doorway gets `budget_steps` steps
    over the run (most remembered doorways are phantoms: a square look from
    `pre_m` closes one)."""
    if len(path) < 2:
        return None
    spent = _door_steps(records, step)
    pts = [_centre(c) for c in path]
    best = None
    for o in mem.openings:
        if o.passed or o.closed or o.dead or o.seen < int(p["min_seen"]):
            continue
        if p.get("strong_only") and not o.strong:
            continue
        if spent.get(o.label, 0) >= int(p["budget_steps"]):
            continue
        at = (o.x, o.y)
        d = spatial.dist(here[:2], at)
        if d > float(p["range_m"]):
            continue
        # Nearest point of the route to the doorway, and the route's direction there.
        near = _route_gap(at, pts)
        if near is None or near[0] > float(p["route_m"]):
            continue
        if best is None or d < best[0]:
            best = (d, o, near[1])
    if best is None:
        return None
    _, o, i = best
    span = int(p["tangent_cells"])
    a, b = pts[max(0, i - span)], pts[min(len(pts) - 1, i + 1 + span)]
    length = spatial.dist(a, b)
    if length < 1e-6:
        return None
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length   # the way through
    rx, ry = here[0] - o.x, here[1] - o.y
    along = -(rx * ux + ry * uy)        # metres still to go to the doorway's plane
    lateral = abs(rx * uy - ry * ux)    # metres off the doorway's line
    if along <= 0.0:
        return None  # already beyond it
    pre = (o.x - float(p["pre_m"]) * ux, o.y - float(p["pre_m"]) * uy)
    through = (o.x + float(p["through_m"]) * ux, o.y + float(p["through_m"]) * uy)
    if lateral <= float(p["align_m"]) or spatial.dist(here[:2], pre) < float(p["pre_reached_m"]):
        phase, wp = "through", through
    else:
        phase, wp = "line_up", pre
        if cm.cost(spatial.cell(pre)) is None:
            return None  # the line-up point is walled on the map
    return wp, {"label": o.label, "phase": phase, "x": round(o.x, 2), "y": round(o.y, 2),
                "along_m": round(along, 2), "lateral_m": round(lateral, 2)}


# --- a80 (R40): the wall survey -------------------------------------------------
#
# docs/research/round-f-analysis.md §9: at 2-9 m a look within 20 degrees of
# square read the open door on 157 of 158 looks and a blank wall strip as open
# on 1 of 366; within 20-40 degrees, 36 of 41 and 17 of 939; beyond 60 degrees,
# 112 of 231 and 76 of 393. a66 meets the s02 divider at a closed door, then
# flies along it: the open door was in view within 20 degrees of square at
# 2-6 m on 58 of 4256 near-side frames. The survey takes the square looks the
# route never takes. When a closed door is read dead ahead on the drone's
# first way in along the direct line from the spawn to the goal, the drone
# steps `stations_m` to the side of that line, turns back to the line's
# bearing and flies at the wall:
# every frame on the way in is a look square to it. An open doorway read on
# such a look takes the waypoint through the wall along that strip's ray. At
# the wall with no door, it goes `standoff_m` back and to the other side, and
# flies in again. Everything is the agent's own: its trail, its perceiver's
# reads after the door confirmer, its bumps. The perceiver's floor classes do
# not give the wall's range (Round F: a closed door "2.5 m ahead" read from
# 16 m, every strip blocked read from 13 m), so the wall is where the drone
# is stopped by it. Parameters: agent.SURVEY_A80.


def survey_from(records: List[Dict[str, Any]], step: int) -> Optional[Dict[str, Any]]:
    """The survey state the newest earlier planner record carries, or None."""
    best: Optional[Dict[str, Any]] = None
    at = -1
    for r in records:
        if "step" in r and at < r["step"] < step:
            sv = (r.get("planner") or {}).get("survey")
            if sv:
                best, at = sv, r["step"]
    return dict(best) if best else None


def survey_frame(sv: Dict[str, Any], at: spatial.Point) -> Tuple[float, float]:
    """(metres toward the wall from where the survey began, metres left of the
    approach axis) for a point on the map."""
    return latch_frame({"origin": sv["at"], "axis_deg": sv["axis_deg"]}, at)


def survey_point(sv: Dict[str, Any], along: float, left: float) -> spatial.Point:
    rad = math.radians(float(sv["axis_deg"]))
    ux, uy = math.cos(rad), math.sin(rad)
    return (float(sv["at"][0]) + along * ux - left * uy,
            float(sv["at"][1]) + along * uy + left * ux)


def survey_station(sv: Dict[str, Any], c: Dict[str, Any]) -> Optional[spatial.Point]:
    """The station the survey is on: the current offset to the side of the
    approach axis, `back_m` behind where the survey began while the wall's
    range is unknown, `standoff_m` back from the wall once the drone has met
    it. None when no station is left."""
    if int(sv["i"]) >= len(sv["order"]):
        return None
    if sv.get("wall") is not None:
        along = float(sv["wall"]) - float(c["standoff_m"])
    elif c.get("fwd_m") is not None:
        # a97: the wall's range unknown, the stations lie fwd_m toward it, not
        # level with where the survey began (R49, R54, R55 s02c final: the
        # first station, 90 degrees to the side, was given up at step 8 in 5
        # of 12 runs, the navigator flying on at the shut door with the tag
        # on sharp left; a station ahead and to the side is one turn away).
        along = float(c["fwd_m"])
    else:
        along = -float(c["back_m"])
    return survey_point(sv, along, float(sv["order"][int(sv["i"])]))


def _centre_floor_before(records: List[Dict[str, Any]], step: int) -> Optional[str]:
    """The floor class the perceiver gave the centre strip on step - 1."""
    for r in records:
        if r.get("step") == step - 1:
            for lane in ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []:
                if lane.get("strip") == "centre":
                    return lane.get("floor")
    return None


def at_wall(mem: spatial.SpatialMemory, records: List[Dict[str, Any]], step: int) -> bool:
    """Whether the drone has met a wall on this step: its last move was stopped
    short, or every strip reads blocked_near now and the step before did not
    read far floor down the centre (Round F read every strip blocked on frames
    5-17 m from any wall, one step after reading 6 m of floor ahead)."""
    if any(b.step == step - 1 for b in mem.blocks):
        return True
    return bool(mem.nose_on and mem.nose_on[-1] == step
                and _centre_floor_before(records, step) in ("open_near", "blocked_near"))


def survey_start(mem: spatial.SpatialMemory, cm: spatial.CostMap, here: spatial.Pose,
                 step: int, goal: spatial.Point, records: List[Dict[str, Any]],
                 c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The survey this step starts, or None. The wall to survey is one across
    the direct line from the spawn to the goal: the approach axis is that
    line's bearing. Starts when a closed door is read in the centre strip on
    this step (after the door confirmer); the drone is heading within
    goal_deg of the axis and has come run_m or more along it; it has never
    been more than line_m off the direct line (it is still on its first way
    in: a corridor turned into lies off it, and a closed door at its end is
    a79's dead end, not a wall to survey); and a station can be flown to over
    passable cells."""
    if not mem.centre_closed or mem.centre_closed[-1] != step or not mem.trail:
        return None
    spawn = mem.trail[0][1:3]
    axis = spatial.bearing(spawn, goal)
    if abs(spatial.wrap(here[2] - axis)) > float(c["goal_deg"]):
        return None
    sv: Dict[str, Any] = {"step": step, "at": [round(here[0], 2), round(here[1], 2)],
                          "axis_deg": round(axis, 1), "wall": None,
                          "order": [], "i": 0, "phase": "transit", "since": step,
                          "best": None, "rays": [], "looks": 0}
    line = {"origin": spawn, "axis_deg": axis}
    if latch_frame(line, here[:2])[0] < float(c["run_m"]):
        return None
    if c.get("line_now"):
        # a95: the drone is on the direct line now (R53, R54 and R55 s02vc final
        # seed 3, R55 s02va dynamic seed 1: a turn-about at the spawn took the
        # drone 4 m off the line, and the test over the whole trail never
        # passed again, the shut door read square from the line at steps 9
        # to 14 or not).
        if abs(latch_frame(line, here[:2])[1]) > float(c["line_m"]):
            return None
    elif any(abs(latch_frame(line, (x, y))[1]) > float(c["line_m"]) for _, x, y, _ in mem.trail):
        return None
    if at_wall(mem, records, step):
        sv["wall"] = float(c["wall_m"])     # already stopped by it: its range is known
    # The side a remembered open doorway lies on goes first; else the left.
    side = 1.0
    live = [o for o in mem.openings if not (o.passed or o.closed or o.dead)]
    if live:
        far = max((survey_frame(sv, (o.x, o.y))[1] for o in live), key=abs)
        if abs(far) >= float(c["side_min_m"]):
            side = 1.0 if far > 0 else -1.0
    sv["order"] = [side * float(c["stations_m"]), -side * float(c["stations_m"])]

    def shut(at: spatial.Point) -> bool:
        if c.get("station_guard") == "hard":
            # a87: only a wall the drone has met stands between it and a
            # station: one it was stopped by, one seen nose-on, a shut door's.
            # R44: in five of six s02 runs looked at, one cell sealed beside a
            # wall the perceiver had read through open floor lay on the line
            # to the station on the open door's side, and the survey went to
            # the other side alone.
            met = set(mem.stop_wall) | set(mem.firm_wall) | set(mem.door_wall)
            n = max(1, int(math.ceil(spatial.dist(here[:2], at) / (spatial.CELL_M / 4.0))))
            return any(spatial.cell((here[0] + (at[0] - here[0]) * i / n,
                                     here[1] + (at[1] - here[1]) * i / n)) in met
                       for i in range(1, n + 1))
        return cm.cost(spatial.cell(at)) is None or not cm.passable_segment(here[:2], at)

    first = survey_station(sv, c)
    if shut(first):
        sv["order"] = sv["order"][1:]
        first = survey_station(sv, c)
        if shut(first):
            return None
    return sv


def _survey_next(sv: Dict[str, Any], step: int) -> None:
    sv.update(i=int(sv["i"]) + 1, phase="transit", since=step, best=None, rays=[])
    sv.pop("again", None)


def survey_rays_cross(sv: Dict[str, Any], c: Dict[str, Any]) -> bool:
    """Whether the survey's kept rays differ enough in bearing to be crossed
    (the least-squares system's determinant over cross_det)."""
    rays = sv.get("rays") or []
    a11 = a12 = a22 = 0.0
    for _, _, rh in rays:
        dx, dy = math.cos(math.radians(rh)), math.sin(math.radians(rh))
        a11 += 1.0 - dx * dx; a12 += -dx * dy; a22 += 1.0 - dy * dy
    return len(rays) >= 2 and a11 * a22 - a12 * a12 > float(c["cross_det"])


def survey_door_line(sv: Dict[str, Any], c: Dict[str, Any],
                     been: Optional[float] = None) -> Optional[float]:
    """Metres left of the approach axis of the doorway the survey's open reads
    point at (sv["rays"]: [x, y, heading] of each, newest last), or None.
    With the wall's range known, where the newest ray meets the wall. Else
    where the rays cross (least squares over the last `rays_kept`), when they
    are not near parallel; else the newest ray taken `reach_ray_m` out (a81,
    `been`: and no nearer than a metre beyond the farthest the drone has been
    toward the wall, which it had not met there)."""
    rays = sv.get("rays") or []
    if not rays:
        return None
    x, y, heading = rays[-1]
    along, left = survey_frame(sv, (x, y))
    off = math.radians(spatial.wrap(heading - float(sv["axis_deg"])))
    if sv.get("wall") is not None:
        return left + math.tan(off) * max(float(sv["wall"]) - along, 0.0)
    a11 = a12 = a22 = b1 = b2 = 0.0
    for rx, ry, rh in rays:
        dx, dy = math.cos(math.radians(rh)), math.sin(math.radians(rh))
        m11, m12, m22 = 1.0 - dx * dx, -dx * dy, 1.0 - dy * dy
        a11 += m11; a12 += m12; a22 += m22
        b1 += m11 * rx + m12 * ry
        b2 += m12 * rx + m22 * ry
    det = a11 * a22 - a12 * a12
    if len(rays) >= 2 and det > float(c["cross_det"]) and not c.get("no_cross"):
        px, py = (a22 * b1 - a12 * b2) / det, (a11 * b2 - a12 * b1) / det
        ahead_m, at_left = survey_frame(sv, (px, py))
        if ahead_m > along:                      # the crossing lies ahead of the drone
            return at_left
    out = float(c["reach_ray_m"])
    if been is not None:
        out = max(out, been + 1.0 - along)
    return left + math.tan(off) * out


def wall_survey(mem: spatial.SpatialMemory, cm: spatial.CostMap, here: spatial.Pose,
                step: int, goal: spatial.Point, records: List[Dict[str, Any]],
                p: Dict[str, Any]) -> Tuple[Optional[spatial.Point], Optional[Dict[str, Any]]]:
    """a80: (the waypoint the survey sets this step or None, the survey's state
    to carry or None).

    transit   fly to the station; a station not come half a metre nearer in
              stall_steps is given up.
    look      at the station, the waypoint is face_m ahead along the approach
              axis: the drone turns to the wall and flies at it, and every
              frame taken with the heading within square_deg of the axis is a
              square look. It ends at the wall (at_wall: the wall's range is
              then known, one cell ahead) or after look_steps.
    through   an open doorway read (after the door confirmer) on any step of
              the survey short of the wall, on a strip whose ray lies within
              open_deg of the approach axis, is kept as a ray. The doorway's
              line (survey_door_line: where the rays cross, or meet a wall
              whose range is known) runs along the approach axis, and the
              waypoint is carrot_m ahead of the drone on it. Done when the
              drone is beyond the wall, or through_steps after the last such
              read; given up (on to the next station) when a move is stopped
              short and no doorway is read from where it stopped (a jamb
              clipped leaves the door in view; a phantom does not read open
              twice).
    check     (a81) a move stopped short in the through phase with no doorway
              read: the route has the waypoint for check_steps; check_m
              farther toward the wall, the drone is through and the survey is
              done; else a phantom, on to the next station.
    The survey is done when the stations are, or after budget_steps."""
    c = p.get("survey")
    if not c:
        return None, None
    sv = survey_from(records, step)
    if sv is None:
        sv = survey_start(mem, cm, here, step, goal, records, c)
        if sv is None:
            return None, None
    if sv["phase"] == "done":
        return None, sv
    if step - int(sv["step"]) >= int(c["budget_steps"]):
        sv["phase"] = "done"
        return None, sv
    axis = float(sv["axis_deg"])
    along, _ = survey_frame(sv, here[:2])
    wall = sv.get("wall")
    short = wall is None or along < float(wall) - 0.5
    cone = float(c["open_deg"])
    if c.get("through_deg") and sv["phase"] in ("through", "check"):
        # a85: once a doorway has been read near square and is being flown at,
        # its later reads count out to through_deg: the drone closes on it at
        # an angle, and the reads say which side of the aim it lies (R44
        # shakedown s02vc final: read 21 degrees off the axis at step 8, then
        # 42-58 degrees off at steps 9-11, dropped, and the aim stayed 1.5 m
        # short of the jamb).
        cone = float(c["through_deg"])
    rays = [r for r in mem.door_rays if r.step == step
            and abs(spatial.wrap(r.heading - axis)) <= cone] if short else []
    ray = min(rays, key=lambda r: abs(spatial.wrap(r.heading - here[2]))) if rays else None
    if c.get("goal_ends") and any(g.step == step for g in mem.goal_rays):
        # a83: the goal is in view: the drone is through the wall or looking
        # through its door, and the route (which knows where the goal is) has
        # the rest. On the s02 near side the goal shows only through a doorway.
        sv["phase"] = "done"
        return None, sv
    side_only = c.get("side_only")
    if side_only == "far" and ray is not None:
        # a84: only a read in one of the two outer strips is side-only; a
        # doorway read in the centre three strips is ahead of the drone, and
        # is flown at whatever the phase.
        side_only = abs(spatial.wrap(ray.heading - here[2])) > float(c["far_strip_deg"])
    if ray is not None and side_only and sv["phase"] == "transit":
        # a83: on the way to a station a doorway read says which side it is
        # on, no more: five strips give a bearing to about 9 degrees, 2.4 m at
        # 16 m (R40 and R42 shakedowns, s02vc final: a door read from 15 m was
        # flown at down lines 4 and 5 m beside it). The station on that side
        # goes first; the door is flown at from there, square to the wall.
        side = 1.0 if spatial.wrap(ray.heading - axis) > 0 else -1.0
        cur = float(sv["order"][int(sv["i"])]) if int(sv["i"]) < len(sv["order"]) else 0.0
        if int(sv["i"]) == 0 and len(sv["order"]) > 1 and cur * side < 0:
            sv.update(order=[sv["order"][1], sv["order"][0]], best=None, since=step)
        ray = None
    if ray is not None:
        toward = ray.heading
        if c.get("ray_mean"):
            # a81: a doorway read across several strips lies at their middle
            # (R40 shakedown s02c dynamic s13: the strip nearest the heading
            # pointed 0.9 m off the door's centre).
            offs = [spatial.wrap(r.heading - axis) for r in rays]
            toward = (axis + sum(offs) / len(offs)) % 360.0
        kept = list(sv.get("rays") or []) + [[round(here[0], 2), round(here[1], 2),
                                              round(toward, 1)]]
        sv["rays"] = kept[-int(c["rays_kept"]):]
        if c.get("through_adv_m"):
            sv["read_at"] = round(along, 2)

    def carrot() -> spatial.Point:
        # The door's line runs along the approach axis through the doorway;
        # the waypoint is carrot_m ahead of the drone on it, so a drone
        # knocked off the line comes back onto it before the wall.
        been = None
        if c.get("been_floor"):
            been = max(survey_frame(sv, (x, y))[0] for _, x, y, _ in mem.trail)
        if c.get("home_ray") and sv.get("wall") is None and (c.get("no_cross")
                                                             or not survey_rays_cross(sv, c)):
            # a81: the wall's range unknown and the rays not yet crossing, the
            # door's line cannot be placed (R40 shakedown s02vc final: read
            # from 16 m, placed 5 m out, the drone met the wall 4 m beside the
            # door). Its bearing can: fly at it, the newest read's ray from
            # where it was taken, carrot_m ahead of the drone along it.
            rx, ry, rh = sv["rays"][-1]
            done = max(0.0, (here[0] - rx) * math.cos(math.radians(rh))
                       + (here[1] - ry) * math.sin(math.radians(rh)))
            return spatial.ahead((rx, ry), rh, done + float(c["carrot_m"]))
        line = survey_door_line(sv, c, been)
        up = c.get("lineup")
        left = survey_frame(sv, here[:2])[1]
        if (up and sv.get("wall") is not None and abs(left - line) > float(up["align_m"])
                and along > float(sv["wall"]) - float(up["pre_m"]) - 1.0):
            # a85: at the wall and off the door's line: first to the point
            # pre_m out from the wall on that line, then through it square
            # (a76's approach pose, with the wall's range and the door's line
            # it lacked).
            return survey_point(sv, float(sv["wall"]) - float(up["pre_m"]), line)
        return survey_point(sv, along + float(c["carrot_m"]), line)

    if sv["phase"] == "check":
        # a81: a move was stopped short in the through phase with no doorway
        # read. The route has the waypoint for check_steps: check_m farther
        # toward the wall than where it stopped, the drone is through (it
        # clipped a jamb: R40 shakedown s02c dynamic s14-16); else a phantom.
        if ray is not None:
            sv.update(phase="through", since=step)
            return carrot(), sv
        if along >= float(sv["mark"]) + float(c["check_m"]):
            sv["phase"] = "done"
            return None, sv
        if step - int(sv["since"]) >= int(c["check_steps"]):
            _survey_next(sv, step)
        else:
            return None, sv

    if sv["phase"] == "through":
        spent = step - int(sv["since"])
        bumped = any(b.step == step - 1 for b in mem.blocks)
        if wall is not None and along >= float(wall) + float(c["through_m"]) - 0.5:
            sv["phase"] = "done"            # beyond the wall: the route takes over
            return None, sv
        if ray is not None:
            sv["since"] = step              # still read ahead: the count restarts
            return carrot(), sv
        stopped = bumped or bool(mem.nose_on and mem.nose_on[-1] == step)
        if stopped and c.get("lineup") and sv.get("rays") and int(sv.get("lined", 0)) < 2:
            # a85: stopped by the wall with the doorway's reads in hand: the
            # wall is wall_m ahead, so the door's line is where the newest ray
            # meets it. Line up on it and go through (twice at most).
            if wall is None:
                sv["wall"] = round(along + float(c["wall_m"]), 2)
            sv.update(lined=int(sv.get("lined", 0)) + 1, since=step)
            return carrot(), sv
        if bumped and c.get("check_steps"):
            sv.update(phase="check", since=step, mark=round(along, 2))
            return None, sv
        if bumped:
            _survey_next(sv, step)          # stopped, and no doorway read from here: a phantom
        elif (spent >= int(c["through_steps"]) and c.get("through_adv_m")
              and sv.get("read_at") is not None
              and along - float(sv["read_at"]) >= float(c["through_adv_m"])):
            # a85: through_adv_m farther on than where the doorway was last
            # read, and nothing stopped the drone: it is through (R44
            # shakedown s02c dynamic: six look steps beyond the wall).
            sv["phase"] = "done"
            return None, sv
        elif spent >= int(c["through_steps"]) and c.get("relook"):
            # a83: no doorway read for through_steps and no goal in view: not
            # through. Fly at the wall again from here (a86: `again`, so the
            # look is the short one).
            sv.update(phase="look", since=step, again=True)
        elif spent >= int(c["through_steps"]):
            sv["phase"] = "done"            # no doorway ahead any more, nothing in the way: through it
            return None, sv
        else:
            return carrot(), sv
    elif ray is not None:
        sv.update(phase="through", since=step)
        return carrot(), sv
    station = survey_station(sv, c)
    if station is None:
        sv["phase"] = "done"
        return None, sv
    if sv["phase"] == "transit":
        d = spatial.dist(here[:2], station)
        if d <= float(c["reach_m"]):
            sv.update(phase="look", since=step)
        else:
            if sv["best"] is None or d < float(sv["best"]) - 0.5:
                sv.update(best=round(d, 2), since=step)
            elif step - int(sv["since"]) >= int(c["stall_steps"]):
                _survey_next(sv, step)
                station = survey_station(sv, c)
                if station is None:
                    sv["phase"] = "done"
                    return None, sv
            if sv["phase"] == "transit":
                return station, sv
    # look: turn to the wall and fly at it until it is met.
    square = abs(spatial.wrap(here[2] - axis)) <= float(c["square_deg"])
    if square:
        sv["looks"] = int(sv["looks"]) + 1
    met = square and step > int(sv["since"]) and at_wall(mem, records, step)
    if c.get("look_nose_on") and square and step > int(sv["since"]):
        # a81: flying at the wall, every strip blocked is the wall (R40
        # shakedown s02c dynamic s5-6: far floor from 3 m, all blocked at 1.3 m).
        met = met or bool(mem.nose_on and mem.nose_on[-1] == step)
    if met:
        sv["wall"] = round(along + float(c["wall_m"]), 2)
    if (not met and sv.get("again") and c.get("relook_steps")
            and step - int(sv["since"]) >= int(c["relook_steps"])):
        # a86: a look taken up again after a doorway was flown at and lost:
        # relook_steps at the wall's bearing with no wall met and no doorway
        # read, the drone is through. (a85's through_adv_m called it through
        # 5 m past a read made from far, still in the hall.)
        sv["phase"] = "done"
        return None, sv
    if met or step - int(sv["since"]) >= int(c["look_steps"]):
        _survey_next(sv, step)
        station = survey_station(sv, c)
        if station is None:
            sv["phase"] = "done"
            return None, sv
        return station, sv
    return spatial.ahead(here[:2], axis, float(c["face_m"])), sv


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
    latch: Optional[Dict[str, Any]] = None
    latched: List[Tuple[int, int]] = []
    if p.get("dead_end_latch"):
        # a78: a latch holds from the step it fires to the end of the run;
        # the first step the drone is back out past its mouth shuts the lane.
        latch = latch_from(records, step)
        surveying = None
        if latch is None and p["dead_end_latch"].get("after_survey") and p.get("survey"):
            # a86: no new latch while the wall survey is running (it is the
            # survey's wall, and its look lanes are straight runs at a wall
            # with a shut door in it).
            surveying = survey_from(records, step)
        if latch is None and (surveying is None or surveying["phase"] == "done"):
            latch = dead_end_latch(mem, here, step, p, goal)
        if latch is not None:
            along = latch_frame(latch, here[:2])[0]
            back_in = p["dead_end_latch"].get("reopen_m")
            far_end = float(latch["reach_m"]) + float(latch["ahead_m"])
            if (latch["out"] and back_in is not None and along > float(back_in)
                    and (not p["dead_end_latch"].get("reopen_inside") or along <= far_end)
                    and abs(latch_frame(latch, here[:2])[1]) <= float(latch["half_width_m"])):
                # a88: the drone is back inside the corridor it had left. The
                # lane shut behind it is opened again, or it has no way out
                # (R45 s03 dynamic seed 1: out at step 36, back in, no route
                # on 21 steps). a89 (reopen_inside): and short of the
                # rectangle's far end (R48 shakedown: reopened for a drone
                # already through the other tine's door, beyond it).
                latch["out"] = False
            if not latch["out"] and along < 0.0:
                latch["out"] = True
            elif not latch["out"]:
                latch["reach_m"] = round(max(float(latch["reach_m"]), along), 2)
            latched = [c for c in latch_cells(latch) if c != end]
    shut = {"latched": latched, "plugged": bool(latch and latch["out"])}
    cm = spatial.CostMap(mem, stall, p, include=(start, end), start=start, **shut)
    path = astar(cm, start, end, strict_corners=bool(p.get("strict_corners")))
    kept: Optional[bool] = None
    fresh_m: Optional[float] = None
    commit = p.get("commit")
    if commit:
        # a72: keep the previous step's route unless the drone has left it,
        # it is now impassable, or a fresh route is at least `gain` cheaper.
        # R30 s03 dynamic: the route alternated every two or three steps
        # between the shut door and the way out as single cells sealed, and
        # the drone turned in place.
        prev = _previous_route(records, step)
        held = committed_route(cm, start, prev, end, commit) if prev else None
        if held is not None:
            kept = True
            if path is not None:
                fresh_m = round(sum(spatial.dist(_centre(a), _centre(b))
                                    for a, b in zip(path, path[1:])), 2)
                fresh, old = path_cost(cm, path), path_cost(cm, held)
                if fresh is not None and old is not None and fresh < (1.0 - float(commit["gain"])) * old:
                    kept = False
            if kept:
                path = held
        elif path is not None and prev:
            kept = False
    if path is None:
        fallback = "soft"
        cm = spatial.CostMap(mem, stall, p, soft=True, include=(start, end), start=start, **shut)
        path = astar(cm, start, end, strict_corners=bool(p.get("strict_corners")))
    if path is None:
        fallback = "frontier"
        fronts = mem.search_frontiers(here[:2])
        if fronts:
            fp = fronts[0][0]
            path = (astar(cm, start, spatial.cell(fp), strict_corners=bool(p.get("strict_corners")))
                    or [start, spatial.cell(fp)])
            target_point = fp
        else:
            path = [start, end]
            target_point = goal
        wp = waypoint_on(cm, here[:2], path, target_point, p)
    else:
        wp = waypoint_on(cm, here[:2], path, goal, p)
    door: Optional[Dict[str, Any]] = None
    if p.get("door_approach") and fallback != "frontier":
        hit = door_approach(mem, cm, here, path, records, step, p["door_approach"])
        if hit is None and p["door_approach"].get("look"):
            hit = door_look(mem, here, path, records, step, p["door_approach"]["look"])
        if hit is not None:
            wp, door = hit
            near = float(p.get("waypoint_min_m", 1.0))
            if spatial.dist(here[:2], wp) < near:
                wp = spatial.ahead(here[:2], spatial.bearing(here[:2], wp), near)
    leave = (p.get("dead_end_latch") or {}).get("exit")
    if leave and latch is not None and not latch["out"] and fallback != "frontier":
        # a82: latched and inside, the waypoint is carrot_m back down the
        # corridor's middle, not the route's next point: one steady bearing
        # to the mouth. R39 (a79) s03 dynamic seed 1 was out of the tine five
        # steps after the latch and lost by two; its shakedown's seed 2 made
        # 0.8 m a step on the way out, the route's point 90 degrees off beside a
        # wall and the tag on the turn-around.
        back = latch_frame(latch, here[:2])[0] - float(leave["carrot_m"])
        rad = math.radians(float(latch["axis_deg"]))
        mid = float(latch.get("mid_m", 0.0))
        wp = (float(latch["origin"][0]) + back * math.cos(rad) - mid * math.sin(rad),
              float(latch["origin"][1]) + back * math.sin(rad) + mid * math.cos(rad))
    survey: Optional[Dict[str, Any]] = None
    if p.get("survey") and latch is None:
        # a80: the wall survey takes the waypoint while it runs. A latched
        # corridor has none (the latch is the way out of it).
        hit_wp, survey = wall_survey(mem, cm, here, step, goal, records, p)
        if hit_wp is not None:
            wp = hit_wp
            near = float(p.get("waypoint_min_m", 1.0))
            if spatial.dist(here[:2], wp) < near:
                wp = spatial.ahead(here[:2], spatial.bearing(here[:2], wp), near)
    elif p.get("survey"):
        survey = survey_from(records, step)
        if survey is not None and survey["phase"] != "done":
            survey["phase"] = "done"
    if (p.get("spawn_ahead") and not records and latch is None and survey is None
            and abs(spatial.wrap(spatial.bearing(here[:2], wp) - here[2])) > 90.0
            and abs(spatial.wrap(spatial.bearing(here[:2], goal) - here[2])) <= 90.0):
        # a96: at the spawn the route's first point lies behind the drone in
        # 13 of 150 runs (R49 to R55): every strip read blocked_near from 20 m,
        # a wall painted one cell ahead, the route going round it. The
        # turn-around then carries "toward your target" and the navigator
        # takes it (R49, R53, R54 s02vc final seed 3, lost; 5 of the 13). The
        # goal lies ahead: the waypoint goes to it, waypoint_min_m away.
        wp = spatial.ahead(here[:2], spatial.bearing(here[:2], goal),
                           float(p.get("waypoint_min_m", 1.0)))
    path_m = round(sum(spatial.dist(_centre(a), _centre(b)) for a, b in zip(path, path[1:])), 2)
    unknown = sum(1 for c in path[1:-1] if c not in cm.known)
    target = spatial.Target("path", "path", wp[0], wp[1], p["words"]["path"], step)
    way_in: Optional[bool] = None
    if p.get("way_in") and p.get("survey"):
        # a90: the first way in, as survey_start reads it. While it lasts the
        # navigator is not told its route is behind it (R46: told so on the
        # way in, it turned off the direct line and 9 of 24 s02 runs never
        # read the shut door in the centre strip).
        way_in = (survey is None and latch is None and bool(mem.trail)
                  and step < int(p["way_in"]["steps"]))
        if way_in:
            line = {"origin": mem.trail[0][1:3],
                    "axis_deg": spatial.bearing(mem.trail[0][1:3], goal)}
            way_in = not any(abs(latch_frame(line, (x, y))[1]) > float(p["survey"]["line_m"])
                             for _, x, y, _ in mem.trail)
    return PathPlan(target, wp, path, path_m, unknown, fallback, added, cm.counts(), sealed_now,
                    kept, fresh_m, door, latch, survey, way_in)


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
