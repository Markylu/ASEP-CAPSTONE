"""Spatial memory for the orchestrated agent (a13 on), written by code.

R6 gave the model its ground-truth pose and it never compared two positions; R6
and R7 show it doing heading arithmetic that turned it away from a goal it could
see. So every spatial judgement here is made by code, and the model is only
shown the verdicts, attached to the actions it can take ("blocked here before",
"new ground", "toward your target").

What the memory may be built from (operator, 2026-10-22):
- the drone's pose at each decision (accepted as fair in R6), and so how far
  each move went;
- what the perceiver (prompt g03) reads off each clean frame: where the goal
  is, how much open floor each strip of the image shows, and doorways.
Not from site.json, depth, raycasts, the sim's `collided` flag, or the goal's
ground truth. The manifest's `goal` block is never read here.

The memory is rebuilt from decisions.jsonl on every step, never carried in the
process, the same way recorder.Run.memory() works. A run directory therefore
replays to exactly the memory the model was shown (eval/spatial_replay.py).

Map frame as prompt._where(): x is Godot's x, y is minus Godot's z, heading is
degrees counter-clockwise from +x, and a left turn raises it.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# --- parameters (hashed into the agent: agent.py a13 features) ---------------

#: Grid cell for visits and seen floor: half of one 1.7 m move.
CELL_M = 0.85
#: Move-length thresholds, the same as R7's comparison lines (prompt.py).
BLOCKED_BELOW_M = 0.3
SHORT_BELOW_M = 1.5
#: A blocked record applies to a new decision made within this distance of
#: where it happened and within this many degrees of its heading.
BLOCK_NEAR_M = 0.85
BLOCK_WITHIN_DEG = 15.0
#: The camera's horizontal field of view and the perceiver's five strips.
FOV_DEG = 87.0
STRIPS = ("far_left", "left", "centre", "right", "far_right")
#: Open floor the perceiver's lane classes stand for, metres along the strip.
FLOOR_RANGE_M = {"open_far": 6.0, "open_near": 2.5, "blocked_near": 1.0}
#: Goal distance classes, as the g03 prompt words them, and the point used
#: when only one sighting exists.
GOAL_RANGE_M = {"touching": 1.0, "near": 4.0, "mid": 10.0, "far": 18.0}
#: Goal rays must spread at least this much to be intersected.
RAY_SPREAD_DEG = 15.0
#: Openings: distance placed along the strip, merge radius, passed radius.
OPENING_AT_M = {"open_far": 5.0, "open_near": 2.0, "blocked_near": 1.0}
OPENING_MERGE_M = 2.5
OPENING_PASSED_M = 1.5
#: Loop detector window and visit count.
LOOP_WINDOW = 10
LOOP_VISITS = 3
#: A target this close counts as reached.
TARGET_REACHED_M = 1.5
#: An action is "toward" a target when it is the nearest heading to it and
#: within this many degrees.
TOWARD_WITHIN_DEG = 33.0

PARAMS = {
    "cell_m": CELL_M, "blocked_below_m": BLOCKED_BELOW_M, "short_below_m": SHORT_BELOW_M,
    "block_near_m": BLOCK_NEAR_M, "block_within_deg": BLOCK_WITHIN_DEG, "fov_deg": FOV_DEG,
    "floor_range_m": FLOOR_RANGE_M, "goal_range_m": GOAL_RANGE_M,
    "ray_spread_deg": RAY_SPREAD_DEG, "opening_at_m": OPENING_AT_M,
    "opening_merge_m": OPENING_MERGE_M, "opening_passed_m": OPENING_PASSED_M,
    "loop_window": LOOP_WINDOW, "loop_visits": LOOP_VISITS,
    "target_reached_m": TARGET_REACHED_M, "toward_within_deg": TOWARD_WITHIN_DEG,
}

#: Every sentence the model can be shown from here. Kept in one table so that
#: wording_sha() changes whenever any of it does, and agent.sha() with it.
WORDS: Dict[str, Any] = {
    "blocked": "blocked here before (step {step})",
    "short": "stopped short here before (step {step})",
    "wall_seen": "wall close (seen now)",
    "doorway_seen": "doorway (seen now)",
    "goal_seen": "goal this way (seen now, {range})",
    "goal_one_move": "goal about one move ahead",
    "toward_target": "toward your target",
    "new_ground": "new ground",
    "visited": "been there {n} {times} (last step {last})",
    "behind_new": "behind you is new ground",
    "behind_visited": "behind you is ground you have covered",
    "range": {"touching": "very close", "near": "near", "mid": "some way off",
              "far": "far off"},
    "rel": ("ahead", "ahead-left", "left", "behind-left", "behind",
            "behind-right", "right", "ahead-right"),
    "critic_blocked": "memory says [{i}] was blocked from here at step {step}",
    "critic_spin": "this would be your third turn-around in four steps",
    "critic_loop": ("memory says [{i}] leads to ground you have covered {n} times in the "
                    "last {w} steps, and {alt} offers {what}"),
    "critic_tail": "Memory note: {why}. Choose again; you may keep [{i}] if the image "
                   "shows it is right.",
}


def wording_sha() -> str:
    """Identity of this module's parameters and wording, for agent.sha()."""
    blob = json.dumps({"params": PARAMS, "words": WORDS}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# --- geometry ------------------------------------------------------------------

Point = Tuple[float, float]
Pose = Tuple[float, float, float]


def pose_xyh(pose: Any) -> Optional[Pose]:
    """A manifest pose on the map: (x, y, heading degrees), or None.

    The same frame as prompt._where(), with heading unrounded."""
    if not pose or pose.get("position") is None or pose.get("yaw") is None:
        return None
    x, _, z = (float(v) for v in pose["position"])
    return x, -z, (math.degrees(float(pose["yaw"])) + 90.0) % 360.0


def wrap(deg: float) -> float:
    """Angle to (-180, 180]."""
    deg = deg % 360.0
    return deg - 360.0 if deg > 180.0 else deg


def ahead(p: Point, heading: float, dist_m: float) -> Point:
    rad = math.radians(heading)
    return p[0] + dist_m * math.cos(rad), p[1] + dist_m * math.sin(rad)


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def bearing(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360.0


def cell(p: Point) -> Tuple[int, int]:
    return int(math.floor(p[0] / CELL_M)), int(math.floor(p[1] / CELL_M))


def strip_offset(strip: str) -> float:
    """Degrees left (+) of straight ahead at the centre of an image strip.

    Five equal strips across the frame; a pinhole camera maps the strip centre
    u in [-1, 1] to atan(u tan(fov/2)). Gives about 37, 21, 0 degrees, close to
    the fan's 43.5 and 21.75."""
    u = (2 - STRIPS.index(strip)) * 0.4
    return math.degrees(math.atan(u * math.tan(math.radians(FOV_DEG / 2.0))))


def relative_word(rel_deg: float) -> str:
    """One of eight words for a direction relative to the drone's heading."""
    return WORDS["rel"][int(((wrap(rel_deg) + 22.5) % 360.0) // 45.0)]


def action_heading(action: Dict[str, Any], heading: float) -> float:
    return (heading + float(action.get("theta_deg") or 0.0)) % 360.0


# --- memory --------------------------------------------------------------------

@dataclass
class Block:
    x: float
    y: float
    heading: float
    step: int
    moved: float

    @property
    def kind(self) -> str:
        return "blocked" if self.moved < BLOCKED_BELOW_M else "short"


@dataclass
class Ray:
    x: float
    y: float
    heading: float
    step: int
    range: str


@dataclass
class Opening:
    x: float
    y: float
    step: int
    seen: int = 1
    passed: bool = False
    closed: bool = False
    label: str = ""


@dataclass
class Target:
    """What the strategist chose, as a map point code can steer by. `label`
    names it ("doorway A (seen at step 6)"); where it is from the drone is
    worded fresh each step by words()."""
    id: str
    kind: str
    x: float
    y: float
    label: str
    step: int = 0

    def words(self, here: "Pose") -> str:
        return "{0}, {1}".format(self.label, where_words(here, (self.x, self.y)))

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "x": round(self.x, 2),
                "y": round(self.y, 2), "label": self.label, "step": self.step}

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["Target"]:
        if not d:
            return None
        return cls(d["id"], d["kind"], float(d["x"]), float(d["y"]), d.get("label", ""),
                   int(d.get("step", 0)))


@dataclass
class SpatialMemory:
    visits: Dict[Tuple[int, int], List[int]] = field(default_factory=dict)
    free: Dict[Tuple[int, int], int] = field(default_factory=dict)
    wall: Dict[Tuple[int, int], int] = field(default_factory=dict)
    blocks: List[Block] = field(default_factory=list)
    goal_rays: List[Ray] = field(default_factory=list)
    openings: List[Opening] = field(default_factory=list)
    trail: List[Tuple[int, float, float, float]] = field(default_factory=list)
    turn_arounds: List[int] = field(default_factory=list)

    # -- folding ---------------------------------------------------------------

    def visit(self, step: int, where: Pose) -> None:
        self.trail.append((step, where[0], where[1], where[2]))
        c = cell(where[:2])
        self.visits.setdefault(c, []).append(step)
        self.wall.pop(c, None)

    def move(self, step: int, before: Pose, after: Pose, action: Dict[str, Any]) -> None:
        """What a move did, from where it started and where the next decision was."""
        if action.get("turn_around"):
            self.turn_arounds.append(step)
            return
        moved = dist(before[:2], after[:2])
        # The ground flown over between two decisions was visited too, once.
        d = CELL_M / 2.0
        while d < moved:
            c = cell((before[0] + (after[0] - before[0]) * d / moved,
                      before[1] + (after[1] - before[1]) * d / moved))
            if c != cell(before[:2]) and c != cell(after[:2]) and step not in self.visits.get(c, []):
                self.visits.setdefault(c, []).append(step)
                self.wall.pop(c, None)
            d += CELL_M / 2.0
        if moved < SHORT_BELOW_M:
            self.blocks.append(Block(before[0], before[1],
                                     action_heading(action, before[2]), step, moved))

    def observe(self, step: int, where: Pose, perception: Optional[Dict[str, Any]]) -> None:
        """Fold one perceiver report taken at `where` into the map. Seen floor is
        weak evidence: a visit always overrides a wall mark, and a newer look
        overwrites an older one."""
        if not perception:
            return
        here = where[:2]
        for lane in perception.get("lanes") or []:
            strip = lane.get("strip")
            floor = lane.get("floor")
            if strip not in STRIPS or floor not in FLOOR_RANGE_M:
                continue
            heading = (where[2] + strip_offset(strip)) % 360.0
            reach = FLOOR_RANGE_M[floor]
            d = CELL_M / 2.0
            while d <= reach:
                c = cell(ahead(here, heading, d))
                self.free[c] = step
                self.wall.pop(c, None)
                d += CELL_M / 2.0
            if floor == "blocked_near":
                end = cell(ahead(here, heading, reach + CELL_M / 2.0))
                if end not in self.visits:
                    self.wall[end] = step
                    self.free.pop(end, None)
            if lane.get("doorway"):
                self._add_opening(step, ahead(here, heading, OPENING_AT_M[floor]))
            self._close_openings(step, here, heading, reach)
        goal = perception.get("goal")
        if goal in STRIPS:
            self.goal_rays.append(Ray(here[0], here[1],
                                      (where[2] + strip_offset(goal)) % 360.0, step,
                                      perception.get("goal_range") or "mid"))

    def _add_opening(self, step: int, p: Point) -> None:
        for o in self.openings:
            if dist((o.x, o.y), p) < OPENING_MERGE_M:
                n = o.seen
                o.x, o.y = (o.x * n + p[0]) / (n + 1), (o.y * n + p[1]) / (n + 1)
                o.seen += 1
                o.closed = False
                return
        self.openings.append(Opening(p[0], p[1], step,
                                     label="ABCDEFGHJKLMNPQRSTUVWXYZ"[len(self.openings) % 24]))

    def _close_openings(self, step: int, here: Point, heading: float, reach: float) -> None:
        """An opening is closed when a later look straight at it sees the floor
        end well short of it."""
        for o in self.openings:
            if o.passed or o.step == step:
                continue
            d = dist(here, (o.x, o.y))
            if d > 8.0 or d < 1.0:
                continue
            if abs(wrap(bearing(here, (o.x, o.y)) - heading)) < 10.0 and reach < d - 1.0:
                o.closed = True

    def settle(self) -> None:
        """Mark openings passed once the trail has come close to them."""
        for o in self.openings:
            if any(dist((x, y), (o.x, o.y)) < OPENING_PASSED_M for _, x, y, _ in self.trail):
                o.passed = True

    # -- queries ---------------------------------------------------------------

    def block_for(self, here: Point, heading: float) -> Optional[Block]:
        """The latest blocked or short move from about here, about this way."""
        hit = None
        for b in self.blocks:
            if (dist(here, (b.x, b.y)) < BLOCK_NEAR_M
                    and abs(wrap(b.heading - heading)) < BLOCK_WITHIN_DEG):
                if hit is None or b.step > hit.step:
                    hit = b
        return hit

    def visits_at(self, p: Point) -> List[int]:
        return list(self.visits.get(cell(p), []))

    def goal_belief(self) -> Optional[Tuple[float, float, int]]:
        """Where the goal probably is, from the perceiver's sightings: (x, y, step).

        The least-squares point nearest every ray, when the rays spread at least
        RAY_SPREAD_DEG and the point lies in front of each; otherwise the latest
        ray at its range class. `step` is the latest sighting it rests on."""
        if not self.goal_rays:
            return None
        rays = self.goal_rays
        last = rays[-1]
        spread = max(abs(wrap(a.heading - b.heading)) for a in rays for b in rays)
        if len(rays) >= 2 and spread >= RAY_SPREAD_DEG:
            # Sum over rays of (I - d d^T) p = (I - d d^T) o.
            a11 = a12 = a22 = b1 = b2 = 0.0
            for r in rays:
                dx, dy = math.cos(math.radians(r.heading)), math.sin(math.radians(r.heading))
                m11, m12, m22 = 1 - dx * dx, -dx * dy, 1 - dy * dy
                a11 += m11
                a12 += m12
                a22 += m22
                b1 += m11 * r.x + m12 * r.y
                b2 += m12 * r.x + m22 * r.y
            det = a11 * a22 - a12 * a12
            if abs(det) > 1e-6:
                px = (a22 * b1 - a12 * b2) / det
                py = (a11 * b2 - a12 * b1) / det
                in_front = all(
                    (px - r.x) * math.cos(math.radians(r.heading))
                    + (py - r.y) * math.sin(math.radians(r.heading)) > 0 for r in rays)
                if in_front:
                    return px, py, last.step
        p = ahead((last.x, last.y), last.heading, GOAL_RANGE_M.get(last.range, 10.0))
        return p[0], p[1], last.step

    def frontiers(self, here: Point, limit: int = 3) -> List[Point]:
        """Centres of seen-free, unvisited ground that borders unknown ground."""
        edge = set()
        for c in self.free:
            if c in self.visits or c in self.wall:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                if n not in self.free and n not in self.visits and n not in self.wall:
                    edge.add(c)
                    break
        clusters: List[List[Tuple[int, int]]] = []
        seen = set()
        for c in sorted(edge):
            if c in seen:
                continue
            group, todo = [], [c]
            seen.add(c)
            while todo:
                cur = todo.pop()
                group.append(cur)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        n = (cur[0] + dx, cur[1] + dy)
                        if n in edge and n not in seen:
                            seen.add(n)
                            todo.append(n)
            if len(group) >= 3:
                clusters.append(group)
        points = []
        for g in clusters:
            px = sum((c[0] + 0.5) * CELL_M for c in g) / len(g)
            py = sum((c[1] + 0.5) * CELL_M for c in g) / len(g)
            if dist(here, (px, py)) > 2.0:
                points.append((len(g), (px, py)))
        points.sort(key=lambda t: (-t[0], dist(here, t[1])))
        return [p for _, p in points[:limit]]

    def loop_score(self) -> float:
        """Share of the last LOOP_WINDOW positions on ground visited LOOP_VISITS+ times."""
        recent = self.trail[-LOOP_WINDOW:]
        if len(recent) < LOOP_WINDOW:
            return 0.0
        hot = sum(1 for _, x, y, _ in recent if len(self.visits_at((x, y))) >= LOOP_VISITS)
        return hot / float(len(recent))

    def snapshot(self) -> Dict[str, Any]:
        """A compact record of the memory for decisions.jsonl and the probe."""
        belief = self.goal_belief()
        return {
            "cells_visited": len(self.visits),
            "cells_free": len(self.free),
            "cells_wall": len(self.wall),
            "blocks": [[round(b.x, 2), round(b.y, 2), round(b.heading, 1), b.step,
                        round(b.moved, 2)] for b in self.blocks],
            "goal_rays": len(self.goal_rays),
            "goal_belief": None if belief is None else [round(belief[0], 2),
                                                        round(belief[1], 2), belief[2]],
            "openings": [{"label": o.label, "x": round(o.x, 2), "y": round(o.y, 2),
                          "step": o.step, "seen": o.seen, "passed": o.passed,
                          "closed": o.closed} for o in self.openings],
            "loop_score": round(self.loop_score(), 2),
        }


def rebuild(records: Iterable[Dict[str, Any]], manifest: Dict[str, Any],
            perception_now: Optional[Dict[str, Any]] = None) -> SpatialMemory:
    """The memory as of this decision, from the run's earlier decision records.

    Each record contributes the pose it was decided at, its perceiver report
    and, against the next record's pose (or the current manifest's), what its
    move did. A failed decision still gives a pose. `perception_now` is the
    perceiver's report for the current frame, folded in last."""
    mem = SpatialMemory()
    step_now = int(manifest.get("step", 0))
    rows = sorted((r for r in records if "step" in r and r["step"] < step_now),
                  key=lambda r: r["step"])
    now = pose_xyh(manifest.get("pose"))
    for i, r in enumerate(rows):
        where = pose_xyh((r.get("manifest") or {}).get("pose"))
        if where is None:
            continue
        mem.visit(r["step"], where)
        mem.observe(r["step"], where, (r.get("perceiver") or {}).get("result"))
        if r.get("error") or r.get("index") is None:
            continue
        after: Optional[Pose] = None
        for later in rows[i + 1:]:
            after = pose_xyh((later.get("manifest") or {}).get("pose"))
            if after is not None:
                break
        if after is None:
            after = now
        actions = (r.get("manifest") or {}).get("actions") or []
        chosen = next((a for a in actions if a.get("index") == r["index"]), None)
        if after is not None and chosen is not None:
            mem.move(r["step"], where, after, chosen)
    if now is not None:
        mem.visit(step_now, now)
        mem.observe(step_now, now, perception_now)
    mem.settle()
    return mem


# --- targets -------------------------------------------------------------------

def where_words(here: Pose, p: Point) -> str:
    """'about 8 m, behind-left': distance and an eight-way direction from the
    drone's heading. No coordinates and no degrees reach the model."""
    d = dist(here[:2], p)
    rel = relative_word(bearing(here[:2], p) - here[2])
    if d < 3.0:
        return "close by, {0}".format(rel)
    return "about {0:.0f} m, {1}".format(d, rel)


def targets(mem: SpatialMemory, here: Pose, step: int) -> List[Target]:
    """The strategist's menu, built by code: the goal belief, doorways not yet
    passed or closed, unexplored edges, and the last place that still had an
    untried open way."""
    out: List[Target] = []
    belief = mem.goal_belief()
    if belief is not None:
        out.append(Target("goal", "goal", belief[0], belief[1],
                          "the goal (last seen at step {0})".format(belief[2]), step))
    for o in mem.openings:
        if o.passed or o.closed:
            continue
        out.append(Target("doorway_" + o.label, "opening", o.x, o.y,
                          "doorway {0} (seen at step {1})".format(o.label, o.step), step))
    for k, p in enumerate(mem.frontiers(here[:2])):
        out.append(Target("unexplored_{0}".format(k + 1), "frontier", p[0], p[1],
                          "unexplored ground", step))
    back = _backtrack_point(mem, here)
    if back is not None:
        s, p = back
        out.append(Target("back_to_step_{0}".format(s), "backtrack", p[0], p[1],
                          "where you were at step {0}".format(s), step))
    return out


def _backtrack_point(mem: SpatialMemory, here: Pose) -> Optional[Tuple[int, Point]]:
    """The latest earlier position, at least 3 m away, from which some way
    ahead was seen open and has not been walked."""
    for s, x, y, h in reversed(mem.trail[:-1]):
        if dist((x, y), here[:2]) < 3.0:
            continue
        for offset in (0.0, 21.75, -21.75, 43.5, -43.5):
            p = ahead((x, y), (h + offset) % 360.0, 1.7)
            c = cell(p)
            if (c in mem.free and c not in mem.visits
                    and mem.block_for((x, y), h + offset) is None):
                return s, (x, y)
    return None


def target_still_valid(mem: SpatialMemory, target: Optional[Target], here: Point) -> bool:
    """False once a target is reached, or a doorway target is closed or passed.
    A goal or doorway target follows its latest estimate."""
    if target is None:
        return False
    if target.kind == "opening":
        label = target.id.split("_", 1)[1]
        o = next((o for o in mem.openings if o.label == label), None)
        if o is None or o.closed or o.passed:
            return False
        target.x, target.y = o.x, o.y
    if target.kind == "goal":
        belief = mem.goal_belief()
        if belief is not None:
            target.x, target.y = belief[0], belief[1]
    return dist(here, (target.x, target.y)) >= TARGET_REACHED_M


# --- projection onto the actions -----------------------------------------------

def strip_for(theta_deg: float) -> str:
    """The image strip an action's heading falls in."""
    return min(STRIPS, key=lambda s: abs(strip_offset(s) - theta_deg))


def project(mem: SpatialMemory, manifest: Dict[str, Any],
            perception: Optional[Dict[str, Any]],
            target: Optional[Target]) -> Dict[int, List[str]]:
    """Up to three tags per offered action, most important first."""
    here = pose_xyh(manifest.get("pose"))
    actions = manifest.get("actions") or []
    tags: Dict[int, List[str]] = {int(a["index"]): [] for a in actions}
    if here is None:
        return tags
    step = int(manifest.get("step", 0))
    lanes = {l.get("strip"): l for l in (perception or {}).get("lanes") or []}
    goal_strip = (perception or {}).get("goal")
    goal_range = (perception or {}).get("goal_range") or "mid"

    toward = None
    if target is not None:
        want = bearing(here[:2], (target.x, target.y))
        flying = [a for a in actions if not a.get("turn_around")]
        best = min(flying, key=lambda a: abs(wrap(action_heading(a, here[2]) - want)),
                   default=None)
        if best is not None and abs(wrap(action_heading(best, here[2]) - want)) <= TOWARD_WITHIN_DEG:
            toward = int(best["index"])
        elif abs(wrap(want - here[2])) > 90.0:
            toward = next((int(a["index"]) for a in actions if a.get("turn_around")), None)

    for a in actions:
        i = int(a["index"])
        out = tags[i]
        if a.get("turn_around"):
            if toward == i:
                out.append(WORDS["toward_target"])
            behind = ahead(here[:2], (here[2] + 180.0) % 360.0, 1.7)
            out.append(WORDS["behind_visited"] if mem.visits_at(behind)
                       else WORDS["behind_new"])
            continue
        heading = action_heading(a, here[2])
        strip = strip_for(float(a.get("theta_deg") or 0.0))
        if goal_strip == strip:
            if goal_range in ("touching", "near") and strip == "centre":
                out.append(WORDS["goal_one_move"])
            else:
                out.append(WORDS["goal_seen"].format(
                    range=WORDS["range"].get(goal_range, "distance unknown")))
        b = mem.block_for(here[:2], heading)
        if b is not None:
            out.append(WORDS[b.kind].format(step=b.step))
        lane = lanes.get(strip) or {}
        if lane.get("floor") == "blocked_near":
            out.append(WORDS["wall_seen"])
        if toward == i:
            out.append(WORDS["toward_target"])
        if lane.get("doorway"):
            out.append(WORDS["doorway_seen"])
        land = ahead(here[:2], heading, float(a.get("r") or 1.7))
        been = [s for s in mem.visits_at(land) if s < step]
        if been:
            out.append(WORDS["visited"].format(n=len(been), times="time" if len(been) == 1
                                               else "times", last=max(been)))
        elif b is None and lane.get("floor") != "blocked_near":
            out.append(WORDS["new_ground"])
        del out[3:]
    return tags


# --- critic --------------------------------------------------------------------

def critique(mem: SpatialMemory, manifest: Dict[str, Any], tags: Dict[int, List[str]],
             pick: int) -> Optional[str]:
    """Why memory disagrees with a pick, or None. Never removes an action: the
    orchestrator asks once more and the second answer stands."""
    here = pose_xyh(manifest.get("pose"))
    actions = {int(a["index"]): a for a in manifest.get("actions") or []}
    a = actions.get(pick)
    if here is None or a is None:
        return None
    step = int(manifest.get("step", 0))
    if a.get("turn_around"):
        if len([s for s in mem.turn_arounds if s >= step - 3]) >= 2:
            return WORDS["critic_spin"]
        return None
    heading = action_heading(a, here[2])
    b = mem.block_for(here[:2], heading)
    if b is not None and b.kind == "blocked":
        return WORDS["critic_blocked"].format(i=pick, step=b.step)
    land = ahead(here[:2], heading, float(a.get("r") or 1.7))
    hot = [s for s in mem.visits_at(land) if step - LOOP_WINDOW <= s < step]
    if len(hot) >= LOOP_VISITS:
        for j, words in sorted(tags.items()):
            if j == pick:
                continue
            for what in (WORDS["toward_target"], WORDS["new_ground"]):
                if what in words and not any(w.startswith(("blocked", "wall"))
                                             for w in words):
                    return WORDS["critic_loop"].format(i=pick, n=len(hot), w=LOOP_WINDOW,
                                                       alt="[{0}]".format(j), what=what)
    return None


# --- the strategist's view -----------------------------------------------------

def situation(mem: SpatialMemory, manifest: Dict[str, Any],
              perception: Optional[Dict[str, Any]], current: Optional[Target],
              menu: List[Target], trigger: str) -> str:
    """What the strategist is told, in words: no coordinates, no degrees."""
    here = pose_xyh(manifest.get("pose"))
    step = int(manifest.get("step", 0))
    lines = ["Step {0}. You are asked now because {1}.".format(step, trigger)]
    goal = (perception or {}).get("goal")
    if goal in STRIPS:
        lines.append("The goal is in the current image ({0}, {1}).".format(
            goal.replace("_", " "),
            WORDS["range"].get((perception or {}).get("goal_range"), "distance unknown")))
    elif mem.goal_rays:
        lines.append("The goal is not in the current image. It was last seen at step "
                     "{0}.".format(mem.goal_rays[-1].step))
    else:
        lines.append("The goal has not been seen yet in this run.")
    if here is not None:
        blocked = sorted({relative_word(b.heading - here[2]) for b in mem.blocks
                          if dist(here[:2], (b.x, b.y)) < BLOCK_NEAR_M})
        if blocked:
            lines.append("Moves from here that were blocked before: {0}.".format(
                ", ".join(blocked)))
        recent = mem.trail[-LOOP_WINDOW:]
        near = sum(1 for _, x, y, _ in recent if dist((x, y), here[:2]) < 2.0)
        if near >= 3:
            lines.append("You have been within 2 m of this spot for {0} of the last {1} "
                         "steps.".format(near, len(recent)))
    if current is not None:
        lines.append("Your current target: {0}: {1}.".format(
            current.id, current.words(here) if here is not None else current.label))
    lines.append("Targets you can choose from:")
    for t in menu:
        lines.append("  {0}: {1}".format(t.id, t.words(here) if here is not None else t.label))
    lines.append("  explore: no fixed target, go where the image shows open floor")
    return "\n".join(lines)


def trigger(mem: SpatialMemory, manifest: Dict[str, Any],
            perception: Optional[Dict[str, Any]], current: Optional[Target],
            last_called: Optional[int], last_perception: Optional[Dict[str, Any]],
            every: int = 8) -> Optional[str]:
    """Why the strategist should be asked this step, or None to keep the target."""
    step = int(manifest.get("step", 0))
    here = pose_xyh(manifest.get("pose"))
    goal_now = (perception or {}).get("goal") in STRIPS
    if last_called is None:
        return "the run is starting"
    if mem.blocks and mem.blocks[-1].step == step - 1 and mem.blocks[-1].kind == "blocked":
        return "your last move was blocked"
    if goal_now and (last_perception or {}).get("goal") not in STRIPS:
        return "the goal just came into view"
    if mem.goal_rays and not goal_now and mem.goal_rays[-1].step == step - 3:
        return "the goal has been out of view for three steps"
    if any(o.step == step and o.seen == 1 for o in mem.openings):
        return "a new doorway is in view"
    if current is not None and here is not None and not target_still_valid(
            mem, current, here[:2]):
        return "your target was reached or is no longer open"
    if mem.loop_score() >= 0.5 and step - last_called >= 3:
        return "you keep coming back to the same ground"
    if step - last_called >= every:
        return "it is time for a regular check"
    return None
