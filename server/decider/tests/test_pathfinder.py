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
