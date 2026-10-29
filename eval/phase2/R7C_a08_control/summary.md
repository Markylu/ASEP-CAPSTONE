# R7C a08 control on the R7 host: summary

**The host (or noise) moved `a08`'s result by as much as the R7 change did.** R7C flew `a08` (R6's
agent), unchanged, on sctsvr6 under lavapipe. It has 8/18 successes against R6's 5/18 on the Mac:
- `initial`: 5/6 (R6 3/6);
- `final`: 3/6 (R6 2/6);
- `dynamic`: 0/6 (R6 0/6).

`final` + `dynamic` is 3/12 (R6 2/12). Collisions: 100 (R6 143). Reasons that claim progress after
a blocked move: 62% (R6 68%).

This is a control, not a round of its own. Read it two ways:
- **R7 against R7C** is the prompt change alone. See [the R7 summary](../R7_comparison_lines/summary.md).
- **R7C against R6** is the host (Metal against lavapipe) plus noise. One seed and 18 runs cannot
  split them. A 3-run gain on the same agent says a 2-run difference between rounds is within
  what this setup produces.

**Not citable.** Agent `a08` (`e8c66be05bd3`), prompts `p09` (`7642a3e1056d`) and `g02`
(`bf175c973dfb`), `Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `468d5ef` on
2026-10-22 in tmux on sctsvr6 (58 minutes). **18 / 18 valid**, with every captured frame
768 × 768 (checked by validation). Labels were reviewed by Claude and confirmed by the operator
on 2026-10-22. No tags.

Pre-registration: [README.md](README.md). Manipulation check:
[manipulation_check.md](manipulation_check.md) (no comparison lines, as expected).

## Result

| Arm | R6 (Mac) | R7C (server) |
|---|---|---|
| initial | 3/6 | **5/6** |
| final | 2/6 | **3/6** |
| dynamic | 0/6 | **0/6** |

- Of the 10 failures, 8 are `replan_failure` and 2 are `timeout` (s02c and s02va `dynamic`).
- The `initial` gain is s02va and s02vc: R6's goal-in-view turn-around at step 12 did not happen
  here (R7C had no goal-in-view turn-arounds; R6 had 3, R7 had 3).
- Collisions by site (R6 / R7C): s01 22 / 14; s02a 8 / 6; s02c 14 / 5; s02va 20 / 17;
  s02vc 31 / 10; s03 48 / 48.

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial | final | dynamic |
|---|---|---|---|
| s01 | ✓ 56 | ✗ replan | ✗ replan |
| s02a | ✓ 14 | ✓ 41 | ✗ replan |
| s02c | ✓ 14 | ✓ 45 | ✗ timeout |
| s02va | ✓ 19 | ✗ replan | ✗ timeout |
| s02vc | ✓ 19 | ✓ 59 | ✗ replan |
| s03 | ✗ replan | ✗ replan | ✗ replan |

## Predictions

| Arm | Predicted | Result |
|---|---|---|
| initial | 2–4/6 | **5/6, above** |
| final | 1–3/6 | 3/6 |
| dynamic | 0–1/6 | 0/6 |

The `initial` prediction missed by one run: the host, or noise.
