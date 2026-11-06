"""a63's route planner on hand-built maps (docs/research/pathfinder-plan.md).

    python -m pytest server/decider/tests -q
"""
from __future__ import annotations

import math
from dataclasses import replace as replace_cfg

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


# --- a72 (R31): a17h, one look is soft; route commitment ---------------------------

H = spatial.A17H
P72 = agent.PATHFINDER_A72


def door_look(door="open", floor="open_far", end="lower"):
    """Every strip open, the centre strip with a doorway verdict."""
    return {"reason": "", "goal": "not_visible", "goal_range": None,
            "lanes": [{"strip": s, "floor": floor, "floor_end": end,
                       "doorway": door if s == "centre" else False} for s in spatial.STRIPS]}


def open_field(cfg, x0=0, x1=4, half=3):
    mem = spatial.SpatialMemory(cfg=cfg)
    for x in range(x0, x1 + 1):
        for y in range(-half, half + 1):
            mem.free[(x, y)] = 0
    return mem


def test_a17h_one_doorway_look_is_soft_and_two_poses_make_it_strong():
    mem = open_field(H)
    mem.visits[(2, 0)] = [1]
    mem.observe(1, pose((2, 0)), door_look())
    o = mem.openings[0]
    assert len(o.sight_poses) == 1 and not mem.opening_confirmed(o)
    # Floor beyond open_far's 4 m reach is claimed by the doorway alone: soft.
    far = spatial.cell(spatial.ahead(centre((2, 0)), 0.0, 5.5))
    assert far in mem.soft_door_cells() and far not in mem.free and far not in mem.free_near
    cm = spatial.CostMap(mem, [], P72)
    assert cm.cost(far) == P72["unknown_cost"] and "soft_door" in cm.counts()
    # Under a17f the same look wrote strong floor there.
    mem_f = open_field(spatial.A17F)
    mem_f.visits[(2, 0)] = [1]
    mem_f.observe(1, pose((2, 0)), door_look())
    assert far in mem_f.free_near
    # A second look from the same spot (a turn-around) does not confirm.
    mem.visits[(2, 0)].append(2)
    mem.observe(2, pose((2, 0)), door_look())
    assert not mem.opening_confirmed(mem.openings[0])
    # From a pose 1 m away it does, and the floor through the gap is strong.
    mem.visits[(4, 0)] = [3]
    mem.observe(3, pose((4, 0)), door_look())
    o = mem.openings[0]
    assert mem.opening_confirmed(o) and o.seen == 3
    near = spatial.cell(spatial.ahead(centre((4, 0)), 0.0, 5.0))
    assert near in mem.free_near and not mem.soft_door_cells()


def test_a17h_soft_doorway_floor_is_never_sealed_but_seals_nothing():
    mem = open_field(H, x1=4)
    mem.visits[(2, 0)] = [1]
    # Jambs either side of the gap, two cells past the open_far reach.
    gap = spatial.cell(spatial.ahead(centre((2, 0)), 0.0, 5.5))
    mem.wall[(gap[0], gap[1] + 1)] = 0
    mem.wall[(gap[0], gap[1] - 1)] = 0
    cm = spatial.CostMap(mem, [], P72)
    assert cm.cost(gap) is None, "unknown beside two walls is sealed"
    mem.observe(1, pose((2, 0)), door_look())
    cm = spatial.CostMap(mem, [], P72)
    assert cm.cost(gap) == P72["unknown_cost"], "the reported gap stays passable"
    # The soft cells are not known ground: a wall beyond them still seals.
    beyond = (gap[0] + 4, gap[1] + 1)
    mem.wall[beyond] = 0
    cm = spatial.CostMap(mem, [], P72)
    assert cm.cost((beyond[0], beyond[1] - 1)) is None


def test_a17h_nose_on_wall_is_firm_only_after_a_second_pose():
    mem = corridor(0, 3, side_walls=False)
    mem.cfg = H
    mem.observe(4, pose((3, 0)), all_walls())
    assert mem.wall and not mem.firm_wall, "one read: a perceiver wall"
    mem.observe(5, pose((3, 0)), all_walls())
    assert not mem.firm_wall, "the same spot again is the same look"
    mem.visits[(3, 2)] = [6]
    mem.observe(6, pose((3, 2)), all_walls())
    assert mem.firm_wall, "a second read from 1.7 m away makes it firm"
    assert all(c[0] == 4 for c in mem.firm_wall), sorted(mem.firm_wall)
    # Firm cells left the perceiver layer; a visit alone erases them.
    assert not (set(mem.firm_wall) & set(mem.wall))
    c = next(iter(mem.firm_wall))
    mem.visit(7, pose(c))
    assert c not in mem.firm_wall


def test_a17h_single_read_wall_is_popped_by_seen_floor_as_a17b():
    mem = corridor(0, 3, side_walls=False)
    mem.cfg = H
    mem.observe(4, pose((3, 0)), all_walls())
    assert (4, 0) in mem.wall
    mem.observe(5, pose((3, 0)), door_look(door=False))   # floor seen straight ahead
    assert (4, 0) not in mem.wall, "a17b: a newer look overwrites"
    mem_f = corridor(0, 3, side_walls=False)
    mem_f.cfg = spatial.A17F
    mem_f.observe(4, pose((3, 0)), all_walls())
    assert (4, 0) in mem_f.firm_wall
    mem_f.observe(5, pose((3, 0)), door_look(door=False))
    assert (4, 0) in mem_f.firm_wall, "a17f kept it"


def test_a17h_two_strong_closes_kill_an_opening():
    mem = open_field(H, x1=6)
    mem.visits[(2, 0)] = [1]
    mem.observe(1, pose((2, 0)), door_look())
    o = mem.openings[0]
    assert mem.soft_door_cells()
    mem.observe(2, pose((2, 0)), door_look(door="closed"))
    assert o.closed and not o.dead and not mem.soft_door_cells()
    mem.visits[(3, 0)] = [3]
    mem.observe(3, pose((3, 0)), door_look())
    assert not o.closed and o.seen == 2 and mem.soft_door_cells(), "one close: reopens"
    mem.visits[(4, 0)] = [4]
    mem.observe(4, pose((4, 0)), door_look(door="closed"))
    assert o.dead and o.closed, "closed from two poses 1 m apart: dead"
    mem.visits[(5, 0)] = [5]
    mem.observe(5, pose((5, 0)), door_look())
    assert o.dead and o.closed and o.seen == 2 and not mem.soft_door_cells()
    assert o not in mem.listed_openings(5)
    snap = mem.snapshot()
    assert snap["openings"][0]["dead"] and snap["cells_soft_door"] == 0


def test_a17h_nose_on_wall_over_the_opening_is_a_strong_close():
    mem = open_field(H, x1=8)
    mem.visits[(2, 0)] = [1]
    mem.observe(1, pose((2, 0)), door_look())
    o = mem.openings[0]
    at = (o.x, o.y)
    # Walk up to it and read a wall nose-on where the doorway was reported.
    near = spatial.cell(spatial.ahead(at, 180.0, 1.2))
    mem.visits[near] = [2]
    mem.observe(2, pose(near), all_walls())
    assert o.closed and len(o.close_poses) == 1


def flat_records(step, cells, start=(0, 0)):
    action = {"index": 3, "r": 1.7, "theta_deg": 0.0, "turn_around": False}
    return [{"step": step - 1, "index": 3,
             "manifest": dict(manifest_at(start, step - 1), actions=[action]),
             "planner": {"path_m": 9.0, "fallback": "none", "stall": [],
                         "path_cells": [[c[0], c[1]] for c in cells]}}]


def test_commit_keeps_the_previous_route_unless_much_cheaper_or_left():
    goal = centre((9, 0))
    mem = open_field(H, x0=0, x1=9, half=3)
    mem.visits[(0, 0)] = [0]
    detour = [(0, 0), (1, 1), (2, 2), (3, 2), (4, 2), (5, 2), (6, 1), (7, 0), (8, 0), (9, 0)]
    plan = planner.pathfind(mem, manifest_at((0, 0), 1), flat_records(1, detour), goal, P72)
    assert plan.kept is True and plan.path == detour and plan.fresh_m is not None
    assert plan.to_dict()["kept"] is True
    # A fresh route a quarter cheaper wins.
    long = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3),
            (9, 3), (9, 2), (9, 1), (9, 0)]
    plan = planner.pathfind(mem, manifest_at((0, 0), 1), flat_records(1, long), goal, P72)
    assert plan.kept is False and plan.path != long
    # The previous route sealed on this step's map: not kept.
    mem.stop_wall[(4, 2)] = 1
    mem.free.pop((4, 2))
    plan = planner.pathfind(mem, manifest_at((0, 0), 1), flat_records(1, detour), goal, P72)
    assert plan.kept is False
    # The drone a cell beside the route is still on it: the rest is kept from
    # the nearest route cell on.
    mem.stop_wall.clear()
    mem.free[(4, 2)] = 0
    mem.visits[(3, 1)] = [0]
    plan = planner.pathfind(mem, manifest_at((3, 1), 1), flat_records(1, detour, (3, 1)),
                            goal, P72)
    assert plan.kept is True and plan.path[:2] == [(3, 1), (4, 2)], plan.path
    # Three cells off the route: left it.
    cm = spatial.CostMap(mem, [], P72, include=((0, 5), (9, 0)), start=(0, 5))
    assert planner.committed_route(cm, (0, 5), detour, (9, 0), P72["commit"]) is None
    assert planner.committed_route(cm, (0, 2), detour, (9, 0), P72["commit"]) is not None
    # No previous route (or commitment off): nothing recorded.
    assert planner.pathfind(mem, manifest_at((0, 0), 1), [], goal, P72).kept is None
    assert "kept" not in planner.pathfind(mem, manifest_at((0, 0), 1), flat_records(1, detour),
                                          goal, P).to_dict()


def test_a72_is_a66_plus_a17h_and_commit():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a72").sha() != agent.get("a66").sha()
    a66 = agent.get("a66").features["orchestrator"]
    a72 = agent.get("a72").features["orchestrator"]
    assert {k: v for k, v in a72.items() if k not in ("memory", "pathfinder")} == \
        {k: v for k, v in a66.items() if k not in ("memory", "pathfinder")}
    assert a72["memory"] == "a17h" and a72["pathfinder"]["commit"]
    assert spatial.A17H.two_pose and not spatial.A17H.firm_walls
    assert "two_pose:" in " ".join(spatial.A17H.sha_segments())


# --- a73 (R33): wall-turn rule and the cost map read against Round F ---------------

def test_strict_corners_refuse_a_diagonal_gap_in_a_wall_line():
    """A wall line y = 2 with cells (3, 2) and (5, 2) hard and (4, 2) unknown
    but sealed: without strict corners the 8-connected search may step
    diagonally past a hard cell; with them it must go round the line's end."""
    mem = spatial.SpatialMemory(cfg=spatial.A17I)
    for x in range(-2, 9):
        mem.visits[(x, 0)] = [1]
    for x in range(0, 8):
        if x != 4:
            mem.stop_wall[(x, 2)] = 1
    start, goal = (4, 0), (4, 4)
    cm = spatial.CostMap(mem, [], agent.PATHFINDER_A65)
    loose = planner.astar(cm, start, goal)
    cm73 = spatial.CostMap(mem, [], agent.PATHFINDER_A73)
    strict = planner.astar(cm73, start, goal, strict_corners=True)
    assert loose is not None and strict is not None
    # a73 seals (4, 2) (4-adjacent to hard cells) and its diagonal neighbours
    # on row 3 over the gap, so the strict route leaves the line by an end.
    assert cm73.cost((4, 2)) is None
    assert all(c[1] != 2 or c[0] in (-1, 8) or c[0] > 8 or c[0] < -1 for c in strict)
    for a, b in zip(strict, strict[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx and dy:
            assert cm73.cost((a[0] + dx, a[1])) is not None
            assert cm73.cost((a[0], a[1] + dy)) is not None


def test_seal_diagonal_closes_the_diagonal_neighbours_of_a_wall():
    mem = spatial.SpatialMemory(cfg=spatial.A17I)
    mem.visits[(0, 0)] = [1]
    mem.stop_wall[(3, 3)] = 1
    cm65 = spatial.CostMap(mem, [], agent.PATHFINDER_A65)
    cm73 = spatial.CostMap(mem, [], agent.PATHFINDER_A73)
    assert cm65.cost((4, 4)) == agent.PATHFINDER_A65["unknown_cost"] == 2.0
    assert cm73.cost((4, 4)) is None and cm73.cost((4, 3)) is None
    assert cm73.cost((5, 5)) == agent.PATHFINDER_A73["unknown_cost"] == 4.0


def _wall_turn_memory(cfg):
    """Two decisions: step 0 faced a wall (every strip blocked_near) at (0, 0)
    heading +x and turned around; step 1 is decided at the same spot heading
    -x, with the route's next point back through the wall at (3, 0)."""
    records = [{"step": 0, "index": 0, "manifest": manifest_at((0, 0), 0, 0.0) | {
        "actions": [{"index": 0, "turn_around": True, "theta_deg": 180.0}]},
        "perceiver": {"result": all_walls()}}]
    man = manifest_at((0, 0), 1, 180.0)
    man["actions"] = [{"index": 0, "turn_around": True, "theta_deg": 180.0, "r": 0.0}] + [
        {"index": i, "turn_around": False, "theta_deg": th, "r": 1.7}
        for i, th in ((1, 43.5), (2, 21.75), (3, 0.0), (4, -21.75), (5, -43.5))]
    # The wall the drone turned from runs on along its left (the target's
    # side): the left strips read it, the right ones open floor. Round F s03
    # dynamic seed 3 s36: the target-side moves carried wall or stopped-short
    # notes, so a17's side rule had nothing to tag and the turn-around got it.
    lanes = {"far_left": "blocked_near", "left": "blocked_near", "centre": "blocked_near",
             "right": "open_near", "far_right": "open_near"}
    floor = {"reason": "", "goal": "not_visible", "goal_range": None,
             "lanes": [{"strip": s, "floor": lanes[s],
                        "floor_end": "no_floor" if lanes[s] == "blocked_near" else "bottom",
                        "doorway": False} for s in spatial.STRIPS]}
    mem = spatial.rebuild(records, man, floor, cfg)
    # The route's next point lies back through the wall, on the walled side.
    target = spatial.Target("path", "path", *centre((3, -1)), "the next point", 1)
    return mem, man, target, floor


def test_wall_turn_moves_toward_off_the_turn_around_and_the_turn_rule_hides_it():
    mem, man, target, floor = _wall_turn_memory(spatial.A17I)
    assert mem.nose_on == [0] and mem.turn_arounds == [0]
    assert spatial.after_wall_turn(mem, 1)
    tags = spatial.project(mem, man, floor, target)
    assert spatial.WORDS["toward_target"] not in tags[0]
    assert spatial.WORDS["toward_target"] in tags[4] or spatial.WORDS["toward_target"] in tags[5]
    assert spatial.hide_turn_around(mem, man, tags) == [0]
    # a66's memory: the same step keeps the loop open.
    mem66, man66, target66, floor66 = _wall_turn_memory(spatial.A17F)
    tags66 = spatial.project(mem66, man66, floor66, target66)
    assert spatial.WORDS["toward_target"] in tags66[0]
    assert spatial.hide_turn_around(mem66, man66, tags66) == []


def test_a73_is_a66_plus_a17i_and_the_cost_map():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a73").sha() not in (agent.get("a66").sha(), agent.get("a72").sha())
    a66 = agent.get("a66").features["orchestrator"]
    a73 = agent.get("a73").features["orchestrator"]
    assert {k: v for k, v in a73.items() if k not in ("memory", "pathfinder")} == \
        {k: v for k, v in a66.items() if k not in ("memory", "pathfinder")}
    assert a73["memory"] == "a17i" and spatial.A17I.wall_turn and spatial.A17I.firm_walls
    assert spatial.A17I.near_free_m == spatial.A17G.near_free_m == 2.5
    assert a73["pathfinder"]["unknown_cost"] == 4.0 and a73["pathfinder"]["strict_corners"]
    assert "wall_turn" in spatial.A17I.sha_segments()


# --- a74 (R34): only ground the drone has stood on is known ----------------------

def test_a74_ray_floor_is_a_claim_a_wall_seals_and_door_floor_is_not():
    mem = spatial.SpatialMemory(cfg=spatial.A17I)
    mem.visits[(0, 0)] = [1]
    mem.stop_wall[(3, 1)] = 1
    for c in ((3, 0), (2, 1), (6, 6)):
        mem.free[c] = 1
        mem.free_near[c] = 1
    mem.door_free[(2, 1)] = 1
    cm73 = spatial.CostMap(mem, [], agent.PATHFINDER_A73)
    cm74 = spatial.CostMap(mem, [], agent.PATHFINDER_A74)
    # a73: near floor is known ground, cost 1, never sealed.
    assert cm73.cost((3, 0)) == 1.0 and cm73.cost((6, 6)) == 1.0
    # a74: floor beside a wall is sealed; elsewhere it costs far_free_cost;
    # a confirmed doorway's floor beside the wall stays passable; a visit is known.
    assert cm74.cost((3, 0)) is None
    assert cm74.cost((6, 6)) == agent.PATHFINDER_A74["far_free_cost"] == 2.0
    assert cm74.cost((2, 1)) == 2.0
    assert cm74.cost((0, 0)) == 1.0


def test_a74_is_a73_plus_the_visits_only_map():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a73").sha() == "7ce95fcbea92"
    a73 = agent.get("a73").features["orchestrator"]
    a74 = agent.get("a74").features["orchestrator"]
    assert {k: v for k, v in a74.items() if k != "pathfinder"} == \
        {k: v for k, v in a73.items() if k != "pathfinder"}
    assert a74["pathfinder"]["ray_floor_known"] is False
    assert agent.get("a74").sha() != agent.get("a73").sha()


# --- a75 (R35): a66 with the wall-turn rule alone ---------------------------------

def test_a75_is_a66_plus_the_wall_turn_rule_only():
    assert agent.get("a66").sha() == "de7f23d07186"
    a66 = agent.get("a66").features["orchestrator"]
    a75 = agent.get("a75").features["orchestrator"]
    assert {k: v for k, v in a75.items() if k != "memory"} == \
        {k: v for k, v in a66.items() if k != "memory"}
    assert a75["pathfinder"] is agent.PATHFINDER_A65
    assert spatial.A17J == replace_cfg(spatial.A17F, name="a17j", wall_turn=True)
    assert agent.get("a75").sha() not in {agent.get(a).sha() for a in ("a66", "a73", "a74")}
    # The rule itself, on a17j: the fixture of the a17i test.
    mem, man, target, floor = _wall_turn_memory(spatial.A17J)
    tags = spatial.project(mem, man, floor, target)
    assert spatial.WORDS["toward_target"] not in tags[0]
    assert spatial.hide_turn_around(mem, man, tags) == [0]


# --- a76 (R36): a66 with the door approach pose -------------------------------------

def _door_memory(seen=2):
    """Open floor the drone has crossed along y = 0 from x = 0 to 2, with a
    remembered open doorway at cell (6, 2): ahead, and off the straight line."""
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    for x in range(0, 3):
        mem.visits[(x, 0)] = [x]
        mem.trail.append((x,) + centre((x, 0)) + (0.0,))
    for x in range(-1, 12):
        for y in range(-4, 5):
            mem.free[(x, y)] = 0
            mem.free_near[(x, y)] = 0
    ox, oy = centre((6, 2))
    mem.openings.append(spatial.Opening(ox, oy, 1, seen=seen, label="A", last_seen=2))
    return mem


def test_door_approach_lines_up_then_goes_through():
    p = agent.PATHFINDER_A76
    d = p["door_approach"]
    mem = _door_memory()
    goal = centre((11, 2))
    # Off the doorway's line: the waypoint is pre_m out on it.
    plan = planner.pathfind(mem, manifest_at((2, 0), 3), [], goal, p)
    assert plan.door is not None and plan.door["label"] == "A", plan.to_dict()
    assert plan.door["phase"] == "line_up"
    ox, oy = centre((6, 2))
    assert abs(spatial.dist(plan.waypoint, (ox, oy)) - d["pre_m"]) < 0.9, plan.waypoint
    assert plan.waypoint[0] < ox                      # on the drone's side of it
    assert plan.to_dict()["door"]["label"] == "A"
    # On the line, three cells out: the waypoint is beyond the doorway.
    mem.visits[(3, 2)] = [3]
    plan = planner.pathfind(mem, manifest_at((3, 2), 4), [], goal, p)
    assert plan.door is not None and plan.door["phase"] == "through", plan.to_dict()
    assert plan.waypoint[0] > ox and abs(plan.waypoint[1] - oy) < 0.5, plan.waypoint
    # a66's planner never lays the waypoint on a doorway.
    plan = planner.pathfind(mem, manifest_at((2, 0), 3), [], goal, agent.PATHFINDER_A65)
    assert plan.door is None and "door" not in plan.to_dict()


def test_door_approach_gates_seen_twice_route_closed_and_budget():
    p = agent.PATHFINDER_A76
    goal = centre((11, 2))
    at = manifest_at((2, 0), 9)
    assert planner.pathfind(_door_memory(seen=1), at, [], goal, p).door is None   # one look
    mem = _door_memory()
    mem.openings[0].closed = True
    assert planner.pathfind(mem, at, [], goal, p).door is None                     # read shut
    mem = _door_memory()
    mem.openings[0].y -= 6 * C                        # 4 cells off the route
    assert planner.pathfind(mem, at, [], goal, p).door is None
    mem = _door_memory()
    spent = [{"step": s, "planner": {"door": {"label": "A"}}}
             for s in range(p["door_approach"]["budget_steps"])]
    assert planner.pathfind(mem, at, spent[:-1], goal, p).door is not None
    assert planner.pathfind(mem, at, spent, goal, p).door is None                  # budget spent
    # Beyond the doorway's plane: nothing to line up on.
    mem = _door_memory()
    assert planner.pathfind(mem, manifest_at((8, 2), 9), [], goal, p).door is None


def test_a76_is_a66_plus_the_door_approach():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a75").sha() == "81d682c1424b"
    a66 = agent.get("a66").features["orchestrator"]
    a76 = agent.get("a76").features["orchestrator"]
    assert {k: v for k, v in a76.items() if k != "pathfinder"} == \
        {k: v for k, v in a66.items() if k != "pathfinder"}
    assert {k: v for k, v in a76["pathfinder"].items() if k != "door_approach"} == \
        agent.PATHFINDER_A65
    assert agent.get("a76").sha() not in {agent.get(a).sha() for a in ("a66", "a73", "a74", "a75")}


# --- a77 (R37): doorway reads trusted by the look ------------------------------------

def _look(ends, doors):
    """A perceiver report: floor ends and doorway reads, far_left to far_right."""
    floors = {"no_floor": "blocked_near", "bottom": "open_near", "lower": "open_far",
              "middle": "open_far"}
    return {"reason": "", "goal": "not_visible", "goal_range": None,
            "lanes": [{"strip": s, "floor": floors[e], "floor_end": e, "doorway": d}
                      for s, e, d in zip(spatial.STRIPS, ends, doors)]}


SQUARE = _look(["lower"] * 5, [False, False, "open", False, False])
ALONG = _look(["middle", "middle", "lower", "bottom", "no_floor"], [False, False, "open", False, False])
EDGE = _look(["lower"] * 5, ["open", False, False, False, False])


def test_look_angle_is_small_square_on_and_large_along_a_wall():
    assert spatial.look_angle(SQUARE["lanes"], "centre") < 5.0
    assert spatial.look_angle(ALONG["lanes"], "centre") > 20.0
    assert spatial.look_angle(EDGE["lanes"], "far_left") is None      # no strip beyond it
    assert spatial.strong_door_read(SQUARE["lanes"], "centre")
    assert not spatial.strong_door_read(ALONG["lanes"], "centre")
    assert not spatial.strong_door_read(EDGE["lanes"], "far_left")
    # A neighbour that is itself an open doorway gives no wall point: the next strip out does.
    two = _look(["lower"] * 5, [False, "open", "open", False, False])
    assert spatial.strong_door_read(two["lanes"], "centre")


def test_a17k_weak_doorway_read_writes_nothing_and_a_strong_one_paints_the_gap():
    for look, strong in ((EDGE, False), (ALONG, False), (SQUARE, True)):
        mem = spatial.SpatialMemory(cfg=spatial.A17K)
        mem.visit(0, pose((0, 0)))
        mem.observe(0, pose((0, 0)), look)
        assert len(mem.openings) == 1, look
        assert bool(mem.openings[0].strong) is strong, look
        assert bool(mem.door_free) is strong, look
        # a66's memory paints the gap on any open read.
        old = spatial.SpatialMemory(cfg=spatial.A17F)
        old.visit(0, pose((0, 0)))
        old.observe(0, pose((0, 0)), look)
        assert old.door_free, look
    # A weak read does not reopen a doorway read closed, a strong one does.
    mem = spatial.SpatialMemory(cfg=spatial.A17K)
    mem.visit(0, pose((0, 0)))
    mem.observe(0, pose((0, 0)), SQUARE)
    mem.openings[0].closed = True
    mem.observe(1, pose((0, 0)), ALONG)
    assert mem.openings[0].closed and mem.openings[0].seen == 2
    mem.observe(2, pose((0, 0)), SQUARE)
    assert not mem.openings[0].closed and mem.openings[0].strong == 2


def test_a77_looks_at_a_weak_doorway_and_approaches_a_strong_one():
    p = agent.PATHFINDER_A77
    goal = centre((11, 2))
    at = manifest_at((2, 0), 9)
    mem = _door_memory()                               # seen twice, never on a square look
    plan = planner.pathfind(mem, at, [], goal, p)
    assert plan.door is not None and plan.door["phase"] == "look", plan.to_dict()
    assert spatial.dist(plan.waypoint, (mem.openings[0].x, mem.openings[0].y)) < 0.01
    looks = [{"step": s, "planner": {"door": {"label": "A", "phase": "look"}}} for s in range(2)]
    assert planner.pathfind(mem, at, looks[:1], goal, p).door["phase"] == "look"
    assert planner.pathfind(mem, at, looks, goal, p).door is None           # two looks spent
    assert planner.pathfind(_door_memory(seen=1), at, [], goal, p).door is None
    mem.openings[0].strong = 1
    plan = planner.pathfind(mem, at, looks, goal, p)   # looks do not spend the approach budget
    assert plan.door is not None and plan.door["phase"] == "line_up", plan.to_dict()
    # a76 approaches the weak doorway outright.
    assert planner.pathfind(_door_memory(), at, [], goal, agent.PATHFINDER_A76).door["phase"] == "line_up"


def test_a77_is_a66_plus_a17k_and_the_trusted_approach():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a76").sha() == "32498e44d94d"
    a66 = agent.get("a66").features["orchestrator"]
    a77 = agent.get("a77").features["orchestrator"]
    assert {k: v for k, v in a77.items() if k not in ("pathfinder", "memory")} == \
        {k: v for k, v in a66.items() if k not in ("pathfinder", "memory")}
    assert spatial.config_for(a77) == replace_cfg(spatial.A17F, name="a17k", door_trust=True)
    assert {k: v for k, v in a77["pathfinder"].items() if k != "door_approach"} == \
        agent.PATHFINDER_A65
    assert agent.get("a77").sha() not in {agent.get(a).sha() for a in ("a66", "a75", "a76")}



# --- a78 (R38): the dead-end latch --------------------------------------------

L = agent.PATHFINDER_A78


def tine(x1, reads, painted=True):
    """A straight run along +x from (0, 0) to (x1, 0) on a66's memory, the
    perceiver's floor painted six cells either side (through the walls, as in
    the shut tine), and the dead-end confirmer's answers [(step, answer)]."""
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    for x in range(0, x1 + 1):
        mem.visits[(x, 0)] = [x]
        mem.trail.append((x,) + centre((x, 0)) + (0.0,))
        if painted:
            for y in range(-6, 7):
                mem.free[(x, y)] = x
    mem.dead_end_reads = list(reads)
    return mem


def test_latch_fires_on_two_yes_in_three_recent_reads_at_the_end_of_a_straight_run():
    here = pose((8, 0))
    assert planner.dead_end_latch(tine(8, [(8, "yes")]), here, 8, L) is None
    assert planner.dead_end_latch(tine(8, [(7, "yes"), (8, "no")]), here, 8, L) is None
    assert planner.dead_end_latch(tine(20, [(2, "yes"), (20, "yes")]), pose((20, 0)), 20,
                                  L) is None                               # 18 steps apart: stale
    assert planner.dead_end_latch(tine(8, [(7, "yes"), (8, "yes")]), here, 9, L) is None  # not now
    assert planner.dead_end_latch(tine(2, [(1, "yes"), (2, "yes")]), pose((2, 0)), 2, L) is None
    latch = planner.dead_end_latch(tine(8, [(6, "yes"), (7, "no"), (8, "yes")]), here, 8, L)
    assert latch is not None and latch["step"] == 8 and not latch["out"]
    assert abs(latch["axis_deg"]) < 1.0
    assert abs(latch["origin"][0] - (centre((0, 0))[0] + 2.0)) < 0.01      # mouth_m down the run
    assert abs(latch["reach_m"] - (centre((8, 0))[0] - latch["origin"][0])) < 0.02
    assert latch["half_width_m"] == round(8 * C, 2) and latch["ahead_m"] == 2.0


def test_latch_corridor_is_the_run_flown_at_the_first_yes_not_the_turning_about_after():
    mem = tine(8, [(8, "yes"), (12, "yes")])
    for step, c, h in ((9, (8, 1), 90.0), (10, (7, 1), 180.0), (11, (7, 0), 270.0),
                       (12, (8, 0), 0.0)):                   # turning about at the door
        mem.visits.setdefault(c, []).append(step)
        mem.trail.append((step,) + centre(c) + (h,))
    assert planner.straight_run(mem.trail, 12, L["dead_end_latch"]) is None
    latch = planner.dead_end_latch(mem, pose((8, 0)), 12, L)
    assert latch is not None and latch["step"] == 12 and abs(latch["axis_deg"]) < 1.0
    assert abs(latch["origin"][0] - (centre((0, 0))[0] + 2.0)) < 0.01
    assert abs(latch["reach_m"] - (centre((8, 0))[0] - latch["origin"][0])) < 0.02


def test_latch_run_starts_where_the_trail_turned():
    mem = tine(8, [(15, "yes"), (16, "yes")])
    for k, y in enumerate(range(1, 9)):                      # then eight cells along +y
        mem.visits[(8, y)] = [9 + k]
        mem.trail.append((9 + k,) + centre((8, y)) + (90.0,))
    latch = planner.dead_end_latch(mem, pose((8, 8), 90.0), 16, L)
    assert latch is not None and abs(latch["axis_deg"] - 90.0) < 1.0
    assert abs(latch["origin"][0] - centre((8, 0))[0]) < 0.01
    assert latch["origin"][1] > centre((8, 0))[1] + 1.9      # past the corner, not the first leg


def test_latch_looks_back_for_the_run_and_skips_one_the_drone_has_left():
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    cells = ([(x, 0) for x in range(0, 5)] + [(4, y) for y in range(1, 11)]     # stem, long leg
             + [(x, 10) for x in range(5, 13)]                                  # the corridor
             + [(12, 11), (11, 11), (12, 10)])                                  # about at the door
    for step, c in enumerate(cells):
        mem.visits.setdefault(c, []).append(step)
        mem.trail.append((step,) + centre(c) + (0.0,))
    mem.dead_end_reads = [(23, "yes"), (25, "yes")]
    d = L["dead_end_latch"]
    leg, corridor = planner.straight_run(mem.trail, 14, d), planner.straight_run(mem.trail, 22, d)
    assert leg[3] > corridor[3] and planner.straight_run(mem.trail, 25, d) is None
    latch = planner.dead_end_latch(mem, pose((12, 10)), 25, L)
    assert latch is not None and abs(latch["axis_deg"]) < 1.0       # not the longer leg
    assert abs(latch["origin"][0] - (centre((4, 10))[0] + 2.0)) < 0.01
    assert abs(latch["origin"][1] - centre((4, 10))[1]) < 0.01
    short = dict(L, dead_end_latch=dict(d, look_back_steps=0))
    assert planner.dead_end_latch(mem, pose((12, 10)), 25, short) is None


def test_latch_shuts_the_rectangle_but_for_the_lane_until_the_drone_is_out():
    latch = planner.dead_end_latch(tine(8, [(7, "yes"), (8, "yes")]), pose((8, 0)), 8, L)
    cells = set(planner.latch_cells(latch))
    assert (5, 0) not in cells and (5, 1) not in cells       # the lane back
    assert (5, 2) in cells and (5, -7) in cells and (5, 7) in cells
    assert (5, 9) not in cells and (0, 3) not in cells       # beyond its width; before its mouth
    assert (9, 0) in cells and (10, 0) in cells              # the lane is capped ahead of the drone
    assert (11, 0) not in cells                              # ahead_m beyond the drone, no farther
    on = set(planner.latch_cells(dict(latch, reach_m=latch["reach_m"] + 2 * C)))
    assert (9, 0) not in on and (11, 0) in on and (12, 0) in on   # the cap moves with the drone
    shut = set(planner.latch_cells(dict(latch, out=True)))
    assert cells < shut and (5, 0) in shut and (5, 1) in shut


def test_latched_route_goes_back_down_the_lane_over_painted_floor():
    mem = tine(8, [(7, "yes"), (8, "yes")])
    goal = centre((14, 3))                                    # beyond the door, off the axis
    free = planner.pathfind(mem, manifest_at((8, 0), 8), [], goal, agent.PATHFINDER_A65)
    assert free.path[1][0] > 8 and free.latch is None        # a66: on through the painted floor
    plan = planner.pathfind(mem, manifest_at((8, 0), 8), [], goal, L)
    assert plan.latch is not None and plan.fallback == "none"
    assert plan.to_dict()["latch"]["step"] == 8
    assert plan.path[1][0] < 8 and plan.waypoint[0] < centre((8, 0))[0]
    inside = [c for c in plan.path if 3 <= c[0] <= 8 and abs(c[1]) <= 7]
    assert inside and all(abs(c[1]) <= 1 for c in inside), plan.path   # only by the lane
    assert plan.path_m > free.path_m


def test_latch_is_carried_by_the_record_and_shuts_the_lane_once_out():
    mem = tine(8, [(7, "yes"), (8, "yes")])
    goal = centre((14, 3))
    fired = planner.pathfind(mem, manifest_at((8, 0), 8), [], goal, L).to_dict()
    records = [{"step": 8, "planner": fired}]
    assert planner.latch_from(records, 9) == fired["latch"]
    assert planner.latch_from(records, 8) is None
    # No confirmer answer on later steps: the latch still holds.
    mem.dead_end_reads = []
    held = planner.pathfind(mem, manifest_at((6, 0), 9), records, goal, L)
    assert held.latch == fired["latch"] and held.path[1][0] < 6
    # Back at the run's start, before the mouth: out, and the lane is shut for good.
    out = planner.pathfind(mem, manifest_at((0, 0), 10), records, goal, L)
    assert out.latch["out"] and out.fallback == "none"
    assert all(not (3 <= c[0] <= 8 and abs(c[1]) <= 7) for c in out.path[1:]), out.path
    records.append({"step": 10, "planner": out.to_dict()})
    again = planner.pathfind(mem, manifest_at((1, 0), 11), records, goal, L)
    assert again.latch["out"]
    assert all(not (4 <= c[0] <= 8 and abs(c[1]) <= 7) for c in again.path[1:]), again.path


def test_a78_sentence_only_inside_a_latched_corridor_with_toward_on_the_turn_around():
    notes = agent.NAVIGATOR_A78
    manifest = {"actions": [{"index": 0, "turn_around": True}, {"index": 3}]}
    back = {0: [spatial.WORDS["toward_target"]]}
    on = {3: [spatial.WORDS["toward_target"]]}
    latch = {"out": False}
    said = orchestrator.behind_note(notes, manifest, back, {"latch": latch})
    assert said == notes["dead_end"] + " " + notes["route_behind"]
    assert orchestrator.behind_note(notes, manifest, on, {"latch": latch}) is None
    assert orchestrator.behind_note(notes, manifest, back, {}) is None
    assert orchestrator.behind_note(notes, manifest, back, {"latch": {"out": True}}) is None
    # a70 is unchanged: its sentence needs no latch.
    assert orchestrator.behind_note(agent.NAVIGATOR_A70, manifest, back, None) == \
        agent.NAVIGATOR_A70["route_behind"]
    assert orchestrator.behind_note({}, manifest, back, None) is None


def test_dead_end_confirmer_is_asked_on_a_closed_door_in_the_centre_three_strips():
    def lanes(**doors):
        return {"lanes": [{"strip": s, "floor": "open_near", "floor_end": "bottom",
                           "doorway": doors.get(s, False)} for s in spatial.STRIPS]}
    assert orchestrator.dead_end_strips(lanes(centre="closed", far_left="closed")) == ["centre"]
    assert orchestrator.dead_end_strips(lanes(far_right="closed")) == []
    assert orchestrator.dead_end_strips(lanes(left="open")) == []
    assert orchestrator.dead_end_strips(None) == []
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    mem.observe(3, pose((0, 0)), dict(lanes(centre="closed"), dead_end="yes"))
    mem.observe(4, pose((0, 0)), lanes(centre="closed"))
    assert mem.dead_end_reads == [(3, "yes")]


def test_a78_is_a66_plus_the_latch_its_confirmer_and_its_sentence():
    assert agent.get("a66").sha() == "de7f23d07186"
    assert agent.get("a75").sha() == "81d682c1424b"
    assert agent.get("a77").sha() == "6744446339b0"
    a66 = agent.get("a66").features["orchestrator"]
    a78 = agent.get("a78").features["orchestrator"]
    added = ("pathfinder", "dead_end_confirmer", "navigator_notes")
    assert {k: v for k, v in a78.items() if k not in added} == \
        {k: v for k, v in a66.items() if k != "pathfinder"}
    assert spatial.config_for(a78) == spatial.config_for(a66)
    assert {k: v for k, v in a78["pathfinder"].items() if k != "dead_end_latch"} == \
        agent.PATHFINDER_A65
    assert [p.version for p in agent.get("a78").subagent_prompts] == ["g05", "d01", "e01"]
    assert [s.name for s in orchestrator.pipeline(a78)][:4] == \
        ["perceiver", "door_confirmer", "dead_end_confirmer", "mapper"]
    assert "dead_end_confirmer" not in [s.name for s in orchestrator.pipeline(a66)]
    assert agent.get("a78").sha() not in {agent.get(a).sha() for a in ("a66", "a68", "a70")}


# --- a79 (R39): the latch fired by the trail ------------------------------------

L79 = agent.PATHFINDER_A79
D79 = L79["dead_end_latch"]


def lane_trail(x1=8, dwell=6, lead=((0, -4), (0, -3), (0, -2), (0, -1))):
    """A trail that comes up +y (`lead`), turns into a straight run along +x
    from (0, 0) to (x1, 0), then turns about at its end for `dwell` steps
    (between x1 and x1 - 1). Returns (trail, the step the run's end was reached)."""
    trail = []
    for c in lead:
        trail.append((len(trail),) + centre(c) + (90.0,))
    for x in range(0, x1 + 1):
        trail.append((len(trail),) + centre((x, 0)) + (0.0,))
    end = trail[-1][0]
    for k in range(dwell):
        c, h = ((x1 - 1, 0), 180.0) if k % 2 == 0 else ((x1, 0), 0.0)
        trail.append((len(trail),) + centre(c) + (h,))
    return trail, end


def fires(trail, closed, step=None):
    step = trail[-1][0] if step is None else step
    cut = [t for t in trail if t[0] <= step]
    return planner.confined_run(cut, [s for s in closed if s <= step], cut[-1][1:], step, D79)


def test_confined_run_fires_after_the_dwell_in_a_lane_the_drone_turned_into():
    trail, end = lane_trail()
    closed = [end - 1, end]                       # two closed-door reads looking down the lane
    dwell = D79["confined"]["dwell_steps"]
    assert fires(trail, closed, end) is None                    # still flying down it
    assert fires(trail, closed, end + 2) is None                # two steps of turning about
    found = fires(trail, closed, end + dwell)
    assert found is not None
    began, since, axis, run = found
    assert began == centre((0, 0)) and abs(axis) < 1.0 and run > 6.0
    assert fires(trail, [end], end + dwell) is None             # one read is not two
    assert fires(trail, [end + 1, end + 3], end + dwell) is None  # read looking back up the lane


def test_confined_run_needs_a_turn_into_the_lane():
    trail, end = lane_trail(lead=())                            # the run from the spawn
    assert fires(trail, [end - 1, end]) is None


def test_confined_run_is_off_once_the_drone_leaves_the_lane_or_has_stood_beside_it():
    trail, end = lane_trail()
    closed = [end - 1, end]
    assert fires(trail, closed) is not None
    out = trail + [(trail[-1][0] + 1,) + centre((7, 3)) + (90.0,)]      # 2.55 m off the axis
    assert fires(out, closed) is None
    # The same lane, but the drone came to its mouth along a line beside it
    # (y = -3 cells, 2.55 m off the axis, abreast of the lane): a hall, no wall there.
    lead = tuple((x, -3) for x in range(6, -1, -1)) + ((0, -2), (0, -1))
    hall, end = lane_trail(lead=lead)
    assert fires(hall, [end - 1, end]) is None


def test_a79_latch_comes_from_the_trail_with_no_confirmer_answers():
    trail, end = lane_trail()
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    mem.trail = list(trail)
    for step, x, y, _ in trail:
        mem.visits.setdefault(spatial.cell((x, y)), []).append(step)
    mem.closed_reads = [end - 1, end]
    step = trail[-1][0]
    latch = planner.dead_end_latch(mem, trail[-1][1:], step, L79)
    assert latch is not None and latch["step"] == step and not latch["out"]
    assert abs(latch["axis_deg"]) < 1.0
    assert abs(latch["origin"][0] - (centre((0, 0))[0] + 2.0)) < 0.01      # mouth_m down the run
    assert abs(latch["reach_m"] - (centre((8, 0))[0] - latch["origin"][0])) < 0.02
    mem.closed_reads = []
    assert planner.dead_end_latch(mem, trail[-1][1:], step, L79) is None


def test_closed_reads_are_the_centre_strip_closed_doors():
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    lanes = [{"strip": s, "floor": "open_far", "floor_end": "lower", "doorway": False}
             for s in spatial.STRIPS]
    mem.observe(3, (0.0, 0.0, 0.0), {"lanes": lanes})
    side = [dict(l, doorway="closed") if l["strip"] == spatial.STRIPS[0] else l for l in lanes]
    mem.observe(4, (0.0, 0.0, 0.0), {"lanes": side})
    mid = [dict(l, doorway="closed") if l["strip"] == spatial.STRIPS[2] else l for l in lanes]
    mem.observe(5, (0.0, 0.0, 0.0), {"lanes": mid})
    assert mem.closed_reads == [5]


def test_a79_is_a66_plus_the_latch_its_trail_trigger_and_the_sentence():
    a66 = agent.get("a66").features["orchestrator"]
    a78 = agent.get("a78").features["orchestrator"]
    a79 = agent.get("a79").features["orchestrator"]
    added = ("pathfinder", "navigator_notes")
    assert {k: v for k, v in a79.items() if k not in added} == \
        {k: v for k, v in a66.items() if k not in added}
    assert "dead_end_confirmer" not in a79
    assert spatial.config_for(a79) == spatial.config_for(a66)
    assert {k: v for k, v in a79["pathfinder"].items() if k != "dead_end_latch"} == \
        a66["pathfinder"]
    assert {k: v for k, v in a79["pathfinder"]["dead_end_latch"].items() if k != "confined"} == \
        dict(a78["pathfinder"]["dead_end_latch"], min_run_m=5.0)
    assert a79["navigator_notes"] == a78["navigator_notes"]
    assert [p.version for p in agent.get("a79").subagent_prompts] == ["g05", "d01"]
    assert "dead_end_confirmer" not in [s.name for s in orchestrator.pipeline(a79)]
    assert agent.get("a79").sha() not in {agent.get(a).sha() for a in ("a66", "a75", "a78")}


# --- a80 (R40): the wall survey --------------------------------------------------

S80 = agent.PATHFINDER_A80
SV = S80["survey"]
GOAL80 = (30.0, C / 2.0)                      # on the line of the approach: the axis is +x


def hall(x1=6):
    """A straight approach along +x from (0, 0) to cell (x1, 0) in open floor
    (a66's memory), a closed door read in the centre strip on the last step."""
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    for x in range(0, x1 + 1):
        mem.visits[(x, 0)] = [x]
        mem.trail.append((x,) + centre((x, 0)) + (0.0,))
    mem.centre_closed = [x1]
    return mem, pose((x1, 0)), x1


def survey_at(mem, here, step, records=(), goal=GOAL80):
    cm = spatial.CostMap(mem, [], S80, include=(spatial.cell(here[:2]), spatial.cell(goal)),
                         start=spatial.cell(here[:2]))
    return planner.wall_survey(mem, cm, here, step, goal, list(records), S80)


def rec(step, sv):
    return {"step": step, "planner": {"survey": sv}}


def test_survey_starts_on_a_closed_door_dead_ahead_and_steps_to_the_side():
    mem, here, step = hall()
    wp, sv = survey_at(mem, here, step)
    assert sv is not None and sv["phase"] == "transit" and sv["step"] == step
    assert abs(sv["axis_deg"]) < 1.0 and sv["wall"] is None
    assert sv["order"] == [7.0, -7.0]                       # the left first
    assert abs(wp[0] - (here[0] - SV["back_m"])) < 0.01 and abs(wp[1] - (here[1] + 7.0)) < 0.01
    # No closed door dead ahead this step, heading off the line, too short a way in: no survey.
    mem2, here2, step2 = hall()
    mem2.centre_closed = [step2 - 1]
    assert survey_at(mem2, here2, step2) == (None, None)
    mem3, here3, step3 = hall()
    assert survey_at(mem3, (here3[0], here3[1], 60.0), step3) == (None, None)
    mem4, here4, step4 = hall(x1=2)
    assert survey_at(mem4, here4, step4) == (None, None)
    mem5, here5, step5 = hall()                             # it has been 3.4 m off the direct line
    mem5.trail.insert(3, (2, centre((2, 4))[0], centre((2, 4))[1], 0.0))
    assert survey_at(mem5, here5, step5) == (None, None)
    mem6, here6, step6 = hall()                             # stopped by the wall already
    mem6.blocks.append(spatial.Block(here6[0] - 0.4, here6[1], 0.0, step6 - 1, 0.4))
    wp, sv = survey_at(mem6, here6, step6)
    assert sv["wall"] == SV["wall_m"]
    assert abs(wp[0] - (here6[0] + SV["wall_m"] - SV["standoff_m"])) < 0.01


def test_survey_goes_first_to_the_side_of_a_remembered_open_doorway():
    mem, here, step = hall()
    mem.openings.append(spatial.Opening(here[0] + 4.0, here[1] - 8.0, 2, label="A"))
    _, sv = survey_at(mem, here, step)
    assert sv["order"] == [-7.0, 7.0]


def test_survey_has_no_station_in_a_corridor_whose_side_walls_are_on_the_map():
    mem, here, step = hall()
    for x in range(0, 12):
        mem.near_wall[(x, 2)] = x
    _, sv = survey_at(mem, here, step)
    assert sv["order"] == [-7.0]                            # the left is walled: the right only
    for x in range(0, 12):
        mem.near_wall[(x, -2)] = x
    assert survey_at(mem, here, step) == (None, None)


def test_survey_flies_at_the_wall_from_the_station_then_goes_back_and_across():
    mem, here, step = hall()
    _, sv = survey_at(mem, here, step)
    station = planner.survey_station(sv, SV)
    at = (station[0], station[1], 90.0)                     # arrived, still heading along the wall
    wp, sv = survey_at(mem, at, step + 4, [rec(step, sv)])
    assert sv["phase"] == "look"
    assert abs(wp[0] - (at[0] + SV["face_m"])) < 0.01 and abs(wp[1] - at[1]) < 0.01   # at the wall
    wp, sv = survey_at(mem, (at[0] + 1.0, at[1] + 1.0, 10.0), step + 6, [rec(step + 4, sv)])
    assert sv["phase"] == "look" and sv["looks"] == 1 and sv["wall"] is None   # square, no wall yet
    met = (at[0] + 6.0, at[1] + 1.0, 0.0)
    mem.blocks.append(spatial.Block(met[0] - 0.4, met[1], 0.0, step + 8, 0.4))   # stopped short
    wp, sv = survey_at(mem, met, step + 9, [rec(step + 6, sv)])
    assert sv["phase"] == "transit" and sv["i"] == 1
    assert abs(sv["wall"] - (met[0] - here[0] + SV["wall_m"])) < 0.02       # the wall's range, now known
    back = here[0] + sv["wall"] - SV["standoff_m"]
    assert sv["looks"] == 2
    assert abs(wp[0] - back) < 0.02 and abs(wp[1] - (here[1] - 7.0)) < 0.01  # back, and the other side
    other = planner.survey_station(sv, SV)
    wp, sv = survey_at(mem, (other[0], other[1], 270.0), step + 18, [rec(step + 9, sv)])
    assert sv["phase"] == "look"
    wp, sv = survey_at(mem, (other[0], other[1], 270.0), step + 18 + SV["look_steps"],
                       [rec(step + 18, sv)])                 # never met the wall: given up
    assert wp is None and sv["phase"] == "done"
    assert survey_at(mem, (other[0], other[1], 0.0), step + 30, [rec(step + 29, sv)]) == (None, sv)


def test_survey_gives_up_a_station_it_does_not_get_nearer_to():
    mem, here, step = hall()
    _, sv = survey_at(mem, here, step)
    recs = [rec(step, sv)]
    for k in range(1, SV["stall_steps"] + 2):
        wp, sv = survey_at(mem, here, step + k, recs)
        recs = [rec(step + k, sv)]
    assert sv["i"] == 1 and sv["phase"] == "transit"


def test_survey_takes_an_open_doorway_read_near_square_through_the_wall():
    mem, here, step = hall()
    _, sv = survey_at(mem, here, step)
    station = planner.survey_station(sv, SV)
    at = (station[0], station[1], 0.0)
    mem.door_rays.append(spatial.Ray(at[0], at[1], 80.0, step + 5, "open_far"))   # along the wall
    wp, sv2 = survey_at(mem, at, step + 5, [rec(step, sv)])
    assert sv2["phase"] != "through"
    mem.door_rays.append(spatial.Ray(at[0], at[1], 0.0, step + 5, "open_far"))    # dead ahead
    wp, sv2 = survey_at(mem, at, step + 5, [rec(step, sv)])
    assert sv2["phase"] == "through" and len(sv2["rays"]) == 1
    assert abs(wp[0] - (at[0] + SV["carrot_m"])) < 0.01 and abs(wp[1] - at[1]) < 0.01   # straight on
    # Knocked 1.5 m off the line with no read: the carrot is still on the door's line.
    off = (at[0] + 1.5, at[1] - 1.5, 315.0)
    wp2, sv3 = survey_at(mem, off, step + 6, [rec(step + 5, sv2)])
    assert sv3["phase"] == "through" and abs(wp2[1] - at[1]) < 0.01
    assert abs(wp2[0] - (off[0] + SV["carrot_m"])) < 0.01
    # A second read from there crosses the first: the door is where the rays meet.
    door = (at[0] + 6.0, at[1])
    mem.door_rays.append(spatial.Ray(off[0], off[1], spatial.bearing(off[:2], door), step + 7,
                                     "open_far"))
    wp3, sv4 = survey_at(mem, off, step + 7, [rec(step + 6, sv3)])
    assert len(sv4["rays"]) == 2 and abs(planner.survey_door_line(sv4, SV) - 7.0) < 0.05
    assert abs(wp3[1] - door[1]) < 0.05
    # through_steps with no read and nothing in the way: through it, the route takes over.
    wp4, sv5 = survey_at(mem, (door[0] + 2.0, door[1], 0.0), step + 7 + SV["through_steps"],
                         [rec(step + 7, sv4)])
    assert wp4 is None and sv5["phase"] == "done"
    # A move stopped short with the doorway still read: a jamb, the survey holds on.
    mem.blocks.append(spatial.Block(off[0], off[1], 0.0, step + 7, 0.3))
    mem.door_rays.append(spatial.Ray(off[0], off[1], 20.0, step + 8, "open_far"))
    wp5, sv6 = survey_at(mem, off, step + 8, [rec(step + 7, sv4)])
    assert sv6["phase"] == "through" and len(sv6["rays"]) == 3
    # Stopped short and no doorway read from there: a phantom, on to the next station.
    mem.blocks.append(spatial.Block(off[0], off[1], 0.0, step + 9, 0.3))
    wp6, sv7 = survey_at(mem, off, step + 10, [rec(step + 8, sv6)])
    assert sv7["phase"] == "transit" and sv7["i"] == 1 and sv7["rays"] == []


def test_survey_door_line_is_where_the_ray_meets_a_wall_whose_range_is_known():
    mem, here, step = hall()
    _, sv = survey_at(mem, here, step)
    sv = dict(sv, wall=6.0, rays=[[here[0], here[1] + 3.0, 21.75]])
    want = 3.0 + math.tan(math.radians(21.75)) * 6.0
    assert abs(planner.survey_door_line(sv, SV) - want) < 0.02


# --- a81 (R41): the survey after a80's shakedown -----------------------------------

S81 = agent.PATHFINDER_A81
SV81 = S81["survey"]


def survey81_at(mem, here, step, records=()):
    cm = spatial.CostMap(mem, [], S81, include=(spatial.cell(here[:2]), spatial.cell(GOAL80)),
                         start=spatial.cell(here[:2]))
    return planner.wall_survey(mem, cm, here, step, GOAL80, list(records), S81)


def test_a81_a_bump_in_the_through_phase_is_checked_before_it_is_called_a_phantom():
    mem, here, step = hall()
    _, sv = survey81_at(mem, here, step)
    station = planner.survey_station(sv, SV81)
    at = (station[0], station[1], 0.0)
    mem.door_rays.append(spatial.Ray(at[0], at[1], 0.0, step + 5, "open_far"))
    wp, sv = survey81_at(mem, at, step + 5, [rec(step, sv)])
    assert sv["phase"] == "through"
    hit = (at[0] + 3.0, at[1], 0.0)
    mem.blocks.append(spatial.Block(hit[0], hit[1], 0.0, step + 6, 0.4))
    wp, chk = survey81_at(mem, hit, step + 7, [rec(step + 5, sv)])
    assert wp is None and chk["phase"] == "check" and abs(chk["mark"] - 3.0) < 0.01   # the route's turn
    # 2 m farther toward the wall: it was a jamb, the drone is through.
    wp, done = survey81_at(mem, (hit[0] + 2.2, hit[1], 0.0), step + 9, [rec(step + 7, chk)])
    assert wp is None and done["phase"] == "done"
    # No farther in check_steps: a phantom, on to the next station.
    wp, nxt = survey81_at(mem, hit, step + 7 + SV81["check_steps"], [rec(step + 7, chk)])
    assert nxt["phase"] == "transit" and nxt["i"] == 1
    # a80 has no check: the bump alone moves it on.
    _, sv80 = survey_at(mem, here, step)
    wp, sv80 = survey_at(mem, at, step + 5, [rec(step, sv80)])
    wp, sv80 = survey_at(mem, hit, step + 7, [rec(step + 5, sv80)])
    assert sv80["phase"] == "transit" and sv80["i"] == 1


def test_a81_door_line_takes_the_middle_of_the_strips_and_no_nearer_than_the_drone_has_been():
    mem, here, step = hall()
    _, sv = survey81_at(mem, here, step)
    station = planner.survey_station(sv, SV81)
    at = (station[0], station[1], 0.0)
    for heading in (10.0, 30.0):                             # the doorway spans two strips
        mem.door_rays.append(spatial.Ray(at[0], at[1], heading, step + 5, "open_far"))
    wp, sv2 = survey81_at(mem, at, step + 5, [rec(step, sv)])
    assert sv2["rays"][-1][2] == 20.0
    # The wall's range unknown: 4 m out along the ray, the carrot on that line.
    want = 7.0 + math.tan(math.radians(20.0)) * SV81["reach_ray_m"]
    assert abs(planner.survey_door_line(sv2, SV81) - want) < 0.02
    assert abs(wp[1] - (here[1] + want)) < 0.05
    # a82: one ray and no range, the waypoint is 3 m out along the ray itself.
    cm = spatial.CostMap(mem, [], agent.PATHFINDER_A82)
    wp82, sv82 = planner.wall_survey(mem, cm, at, step + 5, GOAL80, [rec(step, sv)],
                                     agent.PATHFINDER_A82)
    assert abs(spatial.dist(at[:2], wp82) - SV81["carrot_m"]) < 0.01
    assert abs(spatial.wrap(spatial.bearing(at[:2], wp82) - 20.0)) < 0.5
    on = spatial.ahead(at[:2], 20.0, 2.0)                    # 2 m along it, no new read: 5 m out
    wp83, _ = planner.wall_survey(mem, cm, (on[0], on[1], 20.0), step + 6, GOAL80,
                                  [rec(step + 5, sv82)], agent.PATHFINDER_A82)
    assert abs(spatial.dist(at[:2], wp83) - (2.0 + SV81["carrot_m"])) < 0.01
    # The drone has been 6 m toward the wall without meeting it: at least 7 m out.
    far = 7.0 + math.tan(math.radians(20.0)) * 7.0
    assert abs(planner.survey_door_line(sv2, SV81, been=6.0) - far) < 0.02


def test_a81_flying_at_the_wall_every_strip_blocked_is_the_wall():
    mem, here, step = hall()
    _, sv = survey81_at(mem, here, step)
    station = planner.survey_station(sv, SV81)
    at = (station[0], station[1], 0.0)
    wp, sv = survey81_at(mem, at, step + 4, [rec(step, sv)])
    assert sv["phase"] == "look"
    mem.nose_on.append(step + 6)
    close = (at[0] + 3.0, at[1], 0.0)
    wp, sv2 = survey81_at(mem, close, step + 6, [rec(step + 4, sv)])
    assert sv2["phase"] == "transit" and sv2["i"] == 1 and abs(sv2["wall"] - (3.0 + SV81["wall_m"])) < 0.02
    wp, sv80 = survey_at(mem, close, step + 6, [rec(step + 4, sv)])     # a80 wants more than that
    assert sv80["phase"] == "look"


def test_a81_is_a80_with_the_survey_changed():
    a80 = agent.get("a80").features["orchestrator"]
    a81 = agent.get("a81").features["orchestrator"]
    assert {k: v for k, v in a81.items() if k != "pathfinder"} == \
        {k: v for k, v in a80.items() if k != "pathfinder"}
    assert {k: v for k, v in a81["pathfinder"].items() if k != "survey"} == \
        {k: v for k, v in a80["pathfinder"].items() if k != "survey"}
    assert agent.get("a81").sha() != agent.get("a80").sha()
    assert agent.get("a80").sha() == "1c1790de9767"


# --- a83 (R43): the survey and the latch together ----------------------------------

L83 = agent.PATHFINDER_A83


def test_a83_latched_waypoint_runs_back_down_the_middle_of_the_corridor():
    trail, end = lane_trail(dwell=4)
    trail = [(s, x, y + (0.6 if s > end else 0.0), h) for s, x, y, h in trail]   # dwelt off the axis
    mem = spatial.SpatialMemory(cfg=spatial.A17F)
    mem.trail = list(trail)
    for step, x, y, _ in trail:
        mem.visits.setdefault(spatial.cell((x, y)), []).append(step)
        for dy in range(-6, 7):
            mem.free[(spatial.cell((x, y))[0], dy)] = step
    mem.closed_reads = [end - 1, end]
    step = trail[-1][0]
    here = trail[-1][1:]
    latch = planner.dead_end_latch(mem, here, step, L83)
    assert latch is not None and "mid_m" in latch and 0.0 <= latch["mid_m"] <= 0.6
    assert "mid_m" not in planner.dead_end_latch(mem, here, step, L79)       # a79's latch as it was
    man = {"step": step, "pose": {"position": [here[0], 1.75, -here[1]],
                                  "yaw": math.radians(here[2] - 90.0)}}
    plan = planner.pathfind(mem, man, [], (40.0, centre((0, 0))[1]), L83)
    assert plan.latch is not None and not plan.latch["out"] and plan.survey is None
    along = planner.latch_frame(plan.latch, here[:2])[0]
    back, left = planner.latch_frame(plan.latch, plan.waypoint)
    assert abs(back - (along - 4.0)) < 0.01 and abs(left - plan.latch["mid_m"]) < 0.01


def test_a82_is_a81_homing_on_the_ray_and_a83_is_a82_plus_the_latch_sooner_with_its_way_out():
    assert agent.SURVEY_A82 == dict(agent.SURVEY_A81, home_ray=True)
    assert {k: v for k, v in agent.get("a82").features["orchestrator"].items()
            if k != "pathfinder"} == {k: v for k, v in agent.get("a81").features[
                "orchestrator"].items() if k != "pathfinder"}
    a81 = agent.get("a82").features["orchestrator"]
    a79 = agent.get("a79").features["orchestrator"]
    a82 = agent.get("a83").features["orchestrator"]
    added = ("pathfinder", "navigator_notes")
    assert {k: v for k, v in a82.items() if k not in added} == \
        {k: v for k, v in a81.items() if k not in added}
    assert a82["navigator_notes"] == a79["navigator_notes"]
    assert a82["pathfinder"]["survey"] == dict(a81["pathfinder"]["survey"], side_only=True,
                                               no_cross=True, goal_ends=True, relook=True)
    latch, was = a82["pathfinder"]["dead_end_latch"], a79["pathfinder"]["dead_end_latch"]
    assert latch["exit"] == {"carrot_m": 4.0} and latch["confined"]["dwell_steps"] == 3
    assert {k: v for k, v in latch.items() if k not in ("exit", "confined")} == \
        {k: v for k, v in was.items() if k != "confined"}
    assert {k: v for k, v in latch["confined"].items() if k != "dwell_steps"} == \
        {k: v for k, v in was["confined"].items() if k != "dwell_steps"}
    assert agent.get("a79").sha() == "4ef945298c6d" and agent.get("a81").sha() == "61e8e685422a"


def survey83_at(mem, here, step, records=()):
    cm = spatial.CostMap(mem, [], L83, include=(spatial.cell(here[:2]), spatial.cell(GOAL80)),
                         start=spatial.cell(here[:2]))
    return planner.wall_survey(mem, cm, here, step, GOAL80, list(records), L83)


def test_a83_a_doorway_read_on_the_way_to_a_station_only_picks_the_side():
    mem, here, step = hall()
    wp, sv = survey83_at(mem, here, step)
    assert sv["order"] == [7.0, -7.0]
    mem.door_rays.append(spatial.Ray(here[0], here[1], -30.0, step + 1, "open_far"))   # to the right
    wp, sv2 = survey83_at(mem, (here[0], here[1] + 1.0, 60.0), step + 1, [rec(step, sv)])
    assert sv2["phase"] == "transit" and sv2["order"] == [-7.0, 7.0] and sv2["rays"] == []
    assert abs(wp[1] - (here[1] - 7.0)) < 0.01                    # the right-hand station now
    # From the station, in the look phase, the same kind of read is flown at, on its own ray.
    station = planner.survey_station(sv2, L83["survey"])
    at = (station[0], station[1], 0.0)
    wp, sv3 = survey83_at(mem, at, step + 6, [rec(step + 1, sv2)])
    assert sv3["phase"] == "look"
    for k, heading in ((7, -10.0), (8, 25.0)):                   # bearings 35 degrees apart
        mem.door_rays.append(spatial.Ray(at[0], at[1], heading, step + k, "open_far"))
    wp, sv4 = survey83_at(mem, at, step + 7, [rec(step + 6, sv3)])
    assert sv4["phase"] == "through"
    wp, sv5 = survey83_at(mem, at, step + 8, [rec(step + 7, sv4)])
    assert abs(spatial.wrap(spatial.bearing(at[:2], wp) - 25.0)) < 0.5   # the newest ray, not a crossing


def test_a83_the_goal_in_view_ends_the_survey_and_a_lost_door_goes_back_to_the_look():
    mem, here, step = hall()
    _, sv = survey83_at(mem, here, step)
    station = planner.survey_station(sv, L83["survey"])
    at = (station[0], station[1], 0.0)
    _, look = survey83_at(mem, at, step + 5, [rec(step, sv)])
    mem.door_rays.append(spatial.Ray(at[0], at[1], 0.0, step + 6, "open_far"))
    _, thru = survey83_at(mem, at, step + 6, [rec(step + 5, look)])
    assert thru["phase"] == "through"
    late = step + 6 + L83["survey"]["through_steps"]
    wp, again = survey83_at(mem, (at[0] + 4.0, at[1], 0.0), late, [rec(step + 6, thru)])
    assert again["phase"] == "look" and wp is not None            # no read, no goal: not through
    mem.goal_rays.append(spatial.Ray(at[0] + 4.0, at[1], 0.0, late, "mid"))
    wp, done = survey83_at(mem, (at[0] + 4.0, at[1], 0.0), late, [rec(step + 6, thru)])
    assert wp is None and done["phase"] == "done"
