# R10 probe: a14

Strategist part run 2026-10-24 on the Mac against `Qwen3-VL-30B-A3B` (remote profile, :8004), at
`b98fe7a`, agent `a14` (`63ad006476b6`), strategist `q02` (`f3a866c9d927`). Set:
`strat_set.jsonl` (R9's 321 strategist calls, rebuilt as a14 words them). Results:
`strat_a14.jsonl`; log `r10_probe.log`.

    python eval/r10_probe.py sample-strategist eval/phase2/R9_hail_mary/runs --out strat_set.jsonl
    VLM_PROFILE=remote VLM_AGENT=a14 python eval/r10_probe.py run-strategist strat_set.jsonl --out strat_a14.jsonl
    python eval/r10_probe.py report strat_a14.jsonl turn_a14.jsonl

**Result: the strategist lines pass, two of them by about a point. The turn line is pending**
(it needs R9's frames, on sctsvr6). R10 does not fly until it is run.

## Gate

| Check | Threshold | a14 |
|---|---|---|
| strategist goal-ward: target ≥ 3 m nearer the true goal than the drone | ≥ 55% | **56.1%** (180/321) |
| … against `q01`'s recorded answers on the same calls (113/321, 35.2%) | at least 20 points higher | **+20.9 points** |
| `q02` chooses "explore" | ≤ 20% | **9.0%** (29/321) |
| navigator picks an open move with [0] not offered (25 R9 steps) | ≥ 80% | **pending** |

## Not gated, read before flying

- **The margins are thin.** Goal-ward clears its threshold by 1.1 points and the gain by 0.9:
  about 3 calls each.
- **Agreement with `q01`:** the same target on 204 of 321 calls. Both goal-ward 105, only `q02`
  75, only `q01` 8, neither 133.
- **Choices** (`q02` against `q01`): goal 98 (80), doorway 99 (86), unexplored ground 91 (98),
  explore 29 (37), backtrack 4 (20). Told where the goal is, `q02` still chooses it on under a
  third of calls; most of the gain is fewer backtracks and explores, and doorways and frontiers on
  the goal's side.
- **Modes:** explore 192, approach 125, backtrack 4.
- **By arm**, goal-ward: `dynamic` 59/117, `final` 65/123, `initial` 56/81.
- **No failed calls** (321/321 answered); mean latency 1.6 s.
- **What this set cannot show:** every call keeps R9's history. The target standing before each
  call, the drone's position and the trigger are `q01`'s run, so this is how `q02` chooses in R9's
  situations, not how an a14 run unfolds. Where a14's trigger rule would not have asked, the
  recorded trigger is used (a13's sentence mapped to a14's wording).

## Turn rule (pending)

On sctsvr6, with R9's runs and frames:

    VLM_PROFILE=remote VLM_AGENT=a14 python eval/r10_probe.py sample-turn <R9 runs with frames> --out turn_set.jsonl
    VLM_PROFILE=remote VLM_AGENT=a14 python eval/r10_probe.py run-turn turn_set.jsonl --out turn_a14.jsonl
    python eval/r10_probe.py report strat_a14.jsonl turn_a14.jsonl

The offline set (no frames) finds the same 25 steps: R9 turned around while a14 would not have
offered [0].
