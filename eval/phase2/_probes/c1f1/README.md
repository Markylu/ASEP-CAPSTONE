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

Not yet run.
