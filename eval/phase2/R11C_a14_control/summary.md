# R11C a14 control on the R11 host: summary

**R11C came close to reproducing R10: 11/18 against R10's 11/18, 2 outcomes different, 11 of 18
cells pick for pick.** It is the control R11 is read against, not a round of its own.
- `initial`: 5/6 (R10 5/6);
- `final`: 4/6 (R10 3/6);
- `dynamic`: 2/6 (R10 3/6).

**Not citable.** Agent `a14` (`63ad006476b6`, on every record): navigator `p14` (`31a9f28eaf94`),
perceiver `g03` (`3531e4d9ade9`), strategist `q02` (`f3a866c9d927`), memory `eceb875a68a3` + a14
wording `0075a8a0e5c0`; `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R10.
- Flown at `caa209a` on 2026-10-27, 18:43–19:46 UTC, in tmux (`~/r11_fly.sh`, checkout
  `~/asep-r11`), right after R11 at the same SHA. **18 / 18 valid.** Mean step 3.1 s (R10 3.1 s).
- Labels reviewed by Claude and confirmed by the operator on 2026-10-28. No overrides.
- Pre-registration: [README.md](README.md).

## Predictions

| Arm | R10 `a14` | Predicted | R11C |
|---|---|---|---|
| initial | 5/6 | 5/6 | **5/6** held |
| final | 3/6 | 3/6 | **4/6** missed |
| dynamic | 3/6 | 3/6 | **2/6** missed |

## Determinism

✓ steps to goal, or ✗ label. First pick that differs from R10 in brackets.

| Site | initial R10 → R11C | final R10 → R11C | dynamic R10 → R11C |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 [–] | ✗ replan → **✓ 16** [3] | ✗ timeout → ✗ timeout [–] |
| s02a | ✓ 14 → ✓ 19 [13] | ✓ 32 → ✓ 32 [–] | ✓ 50 → **✗ replan** [7] |
| s02c | ✓ 19 → ✓ 14 [13] | ✓ 47 → ✓ 47 [–] | ✗ replan → ✗ replan [23] |
| s02va | ✓ 19 → ✓ 19 [–] | ✗ replan → ✗ replan [18] | ✓ 48 → ✓ 48 [–] |
| s02vc | ✓ 19 → ✓ 19 [–] | ✗ replan → ✗ replan [–] | ✓ 38 → ✓ 38 [–] |
| s03 | ✗ replan → ✗ replan [–] | ✓ 35 → ✓ 35 [–] | ✗ pre-change → ✗ pre-change [7] |

- **11 of 18 cells** have the same pick sequence as R10 from step 0 to the end; **16 of 18**
  outcomes are the same. The earliest parting is at step 3 (s01 `final`); the others part at step
  7 or later.
- Collisions 24 (R10 36). `spin_failure` on no run (R10 none).
- s03 `dynamic` is `pre_change_failure` in both rounds: the drone never entered a tine, so the
  switch never fired.

`a14`'s code and wording did not change (sha `63ad006476b6`; every R10 decision re-renders
byte-identically at `caa209a`, R11 README), so these differences are run-to-run variation, as in
R10C.

**What this means for reading R11:** `a14`'s measured floor is 2 of 18 outcomes and 7 of 18
sequences that part, lower than `a13`'s (R10C against R9: 3 of 18 outcomes, 11 sequences that
part). With the floor taken as max(6, 2) = 6, R8N's floor still sets the bar for R11.

## Against R11

R11 (`a16`) changes 6 of these 18 outcomes: it gains s01 `dynamic`, s02va `final` and s03
`initial`, and loses s02c `final`, s02va `dynamic` and s02vc `dynamic`. See
[R11 summary](../R11_goal_default/summary.md).
