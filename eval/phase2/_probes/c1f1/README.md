# Probes C1 and F1: mirrored second read, and the perceiver without reason-first

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), sections C and F.
Script: `eval/probes/c1f1.py` (sample, run, score), plus `eval/probes/flip.py` (mirrors the frames).
Both probes share one frame sample and one run, so they share this README.

## Beliefs

- **C.** Temperature is 0, but changing the input still gives a second, independent read. Keeping
  only what the original and mirrored reads agree on should cut noise and cancel any left/right lean
  (self-consistency; egocentric left/right studies). A0 found a lean in the navigator's picks.
- **F.** Putting words before a visual judgement can hurt it ("Mind Your Step"), and strict JSON
  helps classification but hurts reasoning ("Let Me Speak Freely?"). g05 writes a `reason` first,
  under strict JSON. For a pure reader, that may be the worst of both.

## Method

- **Sample.** 300 clean frames from s02* and s03 runs, R22–R26N. Every frame needs a pose.
  - Frames are drawn by a fixed hash, up to 200 per (site, arm).
  - They are then stratified over cells of (site, arm, open door in view), taken in turn from each
    cell until there are 300.
  - "Open door in view" means at least one strip whose ground-truth ray crosses the door plane in
    the run's own world at that step (below).
- **Calls.** Each frame gets four calls, all on the same instance:
  - *orig*: a49's perceiver, g05 with its schema, a49's floor map, 768 max tokens;
  - *orig2*: the same call again, as a noise control;
  - *mirror*: the frame flipped left–right. On the answer, `far_left↔far_right` and `left↔right`
    are swapped back, along with the goal strip;
  - *nr* (F1): g05-nr. This is g05 with the closing "First say, for each strip … Then give the
    report." paragraph replaced by "Give the report.", and with `reason` removed from the schema.
    Classes and all other wording are unchanged.
- **Concurrency.** 1 per instance, one call at a time. N1 put the batching noise at 21.9% of strip
  fields under load, against about 2% alone.
  - Frames are split between `:8004`, used only when no flight is running, and a `:8006` copy on
    GPU 3. N1 passed that copy as a stand-in.
  - That is 4 GPUs in use: Coder-Next on 0–1, `:8004` on 2, the copy on 3. The copy is stopped
    afterwards.
  - Every call records its instance.
- **Truth.** For evaluation only; none of it is shown to the model. It uses geo, through
  `eval/probes/common.py` `world()` with each run's own switch step and s03 shut tine. Each strip is
  judged along its centre heading (`spatial.strip_offset`).
  - *Floor*: `r12_probe.true_reach`, put into a49's map classes. Under 1.0 m is `blocked_near`
    (`no_floor`), 1.0–3.0 m is `open_near` (`bottom`), and 3.0 m or more is `open_far` (`lower`,
    `middle`).
  - *Doorway*: open when one of five rays across the strip crosses the door plane. This is the
    `r20_door_probe.genuine` test, with the run's own world. A read is right when "open" matches
    that truth; `closed` and `none` both count as not open.
  - *Goal*: `r12_probe.in_view`, then `spatial.strip_for(bearing)`; otherwise `not_visible`.
- **Readouts.**
  - *Strip fields* are each strip's floor and doorway: 10 per frame.
  - *Agreement* between two reads is the share of strip fields with the same answer.
  - *Accuracy* is scored per field against the truth.
  - Lean is error on far_left + left minus error on right + far_right.

## Gate C1 (set before the first call)

| Result | Verdict |
|---|---|
| Strip fields where *orig* and *mirror* agree are ≥ 5 pts more accurate than *orig* alone, with agreement ≥ 80%; **or** the left-minus-right error gap is ≥ 10 pts on *orig* and ≤ 3 pts on agreed fields | **Holds** |
| *orig* vs *mirror* disagreement is no higher than *orig* vs *orig2* | **Refuted**: the mirror adds nothing a plain repeat would not |
| Anything else | No call |

**Control.** The accuracy of fields where *orig* and *orig2* agree is reported beside the mirror's.
That control shows how much of the gain only comes from dropping hard fields.

## Gate F1 (set before the first call)

The noise band is |accuracy(*orig*) − accuracy(*orig2*)|, per field type. A difference counts only
if it is at least 3 pts **and** at least 2× the band (N1's rule).

| Result | Verdict |
|---|---|
| *nr* beats *orig* on floor or doorway accuracy by a counting difference, and its goal-strip accuracy is no worse than −1 pt | **Holds**: drop reason-first from the perceiver |
| *nr* is worse than *orig* on floor or doorway accuracy by a counting difference | **Refuted**: reasoning helps our perceiver, so keep it |
| Anything else | No call |

## Result

Run 2026-10-29, `822c59b`.
- 150 frames ran on `:8004` (no flights running) and 150 on the `:8006` copy, both at concurrency 1.
- 1200 calls, none failed.
- The copy was stopped and removed afterwards.
- Output: [score.txt](score.txt); [sample.jsonl](sample.jsonl) has the frames and truth;
  `calls_0of2.jsonl` and `calls_1of2.jsonl` have the calls.

| Read | Floor | Doorway | Goal strip | Open-door recall | False open | Median latency |
|---|---|---|---|---|---|---|
| *orig* | 54.8% | 80.7% | 90.7% | 45.7% | 11.4% | 1.42 s |
| *orig2* | 55.9% | 81.0% | 90.3% | 47.1% | 11.4% | 1.36 s |
| *mirror* (swapped back) | 59.1% | 81.2% | 91.3% | 53.3% | 12.5% | 1.50 s |
| *nr* | 57.7% | 80.1% | 92.0% | 47.1% | 12.4% | 0.85 s |

Floor accuracy is low in absolute terms. The model reads true `open_far` strips as `open_near` 381
times out of 1138, so the 3 m truth cut is probably stricter than g05's `bottom` class. Every read
is scored against the same truth, so the comparisons stand.

### C1: no call

| Gate term | Value | Needed |
|---|---|---|
| Gain on fields where *orig* = *mirror* | **+13.2 pts** (81.0% vs 67.8%) | ≥ 5 |
| Agreement *orig* vs *mirror* | 67.7% | ≥ 80% (**fails**) |
| Lean on *orig*, all fields (error left − right) | +9.5 pts | ≥ 10 (**just fails**) |
| Lean on agreed fields | +3.5 pts | ≤ 3 |
| Disagreement *orig*–*mirror* vs *orig*–*orig2* | 32.3% vs 18.6% | not refuted |

- **Control.** Fields where *orig* = *orig2* are 73.3% accurate, +5.5 pts. Agreeing with the mirror
  picks out right answers more than twice as well as agreeing with a repeat. The mirror is a
  genuinely different read.
- **The lean is in the image, not the world.** Floor accuracy by strip:

  | Strip | far_left | left | centre | right | far_right |
  |---|---|---|---|---|---|
  | *orig* | 42% | 48% | 62% | 62% | 59% |
  | *mirror* | 62% | 67% | 66% | 53% | 47% |

  Mirroring moves the errors to the other world side, so the model reads the *left half of the
  image* worse. That is a reading bias, not a truth artefact. On floor alone the lean is +15.5 pts
  on *orig* and +1.3 pts on agreed fields, which would pass the lean term. The gate was set on all
  fields, though, and doorways carry little lean, so all fields come to +9.5.
- **Post hoc, not gated.** Take each strip from the read that saw it on the image's right half:
  *mirror* for far_left and left, *orig* for the rest. Floor accuracy is then 62.5%, **+7.7 pts**
  over *orig*, doorway 80.3% (−0.4), at the cost of one extra perceiver call per step. Taking the
  more conservative floor of the two reads is worse (40.7%).

**Reading.** Belief C partly holds. The mirror is a real second read, and it exposes a left-of-image
reading bias of about 15 pts on floor. Plain "keep what agrees" leaves a third of the fields with
no answer, though, so it is not usable as is. The lead for a round is the image-right fusion above
(two perceiver calls per step). It is post hoc, so it needs its own probe or round before it counts.

**Correction (C2, same day).** Truth is 78% `open_far`, so raw floor accuracy rewards reads that say
"far" more often. Both the +7.7 fusion gain and the floor lean above are mostly that. Balanced
accuracy moves only +1.7 pts, and wall errors barely change: missed walls 21.5% → 24.2%, phantom
walls 14.4% → 12.6%. See [C2](../c2/README.md), which drops g05 fusion and finds the wall-level
effect in g05-nr instead.

### F1: no call

| Gate term | *nr* − *orig* | Band (2× \|*orig* − *orig2*\|) | Counts |
|---|---|---|---|
| Floor | +2.9 pts | 2.2 pts | no: under 3 pts |
| Doorway | −0.6 pts | 0.6 pts | no |
| Goal strip | +1.3 pts | — | ≥ −1, fine |

**Reading.** Writing a `reason` first does not help g05: without it, floor is +2.9, doorway −0.6 and
goal +1.3. It does not clearly hurt either. *nr* changes 31% of strip fields against *orig*, about
the same as the mirror does, but accuracy is unchanged. What dropping the reason does buy is speed:
0.85 s against 1.42 s per call (−40%), with 375 output characters instead of 1002. Belief F is not
supported as an accuracy effect. g05-nr is a free latency cut.

### Noise: repeat reads disagree on 19% of fields even alone

At concurrency 1, *orig* vs *orig2* still differ on 18.6% of strip fields: 29% of floors and 8% of
doorways. This happens on both instances (82.4% and 80.3% agreement). N1's *alone* arm gave 2–3%,
so N1 was re-read.
- In both N1 frames, trial 0 is the odd one out, and trials 1–19 are identical.
- So the *alone* noise is most likely **first call (image not cached) vs later calls (prefix cache
  hit on the same image)**, not batching.
- Here *orig* is always the first call on a frame and *orig2* the cached repeat. The 18.6% is that
  cold-vs-warm gap, on frames from across the flights rather than two step-0 frames.

This is an inference, not a test. A flight's perceiver call is nearly always on a new image, so it
is cold. The practical point: a "repeat" read on vLLM is not independent noise. Disabling prefix
caching (`--no-enable-prefix-caching`) or a batch-invariant build would be the operator's call.
