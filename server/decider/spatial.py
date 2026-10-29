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

a14 (R10, operator, 2026-10-24) gives the planner the goal's true position. The
orchestrator reads it and passes it in as `goal_at`; the memory itself is built
as before, and nothing here reads the manifest's `goal` block.

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
from dataclasses import dataclass, field, replace
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


#: Why the strategist is asked, as a13 words it. Two keys share a sentence
#: there; a14 words them apart (WORDS_A14). Not in WORDS: a13's sha never
#: covered these sentences, and must not change.
TRIGGERS_A13: Dict[str, str] = {
    "start": "the run is starting",
    "blocked": "your last move was blocked",
    "goal_in_view": "the goal just came into view",
    "goal_out_of_view": "the goal has been out of view for three steps",
    "new_doorway": "a new doorway is in view",
    "target_reached": "your target was reached or is no longer open",
    "target_closed": "your target was reached or is no longer open",
    "loop": "you keep coming back to the same ground",
    "regular": "it is time for a regular check",
}

#: Every sentence a14 adds (R10). Kept apart from WORDS so a13's wording_sha()
#: stays as flown; agent.sha() appends wording_sha_a14() only for an agent that
#: uses it. R9: the strategist read "your target ... is no longer open" as "the
#: goal is blocked", so a14 words those two triggers apart.
WORDS_A14: Dict[str, Any] = {
    "goal_label": "the goal (its position is known)",
    "goal_known": "The goal's position is known: {where}. It does not move.",
    "goal_in_image": "The goal is in the current image ({strip}, {range}).",
    "goal_not_in_image": "The goal is not in the current image.",
    "plan_goal": "head for the goal ({mode}).",
    "triggers": dict(TRIGGERS_A13, **{
        "target_reached": "the drone has reached the target you chose",
        "target_closed": "the doorway you chose is closed or already passed",
    }),
    "turn_rule": "the last pick was a turn-around and a move ahead is open",
}


def wording_sha_a14() -> str:
    """Identity of a14's added wording, for agent.sha()."""
    blob = json.dumps({"words_a14": WORDS_A14}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


#: a15's parameters (R11): the memory's changes and the route planner's
#: (server/decider/planner.py). Kept apart from PARAMS so a13 and a14 keep
#: their shas. R10: the collision after a collision was never warned about,
#: "toward your target" sat on walled moves, doorways churned the strategist.
PARAMS_A15: Dict[str, Any] = {
    # Block memory: a stopped-short move is also recorded where it ended, and a
    # block matches a heading within this much, so the next two fan actions out
    # (21.75 and 43.5 degrees off) are warned too. R9, R10C, R10: of 2179 forward
    # picks, 111 stopped short; at 25 degrees a15 notes 24 of them (and 19 that
    # flew), at 45 degrees 32 (and 28).
    "block_end_pose": True,
    "block_within_deg": 45.0,
    # "toward your target" goes on the open action nearest the target within
    # this many degrees, never on one with a wall, blocked or stopped-short note.
    "toward_open_within_deg": 55.0,
    # Doorway gate: on the menu from the second sighting, off it after this many
    # steps without one.
    "doorway_min_seen": 2,
    "doorway_ttl_steps": 10,
    # Route planner.
    "goal_way_within_deg": 55.0,
    "recent_block_steps": 3,
    "recent_block_near_m": 2.0,
    "stall_steps": 6,
    "stall_gain_m": 0.5,
    "detour_max_steps": 12,
    "explore_hold_steps": 3,
    "same_distance_m": 1.5,
}

#: Every sentence a15 adds (R11): why the detour strategist (q03) is asked, and
#: how far nearer the goal each detour lies. Its own table, so a14's wording sha
#: stays as flown.
WORDS_A15: Dict[str, Any] = {
    "asked": {
        "walled": "the way toward the goal is walled",
        "blocked": "a move toward the goal was blocked",
        "stall": "the drone has not got nearer the goal for six steps",
    },
    "nearer": "about {d:.0f} m nearer the goal than you are",
    "farther": "about {d:.0f} m farther from the goal than you are",
    "same": "about as far from the goal as you are",
    "menu": "Detours you can choose from:",
}


def wording_sha_a15() -> str:
    """Identity of a15's parameters and added wording, for agent.sha()."""
    blob = json.dumps({"params_a15": PARAMS_A15, "words_a15": WORDS_A15}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


#: a16's parameters (R11, after a15's probe failed): a15's, with the block
#: window by kind and the detour menu's unexplored ground on the goal's side.
#: a15's probe (eval/phase2/R11_goal_default/probe/probe_a15.md): at 45 degrees
#: one block straight ahead noted all five forward moves (28 of R10's steps), and
#: the navigator then took the very move that was blocked; 52 of 88 detour menus
#: held nothing 3 m nearer the goal, because each unexplored edge was offered at
#: its centre.
PARAMS_A16: Dict[str, Any] = dict(
    {k: v for k, v in PARAMS_A15.items() if k != "block_within_deg"},
    # After a move that did not get going (under BLOCKED_BELOW_M) only the same
    # heading is warned: the next fan action out stopped short 2 of 11 times in
    # R9, R10C and R10. After a move that stopped short, the next one out is
    # warned too (11 of 20).
    block_within_deg_blocked=15.0,
    block_within_deg_short=25.0,
    # Unexplored ground is offered at the point of each edge nearest the goal,
    # nearest-to-goal edges first: 85 of the 88 menus then hold a detour 3 m
    # nearer the goal (at the centre, 36).
    frontier="goal_side",
)


def wording_sha_a16() -> str:
    """Identity of a16's parameters and added wording (a15's), for agent.sha()."""
    blob = json.dumps({"params_a16": PARAMS_A16, "words_a15": WORDS_A15}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


#: a17's parameters (R12, operator, 2026-10-28): staged search with a coverage
#: map, and no goal truth anywhere. R11's failure analysis: detour targets lay
#: behind or inside walls (34 of 37), because collisions never wrote walls,
#: newer looks erased them, open floor ran a fixed 6 m and targets were never
#: checked for a path. R9-R11 (analysis/d_detect.py): g03 reports the goal in
#: view 612 of 612 times out past 30 m, so a look's cone is cut by walls only,
#: and its range class says nothing (a single sighting is a bearing).
PARAMS_A17: Dict[str, Any] = dict(
    {k: v for k, v in PARAMS_A16.items() if k != "frontier"},
    # Open floor along a strip, by class; g03's classes kept for replay on
    # R9-R11. g04 splits open_far into wall_far and open_very_far. Against
    # R11's geometry (eval/r12_probe.py): blocked_near had the wall within 1 m
    # on 378 of 606 lane reads, open_near within 2.5 m on 69 of 335, open_far
    # within 6 m on 849 of 2589 (within 4 m, 393).
    floor_range_m={"blocked_near": 0.5, "open_near": 2.0, "open_far": 4.0,
                   "wall_far": 6.0, "open_very_far": 10.0},
    # Classes whose floor ends at a wall (or door) the perceiver saw.
    floor_ends=["blocked_near", "open_near", "wall_far"],
    # Classes with no wall seen at their end: a look down such a strip that
    # does not show the goal disproves a belief on that line.
    open_floor=["open_far", "open_very_far"],
    opening_at_m={"blocked_near": 1.0, "open_near": 2.0, "open_far": 5.0,
                  "wall_far": 6.0, "open_very_far": 6.0},
    # Rays per strip, as offsets in image units from the strip's centre (a
    # strip is 0.4 wide).
    cone_rays=[-0.13, 0.0, 0.13],
    # A move under short_below_m writes a wall one cell ahead of where it
    # stopped; looks cannot erase it.
    stop_wall=True,
    # A doorway is passed when a move's segment runs through it this close.
    door_cross_m=0.6,
    # One sighting: steer on its bearing, at this distance along it.
    single_ray_m=10.0,
    # Search targets: edges of unsearched ground reachable over known floor,
    # keeping a cell from walls; a blacklisted point removes its edge.
    frontier="search",
    frontier_min_cells=2,
    frontier_min_m=1.5,
    frontier_path_bias_m=2.0,
    blacklist_near_m=1.5,
    # A move's look ahead for "new ground" against "searched already".
    searched_ahead_m=4.0,
)

#: Every sentence a17 adds (R12).
WORDS_A17: Dict[str, Any] = {
    "searched": "searched already this way",
    "frontier": "unsearched ground ({cells} cells along its edge), {path:.0f} m away over "
                "known floor",
    "doorway": "doorway {label} (seen at step {step}), {path:.0f} m away over known floor",
}


def wording_sha_a17() -> str:
    """Identity of a17's parameters and added wording, for agent.sha()."""
    blob = json.dumps({"params_a17": PARAMS_A17, "words_a17": WORDS_A17}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class SpatialConfig:
    """One agent's memory: which wording it is shown and which a15 behaviours
    it has. `sha_segments()` is what agent.sha() appends for it, and must stay
    exactly what a13 and a14 were hashed with."""
    name: str
    triggers: Dict[str, str]
    a14_words: bool = False
    block_end_pose: bool = False
    block_within_deg: float = BLOCK_WITHIN_DEG
    toward: str = "bearing"
    toward_within_deg: float = TOWARD_WITHIN_DEG
    doorway_min_seen: int = 1
    doorway_ttl_steps: Optional[int] = None
    #: a16: the window after a move that did not get going; None uses
    #: block_within_deg for both kinds.
    block_within_deg_blocked: Optional[float] = None
    #: "size" (largest edges, at their centres), "goal_side" (a16) or
    #: "search" (a17: reachable edges of unsearched ground).
    frontier: str = "size"
    #: a17: a look's cone marks ground searched; stop walls; doors crossed.
    coverage: bool = False
    #: a17b: floor classes whose end writes a wall; None keeps PARAMS_A17's.
    floor_ends: Optional[Tuple[str, ...]] = None

    def sha_segments(self) -> List[str]:
        out = ["spatial:" + wording_sha()]
        if self.a14_words:
            out.append("spatial_a14:" + wording_sha_a14())
        if self.name == "a15":
            out.append("spatial_a15:" + wording_sha_a15())
        if self.name == "a16":
            out.append("spatial_a16:" + wording_sha_a16())
        if self.name in ("a17", "a17b"):
            out.append("spatial_a17:" + wording_sha_a17())
        if self.floor_ends is not None:
            out.append("floor_ends:" + ",".join(self.floor_ends))
        return out


A13 = SpatialConfig("a13", TRIGGERS_A13)
A14 = SpatialConfig("a14", WORDS_A14["triggers"], a14_words=True)
A15 = SpatialConfig("a15", WORDS_A14["triggers"], a14_words=True,
                    block_end_pose=PARAMS_A15["block_end_pose"],
                    block_within_deg=PARAMS_A15["block_within_deg"],
                    toward="open", toward_within_deg=PARAMS_A15["toward_open_within_deg"],
                    doorway_min_seen=PARAMS_A15["doorway_min_seen"],
                    doorway_ttl_steps=PARAMS_A15["doorway_ttl_steps"])
A16 = SpatialConfig("a16", WORDS_A14["triggers"], a14_words=True,
                    block_end_pose=PARAMS_A16["block_end_pose"],
                    block_within_deg=PARAMS_A16["block_within_deg_short"],
                    block_within_deg_blocked=PARAMS_A16["block_within_deg_blocked"],
                    toward="open", toward_within_deg=PARAMS_A16["toward_open_within_deg"],
                    doorway_min_seen=PARAMS_A16["doorway_min_seen"],
                    doorway_ttl_steps=PARAMS_A16["doorway_ttl_steps"],
                    frontier=PARAMS_A16["frontier"])
#: a17 keeps a16's block windows, wall-aware "toward" and doorway gate, with
#: a14's trigger wording (unused: a17 has no goal triggers).
A17 = SpatialConfig("a17", WORDS_A14["triggers"], a14_words=True,
                    block_end_pose=PARAMS_A17["block_end_pose"],
                    block_within_deg=PARAMS_A17["block_within_deg_short"],
                    block_within_deg_blocked=PARAMS_A17["block_within_deg_blocked"],
                    toward="open", toward_within_deg=PARAMS_A17["toward_open_within_deg"],
                    doorway_min_seen=PARAMS_A17["doorway_min_seen"],
                    doorway_ttl_steps=PARAMS_A17["doorway_ttl_steps"],
                    frontier=PARAMS_A17["frontier"], coverage=True)


#: a17b (a42 on): a17 without the wall at the end of an open_near strip. g05's
#: "bottom" maps to open_near and is a wall within 1.9 m on 3% of strips (R14),
#: yet the wall written 2.5 m out made the move ahead "searched already": on
#: s03, 279 toward moves in R15-R17K, the turn-arounds in the lobby
#: (eval/phase2/R17_doorway_first/s03_analysis.md).
A17B = replace(A17, name="a17b", floor_ends=("blocked_near", "wall_far"))


def config_for(orchestrator: Dict[str, Any]) -> SpatialConfig:
    """The memory an orchestrated agent's features name (agent.py)."""
    if orchestrator.get("memory") == "a17":
        return A17
    if orchestrator.get("memory") == "a17b":
        return A17B
    if orchestrator.get("memory") == "a15":
        return A15
    if orchestrator.get("memory") == "a16":
        return A16
    if orchestrator.get("goal_truth") or orchestrator.get("turn_rule"):
        return A14
    return A13


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


def strip_ray_offsets(strip: str, du: Iterable[float]) -> List[float]:
    """a17: degrees left of ahead for rays spread across one strip, `du` image
    units either side of its centre (pinhole, as strip_offset)."""
    u0 = (2 - STRIPS.index(strip)) * 0.4
    t = math.tan(math.radians(FOV_DEG / 2.0))
    return [math.degrees(math.atan((u0 + d) * t)) for d in du]


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
    last_seen: int = -1


@dataclass
class Look:
    """a17: what one look's cone covered. `cells` excludes the strip the goal
    was reported in; `new` of them had never been searched before."""
    step: int
    cells: frozenset
    new: int

    @property
    def revisit(self) -> float:
        """Share of the cone already searched: 'seen this view before'."""
        return 1.0 - self.new / len(self.cells) if self.cells else 1.0


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
    #: a17: ground searched (seen with no goal in it), walls written where a
    #: move stopped (never erased by a look), and each look's cone.
    seen: Dict[Tuple[int, int], int] = field(default_factory=dict)
    stop_wall: Dict[Tuple[int, int], int] = field(default_factory=dict)
    looks: List[Look] = field(default_factory=list)
    cfg: SpatialConfig = A13

    # -- folding ---------------------------------------------------------------

    def visit(self, step: int, where: Pose) -> None:
        self.trail.append((step, where[0], where[1], where[2]))
        c = cell(where[:2])
        self.visits.setdefault(c, []).append(step)
        self.wall.pop(c, None)
        self.stop_wall.pop(c, None)

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
            # a15: also where it stopped, the spot the next decision is made from.
            if self.cfg.block_end_pose and moved >= BLOCKED_BELOW_M:
                self.blocks.append(Block(after[0], after[1],
                                         action_heading(action, before[2]), step, moved))
            # a17: the move hit something one cell on from where it stopped.
            if self.cfg.coverage:
                c = cell(ahead(after[:2], action_heading(action, before[2]), CELL_M))
                if c not in self.visits:
                    self.stop_wall[c] = step
                    self.free.pop(c, None)

    def observe(self, step: int, where: Pose, perception: Optional[Dict[str, Any]]) -> None:
        """Fold one perceiver report taken at `where` into the map. Seen floor is
        weak evidence: a visit always overrides a wall mark, and a newer look
        overwrites an older one."""
        if not perception:
            return
        if self.cfg.coverage:
            self._observe_cone(step, where, perception)
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

    def _observe_cone(self, step: int, where: Pose, perception: Dict[str, Any]) -> None:
        """a17: each strip is a slice of the cone, cast as a few rays out to where
        the perceiver says its floor ends, or to a stop wall first. Floor that
        ends at a wall or a closed door writes a wall there; a stop wall is never
        erased. Ground under the cone is searched unless the goal was reported
        in that strip."""
        here = where[:2]
        goal = perception.get("goal")
        rng = PARAMS_A17["floor_range_m"]
        covered = set()
        for lane in perception.get("lanes") or []:
            strip = lane.get("strip")
            floor = lane.get("floor")
            if strip not in STRIPS or floor not in rng:
                continue
            reach = rng[floor]
            ends = floor in (self.cfg.floor_ends if self.cfg.floor_ends is not None
                             else PARAMS_A17["floor_ends"])
            door = lane.get("doorway")
            if door is True:
                door = "open"  # g03 flags a doorway without saying open or closed
            for off in strip_ray_offsets(strip, PARAMS_A17["cone_rays"]):
                heading = (where[2] + off) % 360.0
                d, cut = CELL_M / 2.0, False
                while d <= reach:
                    c = cell(ahead(here, heading, d))
                    if c in self.stop_wall:
                        cut = True
                        break
                    self.free[c] = step
                    self.wall.pop(c, None)
                    if goal != strip:
                        covered.add(c)
                    d += CELL_M / 2.0
                if ends and not cut and door != "open":
                    end = cell(ahead(here, heading, reach + CELL_M / 2.0))
                    if end not in self.visits:
                        self.wall[end] = step
                        self.free.pop(end, None)
            centre = (where[2] + strip_offset(strip)) % 360.0
            at = ahead(here, centre, PARAMS_A17["opening_at_m"][floor])
            if door == "open":
                self._add_opening(step, at)
            elif door == "closed":
                for o in self.openings:
                    if dist((o.x, o.y), at) < OPENING_MERGE_M:
                        o.closed = True
            self._close_openings(step, here, centre, reach)
        new = sum(1 for c in covered if c not in self.seen)
        for c in covered:
            self.seen.setdefault(c, step)
        self.looks.append(Look(step, frozenset(covered), new))
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
                o.last_seen = step
                return
        self.openings.append(Opening(p[0], p[1], step,
                                     label="ABCDEFGHJKLMNPQRSTUVWXYZ"[len(self.openings) % 24],
                                     last_seen=step))

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
        """Mark openings passed once the trail has come close to them (a17: once
        a move ran through them)."""
        for o in self.openings:
            if self.cfg.coverage:
                o.passed = self._crossed((o.x, o.y))
            elif any(dist((x, y), (o.x, o.y)) < OPENING_PASSED_M for _, x, y, _ in self.trail):
                o.passed = True

    def _crossed(self, p: Point) -> bool:
        """a17: some move's segment passes within door_cross_m of `p`, with `p`
        between its two ends. R11: 10 of 14 true doors were struck as passed
        because the drone came within 1.5 m of the near-side estimate."""
        for (_, x0, y0, _), (_, x1, y1, _) in zip(self.trail, self.trail[1:]):
            vx, vy = x1 - x0, y1 - y0
            n2 = vx * vx + vy * vy
            if n2 < 1e-6:
                continue
            t = ((p[0] - x0) * vx + (p[1] - y0) * vy) / n2
            if 0.0 < t < 1.0 and dist((x0 + t * vx, y0 + t * vy), p) < PARAMS_A17["door_cross_m"]:
                return True
        return False

    # -- queries ---------------------------------------------------------------

    def block_for(self, here: Point, heading: float) -> Optional[Block]:
        """The latest blocked or short move from about here, about this way."""
        hit = None
        for b in self.blocks:
            within = self.cfg.block_within_deg
            if self.cfg.block_within_deg_blocked is not None and b.kind == "blocked":
                within = self.cfg.block_within_deg_blocked
            if (dist(here, (b.x, b.y)) < BLOCK_NEAR_M
                    and abs(wrap(b.heading - heading)) < within):
                if hit is None or b.step > hit.step:
                    hit = b
        return hit

    def listed_openings(self, step: int) -> List[Opening]:
        """Doorways the strategist may be offered: not passed or closed; for a15
        also seen twice and seen within the last few steps (doorway gate)."""
        out = []
        for o in self.openings:
            if o.passed or o.closed or o.seen < self.cfg.doorway_min_seen:
                continue
            ttl = self.cfg.doorway_ttl_steps
            if ttl is not None and step - o.last_seen > ttl:
                continue
            out.append(o)
        return out

    def visits_at(self, p: Point) -> List[int]:
        return list(self.visits.get(cell(p), []))

    def goal_belief(self, since: int = -1,
                    until: Optional[int] = None) -> Optional[Tuple[float, float, int]]:
        """Where the goal probably is, from the perceiver's sightings: (x, y, step).

        The least-squares point nearest every ray, when the rays spread at least
        RAY_SPREAD_DEG and the point lies in front of each; otherwise the latest
        ray at its range class (a17: at single_ray_m, the range class being
        uninformative). `step` is the latest sighting it rests on. a17: only
        rays from step `since` on, the planner dropping those a look disproved.
        a20: only rays up to step `until`, the belief before a new sighting."""
        rays = [r for r in self.goal_rays
                if r.step >= since and (until is None or r.step <= until)]
        if not rays:
            return None
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
        if self.cfg.coverage:
            p = ahead((last.x, last.y), last.heading, PARAMS_A17["single_ray_m"])
            return p[0], p[1], last.step
        p = ahead((last.x, last.y), last.heading, GOAL_RANGE_M.get(last.range, 10.0))
        return p[0], p[1], last.step

    def goal_rays_since(self, since: int) -> int:
        return sum(1 for r in self.goal_rays if r.step >= since)

    def covered(self, p: Point, step: int) -> bool:
        """a17: whether the look at `step` searched the cell `p` lies in (its
        cone reached it and the goal was not reported in that strip)."""
        look = next((l for l in reversed(self.looks) if l.step == step), None)
        return look is not None and cell(p) in look.cells

    def faces_unseen(self, p: Point, where: Pose,
                     perception: Optional[Dict[str, Any]]) -> bool:
        """a17: a look from `where` that should have shown a goal at `p` and did
        not. The perceiver reports the goal whenever it is in view, at any
        distance (R9-R11, 612 of 612): so `p` within the cone, the strip toward
        it reading floor open past where its floor would end at a wall, and no
        wall the map knows on the line, means the goal is not at `p`."""
        if not perception or perception.get("goal") in STRIPS:
            return False
        rel = wrap(bearing(where[:2], p) - where[2])
        if abs(rel) > FOV_DEG / 2.0 - 4.0:
            return False
        lane = next((l for l in perception.get("lanes") or []
                     if l.get("strip") == strip_for(rel)), None)
        if lane is None or lane.get("floor") not in PARAMS_A17["open_floor"]:
            return False
        d, far = CELL_M / 2.0, dist(where[:2], p)
        while d < far:
            c = cell(ahead(where[:2], bearing(where[:2], p), d))
            if (c in self.wall or c in self.stop_wall) and c not in self.visits:
                return False
            d += CELL_M / 2.0
        return True

    def last_look(self) -> Optional[Look]:
        return self.looks[-1] if self.looks else None

    # -- a17: reachability and search targets ----------------------------------

    def _blocked_cell(self, c: Tuple[int, int]) -> bool:
        return c in self.wall or c in self.stop_wall

    def reach(self, here: Point,
              parent: Optional[Dict[Tuple[int, int], Tuple[int, int]]] = None
              ) -> Dict[Tuple[int, int], float]:
        """Path length in metres from `here` to every known-floor cell a path
        over visited or seen-free cells reaches, keeping one cell clear of walls
        (a visited cell is always allowed: the drone has been there). `parent`,
        if given, is filled with each cell's previous cell on its path."""
        def ok(c: Tuple[int, int]) -> bool:
            if c in self.visits:
                return True
            if c not in self.free or self._blocked_cell(c):
                return False
            return not any(self._blocked_cell((c[0] + dx, c[1] + dy))
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        start = cell(here)
        out = {start: 0.0}
        todo = [start]
        diag = CELL_M * math.sqrt(2.0)
        # Uniform-ish costs: a plain breadth-first pass, relaxed once more.
        while todo:
            nxt = []
            for c in todo:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        n = (c[0] + dx, c[1] + dy)
                        cost = out[c] + (diag if dx and dy else CELL_M)
                        if (n not in out or cost < out[n] - 1e-9) and ok(n):
                            out[n] = cost
                            if parent is not None:
                                parent[n] = c
                            nxt.append(n)
            todo = nxt
        return out

    def search_frontiers(self, here: Point, blacklist: Iterable[Point] = (),
                         limit: int = 3) -> List[Tuple[Point, int, float]]:
        """a17: edges of unsearched ground a known path reaches, as (point, edge
        cells, path metres), best first: edge cells / (path + bias). Each edge is
        offered one cell short of its reachable cell nearest the drone, on the
        path there: an edge cell can sit in a wall the map has not seen (R11
        geometry: 10 of 38 top edges did)."""
        parent: Dict[Tuple[int, int], Tuple[int, int]] = {}
        reach = self.reach(here, parent)
        edge = set()
        for c in reach:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                if n not in self.seen and n not in self.visits and not self._blocked_cell(n):
                    edge.add(c)
                    break
        black = list(blacklist)
        clusters: List[List[Tuple[int, int]]] = []
        done = set()
        for c in sorted(edge):
            if c in done:
                continue
            group, todo = [], [c]
            done.add(c)
            while todo:
                cur = todo.pop()
                group.append(cur)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        n = (cur[0] + dx, cur[1] + dy)
                        if n in edge and n not in done:
                            done.add(n)
                            todo.append(n)
            clusters.append(group)
        out = []
        for g in clusters:
            if len(g) < PARAMS_A17["frontier_min_cells"]:
                continue
            pts = [((c[0] + 0.5) * CELL_M, (c[1] + 0.5) * CELL_M) for c in g]
            if any(dist(p, b) < PARAMS_A17["blacklist_near_m"] for p in pts for b in black):
                continue
            far = [(reach[c], c) for c, p in zip(g, pts)
                   if dist(here, p) >= PARAMS_A17["frontier_min_m"]]
            if not far:
                continue
            path, c = min(far)
            back = parent.get(c, c)
            p = ((back[0] + 0.5) * CELL_M, (back[1] + 0.5) * CELL_M)
            if dist(here, p) < PARAMS_A17["frontier_min_m"]:
                p = ((c[0] + 0.5) * CELL_M, (c[1] + 0.5) * CELL_M)
            out.append((p, len(g), path))
        out.sort(key=lambda t: -t[1] / (t[2] + PARAMS_A17["frontier_path_bias_m"]))
        return out[:limit]

    def reachable(self, p: Point, reach: Dict[Tuple[int, int], float],
                  within_m: float = 1.5) -> Optional[float]:
        """a17: path metres to the nearest reached cell within `within_m` of `p`
        (a doorway sits on its wall, so its own cell is never reached), or None."""
        best = None
        for c, d in reach.items():
            q = ((c[0] + 0.5) * CELL_M, (c[1] + 0.5) * CELL_M)
            if dist(q, p) <= within_m and (best is None or d < best):
                best = d
        return best

    def frontiers(self, here: Point, limit: int = 3,
                  goal: Optional[Point] = None) -> List[Point]:
        """Centres of seen-free, unvisited ground that borders unknown ground,
        largest first. a16 (cfg.frontier "goal_side", with `goal`): each edge's
        cell nearest the goal instead, nearest the goal first."""
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
        if self.cfg.frontier == "goal_side" and goal is not None:
            near = []
            for g in clusters:
                p = min((((c[0] + 0.5) * CELL_M, (c[1] + 0.5) * CELL_M) for c in g),
                        key=lambda q: dist(q, goal))
                if dist(here, p) > 2.0:
                    near.append(p)
            near.sort(key=lambda q: (dist(q, goal), dist(here, q)))
            return near[:limit]
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
            "openings": [dict({"label": o.label, "x": round(o.x, 2), "y": round(o.y, 2),
                               "step": o.step, "seen": o.seen, "passed": o.passed,
                               "closed": o.closed},
                              **({"last_seen": o.last_seen}
                                 if self.cfg.doorway_ttl_steps is not None else {}))
                         for o in self.openings],
            "loop_score": round(self.loop_score(), 2),
        }


def rebuild(records: Iterable[Dict[str, Any]], manifest: Dict[str, Any],
            perception_now: Optional[Dict[str, Any]] = None,
            cfg: SpatialConfig = A13) -> SpatialMemory:
    """The memory as of this decision, from the run's earlier decision records.

    Each record contributes the pose it was decided at, its perceiver report
    and, against the next record's pose (or the current manifest's), what its
    move did. A failed decision still gives a pose. `perception_now` is the
    perceiver's report for the current frame, folded in last. `cfg` is the
    agent's memory (a13 and a14 share one)."""
    mem = SpatialMemory(cfg=cfg)
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


def targets(mem: SpatialMemory, here: Pose, step: int,
            goal_at: Optional[Point] = None) -> List[Target]:
    """The strategist's menu, built by code: the goal belief, doorways not yet
    passed or closed, unexplored edges, and the last place that still had an
    untried open way. With `goal_at` (a14), the goal is listed at its true
    position on every step instead."""
    out: List[Target] = []
    belief = mem.goal_belief()
    if goal_at is not None:
        out.append(Target("goal", "goal", goal_at[0], goal_at[1],
                          WORDS_A14["goal_label"], step))
    elif belief is not None:
        out.append(Target("goal", "goal", belief[0], belief[1],
                          "the goal (last seen at step {0})".format(belief[2]), step))
    for o in mem.listed_openings(step):
        out.append(Target("doorway_" + o.label, "opening", o.x, o.y,
                          "doorway {0} (seen at step {1})".format(o.label, o.step), step))
    for k, p in enumerate(mem.frontiers(here[:2], goal=goal_at)):
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


def target_still_valid(mem: SpatialMemory, target: Optional[Target], here: Point,
                       goal_at: Optional[Point] = None) -> bool:
    """False once a target is reached, or a doorway target is closed or passed.
    A goal or doorway target follows its latest estimate (a14: the goal's true
    position)."""
    return target_state(mem, target, here, goal_at) == "open"


def target_state(mem: SpatialMemory, target: Optional[Target], here: Point,
                 goal_at: Optional[Point] = None) -> str:
    """'open', 'reached' or 'closed' (a doorway closed or passed, or no target)."""
    if target is None:
        return "closed"
    if target.kind == "opening":
        label = target.id.split("_", 1)[1]
        step = mem.trail[-1][0] if mem.trail else 0
        o = next((o for o in mem.listed_openings(step) if o.label == label), None)
        if o is None:
            return "closed"
        target.x, target.y = o.x, o.y
    if target.kind == "goal":
        if goal_at is not None:
            target.x, target.y = goal_at
        else:
            belief = mem.goal_belief()
            if belief is not None:
                target.x, target.y = belief[0], belief[1]
    return "open" if dist(here, (target.x, target.y)) >= TARGET_REACHED_M else "reached"


# --- projection onto the actions -----------------------------------------------

def strip_for(theta_deg: float) -> str:
    """The image strip an action's heading falls in."""
    return min(STRIPS, key=lambda s: abs(strip_offset(s) - theta_deg))


def not_open(mem: SpatialMemory, here: Pose, action: Dict[str, Any],
              lanes: Dict[Any, Dict[str, Any]]) -> bool:
    """Whether project() will note this forward action blocked, stopped short or
    walled: the same tests, in the same order."""
    if mem.block_for(here[:2], action_heading(action, here[2])) is not None:
        return True
    lane = lanes.get(strip_for(float(action.get("theta_deg") or 0.0))) or {}
    return lane.get("floor") == "blocked_near"


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
        if mem.cfg.toward == "open":
            # a15: only an action the map does not call blocked, stopped short
            # or walled may be "toward your target" (R10: 36 walled picks).
            flying = [a for a in flying if not not_open(mem, here, a, lanes)]
        best = min(flying, key=lambda a: abs(wrap(action_heading(a, here[2]) - want)),
                   default=None)
        side = [a for a in flying
                if wrap(action_heading(a, here[2]) - here[2]) * wrap(want - here[2]) > 0]
        if (best is not None and abs(wrap(action_heading(best, here[2]) - want))
                <= mem.cfg.toward_within_deg):
            toward = int(best["index"])
        elif mem.cfg.coverage and side:
            # a17: nothing in the fan points at the target; the sharpest open
            # move on its side does (R11: 185 steps with "toward" on [0] not
            # followed, +158 m away from the goal).
            toward = int(max(side, key=lambda a: abs(float(a.get("theta_deg") or 0.0)))["index"])
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
            if not mem.cfg.coverage or _unsearched_ahead(mem, land, heading):
                out.append(WORDS["new_ground"])
            else:
                out.append(WORDS_A17["searched"])
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
              menu: List[Target], trigger: str,
              goal_at: Optional[Point] = None) -> str:
    """What the strategist is told, in words: no coordinates, no degrees.
    With `goal_at` (a14), where the goal is, from its true position."""
    here = pose_xyh(manifest.get("pose"))
    step = int(manifest.get("step", 0))
    lines = ["Step {0}. You are asked now because {1}.".format(step, trigger)]
    goal = (perception or {}).get("goal")
    if goal_at is not None:
        if goal in STRIPS:
            lines.append(WORDS_A14["goal_in_image"].format(
                strip=goal.replace("_", " "),
                range=WORDS["range"].get((perception or {}).get("goal_range"),
                                         "distance unknown")))
        else:
            lines.append(WORDS_A14["goal_not_in_image"])
        if here is not None:
            lines.append(WORDS_A14["goal_known"].format(where=where_words(here, goal_at)))
    elif goal in STRIPS:
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
            every: int = 8, goal_at: Optional[Point] = None,
            words: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Why the strategist should be asked this step, or None to keep the target.
    Worded from `words` (a13: TRIGGERS_A13; a14: WORDS_A14["triggers"])."""
    key = trigger_key(mem, manifest, perception, current, last_called, last_perception,
                      every, goal_at)
    return None if key is None else (words or TRIGGERS_A13)[key]


def trigger_key(mem: SpatialMemory, manifest: Dict[str, Any],
                perception: Optional[Dict[str, Any]], current: Optional[Target],
                last_called: Optional[int], last_perception: Optional[Dict[str, Any]],
                every: int = 8, goal_at: Optional[Point] = None) -> Optional[str]:
    """The key in TRIGGERS_A13 of why the strategist should be asked, or None."""
    step = int(manifest.get("step", 0))
    here = pose_xyh(manifest.get("pose"))
    goal_now = (perception or {}).get("goal") in STRIPS
    if last_called is None:
        return "start"
    if mem.blocks and mem.blocks[-1].step == step - 1 and mem.blocks[-1].kind == "blocked":
        return "blocked"
    if goal_now and (last_perception or {}).get("goal") not in STRIPS:
        return "goal_in_view"
    if mem.goal_rays and not goal_now and mem.goal_rays[-1].step == step - 3:
        return "goal_out_of_view"
    if any(o.last_seen == step and o.seen == mem.cfg.doorway_min_seen for o in mem.openings):
        return "new_doorway"
    if current is not None and here is not None:
        state = target_state(mem, current, here[:2], goal_at)
        if state != "open":
            return "target_" + state
    if mem.loop_score() >= 0.5 and step - last_called >= 3:
        return "loop"
    if step - last_called >= every:
        return "regular"
    return None


# --- turn rule (a14) -------------------------------------------------------------

#: The notes that say a forward move is not open.
_NOT_OPEN = (WORDS["blocked"].split(" (")[0], WORDS["short"].split(" (")[0],
             WORDS["wall_seen"])


def _unsearched_ahead(mem: SpatialMemory, land: Point, heading: float) -> bool:
    """a17: whether the ground a move lands facing has some cell not yet
    searched within searched_ahead_m (a wall cell ends the look)."""
    d = CELL_M / 2.0
    while d <= PARAMS_A17["searched_ahead_m"]:
        c = cell(ahead(land, heading, d))
        if c in mem.wall or c in mem.stop_wall:
            return False
        if c not in mem.seen and c not in mem.visits:
            return True
        d += CELL_M / 2.0
    return False


def hide_turn_around(mem: SpatialMemory, manifest: Dict[str, Any],
                     tags: Dict[int, List[str]]) -> List[int]:
    """The turn-around indices to leave off this step (a14, operator 2026-10-24):
    the previous decision was a turn-around and some forward action carries no
    blocked, stopped-short or wall note. R9: every spin_failure alternated
    turn-arounds while moves ahead were open."""
    step = int(manifest.get("step", 0))
    previous = [s for s, _, _, _ in mem.trail if s < step]
    if not previous or not mem.turn_arounds or mem.turn_arounds[-1] != max(previous):
        return []
    actions = manifest.get("actions") or []
    turn = [int(a["index"]) for a in actions if a.get("turn_around")]
    # a17: never hide a turn-around that alone carries "toward your target".
    if mem.cfg.coverage and any(WORDS["toward_target"] in tags.get(i, []) for i in turn):
        return []
    forward_open = any(
        not any(w.startswith(_NOT_OPEN) for w in tags.get(int(a["index"]), []))
        for a in actions if not a.get("turn_around"))
    return turn if forward_open else []
