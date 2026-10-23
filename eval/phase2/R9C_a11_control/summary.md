# R9C a11 control on the R9 host: summary

**R9C reproduced R8: 6/18, every outcome the same, 16 of 18 cells pick for pick.** It is the
control R9 is read against, not a round of its own.
- `initial`: 5/6 (R8 5/6);
- `final`: 1/6 (R8 1/6);
- `dynamic`: 0/6 (R8 0/6).

**Not citable.** Agent `a11` (`3859d0345560`), prompts `p12` (`f24e2855bfbe`) and `g02`
(`bf175c973dfb`), `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R8.
- Flown at `756345b` on 2026-10-23, 17:36–18:35 UTC, in tmux, right after R9 at the same SHA.
  **18 / 18 valid.**
- Labels reviewed by Claude on 2026-10-23; **operator confirmation pending**.
- Pre-registration: [README.md](README.md).

## Predictions

| Arm | R8 `a11` | Predicted | R9C |
|---|---|---|---|
| initial | 5/6 | 5/6 | **5/6** held |
| final | 1/6 | 1/6 | **1/6** held |
| dynamic | 0/6 | 0/6 | **0/6** held |

## Determinism

- **16 of 18 cells** have the same pick sequence as R8 from step 0 to the end.
- The two that differ are both s03: `initial` from step 2 and `dynamic` from step 0. Both end
  with R8's label (`replan_failure`, `pre_change_failure`).
- Collisions 42 (R8 41).

So `a11`'s behaviour did not change between `4c67fc6` and `756345b`, and R9 against R9C reads the
bundle alone. The cause of the two s03 splits was not traced; the s03 `dynamic` one is at step 0,
before any memory exists, so it is run-to-run variation, not a code change.

## Against R9

R9 (`a13`) changes 2 of these 18 outcomes: it gains s02va `dynamic` and loses s01 `final`. See
[R9 summary](../R9_hail_mary/summary.md).
