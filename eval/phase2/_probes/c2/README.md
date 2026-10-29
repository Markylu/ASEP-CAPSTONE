# Probe C2: does image-right fusion of two reads beat one read?

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), section C. Script:
`eval/probes/c2.py`, which reuses `eval/probes/c1f1.py` (truth, sampling, calls) and
`eval/probes/flip.py`. It follows from [C1](../c1f1/README.md).

## Belief

C1 found that g05 reads the **left half of the image** worse. Floor accuracy by strip was 42/48/62/
62/59%, and a mirrored read flipped the pattern. So each strip should be taken from whichever read
saw it on the image's right half:
- the mirrored read for `far_left` and `left`;
- the original read for `centre`, `right` and `far_right`.

That should lift floor accuracy without hurting doorways. In C1 the rule gave +7.7 pts on floor,
but it was found after looking at C1's data. C2 tests it on fresh frames.

## Method

- **Sample.** 300 fresh clean frames, drawn with C1's rules: s02* and s03, R22–R26N, stratified by
  (site, arm, open door in view). The hash is salted `c2:`, and every frame key in C1's sample is
  excluded.
- **Reads.** Five per frame, all on the same instance, one call at a time:
  - *orig*: g05;
  - *orig2*: g05 again (noise band);
  - *mirror*: g05 on the flipped frame, swapped back;
  - *nr*: g05-nr (F1's variant: no `reason`, no describe-first paragraph);
  - *nr_mirror*: g05-nr on the flipped frame, swapped back.
- **Fusions, built in code from the reads.**
  - *fused* takes `far_left` and `left` from *mirror* and the other strips from *orig*.
  - *fused_nr* does the same with *nr_mirror* and *nr*.
  - The goal strip and range come from the unmirrored read.
- **Instances.** `:8004` (no flights running) and a `:8006` copy on GPU 3, the same as C1. That is
  4 GPUs in use; the copy is stopped afterwards.
- **Truth and scoring.** Identical to C1: geo with each run's own world, floor put into a49's
  classes (< 1.0 m, 1.0–3.0 m, ≥ 3.0 m), doorway open or not, goal via `in_view`.
- **Band.** |floor accuracy(*orig*) − floor accuracy(*orig2*)|.

## Gate (set before the first call)

| Result | Verdict |
|---|---|
| *fused* floor − *orig* floor ≥ +5 pts and ≥ 2× band, and *fused* doorway − *orig* doorway ≥ −1 pt | **Holds** |
| *fused* floor − *orig* floor < +2 pts | **Refuted**: C1's +7.7 did not replicate |
| Anything else | No call |

**Decision rules, set before the run:**
- **Mirror alone.** If *mirror* alone comes within 2 pts of *fused* on floor, a round should use one
  mirrored read, not two reads.
- **Cheap version.** If *fused_nr* comes within 2 pts of *fused* on floor and 1 pt on doorway, the
  round should use *fused_nr*: two no-reason calls (about 1.7 s) against one g05 call (1.4 s).
- **Lean replication.** The left-minus-right floor error on *orig* is reported. A lean under 5 pts
  means the bias did not replicate, whatever the gate says.

## Result

Not yet run.
