# R7 Comparison lines in the log: summary

**The mechanism worked; success did not move, and it cannot be credited to the change. `a10` is
not dropped (0 of 4 drop conditions met).** R7 has 6/18 successes:
- `initial`: 4/6 (R6 3/6, R7C 5/6);
- `final`: 0/6 (R6 2/6, R7C 3/6);
- `dynamic`: 2/6 (R6 0/6, R7C 0/6).

`final` + `dynamic` is 2/12 (R6 2/12, R7C 3/12).

The comparison lines did what they were built for:
- After a blocked move `a10` repeats the same pick 8% of the time (R7C 33%, R6 42%) and cites
  the line in 39 of 40 reasons.
- Reasons that claim progress after a blocked move: 20% (R7C 62%, R6 68%).
- Blocked moves: 40 (R7C 91, R6 123). Collisions: **60** (R7C 100, R6 143).
- Blocking at an already-blocked spot: 3 (R7C 21, R6 41).
- No spin came back: two turn-arounds in a row is 1% of pairs.

But the extra success cannot be read as an effect of the lines:
- **Five of the six cells that changed outcome diverge from R7C at step 0 or step 4**, before a
  blocked move exists and before any line is shown. The extra system-prompt paragraph or
  run-to-run noise changed those picks. This data cannot say which.
- Net: `a10` gained `dynamic` s01 and s02vc, and lost `final` s02a, s02c, s02vc and `initial`
  s02vc.
- The remaining failures are the ones the lines do not touch: a goal-in-view turn-around (three
  in R7, none in R7C), corner traps on s03 (0/3 on every round), and overshoot at close range.

**Not citable, and flown on a different host.** R7 flew agent `a10` (`b5b7bcd218cc`), with
prompts `p11` (`55414df4bc89`) and `g02` (`bf175c973dfb`), on `Qwen3-VL-30B-A3B`, remote
profile, temperature 0.
- **Host:** sctsvr6 (headless Linux, Xvfb, Mesa lavapipe CPU Vulkan, Docker), not the Mac that
  flew R1–R6. Frames are not the Mac's pixels, so the host is a config change. The final round
  is flown on the Mac.
- **Control:** R7C is `a08` flown on the same host, so R7 against R7C isolates the prompt
  change. R7C scored 8/18 against R6's 5/18 on the Mac: the host or noise moves the total as
  much as this change does.
- Flown at `468d5ef` (both rounds) on 2026-10-22 (sctsvr6 clock), in tmux on sctsvr6. R7 took 59
  minutes, R7C 58.
- **18 / 18 valid** in both rounds (the captured frame size was checked against 768 × 768).
- Probe: `a09` (the lines on `a07`) failed its gate by one frame and did not fly. `a10` passed
  (spin 5/40, `lost` 3/25, `offcentre` 1/11). [probe/probe_r7.md](probe/probe_r7.md).
- Labels were reviewed by Claude and confirmed by the operator on 2026-10-22.
- Pre-registration: [README.md](README.md). Reasoning analysis:
  [reasoning_analysis.md](reasoning_analysis.md). Manipulation check:
  [manipulation_check.md](manipulation_check.md).

## Result

| Arm | R0 | R1 | R5 | R6 (Mac) | R7C `a08` (server) | R7 `a10` (server) |
|---|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | 6/6 | 3/6 | 5/6 | **4/6** |
| final | 0/6 | 2/6 | 2/6 | 2/6 | 3/6 | **0/6** |
| dynamic | 0/6 | 1/6 | 0/6 | 0/6 | 0/6 | **2/6** |

- Of the 12 failures, 9 are `replan_failure`, 2 are `timeout` (s02vc `final`, s02c `dynamic`)
  and 1 is `pre_change_failure` (s03 `dynamic`).
- **Tag:** s02vc `final` takes `failed_goal_identification` (close-range facet): the drone was
  1.4 m from the goal, passed it, and flew away. No `spin_failure`.
- Collisions by site (R6 / R7C / R7): s01 22 / 14 / 8; s02a 8 / 6 / 11; s02c 14 / 5 / 8;
  s02va 20 / 17 / 9; s02vc 31 / 10 / 7; s03 48 / 48 / 17.

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial R6 → R7C → R7 | final R6 → R7C → R7 | dynamic R6 → R7C → R7 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 56 → ✓ 35 | ✗ replan → ✗ replan → ✗ replan | ✗ replan → ✗ replan → **✓ 33** |
| s02a | ✓ 14 → ✓ 14 → ✓ 14 | ✓ 18 → ✓ 41 → ✗ replan | ✗ replan → ✗ replan → ✗ replan |
| s02c | ✓ 14 → ✓ 14 → ✓ 14 | ✗ replan → ✓ 45 → ✗ replan | ✗ replan → ✗ timeout → ✗ timeout |
| s02va | ✗ replan → ✓ 19 → ✓ 19 | ✗ replan → ✗ replan → ✗ replan | ✗ timeout → ✗ timeout → ✗ replan |
| s02vc | ✗ replan → ✓ 19 → ✗ replan | ✓ 54 → ✓ 59 → ✗ timeout | ✗ replan → ✗ replan → **✓ 23** |
| s03 | ✗ replan → ✗ replan → ✗ replan | ✗ replan → ✗ replan → ✗ replan | ✗ pre-change → ✗ replan → ✗ pre-change |

**Fewer independent observations than cells:**
- s02a and s02c `initial` fly the same 14 picks in R7C and R7, and s01, s02a and s02c `initial`
  fly the same 14 in R6.
- R7 and R7C start the same for 4 steps or more in 10 of 18 cells, and are identical to the end
  in 2.
- With one seed, a 2-run difference between two rounds is not a result (§3 of the test plan).

## Pre-registered predictions

| Prediction | Result |
|---|---|
| initial 3–5/6 | held: 4/6 |
| final 2–3/6 | **missed: 0/6** |
| dynamic 1/6 or more | held: 2/6 |
| collisions well below 143, near R5's 38 or lower | partly: 60, below 143, not near 38 |
| reasons claiming progress after a blocked move < 30% | held: 20% |
| s03 not pinned at x = 15.2 for more than 5 steps | **missed:** s03 `initial` and `final` end at min x 15.2 |
| two turn-arounds in a row on `dynamic` < 20% | held: 1% |
| `final` + `dynamic` at least 3/12 | **missed:** 2/12 |
| lost goals not expected to improve | held: 2 runs (R7C 4, R6 3), not attributable |

## Drop criterion

`a10` is dropped if two or more of these hold. None does.

| Condition | R7 |
|---|---|
| `final` + `dynamic` below 2/12 | no: 2/12 |
| collisions not at least a third below R6's 143 | no: 60 |
| reasons after a blocked move that claim progress above 50% | no: 20% |
| `initial` not above 3/6 | no: 4/6 |

**Carried forward, with the caveat that the success counts say nothing about the change.** The
mechanism result (the lines worked) is the finding.

## What the model did

See [reasoning_analysis.md](reasoning_analysis.md). In short:
- **It reads the line and acts on it,** with one answer: turn around (65% of the time after a
  block, R7C 24%). That stops repeated blocking and may be too strong for corner traps.
- **It still turns away from a goal it can see** at a doorway where the goal swings from left to
  right (s02vc `initial`, step 12, 12 m; also s01 and s02c `dynamic`).
- **It overshoots at close range:** s02vc `final`, 1.4 m, then 7 steps away.
- **The step-0 pick is fragile.** One added paragraph moved 5 of 18 first picks.

## For the next round

1. **Measure the noise floor first.** Run a no-op prompt edit (one extra sentence) through the
   same 18 cells. Without it, any next result has the step-0 problem seen here.
2. **Heading:** try heading as a word ("facing west"), tested on the 11 `offcentre` probe frames
   first.
3. **More seeds.** One seed cannot tell a 2-run difference from noise.
4. **Host:** fly the next round on one host, and fly its control there too.
