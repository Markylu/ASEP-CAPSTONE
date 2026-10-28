# R11 probe: a15

Run 2026-10-26/27 at `a1b871b`, agent `a15` (`a17e9cadddc3`), against `Qwen3-VL-30B-A3B`
(remote profile, vLLM on 127.0.0.1:8004). Detour line on the Mac; toward line on sctsvr6 in
Docker (`~/r11_probe.sh`, scratch clone `~/r11_scratch` from `~/r11.bundle`, R10's frames read
from `~/asep-r10`, mounted read-only at `/r10`).

**Result: gate failed. R11 does not fly with `a15`.** The offline lines passed (README); all three
live lines failed.

## Gate

| Check | Threshold | a15 |
|---|---|---|
| `q03` detour ≥ 3 m nearer the true goal than the drone | ≥ 60% | **40%** (35/88) |
| `q03` chooses "explore" | ≤ 10% | **32%** (28/88) |
| `p14` pick carries no not-open note, a15's notes | ≥ 80% | **64%** (9/14) |

## Why

- **The detour menu, not `q03`.** 52 of the 88 menus held no detour 3 m nearer the goal. Where
  one was offered (36), `q03` chose a goal-ward one 35 times. By reason asked: blocked 34 (menu
  had one 19, chosen 19, explore 12), stall 14 (10, 9, 1), walled 40 (7, 7, 15). When the way to
  the goal is walled, the menu is mostly ground behind or beside the drone, and `q03` takes
  "explore" instead.
- **Choices:** frontier 52, explore 28, opening 5, backtrack 3. No failed calls (88/88); mean
  latency 2.4 s.
- **The navigator's five not-open picks.** Two are "goal about one move ahead" with "wall close"
  on the same action (s02a `dynamic` and `initial` step 3: the perceiver contradicts itself, and
  R10 took the same move). Three are "blocked here before" with "doorway (seen now)" on the
  straight move (s02vc `final` 19; s03 `initial` and `dynamic` 9, which R10 flew identically, so
  two distinct situations). The set is 14 steps (12 distinct): one pick is 7 points.

## Commands

    python eval/r11_probe.py sample-detour eval/phase2/R10_goal_planner/runs --out detour_set.jsonl
    VLM_PROFILE=remote VLM_AGENT=a15 python eval/r11_probe.py run-detour detour_set.jsonl --out detour_a15.jsonl
    # on sctsvr6, ~/r11_probe.sh:
    VLM_PROFILE=remote VLM_AGENT=a15 python eval/r11_probe.py sample-toward /r10/eval/phase2/R10_goal_planner/runs --out toward_set.jsonl
    VLM_PROFILE=remote VLM_AGENT=a15 python eval/r11_probe.py run-toward toward_set.jsonl --out toward_a15.jsonl
    python eval/r11_probe.py report detour_a15.jsonl toward_a15.jsonl

Files: `detour_set.jsonl`, `detour_a15.jsonl`, `r11_detour_probe.log`, `toward_set.jsonl`,
`toward_a15.jsonl`, `r11_toward_probe.log`, `report.txt`.
