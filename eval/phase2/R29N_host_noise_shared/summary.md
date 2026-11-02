# R29N a49 again, 4 lanes on one vLLM: summary

**11/18 (R25D 14): the same agent, the same host layout, three runs fewer.** `a49` re-flown as
R25D was flown, 4 lanes sharing `:8004`, nothing else on it:
- `initial`: 6/6 (R25D 6/6).
- `final`: 3/6 (R25D 3/6). Won s02c and s02va, which R25D lost; lost s02a and s02vc, which R25D won.
- `dynamic`: 2/6 (R25D 5/6). Lost s02a, s02c (1.4 m short at step 60) and s02vc.

Nothing changed but the draw. Five s02 cells flipped against R25D, three down and two up, and
the step-0 perceiver reading differs from R25D's in 12 of 18 cells on byte-identical frames
([why_14.md](../R25D_door_confirmer_open_near_unwalled/why_14.md) §4 again). 11 is where the
`a17b` family's expectation sits (11.3 ± 1.4); R25D's 14 was the upper draw why_14 said it was.

In flight (`eval/r28_flight.py`): missed walls **15.4%** (R25D 17.3%), phantom walls 12.0% (12.7%),
s03 phantom 14.1% (16.2%), longest turn-around streak 3 (3). Gate check 5 (shared host reproduces
R25D's wall rates within 4 pts): **holds**.

The two s03 failures are the dead-end pattern: into the shut tine, 34–46 steps there, never out.
The four s02 failures walk the door wall with the open door seldom in view and never cross the
divider. s02c `dynamic` got through at about step 50 and ran out of steps 1.4 m from the goal.

**Not citable.** Agent `a49` (`83f7a6a19b01`), prompt `p17`, perceiver `g05`, strategist `q03`,
door confirmer `d01`, memory `a17b`; `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6, lanes 1–4 (`~/asep-r29n-l1..4`, `~/round_lane.sh`), shared vLLM `:8004`, nothing
  else on it. The three `:8006`–`:8008` copies were loading on GPUs 3–5 during this round and took
  no calls.
- Flown at `822f1d7` on 2026-11-02, 16:00–16:33 UTC, 32 min. **18/18 valid**, 0 of 731 perceiver
  calls failed.
- Labels: Claude review, not yet confirmed by the operator.

The gate's reading across both rounds: [R29S summary](../R29S_host_noise_solo/summary.md).
