# R11 probe: a16

Run 2026-10-27 at `1cad3c8`, agent `a16` (`6d614e3c4450`, memory `spatial_a16` `1af123e381c0`),
against `Qwen3-VL-30B-A3B` (remote profile, vLLM on 127.0.0.1:8004), as [a15's](probe_a15.md):
detour line on the Mac, toward line on sctsvr6 in Docker (`~/r11_probe.sh` with
`VLM_AGENT=a16`, scratch clone `~/r11_scratch`; a15's outputs there moved to
`~/r11_a15_probe_out`).

**Result: gate failed on two lines. R11 does not fly with `a16` under the gate as written.** The
detour lines now pass by a wide margin; the near-repeat line fails by design (below) and the
navigator line by one pick.

## What a16 changes from a15

- **Block window by kind:** 15° after a move that did not get going (under 0.3 m), 25° after one
  that stopped short (a15: 45° for both). At 45° one block straight ahead noted all five forward
  moves (28 of R10's steps), and on 3 of a15's 14 navigator steps the navigator then took the
  move that had been blocked.
- **Goal-side detour menu:** each unexplored edge is offered at its cell nearest the goal,
  nearest first (a15: at the edge's centre, largest first). On a15's 88 detour situations,
  menus holding a detour 3 m nearer the goal: 36 → 85.

## Gate

| Check | Threshold | a15 | a16 |
|---|---|---|---|
| near-repeat collisions noted (code only) | ≥ 30 of 37 | 32 | **22** |
| route planner keeps the goal (code only) | ≥ 50% | 57% | 57% (434/755) |
| "toward" on a not-open action (code only) | 0 | 0 | 0 |
| goal truth in navigator text (code only) | 0 | 0 | 0 |
| `q03` detour ≥ 3 m nearer the goal | ≥ 60% | 40% | **95%** (82/86) |
| `q03` chooses "explore" | ≤ 10% | 32% | **1%** (1/86) |
| `p14` pick carries no not-open note | ≥ 80% | 64% | **79%** (11/14) |

## The two failed lines

- **Near-repeats, 22 of 37.** The line cannot pass without the saturation that failed a15's
  navigator line. Over R9, R10C and R10's 2179 forward picks (111 stopped short):

  | Window (full block / stopped short) | near-repeats noted | noted, stopped short | noted, flew | R10 steps with every forward move noted |
  |---|---|---|---|---|
  | 15° / 15° | 11 | 11 | 1 | 0 |
  | 15° / 25° (a16) | 22 | 22 | 11 | 0 |
  | 25° / 25° | 24 | 24 | 19 | 0 |
  | 25° / 45° | 28 | 28 | 25 | 17 |
  | 45° / 45° (a15) | 32 | 32 | 28 | 28 |

  Falling back to 15° on steps where every forward move would be noted keeps only 13–14: most
  near-repeats happen where the whole fan faces a wall. After a full block, the next fan move out
  stopped short 2 of 11 times; after a stopped-short move, 11 of 20 (same heading 10 of 10).
- **Navigator, 11 of 14.** The three "blocked here before" picks are gone (s02vc `final` 19, s03
  `initial`/`dynamic` 9 now take the next move out, which flew 1.7 m in R10). Left: s02a
  `dynamic` and `initial` step 3 ("goal about one move ahead" with "wall close" on the same
  move; R10 took it and flew 1.7 m, so the wall note was wrong), and s02c `final` 3 ("wall close"
  and "doorway (seen now)" on [4]; R10 took [5]). The set is 14 steps, 12 distinct; one pick is
  7 points.

## Detour line

Choices: frontier 85, explore 1; no failed calls (86/86). Menus with a goal-ward detour 83 of 86;
`q03` took one on 82. 86 situations, not 88: a16's map asks on slightly different steps
(blocked 34, stall 14, walled 38).

## Smoke (not gated)

`VLM_AGENT=a16 python eval/r11_probe.py smoke eval/phase2/R10_goal_planner/runs`: 755 decisions,
0 failed steps, 0 leaks, 0 "toward" on a not-open action; goal standing on 423; `q03` asked 40
times (5%: stall 17, walled 15, blocked 8); detours handed back 35 (too long 16, closed 12, goal
in view 7, reached 0 with the stub's first-listed pick). Re-render of R9, R10C and R10
byte-identical; 15/15 locks match.

## Commands

    VLM_AGENT=a16 python eval/r11_probe.py offline --r9 eval/phase2/R9_hail_mary/runs \
        --r10c eval/phase2/R10C_a13_control/runs --r10 eval/phase2/R10_goal_planner/runs
    VLM_AGENT=a16 python eval/r11_probe.py sample-detour eval/phase2/R10_goal_planner/runs --out detour_set_a16.jsonl
    VLM_PROFILE=remote VLM_AGENT=a16 python eval/r11_probe.py run-detour detour_set_a16.jsonl --out detour_a16.jsonl
    # on sctsvr6, ~/r11_probe.sh (VLM_AGENT=a16):
    VLM_PROFILE=remote VLM_AGENT=a16 python eval/r11_probe.py sample-toward /r10/eval/phase2/R10_goal_planner/runs --out toward_set.jsonl
    VLM_PROFILE=remote VLM_AGENT=a16 python eval/r11_probe.py run-toward toward_set.jsonl --out toward_a16.jsonl
    VLM_AGENT=a16 python eval/r11_probe.py report detour_a16.jsonl toward_a16.jsonl

Files: `detour_set_a16.jsonl`, `detour_a16.jsonl`, `r11_detour_probe_a16.log`,
`toward_set_a16.jsonl`, `toward_a16.jsonl`, `r11_toward_probe_a16.log`, `report_a16.txt`.
