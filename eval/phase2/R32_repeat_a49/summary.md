# R32 / R32P a49 and a66 on the ten contested cells, seeds 1-3: summary

**a66 15/30, a49 11/30: gap 4, at the decision rule's threshold of 3. By the rule written
before flying, the final 90 flies `a66`.** s03 `final` 3/3 for `a66` (22, 56 and 25 steps, the
shut door on tine R at seed 2) against 1/3 for `a49`; s03 `dynamic` 0/3 for both, as in every
round since R1. Fisher's exact two-sided p = 0.44: the gap is a screen's reading, not an
estimate, and the final's 90 runs are the estimate.

| cell | `a49` (R32) | `a66` (R32P) |
|---|---|---|
| s02a `final` | 3/3 (48, 48, 49) | 2/3 (38, 22, —) |
| s02a `dynamic` | 1/3 (26, —, —) | 2/3 (—, 25, 46) |
| s02c `final` | 1/3 (26, —, —) | 1/3 (—, —, 52) |
| s02c `dynamic` | 0/3 | 0/3 |
| s02va `final` | 2/3 (—, 53, 32) | 2/3 (36, —, 46) |
| s02va `dynamic` | 1/3 (—, 56, —) | 2/3 (28, —, 47) |
| s02vc `final` | 2/3 (29, —, 34) | 1/3 (—, —, 60) |
| s02vc `dynamic` | 0/3 | 2/3 (50, 40, —) |
| s03 `final` | 1/3 (55, —, —) | **3/3** (22, 56, 25) |
| s03 `dynamic` | 0/3 | 0/3 |
| **total** | **11/30** | **15/30** |
| s02 | 10/24 | 12/24 |
| s03 | 1/6 | 3/6 |

Against the predictions (README): `a49` 10–12, landed 11; `a66` 10–13, landed 15, above its
range on s02vc `dynamic` (predicted 1, got 2) and s03 `final` (predicted 2, got 3). The R19–R30
per-cell rates put both at 10.7 of 30; `a66`'s 15 is 1.6 family sigmas above that, `a49`'s 11 on it.

What the runs say:
- **s03 `final` is the planner's cell.** `a66` took the open tine in all three runs: 0 steps in
  the shut tine, lobby 4 in each (`eval/r30_check.py`); seed 2 (door R shut) solved at 56. `a49`
  solved only seed 1 (55 steps), and lost seeds 2 and 3 at 9.8 and 7.3 m, in the shut tine.
- **s03 `dynamic` stays unsolved** (0/6 here, 0/47 in Phase 2): `a66` spent 35, 39 and 19 steps
  in the shut tine after the closed read, open tine 0, the oscillation R30 and its shakedown
  described. The lobby cost 4 steps in every a66 s03 run; its `initial`-arm lobby waste (R30: 37)
  did not recur in these arms.
- **s02: 12/24 against 10/24.** `a66` won s02vc `dynamic` twice and s02a/s02va `dynamic` once
  more each; `a49` won s02a `final` three times and s02vc `final` once more. s02c `dynamic` is
  0/6 between them. Each agent's wins at the divider are the coin flip and the crossing: `a66`'s
  four crossing-readout runs crossed through the true gap at steps 15–35 on "toward your target".
- **Walls in flight** (`eval/r28_flight.py`): `a49` missed 17.2%, phantom 11.6%, s03 phantom
  13.6% (R25D 17.3 / 12.7 / 16.2); `a66` missed 21.2%, phantom 11.2%, s03 phantom 15.0% (R30
  18.5 / 11.1). `a66`'s missed walls are 2.7 points over the 4-point window's centre and within
  it. Longest turn-around streak 5 in both.
- **Labels** (`labels.csv`, Claude review): `a49` 11 success, 15 replan_failure, 3 timeout
  (through the door, out of steps), 1 pre_change_failure (s03 `dynamic` seed 3 never reached a
  tine); `a66` 15 success, 15 replan_failure. No spin or goal-identification tags fired.

**Manipulation check.** Every `run.json` carries its round's agent and sha (`83f7a6a19b01`,
`de7f23d07186`) at git `6ebcaf2`; both rounds flown together 16:29–17:39 UTC on `:8004`, lanes
1–4 and 5–8 (`phase.json`); s03 `final` seed 2 has `final_closed: BranchR` in both rounds; walls
within the window. Held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, eight lanes on one vLLM
(`Qwen3-VL-30B-A3B`, remote profile, temperature 0), about 8 min per run under the shared load.
Flown at `6ebcaf2` on 2026-11-04 on the operator's instruction. **60/60 valid.** Labels: Claude
review, not yet confirmed by the operator. Frames stay on the host (`~/asep-r32-l1..4`,
`~/asep-r32p-l5..8`).

**Next, by the rule:** the final 90 on `a66`, branch `phase2/final` from this tip, order
`random.Random("phase2-F")`, seeds 1–5, all six sites and three arms.
