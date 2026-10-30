# R27 Perceiver read twice, plain and mirrored (g07): summary

**12/18 against R25D's 14. The hypothesis did not hold, and `a60` is dropped.** R27 (`a60`)
against R25D (`a49`), the best round so far:
- `initial`: 5/6 (R25D 6/6). It lost s03.
- `final`: **4/6** (R25D 3/6). It won s02c and s02va and lost s02a.
- `dynamic`: 3/6 (R25D 5/6). It lost s02a and s02vc.

What changed:
- **The perceiver ran as built.** Both reads came back on 632/632 steps.
- **Missed walls fell as the probes said.** The fused reading missed **2.5%** of real walls in
  flight, against R25D's 17.3%.
- **Phantom walls rose far past the probe's figure.** The reading called **28.2%** of open strips
  walls, against R25D's 12.7%. The probe gate had measured 17.0%, and the check's limit was 20%. On
  s03 the rate was 60% (R25D 16%) ([walls.txt](walls.txt)).
- **All three s03 runs failed on those walls.** In `initial` and `dynamic` the drone faces open
  floor, reads `XXXXX`, turns around, and repeats, for 33 and 36 turn-arounds in a row
  ([labels.csv](labels.csv): `spin_failure;obstacle_hallucination`). `final` wandered the lobby
  and the crossbar, with phantom walls at 29%.
- **The three s02 failures are the old s02 failure, not this change.** The drone walks the door
  wall with many false door reports and the open door seldom in view. Phantom walls there ran
  12–25%, and none fell on a strip through the open door. R25D failed the same way in two other
  s02 cells (s02c and s02va `final`), and R27 won those two.

Why the probe gate passed: its frames came from the paths earlier agents flew. Probe AG
([../_probes/agree/README.md](../_probes/agree/README.md)) re-read R27's own 576 flight frames
at concurrency 1:
- On R27's own frames, `g07` calls 65% of open s03 strips walls, and `g05` calls 10%.
- The plain and mirrored reads mark the same phantom walls, so fusing them cannot remove them.
- The phantom walls come from dropping the describe-first paragraph, the same change that cut the
  missed walls.

**Not citable.** Agent `a60` (`464cf29e24ed`): navigator `p17` (`cb3578251cfe`), perceiver `g07`
(`b27efda96465`) read twice with image-right fusion, strategist `q03` (`1ec0f511a6e0`), door
confirmer `d01` (`95c80a5ef984`), memory `a17b`; `Qwen3-VL-30B-A3B`, remote profile,
temperature 0.
- Host: sctsvr6, lanes 1–4 (`~/asep-r27-l1..4`, `~/round_lane.sh`), nothing else running on
  `:8004`.
- Flown at `d6fd12a` on 2026-10-30, 02:13–02:36 UTC. **18/18 valid.**
- Labels: Claude review, not yet confirmed by the operator.
- Probe gate: passed ([README](README.md#probe-gate)).

What we learned across the probes and this round: [docs/research/what-we-learned.md](../../../docs/research/what-we-learned.md).
