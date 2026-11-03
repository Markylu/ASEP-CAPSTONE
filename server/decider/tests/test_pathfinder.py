"""a63's route planner on hand-built maps (docs/research/pathfinder-plan.md).

    python -m pytest server/decider/tests -q
"""
from __future__ import annotations

import math

from server.decider import agent, orchestrator, planner, spatial

P = agent.PATHFINDER_A63
C = spatial.CELL_M


def centre(c):
    return (c[0] + 0.5) * C, (c[1] + 0.5) * C


def pose(c, heading=0.0):
    x, y = centre(c)
    return x, y, heading


def manifest_at(c, step, heading=0.0):
    x, y = centre(c)
    return {"step": step, "pose": {"position": [x, 1.75, -y],
                                   "yaw": math.radians(heading - 90.0)}}


def corridor(x0, x1, half=1, side_walls=True):
    """A corridor along +x: visited cells on y = 0 from x0 to x1, free cells
    either side, perceiver walls along both sides."""
    mem = spatial.SpatialMemory(cfg=spatial.A17D)
    for x in range(x0, x1 + 1):
        mem.visits[(x, 0)] = [x]
        mem.trail.append((x,) + centre((x, 0)) + (0.0,))
        for y in range(-half, half + 1):
            mem.free[(x, y)] = x
        if side_walls:
            mem.wall[(x, half + 1)] = x
            mem.wall[(x, -half - 1)] = x
    return mem


def all_walls():
    return {"reason": "", "goal": "not_visible", "goal_range": None,
            "lanes": [{"strip": s, "floor": "blocked_near", "floor_end": "no_floor",
                       "doorway": False} for s in spatial.STRIPS]}


def test_nose_on_wall_is_written_across_the_span():
    mem = corridor(0, 3, side_walls=False)
    mem.observe(4, pose((3, 0)), all_walls())
    xs = sorted({c[0] for c in mem.wall})
    ys = sorted({c[1] for c in mem.wall})
    assert xs == [4], xs                      # one wall row, one cell ahead
    # Under 1 m the five strips span about 1.8 m: three cells, plus one cell
    # beyond each end. a17b alone wrote the three.
    assert ys[-1] - ys[0] >= 3, ys
    cm = spatial.CostMap(mem, [], agent.PATHFINDER_A63)
    assert all(cm.cost((4, y)) is None for y in range(ys[0] - 1, ys[-1] + 2)), "sealed ends"


def test_sealed_exit_wall_routes_back_out():
    mem = corridor(0, 3)
    mem.observe(4, pose((3, 0)), all_walls())
    goal = centre((8, 0))
    plan = planner.pathfind(mem, {"step": 4, "pose": None}, [], goal, P)
    assert plan.fallback == "no_pose"
    plan = planner.pathfind(mem, manifest_at((3, 0), 4), [], goal, P)
    assert plan.fallback == "none"
    assert plan.path[1][0] < 3, plan.path[:4]           # the first step goes back
    assert all(not (c[0] in (4, 5) and abs(c[1]) <= 2) for c in plan.path), plan.path
    assert plan.waypoint is not None and plan.waypoint[0] < centre((3, 0))[0]


def test_door_gap_stays_open_and_waypoint_goes_through_it():
    mem = spatial.SpatialMemory(cfg=spatial.A17D)
    for y in range(-6, 7):
        if abs(y) <= 1:
            mem.free[(5, y)] = 1          # looked through the door
            mem.free[(6, y)] = 1
        else:
            mem.wall[(5, y)] = 1
    for x in range(0, 5):
        for y in range(-6, 7):
            mem.free[(x, y)] = 1
    here = (2, 3)
    mem.visits[here] = [1]
    goal = centre((9, 0))
    plan = planner.pathfind(mem, manifest_at(here, 2), [], goal, P)
    assert plan.fallback == "none"
    through = [c for c in plan.path if c[0] == 5]
    assert through and all(abs(c[1]) <= 1 for c in through), plan.path
    # The waypoint is the farthest route point in a straight line: on or
    # past the door's row, so "toward" points through the gap, not at the jamb.
    wp = plan.waypoint
    assert wp is not None and wp[0] >= centre((4, 0))[0], wp
    cm = spatial.CostMap(mem, [], P)
    assert cm.passable_segment(centre(here), wp)


def test_soft_fallback_lifts_perceiver_walls_not_stop_walls():
    goal = centre((9, 0))
    mem = spatial.SpatialMemory(cfg=spatial.A17D)
    mem.visits[(0, 0)] = [1]
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if max(abs(dx), abs(dy)) == 2:
                mem.wall[(dx, dy)] = 1
    plan = planner.pathfind(mem, manifest_at((0, 0), 3), [], goal, P)
    assert plan.fallback == "soft" and plan.path[-1] == (9, 0)
    mem.stop_wall = dict(mem.wall)
    mem.wall = {}
    plan = planner.pathfind(mem, manifest_at((0, 0), 3), [], goal, P)
    assert plan.fallback == "frontier"


def records_flat(n, path_m=10.0, turn=False):
    out = []
    for s in range(n):
        action = {"index": 3, "r": 1.7, "theta_deg": 0.0, "turn_around": False}
        if turn:
            action = {"index": 0, "r": 0.0, "theta_deg": 180.0, "turn_around": True}
        out.append({"step": s, "index": action["index"],
                    "manifest": dict(manifest_at((0, 0), s), actions=[action]),
                    "planner": {"path_m": path_m, "stall": []}})
    return out


def test_stall_rule_fires_only_after_flat_steps_on_a_forward_move():
    mem = spatial.SpatialMemory(cfg=spatial.A17D)
    mem.visits[(0, 0)] = [0]
    goal = centre((9, 0))
    plan = planner.pathfind(mem, manifest_at((0, 0), 5), records_flat(5), goal, P)
    assert plan.stall, "five flat steps on a forward move add stall cells"
    assert all(c[0] >= 1 for c in plan.stall), plan.stall
    assert not planner.pathfind(mem, manifest_at((0, 0), 4), records_flat(4), goal, P).stall
    assert not planner.pathfind(mem, manifest_at((0, 0), 5), records_flat(5, turn=True),
                                goal, P).stall
    # Once added, the cells come back from the record alone.
    rec = records_flat(5) + [{"step": 5, "index": 3, "manifest": manifest_at((0, 0), 5),
                              "planner": plan.to_dict()}]
    assert set(planner.stall_cells_from(rec, 6)) == {tuple(c) for c in plan.stall}


def test_cost_map_never_seals_visited_or_free_cells():
    mem = corridor(0, 6)
    mem.observe(7, pose((6, 0)), all_walls())
    cm = spatial.CostMap(mem, [], P)
    for c in list(mem.visits) + list(mem.free):
        assert cm.cost(c) is not None, c
    assert cm.cost((7, 0)) is None and cm.cost((8, 0)) is None  # the wall and beyond
    assert cm.cost((20, 20)) == P["unknown_cost"]


def test_plan_line_for_a_route_point_is_the_goal_sentence():
    here = (0.0, 0.0, 0.0)
    t = spatial.Target("path", "path", 3.0, 0.0, P["words"]["path"], 1)
    assert orchestrator.plan_line(t, "approach", here, True) == \
        spatial.WORDS_A14["plan_goal"].format(mode="approach")


def test_earlier_agents_keep_their_sha():
    assert agent.get("a49").sha() == "83f7a6a19b01"
    assert agent.get("a37").sha() == "a07b58847180"
    assert agent.get("a63").sha() != agent.get("a64").sha()
    assert "q03" not in agent.describe("a63")["subagent_prompts"]


def test_a70_route_behind_sentence_only_when_toward_is_on_the_turn_around():
    here = (0.0, 0.0, 0.0)
    t = spatial.Target("path", "path", -3.0, 0.0, P["words"]["path"], 1)
    notes = agent.NAVIGATOR_A70
    manifest = {"actions": [{"index": 0, "turn_around": True}, {"index": 3}]}
    assert spatial.toward_on_turn_around(manifest, {0: [spatial.WORDS["toward_target"]]})
    assert not spatial.toward_on_turn_around(manifest, {3: [spatial.WORDS["toward_target"]]})
    goal = spatial.WORDS_A14["plan_goal"].format(mode="approach")
    assert orchestrator.plan_line(t, "approach", here, True, notes["route_behind"]) == \
        goal + "\n" + notes["route_behind"]
    assert orchestrator.plan_line(t, "approach", here, True, None) == goal


def test_a70_route_critic_fires_only_against_an_open_toward_move():
    words = agent.NAVIGATOR_A70["critic_route"]
    toward, wall = spatial.WORDS["toward_target"], spatial.WORDS["wall_seen"]
    manifest = {"actions": [{"index": 0, "turn_around": True}, {"index": 3}, {"index": 4}]}
    # The pick ignores an open "toward" on the turn-around: a note naming it.
    assert spatial.critique_route(manifest, {0: [toward], 3: ["new ground"]}, 3, words) == \
        words.format(i=3, j=0)
    # The pick is the "toward" move: nothing to say.
    assert spatial.critique_route(manifest, {3: [toward]}, 3, words) is None
    # The only "toward" move carries a wall note: nothing to say.
    assert spatial.critique_route(manifest, {0: [toward, wall], 3: []}, 3, words) is None
    # No "toward" anywhere: nothing to say.
    assert spatial.critique_route(manifest, {3: ["new ground"], 4: []}, 3, words) is None


def test_a70_is_a66_plus_the_navigator_notes():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a70").sha() != agent.get("a66").sha()
    a66 = agent.get("a66").features["orchestrator"]
    a70 = agent.get("a70").features["orchestrator"]
    assert {k: v for k, v in a70.items() if k not in ("critic", "navigator_notes")} == \
        {k: v for k, v in a66.items() if k != "critic"}
    assert a70["critic"] == "route" and a66["critic"] == "none"
