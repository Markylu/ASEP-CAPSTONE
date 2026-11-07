# F2: Final design: a102 on the full design, lavapipe

**Agent:** `a102` (`e405aeb4a004`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Planner:** `planner.pathfind` (`PATHFINDER_A102`: survey stations held
10 steps in transit, a94's dead-end latch) · **Goal check:** 26° · **Status:** flown 2026-11-07 at `00e8b2b`, 90/90 valid, **76/90** ([summary](summary.md))

Written before flying. Spec: `docs/phase2-test-plan.md` §6 and P1 §5–§7. **Citable. Phase 2's closing round:** the operator froze `a102` as the Phase 2 agent after the flight (2026-11-07, "Freeze a102"); the tip is tagged `phase2-complete`. Flown on
the operator's instruction (2026-11-07, after the night's screen): "fly it on lavapipe, but use
the final format, so the same test we used for phase 1".

## Change

None to the agent. `a102` is the night's best agent (R66 23/30, R70 21/30 on H100 frames,
contested cells), frozen. What changes against every flight it has had is the design and the
renderer: the full Phase 1 design (six sites × three arms × seeds 1–5 = 90 runs, one SHA) and
Godot under lavapipe, as Phase 1 and Round F were flown, instead of H100 frames. Order
`random.Random("phase2-F2")`; validity P1 §10, rubric P1 §9 with Phase 2's tags; Phase 2's lock
plus the agent fields. s03 `final`: the shut exit is tine L on odd seeds, tine R on even.

## Evidence

- Phase 1 (`a00`, `p02`): 25/90, `initial` 25/30, `final` 0/30, `dynamic` 0/30
  (`eval/phase1/results/results.md`).
- Round F (`a66`, lavapipe, eight lanes on `:8004`): 64/90, `initial` 30/30, `final` 17/30,
  `dynamic` 17/30; s01 15/15, s02a 9/15, s02c 8/15, s02va 13/15, s02vc 10/15, s03 9/15
  ([final/README.md](../final/README.md), [final/summary.md](../final/summary.md)).
- `a102` on the contested cells, H100 frames: 44/60 over two flights, s02 38/48, s03 6/12;
  s02c `dynamic`, s02va both arms and s02vc `final` 6/6 each, s02vc `dynamic` 2/6, s03 `final`
  4/6, s03 `dynamic` 2/6 ([R66](../R66_wait_latch/summary.md), [R70](../R70_ref_a102/summary.md)).
- Its parent `a93` on the same cells: H100 20, 21, 16 of 30 (R58, R61, R64); lavapipe 24/30
  ([R53](../R53_goal_check/summary.md)). Lavapipe frames have run three to five runs per 30
  above H100 frames for the same agent (R55's note), so the H100 rates below are a floor.
- `a102` has never flown s01 or an `initial` arm: every round since R32 flew the ten contested
  cells only. The eight settled cells were solved in 14 of 14 screening rounds up to R32 under
  the `a17`–`a66` line; `a102` adds the wall survey (a83–a100), the latch (a94) and the goal
  check (a93) to that line, none of which has been seen on s01 or an `initial` arm in flight.

## Hypothesis

`a102` beats Round F's 64/90 by at least ten runs, with the gain on the s02 change arms, and
holds the eight settled cells.

## Predictions

From `a102`'s H100 cell rates on the contested cells (44/60), Round F for the settled cells,
and three to five runs per 30 for lavapipe over H100 on the contested cells:

| Arm | Phase 1 (`a00`) | Round F (`a66`) | Predicted `a102` | Where it comes from |
|---|---|---|---|---|
| initial | 25/30 | 30/30 | 28–30 | settled; s03 `initial` the one cell not solved every round |
| final | 0/30 | 17/30 | 24–28 | s01 5; s02 ×4 at 83% H100 → 16–19 of 20; s03 `final` 3–4 of 5 |
| dynamic | 0/30 | 17/30 | 20–25 | s01 5; s02 ×4 at 75% H100 → 14–18 of 20; s03 `dynamic` 1–2 of 5 |
| total | 25/90 | 64/90 | **72–83** | |

Per layout (15 runs each): s01 15; s02a 11–13; s02c 11–13; s02va 14–15; s02vc 12–14; s03 8–10.
The weakest cell stays s03 `dynamic` (a102 2/6 on H100; its losses are the latch missing or
firing late, the 60-step budget after a correct latch, and a lobby stall before the switch).

## Manipulation check

- Every `run.json` carries `agent_version` a102, `agent_sha` `e405aeb4a004`, one `git_sha`.
- Every `godot.log` names the lavapipe device ("Using Device" lines, counted per lane by
  `round_lane.sh`); none names an H100.
- s03 `final` seeds 2 and 4: `final_closed` BranchR; seeds 1, 3, 5: BranchL.
- Survey and latch records present: `survey` stations in the planner record on s02 change arms,
  `dead_end_latch` set within nine steps of a closed read on the s03 runs that reach a shut door
  (`eval/probes/a94_latch_check.py` on the recorded runs).

## Drop criterion

None: the round is the measurement. If `a102` lands below Round F's 64, `a66` stays the better
measured agent on this design and the night's carry is not confirmed.

## Probe gate

Not needed: no change to the agent.

## Builds on

R70 (`a102`, the night's last reference flight). Branch `phase2/f2-a102-lavapipe` from
`phase2/r68-latch-inflate-20` (`95a3733`); PR against it, never merged. Round F's data
(`eval/phase2/final/`) is untouched; `python eval/phase2.py results` now prints one §11 section
per final-design round, so F and F2 are never pooled.

## Notes for the operator

- **Host.** 90 runs, eight lanes on `:8004`, lavapipe, as Round F: `sh ~/round_lane.sh k 8
  ~/asep-r68-lk a102 e405aeb4a004 F2 final_a102`, k = 1..8, no `LITELLM_BASE_URL`, no `GODOT_VK`.
  Round F took 74 min for 90 runs on this layout.
- **Preflight.** Clean tree at the flight SHA in every lane, every lane's `/health` reports
  `e405aeb4a004`, no vLLM copies running (GPUs 3–7 empty), tunnel the operator's.
- **After.** Validity on all 90; `python eval/phase1_label.py --round F2`; labels; `summary.md`;
  `python eval/phase2.py results`; `phase.json` complete; tag `p2-f2`.

## Outcome

**76/90: `initial` 30/30, `final` 23/30, `dynamic` 23/30** (Round F 64/90, 30/17/17; Phase 1 25/90,
25/0/0). Predicted 72–83, landed 76; `final` one under its 24–28, `dynamic` inside 20–25. The
hypothesis held: twelve over Round F (p = 0.048), the gain on the change arms (s02 out of view
15/20 against 7/20; s03 `dynamic` 4/5 against 0/5, the cell's first wins in Phase 2), the eight
settled cells 40/40. At least 50% on every layout: s01 15, s02a 13, s02c 12, s02va 12, s02vc 11,
s03 13 of 15. Lavapipe gave no lift over the H100 flights (19/30 on the thirty cells they share,
against 23 and 21). Manipulation check held: one SHA on 90 runs, llvmpipe on all 90, s03
`final_closed` L/R/L/R/L, latch within seven steps of every shut-door read in a tine. Flown
16:01–17:04 UTC on eight lanes. Labels Claude review, operator to confirm.
Details: [summary.md](summary.md); tables and contrasts: [results](../results/results.md).

**Frozen.** Operator, 2026-11-07, after reading this round beside the night's screen (R56–R70):
"Freeze a102". `a102` (`e405aeb4a004`, prompt `p17` `cb3578251cfe`) is the Phase 2 agent; this
round is Phase 2's citable result; the tip of `phase2/f2-a102-lavapipe` is tagged `phase2-complete`.
Round F stays a citable 90-run measurement of `a66`. Labels remain Claude review until the operator
confirms them. Not changed: the decider's default agent (`DEFAULT_AGENT = "a00"`, Phase 1's), served
agents are chosen with `--agent`.
