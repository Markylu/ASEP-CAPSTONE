# R10C a13 control on the R10 host: summary

**R10C did not reproduce R9: 7/18 against R9's 6/18, 3 outcomes different, 7 of 18 cells pick
for pick.** It is the control R10 is read against, not a round of its own.
- `initial`: 5/6 (R9 5/6);
- `final`: 1/6 (R9 0/6);
- `dynamic`: 1/6 (R9 1/6).

**Not citable.** Agent `a13` (`3de550e110e7`): navigator `p14` (`31a9f28eaf94`), perceiver `g03`
(`3531e4d9ade9`), strategist `q01` (`40fb0fbc3285`), memory `eceb875a68a3`; `Qwen3-VL-30B-A3B`,
remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R9.
- Flown at `76f8a05` on 2026-10-25, 03:21–04:44 UTC, in tmux (`~/r10_fly.sh`), right after R10
  at the same SHA. **18 / 18 valid.**
- Labels reviewed by Claude and confirmed by the operator on 2026-10-25. One override:
  s02va `dynamic` `replan_failure` → `ignore_change` (labels.csv note).
- Pre-registration: [README.md](README.md).

## Predictions

| Arm | R9 `a13` | Predicted | R10C |
|---|---|---|---|
| initial | 5/6 | 5/6 | **5/6** held |
| final | 0/6 | 0/6 | **1/6** missed |
| dynamic | 1/6 | 1/6 | **1/6** held (a different cell) |

## Determinism

✓ steps to goal, or ✗ label. First pick that differs from R9 in brackets.

| Site | initial R9 → R10C | final R9 → R10C | dynamic R9 → R10C |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 [–] | ✗ replan, spin → ✗ replan, spin [–] | ✗ replan → **✓ 48** [7] |
| s02a | ✓ 14 → ✓ 49 [13] | ✗ timeout → **✓ 58** [6] | ✗ replan → ✗ replan [–] |
| s02c | ✓ 56 → ✓ 32 [18] | ✗ timeout → ✗ replan [2] | ✗ replan → ✗ replan [7] |
| s02va | ✓ 19 → ✓ 19 [–] | ✗ replan, spin → ✗ replan, spin [–] | ✓ 29 → **✗ ignore** [5] |
| s02vc | ✓ 19 → ✓ 19 [–] | ✗ replan → ✗ replan [31] | ✗ replan, spin → ✗ replan, spin [–] |
| s03 | ✗ replan → ✗ replan, spin [1] | ✗ replan → ✗ replan [1] | ✗ replan, spin → ✗ replan [5] |

- **7 of 18 cells** have the same pick sequence as R9 from step 0 to the end; **15 of 18**
  outcomes are the same. Three cells part at step 1 or 2 (s03 `initial`, s03 `final`, s02c
  `final`).
- Collisions 57 (R9 34). `spin_failure` on 4 runs (R9 4), one on a different cell (s03
  `initial` in place of s03 `dynamic`).
- s01 `dynamic` reached the goal in 48 steps, as R9's unscored shakedown run did (48 steps), and
  unlike R9's round run.

`a13`'s code and wording did not change (sha `3de550e110e7`, every R9 decision re-renders
byte-identically at `76f8a05`; R10 README), so these differences are run-to-run variation. `a11`
repeated R8 in 16 of 18 cells and every outcome (R9C); `a13` makes two to four model calls a step,
and one different perceiver or strategist answer changes the map and every pick after it. The
cause was not traced further.

**What this means for reading R10:** R8N's noise floor (6 of 18 outcomes) was measured on a
single-call agent. For `a13`, two runs of the unchanged agent moved 3 of 18 outcomes; a
measured floor for `a14` would need a re-fly of `a14` itself.

## Against R10

R10 (`a14`) changes 6 of these 18 outcomes: it gains s02a `dynamic`, s02c `final`, s02va
`dynamic`, s02vc `dynamic` and s03 `final`, and loses s01 `dynamic`. See
[R10 summary](../R10_goal_planner/summary.md).
