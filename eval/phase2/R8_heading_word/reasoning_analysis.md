# R8 (a11) and R8N (a12) reasoning analysis: heading as a word, against a no-op edit

Written by Claude. Every decision in R8 (842), R8N (911) and R7 (858) went through scripts
(`eval/agent_evidence.py` and a cell-by-cell comparison of picks); what was read by eye is
listed in §6. R8 = `a11` (`p12`), R8N = `a12` (`p13`), R7 = `a10` (`p11`). All three flew on
sctsvr6 under lavapipe; R8 and R8N at one SHA (`4c67fc6`), R8N first.

## 0. Headline

**A sentence that says nothing changed the outcome of 6 of 18 cells. The heading word changed 4.
By the pre-registered rule, no success change is credited to the heading; the mechanism it
targeted did change.**
- Success: R7 6/18, R8N 6/18, R8 6/18. The arms moved, the totals did not.
- R8N against R7 flips 6 cells (3 gained, 3 lost). That is the noise floor of a one-sentence
  prompt edit on this setup, with a deterministic server.
- Heading arithmetic: R7 23, R8N 34, R8 **2** reasons. Degrees cited: 94%, 96%, **0.6%**.
- Turn-arounds with the goal in view: R7 3, R8N 2, R8 **0**. Every one of the five in R7 and R8N
  reads the heading in degrees ("facing 221 degrees, which is toward the left side of the
  scene"). R8 flies s02vc `initial` to the goal (19 steps); R7 and R8N turn around at step 12.
- The probe predicted every step-0 divergence exactly, for both agents (§2).

## 1. Every cell

✓ steps to goal, or ✗. "Step N" is the first step where the two rounds pick differently;
**flip** marks a changed outcome. The last column applies the attribution rule's second clause
to R8 against R7: at the first different pick, was the goal in view, and does the reason cite
the heading?

| cell | R7 | R8N | R8 | R8N vs R7 | R8 vs R7 | R8 vs R8N | R8 first diff: goal in view / cites heading |
|---|---|---|---|---|---|---|---|
| s01 initial | ✓ 35 | ✓ 14 | ✓ 14 | step 13 | step 13 | same | yes / yes |
| s01 final | ✗ | ✓ 39 | ✓ 42 | step 1 **flip** | step 4 **flip** | step 1 | no / yes |
| s01 dynamic | ✓ 33 | ✗ | ✗ | step 4 **flip** | step 4 **flip** | step 5 | no / yes |
| s02a initial | ✓ 14 | ✓ 14 | ✓ 14 | step 5 | step 11 | step 5 | yes / yes |
| s02a final | ✗ | ✗ | ✗ | step 1 | step 0 | step 0 | no / yes |
| s02a dynamic | ✗ | ✓ 51 | ✗ | step 5 **flip** | step 4 | step 4 **flip** | no / yes |
| s02c initial | ✓ 14 | ✓ 14 | ✓ 14 | step 5 | step 11 | step 5 | yes / yes |
| s02c final | ✗ | ✗ | ✗ | step 0 | step 0 | step 0 | no / yes |
| s02c dynamic | ✗ | ✗ | ✗ | step 10 | step 4 | step 4 | no / yes |
| s02va initial | ✓ 19 | ✗ | ✓ 19 | step 11 **flip** | step 11 | step 12 **flip** | yes / yes |
| s02va final | ✗ | ✗ | ✗ | step 0 | step 1 | step 0 | no / yes |
| s02va dynamic | ✗ | ✓ 59 | ✗ | step 4 **flip** | step 4 | step 5 **flip** | no / yes |
| s02vc initial | ✗ | ✗ | ✓ 19 | step 13 | step 12 **flip** | step 12 **flip** | yes / yes |
| s02vc final | ✗ | ✗ | ✗ | step 0 | step 0 | step 0 | no / yes |
| s02vc dynamic | ✓ 23 | ✗ | ✗ | step 5 **flip** | step 11 **flip** | step 5 | no / yes |
| s03 initial | ✗ | ✗ | ✗ | step 2 | step 0 | step 0 | no / yes |
| s03 final | ✗ | ✗ | ✗ | step 2 | step 0 | step 0 | no / yes |
| s03 dynamic | ✗ | ✗ | ✗ | step 1 | step 0 | step 0 | no / yes |

Flips: R8N vs R7 **6**, R8 vs R7 **4**, R8 vs R8N 4.

- **No cell is identical** between R8N and R7. Every cell diverges by step 13, 14 of 18 by
  step 5. Wording reaches every trajectory.
- s02a and s02c `initial` reach the goal in 14 steps in all three rounds; they diverge at step 5
  or 11, with the goal in view and close. The path differs, the outcome does not.
- **"Cites heading" is yes in every row.** R8's reasons use a compass word in 842 of 842
  decisions, so this clause of the rule separates nothing. Only the first clause (goal in view)
  and the count do.

## 2. The probe predicted the step-0 divergences

The server repeated `a10` exactly in the probe (80/80 spin picks, 18/18 step-0 picks), so a
step-0 pick on a recorded frame is the pick in flight.

| Agent | step-0 cells that differ from `a10`, probe | step-0 divergences from R7, flight |
|---|---|---|
| `a12` | s02c, s02va, s02vc `final` | s02c, s02va, s02vc `final` |
| `a11` | s02a, s02c, s02vc `final`; s03 `initial`, `final`, `dynamic` | the same six |

Both match cell for cell. A step-0 replay of the recorded frames is a free, exact preview of
where a prompt change will split from its base.

## 3. Attribution rule, applied

Pre-registered (R8 README): an R8 change counts toward the heading only if R8 changes more cells
than R8N, and the first different pick was made with the goal in view or a reason citing the
heading.
- **The count fails: 4 is not more than 6.** No outcome change is credited to the heading.
- For the record, R8's four flips against R7:
  - s01 `final` ✗ → ✓ (step 4, goal not in view). R8N also gains it. Noise.
  - s01 `dynamic` ✓ → ✗ (step 4). R8N also loses it. Noise.
  - s02vc `dynamic` ✓ → ✗ (step 11, goal not in view). R8N also loses it. Noise.
  - **s02vc `initial` ✗ → ✓ (step 12, goal in view, 12.0 m right).** This is the cell the change
    targets, the divergence is at the step the change targets, and R8N does not gain it. It is
    the only flip that meets the first clause. The count rule still says not credited; it is
    one cell.
- R8 against R8N also flips 4, including s02va `initial` (R8N turns around at step 12, R8 does
  not), the twin of s02vc.

## 4. The mechanism

| | R7 `a10` | R8N `a12` | R8 `a11` |
|---|---|---|---|
| decisions | 858 | 911 | 842 |
| reason cites degrees | 810 (94%) | 872 (96%) | **5 (0.6%)** |
| reason uses a compass word | 292 (34%) | 340 (37%) | **842 (100%)** |
| heading arithmetic | 23 | 34 | **2** |
| turn-around with the goal in view | 3 of 134 | 2 of 109 | **0 of 101** |
| blocked forward moves | 40 | 40 | 26 |
| same pick after a blocked move | 3 (8%) | 3 (8%) | 0 |
| claims progress after a blocked move | 8 (20%) | 11 (28%) | 5 (19%) |
| comparison line shown after one | 40 of 40 | 40 of 40 | 26 of 26 |
| two turn-arounds in a row | 10 | 5 | 9 |
| collisions | 60 | 55 | **41** |

- **The heading word did what it was built for.** The model stopped quoting and adding degrees.
  The five goal-in-view turn-arounds in R7 and R8N all begin "the drone is currently facing
  221 degrees, which is toward the left side of the scene" (or 259, 107): a map angle read as an
  image direction. R8 has no such sentence and no such turn-around.
- **R8N's numbers sit next to R7's** on every mechanism row: the no-op edit moved outcomes, not
  behaviour. Collisions 60 → 55, blocked moves 40 → 40.
- **Collisions fell to 41 and blocked moves to 26 in R8,** below R8N's spread. Not predicted
  (the prediction was "at most 80"), one round, one seed: noted, not claimed.
- **The compass word carries its own frame error, rarely.** Reasons that state "facing X, so
  right / left is Y": 7 in R8, read by eye; 2 are wrong (s02c `final` step 6, "facing west and
  the doorway is to the left (north)": it is south; s02va `final` step 2, "facing west … turning
  right (toward south-east)": it is north). The step-12 success itself says "facing south-west …
  'right' corresponds to roughly south-east" (it is north-west) and picks the right-hand marker
  anyway. The model follows the image marker over its own compass sentence. The probe's s02vc
  `dynamic` step-14 error ("facing west … must turn to face east") was not reached in flight: R8
  left R7's path there at step 11.

## 5. Failures

All 24 failures keep their auto label (12 per round). No `spin_failure` or
`failed_goal_identification` tag fires in either round.
- s03: 0/3 in both rounds, as in every round since R5. R8's s03 `final` and `dynamic` fly the
  same path (closest approach 26.8 m).
- R8N s02va and s02vc `initial` are one run twice (same picks): the step-12 turn-around, then
  33 m out.
- Timeouts: R8N s02vc `dynamic` (12.3 m) and `final` (came within 4.2 m, left, ended
  11.7 m: not within the 3.0 m close-range facet); R8 s02c `dynamic` (11.2 m) and s02vc
  `dynamic` (got through, ended 35 m out).
- `dynamic` is 0/6 in R8. Its two R7 successes are lost at step 4 and step 11 with the goal out
  of view, and R8N loses the same two: the noise floor, not the heading.

## 6. What was read by eye

- The five goal-in-view turn-around reasons (R7 ×3, R8N ×2) and R8 s02vc `initial` step 12.
- The 7 "facing X, so right / left is Y" sentences in R8 (regex-found, judged by eye; the regex
  mis-parsed 2 of them, both judged correct by eye).
- The first different pick of the four R8 vs R7 flips.
- Every failure's auto-label evidence (`auto_labels.json`): closest approach, final distance,
  min x, collisions, spin streak, goal-identification facets.
- The rest was counted by script, not read.

## 7. For R9

1. **Screen against the noise floor, not against the previous round.** A one-sentence no-op
   moves 6 of 18 outcomes. Any 18-run comparison needs a difference above that, or a mechanism
   metric, to say anything. The success counts of R1–R8 are all within it.
2. **Use the step-0 replay as a free pre-flight check.** It predicted every step-0 split exactly.
3. **Keep the heading word.** It removed the arithmetic and the goal-in-view turn-around at no
   cost to the blocked-move behaviour; that is a mechanism result, and the drop criterion is not
   met (1 of 4).
4. **More seeds, or more no-op variants, before the final round.** With a deterministic server,
   seeds (spawn jitter) and wording are the only sources of spread. A few no-op variants of the
   chosen agent would give the final round a distribution to compare against.
