# R8N No-op prompt edit: summary

**The hypothesis held: a sentence that says nothing changed the outcome of 6 of 18 cells
against R7.** Net success is unchanged, 6/18:
- `initial`: 3/6 (R7 4/6);
- `final`: 1/6 (R7 0/6);
- `dynamic`: 2/6 (R7 2/6).

Three cells gained (s01 `final`, s02a and s02va `dynamic`) and three lost (s01 and s02vc
`dynamic`, s02va `initial`). s01 `final` had failed in every round from R0 to R7C.

This is the noise floor for one-sentence prompt edits on this setup:
- **The server is deterministic** (probe: `a10` repeated 80/80 spin picks and its 18 recorded
  step-0 picks). The spread is wording, not sampling.
- **No cell flies the same path** as R7. 14 of 18 diverge by step 5.
- **The probe predicted the step-0 divergences exactly**: s02c, s02va and s02vc `final`, and no
  other cell.
- **Behaviour did not move**, only outcomes: blocked forward moves 40 (R7 40), same pick after
  one 8% (R7 8%), comparison line shown 40 of 40, collisions 55 (R7 60), heading arithmetic 34
  (R7 23), goal-in-view turn-arounds 2 (R7 3).
- Every success difference between R1 and R8 is within this floor.

**Control, never carried forward. Not citable.** Agent `a12` (`6d65de968c98`), prompts `p13`
(`5aca3d233965`) and `g02` (`bf175c973dfb`), `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
Flown at `4c67fc6` on sctsvr6 (headless, lavapipe, Docker) in tmux, before R8 (64 minutes).
**18 / 18 valid.** Labels reviewed by Claude and confirmed by the operator on 2026-10-23. No tags.

Pre-registration: [README.md](README.md). Manipulation check:
[manipulation_check.md](manipulation_check.md). Cell-by-cell comparison:
[R8 reasoning analysis](../R8_heading_word/reasoning_analysis.md) §1.

## Predictions

| Prediction | Result |
|---|---|
| initial 3–5/6 | held: 3/6 |
| final 0–2/6 | held: 1/6 |
| dynamic 1–3/6 | held: 2/6 |
| 3–6 of 18 cells change outcome | held: 6 |
| most first diverging at step 0–4 | partly: 3 of the 6 flips (steps 1, 4, 4); the others at 5, 5, 11 |
| blocked-move metrics near R7's | held |
| step-0 divergences exactly s02c, s02va, s02vc `final` | held |
