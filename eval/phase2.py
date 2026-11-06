#!/usr/bin/env python3
"""Phase 2 runner: fly a round of the iterative-improvement loop, then check it.

The spec is docs/phase2-test-plan.md; validity (§10) and the rubric (§9) are
Phase 1's, docs/phase1-test-plan.md. The engine is eval/phaselib.py.

    python eval/phase2.py init                     # lay out eval/phase2/ (idempotent)
    python eval/phase2.py run --round P2.0         # fly order.txt, skip valid runs
    python eval/phase2.py run --round R1 --only s01/dynamic/1
    python eval/phase2.py validate --round R1      # re-check without flying
    python eval/phase2.py status
    python eval/phase2.py results                  # round comparison -> eval/phase2/results/

A round tests one agent version (server/decider/agent.py) on every site, every
arm, seed 1: 18 runs. The decider must be serving that agent:

    python -m server.decider --profile remote --agent a01

Adding a round: add the agent version in agent.py, add an entry to ROUNDS, run
`init`. A round's lock includes its agent's sha, so editing an agent after its
round is laid out is refused.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phaselib import (ARMS, ALL_SITES, REPO_ROOT, SEEDS, SITES, Phase,  # noqa: E402
                      s11_tables, write_runs_csv)
from server.decider import agent as agents  # noqa: E402

import phase1  # noqa: E402

PHASE_DIR = REPO_ROOT / "eval" / "phase2"

#: What every screening round flies: all six sites, all three arms, one seed.
ROUND_SITES = list(SITES)
ROUND_SEEDS = [1]
#: R32 (operator, 2026-11-04): the repeat screen flies only the ten contested
#: cells (s02 and s03, final and dynamic; the other eight were solved in 14 of
#: the last 14 rounds), three seeds each, so a cell is a rate and not a draw.
#: s03 final: the closed exit is L on odd seeds and R on even (P1 §5).
CONTESTED_SITES = ["s02a", "s02c", "s02va", "s02vc", "s03"]
CONTESTED_ARMS = ("final", "dynamic")
REPEAT_SEEDS = [1, 2, 3]

#: Rounds in the order they were flown. Never edit a flown round; add one.
#:   "R1": {"folder": "R1_<slug>", "title": "...", "agent": "a01",
#:          "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
#: The final round is the full Phase 1 design under the chosen agent:
#:   "F": {"folder": "final", "title": "Final: <agent>", "agent": "aNN",
#:         "sites": ROUND_SITES, "seeds": list(SEEDS), "citable": True},
ROUNDS: Dict[str, Dict[str, Any]] = {
    "P2.0": {"folder": "P2.0_shakedown", "title": "Shakedown (fake decider)",
             "agent": "a00", "sites": ROUND_SITES, "seeds": ROUND_SEEDS,
             "citable": False},
    "R1": {"folder": "R1_no_goal_hint", "title": "No goal hint", "agent": "a01",
           "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R2": {"folder": "R2_text_memory", "title": "Text memory, full run", "agent": "a02",
           "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R3": {"folder": "R3_memory_log", "title": "Memory log, code-written", "agent": "a03",
           "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R4": {"folder": "R4_goal_after_reason", "title": "Memory log, goal reported last",
           "agent": "a04", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # Defined with a05; its probe failed (the identifier took the drawn turn-around
    # marker for the goal), so before flying the round moved to a06, which shows
    # the identifier the unannotated frame. R5 README, "Change".
    "R5": {"folder": "R5_goal_identifier", "title": "Goal identifier on the clean frame, sighting age",
           "agent": "a06", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # Two candidates were probed: a07 (pose log, sighting line kept) and a08 (pose
    # log, no sighting line). Defined with a07, the tie-break; a08 won the probe
    # (spin turn-around 6/40 against 17/40) and flies. R6 README, "Probe gate".
    "R6": {"folder": "R6_pose_log", "title": "Ground-truth pose in the memory log",
           "agent": "a08", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # a10 is a08 (no sighting line) plus comparison lines in the log. a09 (a07 plus
    # the same lines) was probed first and did not fly. R7 README, "Change".
    "R7": {"folder": "R7_comparison_lines", "title": "Comparison lines in the log",
           "agent": "a10", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R7C: a08 (R6's agent) flown on sctsvr6 under lavapipe, the host R7 flies on, so R7
    # against R6 can be read without the renderer change. Not a round of its own: no
    # change, no prediction. R7 README, "Host".
    "R7C": {"folder": "R7C_a08_control", "title": "a08 control on the R7 host",
            "agent": "a08", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R8": {"folder": "R8_heading_word", "title": "Heading as a compass word",
           "agent": "a11", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R8N: a12 is a10 plus one sentence with no content, flown beside R8 on the same
    # host and SHA. R8N against R7 is the noise floor of a prompt edit; R8 is read
    # against it. R8 README, "Attribution rule".
    "R8N": {"folder": "R8N_noop_control", "title": "No-op prompt edit (noise floor)",
            "agent": "a12", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R9: the bundle round (operator, 2026-10-22). a13 is several calls with one job
    # each plus a code-kept map (server/decider/orchestrator.py, spatial.py). More than
    # one change, by decision: success is credited to the bundle, not its parts. Its
    # control is R9C below. R9 README, "Change".
    "R9": {"folder": "R9_hail_mary", "title": "Orchestrated agent with a spatial memory",
           "agent": "a13", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R9C: a11 (R8's agent, carried forward) flown on the R9 host at the R9 SHA. Not a
    # round of its own. R9 README, "Control".
    "R9C": {"folder": "R9C_a11_control", "title": "a11 control on the R9 host",
            "agent": "a11", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R10: a bundle on a13 (operator, 2026-10-24): the strategist is given the goal's
    # true position, no turn-around right after a turn-around while a move ahead is
    # open, no critic. Credited to the bundle. Its control is R10C below. R10 README.
    "R10": {"folder": "R10_goal_planner", "title": "Goal known to the planner, no double turn",
            "agent": "a14", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R10C: a13 (R9's agent) flown on the R10 host at the R10 SHA. Not a round of its
    # own. R10 README, "Control".
    "R10C": {"folder": "R10C_a13_control", "title": "a13 control on the R10 host",
             "agent": "a13", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R11: a bundle on a14 (operator, 2026-10-26/27): the goal is the standing target by
    # default (route planner, goal truth in code only), q03 asked only for detours on a
    # goal-side menu, a progress monitor, a doorway gate, block memory at the end pose
    # with a window by kind, wall-aware "toward". Agent a16 (a15 failed its probe).
    # Credited to the bundle. Its control is R11C. R11 README.
    "R11": {"folder": "R11_goal_default", "title": "Goal by default, detours on demand",
            "agent": "a16", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R11C: a14 (R10's agent) flown on the R11 host at the R11 SHA; also a14's
    # run-to-run floor against R10. Not a round of its own. R11 README, "Control".
    "R11C": {"folder": "R11C_a14_control", "title": "a14 control on the R11 host",
             "agent": "a14", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R12: a bundle with no goal truth anywhere (operator, 2026-10-28): staged search
    # (explore until the goal is seen, then head for it), a coverage map of searched
    # ground, an evaluator per step, reachable search targets (q04), perceiver g04,
    # stop walls and doors passed only when crossed. Agent a19 (perceiver g05).
    # Read against R11; R12C (a13) dropped by the operator. R12 README.
    "R12": {"folder": "R12_staged_search", "title": "Staged search with a coverage map",
            "agent": "a19", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R13: a19 with a verify stage (operator, 2026-10-28): the first look without the
    # goal sends the drone back to where it was seen from to look again; seen, the goal
    # stage resumes (the old sighting dropped if the new one disagrees); not seen, the
    # sighting is dropped and the search goes on. Agent a20, no goal truth. R13 README.
    "R13": {"folder": "R13_verify", "title": "Lose sight, verify, then explore or pursue",
            "agent": "a20", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R13G: a20 with the goal's true position in the strategist's text only (a21,
    # q05), flown beside R13 at the same SHA. Not a control: the operator's second
    # candidate. R13 README, "Two agents".
    "R13G": {"folder": "R13G_verify_goal_words", "title": "R13 with goal truth in the search menu",
             "agent": "a21", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R14: a20 with a18's floor map and a verify step limit grown with the distance
    # back (a22); R14G: the same on a21 (a23). Flown beside R13/R13G's results
    # (operator, 2026-10-28: fix what probing finds, then fly, without waiting).
    "R14": {"folder": "R14_open_floor", "title": "R13 with g05's floor read as open",
            "agent": "a22", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R14G": {"folder": "R14G_open_floor_goal_words",
             "title": "R14 with goal truth in the search menu",
             "agent": "a23", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R15: the goal's true position kept by the planner again (a16's routing, R11's
    # 11/18) on a17's memory with reachable detours only and a22's floor map (a25);
    # R15N: a25 with navigator prompt p16 (a26). Goal truth is a tool here (operator,
    # 2026-10-28: the aim is the best agent).
    "R15": {"folder": "R15_known_goal_reach", "title": "Known goal, reachable detours",
            "agent": "a25", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R15N": {"folder": "R15N_known_goal_ranked_notes",
             "title": "R15 with the navigator's notes ranked (p16)",
             "agent": "a26", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R16: a22 (R14) with the goal confirmer c01 and verify's check look within 2.6 m
    # (a27); R16K: a25 (R15, known goal) with c01 (a28). Each line moves on beside
    # the other before its previous round is read (overnight, 2026-10-29).
    "R16": {"folder": "R16_goal_confirmer", "title": "R14 with a goal confirmer",
            "agent": "a27", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R16K": {"folder": "R16K_known_goal_confirmer",
             "title": "R15 (known goal) with a goal confirmer",
             "agent": "a28", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R17": {"folder": "R17_doorway_first", "title": "R15 (known goal) with detour strategist q07",
            "agent": "a31", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R17K": {"folder": "R17K_doorway_first_confirmer",
             "title": "R16K (known goal, goal confirmer) with detour strategist q07",
             "agent": "a32", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R18": {"folder": "R18_detour_stall", "title": "R17 with stalled detours handed back",
            "agent": "a33", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R18K": {"folder": "R18K_detour_stall_confirmer",
             "title": "R17K with stalled detours handed back",
             "agent": "a34", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R19": {"folder": "R19_searched_defined",
            "title": "R15N with 'searched already' defined and stalled detours handed back",
            "agent": "a35", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R19K": {"folder": "R19K_searched_defined_confirmer",
             "title": "R19 with the goal confirmer",
             "agent": "a36", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R20": {"folder": "R20_door_confirmer", "title": "R19 with the doorway confirmer",
            "agent": "a37", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R20K": {"folder": "R20K_door_confirmer_goal_confirmer",
             "title": "R19K with the doorway confirmer",
             "agent": "a38", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R21": {"folder": "R21_along_wall", "title": "R20 with along-the-wall detours",
            "agent": "a40", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R21K": {"folder": "R21K_along_wall_goal_confirmer",
             "title": "R20K with along-the-wall detours",
             "agent": "a41", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R22": {"folder": "R22_open_near_unwalled",
            "title": "R21 without the wall at the end of an open_near strip",
            "agent": "a42", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R22K": {"folder": "R22K_open_near_unwalled_goal_confirmer",
             "title": "R21K without the wall at the end of an open_near strip",
             "agent": "a43", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R23": {"folder": "R23_through_doorway",
            "title": "R22 with the doorway tags fixed and navigator p18",
            "agent": "a44", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R23K": {"folder": "R23K_through_doorway_goal_confirmer",
             "title": "R22K with the doorway tags fixed and navigator p18",
             "agent": "a45", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R25": {"folder": "R25_best_open_near_unwalled",
            "title": "R20K without the wall at the end of an open_near strip",
            "agent": "a48", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R25D": {"folder": "R25D_door_confirmer_open_near_unwalled",
             "title": "R20 without the wall at the end of an open_near strip",
             "agent": "a49", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R26": {"folder": "R26_other_way",
            "title": "R22K with the other way at the fork",
            "agent": "a58", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R26N": {"folder": "R26N_other_way_no_goal_confirmer",
             "title": "R22 with the other way at the fork",
             "agent": "a59", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R27": {"folder": "R27_mirrored_nr_perceiver",
            "title": "R25D with the perceiver read twice, plain and mirrored (g07)",
            "agent": "a60", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R28": {"folder": "R28_wall_reader",
            "title": "R25D with each strip's floor from a wall reader (w01)",
            "agent": "a61", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R29: the host, not the agent (operator, 2026-11-02). Probe LD found the model
    # deterministic when called alone with a warm prefix cache, and two thirds of
    # the flight-time missed walls gone when the same frame is read alone. Every
    # round so far ran 4 lanes on one vLLM (N1: 16-28% of strip fields change with
    # neighbours in the batch). R29N re-flies a49 that way; R29S flies a49 with one
    # lane per vLLM instance. Same agent, same sha, in both. R29 README.
    "R29N": {"folder": "R29N_host_noise_shared",
             "title": "a49 again, 4 lanes on one vLLM (host-noise control)",
             "agent": "a49", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R29S": {"folder": "R29S_host_noise_solo",
             "title": "a49, one lane per vLLM instance (every call alone)",
             "agent": "a49", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R30: a code route planner (A* over the memory's cost map, planner.pathfind)
    # in place of a49's local goal-way test and the q03 detour strategist. The
    # s03 dead end and the s02 door wall are routing failures on a map that was
    # right (probe B0, s03_tines_analysis, R19's s02 analysis). R30 README and
    # docs/research/pathfinder-plan.md.
    # a65 after the shakedown's first s03 dynamic run on a63, a66 after a63's
    # s02c and a64's s03 traces (R30 README, Probe gate 2): side-strip near
    # walls, local mobility, firm walls. Neither a63 nor a65 flew as a round.
    "R30": {"folder": "R30_pathfinder",
            "title": "a49 with a code route planner in place of goal-way and q03",
            "agent": "a66", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R31: a72 = a66 with memory a17h (one look is soft: two-pose confirmation
    # of doorways and firm walls, two strong closes kill an opening) and route
    # commitment. Offline gate on R30's records failed (R31 README, Probe
    # gate): the route crosses the s02 divider through phantom floor on 90%+
    # of near-side steps under every map variant tried. Not flown.
    "R31": {"folder": "R31_two_pose_commit",
            "title": "a66 with one-look-is-soft memory (a17h) and route commitment",
            "agent": "a72", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R32: the repeat screen (operator, 2026-11-04). a49 (R25D) and a66 (R30)
    # both scored 14/18 on one seed, on a family that expects 11.3 +- 1.4; the
    # final 90 flies whichever has the higher rate on the contested cells.
    # Flown together on the same host, as R25 beside R25D. R32 README.
    "R32": {"folder": "R32_repeat_a49",
            "title": "a49 on the ten contested cells, seeds 1-3",
            "agent": "a49", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    "R32P": {"folder": "R32P_repeat_a66",
             "title": "a66 on the ten contested cells, seeds 1-3",
             "agent": "a66", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
             "seeds": REPEAT_SEEDS, "citable": False},
    # F: the final round (spec §6), the full Phase 1 design on the agent the
    # screening chose: a66 by R32's decision rule (15/30 against a49's 11/30,
    # operator 2026-11-04, "Fly the final"). Order random.Random("phase2-F").
    "F": {"folder": "final", "title": "Final: a66 (R30's route planner) on the full design",
          "agent": "a66", "sites": ROUND_SITES, "seeds": list(SEEDS), "citable": True},
    # R33: a73 (a66 with the wall-turn rule and the Round F cost map) on the
    # ten contested cells, seeds 1-3, read against R32P (a66, 15/30). Laid out
    # from Round F's 90 recorded runs (docs/research/round-f-analysis.md).
    "R33": {"folder": "R33_wall_turn_costmap",
            "title": "a66 with the wall-turn rule and the Round F cost map, contested cells",
            "agent": "a73", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R34: a74 (a73 on a map where only visited ground is known), the same
    # screen, read against R32P and R33.
    "R34": {"folder": "R34_visits_only_map",
            "title": "a73 with only visited ground known to the route, contested cells",
            "agent": "a74", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R35: a75 (a66 with the wall-turn rule alone), the same screen, after
    # R33's shakedown split the bundle. Read against R32P (a66, 15/30).
    "R35": {"folder": "R35_wall_turn_only",
            "title": "a66 with the wall-turn rule alone, contested cells",
            "agent": "a75", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R36: a76 (a66 with the door approach pose), the same screen. Read against
    # R32P (a66, 15/30) and R35 (a75, 13/30).
    "R36": {"folder": "R36_door_approach",
            "title": "a66 with the door approach pose, contested cells",
            "agent": "a76", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R37: a77 (a66 with doorway reads trusted by the look, and a76's approach
    # on trusted doorways), the same screen. Read against R32P (a66, 15/30).
    "R37": {"folder": "R37_trusted_doorways",
            "title": "a66 with doorway reads trusted by the look, contested cells",
            "agent": "a77", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R38: a78 (a66 with a dead-end latch: confirmer e01, the corridor shut on
    # the route's map, the sentence while latched), the same screen. Read
    # against R32P (a66, 15/30). Not flown before probe DE passes.
    "R38": {"folder": "R38_dead_end_latch",
            "title": "a66 with a dead-end latch, contested cells",
            "agent": "a78", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R39: a79 (a66 with R38's dead-end latch fired by the drone's own trail,
    # planner.confined_run, no confirmer), the same screen. Read against R32P
    # (a66, 15/30). Overnight run 2026-11-05.
    "R39": {"folder": "R39_confined_latch",
            "title": "a66 with the dead-end latch fired by the trail, contested cells",
            "agent": "a79", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R40: a80 (a66 with the wall survey, planner.wall_survey: square looks at
    # the wall either side of a closed door met on the direct line), the same
    # screen. Read against R32P (a66, 15/30). Overnight run 2026-11-05.
    "R40": {"folder": "R40_wall_survey",
            "title": "a66 with the wall survey, contested cells",
            "agent": "a80", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R41: a81 (a80 with the survey's through phase made sure after a80's
    # shakedown), the same screen. Read against R32P (a66, 15/30).
    "R41": {"folder": "R41_survey_check",
            "title": "a66 with the wall survey, through phase checked, contested cells",
            "agent": "a81", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R42: a82 (a81 with the survey homing on the door's bearing while the
    # wall's range is unknown), the same screen. Read against R32P (a66, 15/30).
    "R42": {"folder": "R42_survey_homing",
            "title": "a66 with the wall survey homing on the door's bearing, contested cells",
            "agent": "a82", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R43: a83, a bundle: the wall survey after a82's shakedown (far reads pick
    # the side only, no crossing of rays, the goal in view ends it) with
    # a79's dead-end latch, sooner and with a steadier way out. The same
    # screen, read against R32P (a66, 15/30) and R39 (a79).
    "R43": {"folder": "R43_survey_latch",
            "title": "a66 with the wall survey and the dead-end latch, contested cells",
            "agent": "a83", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R44: a84, R43's bundle with the two faults its shakedown showed taken
    # out (the survey ended by a goal report that was not there; the latch's
    # lane narrower than the tine). The same screen, read against R32P (a66,
    # 15/30) and R39 (a79, 15/30).
    "R44": {"folder": "R44_survey_latch_fixed",
            "title": "a66 with the wall survey and the dead-end latch, after R43's shakedown, contested cells",
            "agent": "a84", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R45: a85 (a84 with the survey's last stretch: reads out to 65 degrees
    # once a door is being flown at, a line-up in front of the door when
    # stopped by the wall, through by distance flown). The same screen, read
    # against R32P (a66, 15/30) and R44 (a84).
    "R45": {"folder": "R45_survey_lineup",
            "title": "a84 with the survey lining up on the door, contested cells",
            "agent": "a85", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R46: a86 (a85 with a70's route-behind sentence always, the latch kept
    # off the survey's ground, and the survey's through-by-distance rule
    # replaced by a short second look). The same screen, read against R32P
    # (a66, 15/30), R44 (a84) and R45 (a85).
    "R46": {"folder": "R46_behind_always",
            "title": "a85 with the route-behind sentence always and the latch off the survey's ground, contested cells",
            "agent": "a86", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R47: a87 (a86 with the survey's stations shut only by walls the drone
    # has met). The same screen, read against R44 (a84, 18/30) and the rounds
    # between.
    "R47": {"folder": "R47_station_guard",
            "title": "a86 with the survey's stations shut only by walls the drone has met, contested cells",
            "agent": "a87", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R48: a88 (a87 with the latched corridor's lane opened again when the
    # drone is back inside it). The same screen, read against R45 (a85, 23/30)
    # and the rounds between.
    "R48": {"folder": "R48_latch_reopen",
            "title": "a87 with the latched corridor reopened to a drone back inside it, contested cells",
            "agent": "a88", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R49: a89 (a88's planner with a85's navigator: the route-behind sentence
    # only inside a latched corridor, after R46). The same screen, read
    # against R45 (a85, 23/30).
    "R49": {"folder": "R49_no_sentence",
            "title": "a88's planner without the route-behind sentence outside a latched corridor, contested cells",
            "agent": "a89", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R50: a90 (a89 with a86's sentence outside a latched corridor again, but
    # not on the drone's first way in). The same screen, read against R45
    # (a85, 23/30), R46 (a86) and R49 (a89).
    "R50": {"folder": "R50_sentence_after_way_in",
            "title": "a89 with the route-behind sentence after the first way in, contested cells",
            "agent": "a90", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R51: a91 (a89 without a87's station guard: a85's navigator on a86's
    # planner). With R46, R47 and R49 a square over a86's planner: the
    # sentence and the station guard, each on and off.
    "R51": {"folder": "R51_no_station_guard",
            "title": "a85's navigator on a86's planner (a89 without the station guard), contested cells",
            "agent": "a91", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R52: a92 (a91 with the survey waiting 12 steps before it gives a
    # station up, after 9 first stations given up in transit in R45-R51).
    "R52": {"folder": "R52_station_stall",
            "title": "a91 with the survey's stations held for 12 steps, contested cells",
            "agent": "a92", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R53: a93 (a89 with the perceiver's goal reports checked against the
    # bearing to the goal: 249 reports with no line of sight in R44-R52, the
    # navigator took the tag on 247; s03 seed 1 turned off the stem's line at
    # step 2 on one in 12 of 14 runs).
    "R53": {"folder": "R53_goal_check",
            "title": "a89 with goal reports off the line to the goal dropped, contested cells",
            "agent": "a93", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
    # R54: a host round (2026-11-02's rule), flown beside R53: the same a93,
    # Godot rendered on an H100 (GODOT_VK=nvidia) and not by lavapipe. Not an
    # agent change: it asks whether a round flown on H100 frames reads like
    # one flown on lavapipe's.
    "R54": {"folder": "R54_h100_frames",
            "title": "a93 again with Godot rendered on an H100 (host round), contested cells",
            "agent": "a93", "sites": CONTESTED_SITES, "arms": CONTESTED_ARMS,
            "seeds": REPEAT_SEEDS, "citable": False},
}

#: Phase 1 §3 and §6, minus the prompt: in Phase 2 the prompt is part of the
#: agent, and each round's own config.lock.json adds the agent's version and
#: sha and its prompt's version and sha.
LOCK: Dict[str, Any] = {
    "spec": "docs/phase2-test-plan.md",
    "model": "Qwen3-VL-30B-A3B",
    "vlm_profile": "remote",
    "temperature": 0.0,
    "frame_size": [768, 768],
    "freeze_world": True,
    "physics_ticks_per_second": 60,
    "godot_version": "4.7.2-stable (official)",
    "config": {"fov_deg": 87.0, "camera_pitch": 0.0, "num_actions": 5,
               "include_turn_around": True, "fan_spread": 1.0,
               "action_dist": 1.7, "annotation_distance": 6.0},
    "max_steps": 60,
    "max_collisions": -1,
    "stop_on_goal": True,
    "wall_clock_s": 900,
    "seeds": list(SEEDS),
    "spawn_jitter": {"dz_m": 0.5, "dyaw_deg": 5.0},
    "sites": {site_id: version for site_id, version in SITES.values()},
    # P2.0 flies the stand-in router (server/decider/fake_litellm.py), as 1.0 did.
    "overrides": {"P2.0": {"model": "stub"}},
}

for _round, _spec in ROUNDS.items():
    if not _spec.get("agent"):
        raise SystemExit("round {0} names no agent".format(_round))

def round_readme(unit: str) -> str:
    """Stub for a round's write-up (docs/phase2-test-plan.md §4 step 1).

    Filled in and committed before the round flies; after it flies only the
    Outcome section changes. Every claim under Evidence cites a path.
    """
    spec = ROUNDS[unit]
    ident = agents.describe(spec["agent"])
    return "\n".join([
        "# {0}: {1}".format(unit, spec["title"]), "",
        "**Agent:** `{agent_version}` (`{agent_sha}`) · **Prompt:** `{prompt_version}` "
        "(`{prompt_sha}`) · **Status:** pre-registered, not flown".format(**ident), "",
        "Written before flying. Spec: `docs/phase2-test-plan.md`.", "",
        "## Change", "", "<!-- One change, and how it differs from the agent it builds on. -->", "",
        "## Evidence", "",
        "<!-- Past data that points at this change. Every claim cites a path: results tables,",
        "     summary.md, run IDs and steps, evidence.md (python eval/agent_evidence.py ...). -->", "",
        "## Hypothesis", "", "<!-- One falsifiable sentence. -->", "",
        "## Predictions", "", "<!-- Per arm, and per site where it differs. Direction and size. -->", "",
        "| Arm | Baseline (R0) | Predicted |", "|---|---|---|",
        "| initial | | |", "| final | | |", "| dynamic | | |", "",
        "## Manipulation check", "",
        "<!-- A measurable sign the change took effect, independent of success. -->", "",
        "## Drop criterion", "", "<!-- The result that means this change is not carried forward. -->", "",
        "## Probe gate", "",
        "<!-- Required when the change touches what the model is asked to perceive (§4 step 2):",
        "     eval/goal_probe.py thresholds, set before the probe runs. Otherwise \"Not needed\". -->", "",
        "## Builds on", "", "<!-- Previous round and agent. -->", "",
        "## Outcome", "", "Not flown. After the round: one line on whether the hypothesis held, "
        "and a link to [summary.md](summary.md).", ""])


PHASE = Phase(number=2, root=PHASE_DIR, unit_key="round", unit_label="Round",
              units=ROUNDS, lock=LOCK, script="eval/phase2.py",
              spec="docs/phase2-test-plan.md", agent_lock=agents.describe,
              unit_readme=round_readme)

BASELINE = "R0"
BASELINE_NOTE = ("R0 is the Phase 1 agent (a00), not flown again: its seed-1 runs from "
                 "eval/phase1/, under the same lock apart from the agent fields.")


def baseline_runs() -> List[Dict[str, Any]]:
    """Phase 1's seed-1 runs, as the round every Phase 2 round is compared with."""
    units = phase1.PHASE.complete_units(citable_only=True)
    return [dict(r, unit=BASELINE) for r in phase1.PHASE.collect_runs(units)
            if r["seed"] in ROUND_SEEDS]


def cell(run: Dict[str, Any]) -> str:
    if run["goal_reached"]:
        return "✓ {0}".format(run["steps"])
    return "✗ {0}".format(run["label"] or run["end_reason"])


def cells(runs: List[Dict[str, Any]]) -> str:
    """One run: as cell(). Several (a repeat screen, R32): solved k/n and each
    run's steps or label, seeds in order."""
    if len(runs) == 1:
        return cell(runs[0])
    solved = sum(1 for r in runs if r["goal_reached"])
    return "{0}/{1}: ".format(solved, len(runs)) + ", ".join(
        str(r["steps"]) if r["goal_reached"] else (r["label"] or r["end_reason"])
        for r in sorted(runs, key=lambda r: r["seed"]))


def cmd_results(_args: argparse.Namespace) -> int:
    """Every complete round side by side, R0 first. Deterministic, like Phase 1's."""
    screening = [u for u in PHASE.complete_units(citable_only=False)
                 if not ROUNDS[u]["citable"] and u != "P2.0"]
    finals = PHASE.complete_units(citable_only=True)
    columns = [(BASELINE, baseline_runs())]
    columns += [(u, PHASE.collect_runs([u])) for u in screening]

    lines = ["# Phase 2 results", "",
             "Generated by `python eval/phase2.py results`. Do not edit by hand.", "",
             "Spec: `docs/phase2-test-plan.md`. One run per cell (seed 1), so each "
             "cell is a screen, not an estimate; a repeat screen (R32) flies three "
             "seeds per contested cell and reads k/3. " + BASELINE_NOTE, ""]
    pending = sum(1 for _, runs in columns[1:] for r in runs if not r["label"])
    if pending:
        lines += ["> **{0} runs have no manual label yet.** Rerun after labelling."
                  .format(pending), ""]

    lines += ["## Rounds", "",
              "| Round | Agent | Title |", "|---|---|---|",
              "| {0} | a00 | Phase 1 baseline |".format(BASELINE)]
    lines += ["| {0} | {1} | {2} |".format(u, ROUNDS[u]["agent"], ROUNDS[u]["title"])
              for u in screening]
    lines.append("")

    lines += ["## Success by arm", "",
              "| Arm | " + " | ".join(name for name, _ in columns) + " |",
              "|---" * (len(columns) + 1) + "|"]
    for arm in ARMS:
        counts = []
        for _, runs in columns:
            in_arm = [r for r in runs if r["arm"] == arm]
            counts.append("{0}/{1}".format(sum(r["goal_reached"] for r in in_arm),
                                           len(in_arm)))
        lines.append("| {0} | {1} |".format(arm, " | ".join(counts)))
    lines.append("")

    lines += ["## Every cell", "",
              "✓ steps to goal, or ✗ and the §9 label (end reason if not yet labelled).", "",
              "| Site | Arm | " + " | ".join(name for name, _ in columns) + " |",
              "|---|---" + "|---" * len(columns) + "|"]
    for site in ALL_SITES:
        for arm in ARMS:
            row = []
            for _, runs in columns:
                match = [r for r in runs if r["site"] == site and r["arm"] == arm]
                row.append(cells(match) if match else "")
            lines.append("| {0} | {1} | {2} |".format(site, arm, " | ".join(row)))
    lines.append("")

    final_runs: List[Dict[str, Any]] = []
    if finals:
        final_runs = PHASE.collect_runs(finals)
        lines += ["# Final round ({0}, agent {1})".format(
            ", ".join(finals), ", ".join(ROUNDS[u]["agent"] for u in finals)), ""]
        lines += s11_tables(final_runs)

    PHASE.results_dir.mkdir(parents=True, exist_ok=True)
    (PHASE.results_dir / "results.md").write_text("\n".join(lines))
    flown = [r for _, runs in columns[1:] for r in runs] + final_runs
    write_runs_csv(PHASE.results_dir / "runs.csv", flown, PHASE.unit_key)
    print("{0} rounds + {1} -> {2}".format(len(screening), BASELINE,
                                           PHASE.results_dir.relative_to(REPO_ROOT)))
    return 0


def main() -> int:
    return PHASE.main(__doc__, extra=lambda sub: sub.add_parser("results")
                      .set_defaults(func=cmd_results))


if __name__ == "__main__":
    raise SystemExit(main())
