# R8N: No-op prompt edit (noise floor)

**Agent:** `a12` (`6d65de968c98`) · **Prompt:** `p13` (`5aca3d233965`) · **Identifier prompt:**
`g02` (`bf175c973dfb`) · **Status:** pre-registered, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. A control, flown beside
[R8](../R8_heading_word/README.md) on the same host at the same SHA. Its hypothesis is about the
measurement, not the drone.

## Change

`a12` is `a10` (the agent R7 flew) plus one sentence at the end of the system prompt's
comparison paragraph:

> The log lists your steps in the order they happened, oldest first.

It is true and adds nothing the log does not already show (each line starts with its step
number, in order). The user prompt `p13` renders is byte-identical to `p11`'s on every recorded R7
decision, and the system prompts differ by that one line.

## Evidence

- One added paragraph moved 5 of 18 first picks in R7: every `final` cell except s03 diverged
  from R7C at step 0, with an empty log and identical positions
  ([R7 reasoning analysis](../R7_comparison_lines/reasoning_analysis.md) §3).
- Five of the six cells whose outcome changed between R7C and R7 diverge at step 0 or step 4,
  before any comparison line exists. R7 could not say whether wording or noise did it.
- On the server, temperature-0 replays of identical inputs differ in 2 of 80 picks
  ([R7 README](../R7_comparison_lines/README.md), Probe gate). Sensitivity to wording has not
  been measured.

## Hypothesis

A prompt edit with no content changes some cells' outcomes against R7. The number of cells that
change is the floor a one-paragraph change has to beat before it is credited.

## Predictions

| Arm | R7 | Predicted R8N |
|---|---|---|
| initial | 4/6 | 3–5/6 |
| final | 0/6 | 0–2/6 |
| dynamic | 2/6 | 1–3/6 |

- 3–6 of 18 cells change outcome against R7, most first diverging at step 0–4.
- Blocked-move metrics stay near R7's: same pick after a blocked move at most 15% (R7 8%),
  progress claimed after one below 30% (R7 20%), comparison line shown after every one.
- The probe's step-0 set predicts the step-0 divergences: cells where `a12`'s step-0 pick differs
  from `a10`'s on the recorded frame are the ones that diverge at step 0 in flight, allowing for
  the server's 2-in-80 noise.

**Probe, before flight** ([R8 probe](../R8_heading_word/probe/probe_r8.md)): the server repeated
`a10` exactly (80/80 spin picks, 18/18 step-0 picks), so there is no sampling noise to allow
for. `a12`'s step-0 pick differs from `a10`'s in **s02c, s02va and s02vc `final`**. Those three
cells are predicted to diverge from R7 at step 0 in flight, and no other cell is. On spin frames
`a12` agrees with `a10` on 45 of 80 picks.

## Manipulation check

- `/health` reports prompt sha `5aca3d233965` before flight; the sentence is in every decision's
  system prompt.
- Comparison line shown after a blocked move: 100%, as in R7.

## Drop criterion

None: `a12` is a control and is never carried forward.

## Probe gate

Not gated. `a12` runs through R8's probe sets and is reported beside `a10` and `a11`, so the
step-0 set gives the noise floor offline before flight.

## Builds on

R7 and agent `a10`. Same branch as R8 (`phase2/r8-heading-word`), cut from `4d82a10`.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
