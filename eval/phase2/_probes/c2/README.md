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

Run 2026-10-29, `73e901f`.
- 150 frames ran on `:8004` (no flights running) and 150 on the `:8006` copy, both at concurrency 1.
- 1500 calls, none failed.
- The copy was stopped and removed afterwards.
- Output: [score.txt](score.txt), [sample.jsonl](sample.jsonl), `calls_0of2.jsonl`,
  `calls_1of2.jsonl`.

| Read | Floor | Doorway | Goal | Floor by strip, far_left → far_right | Median latency |
|---|---|---|---|---|---|
| *orig* | 54.9% | 82.8% | 90.0% | 42 48 65 61 58 | 1.44 s |
| *orig2* | 52.9% | 82.1% | 91.7% | 40 47 63 59 55 | 1.34 s |
| *mirror* | 52.9% | 80.9% | 92.0% | 56 63 61 45 39 | 1.51 s |
| *nr* | 58.6% | 81.1% | 92.3% | 35 44 85 67 62 | 0.85 s |
| *nr_mirror* | 59.5% | 80.5% | 93.0% | 67 72 81 41 36 | 0.85 s |
| *fused* | 60.6% | 80.4% | 90.0% | 56 63 65 61 58 | 2 calls |
| *fused_nr* | 70.7% | 81.7% | 92.3% | 67 72 85 67 62 | 2 calls, about 1.7 s |

### Gate: no call

| Gate term | Value | Needed |
|---|---|---|
| *fused* floor − *orig* floor | +5.7 pts | ≥ 5 and ≥ 2× band (1.9): **passes** |
| *fused* doorway − *orig* doorway | −2.4 pts | ≥ −1: **fails** |

Decision rules, as the script printed them:
- *fused* beats *mirror* alone by 7.7 pts, which points to fusion.
- *fused_nr* beats *fused* by +10.1 on floor and +1.3 on doorway, which points to "fused_nr is enough".
- The left-minus-right floor error on *orig* is +14.3 pts, so the lean **replicates**.

### Correction: floor accuracy is the wrong yardstick

Truth is 78% `open_far` in both samples. Always answering `open_far` would score about 78% on floor,
better than every read here. Raw floor accuracy rewards reads that say "far" more often. The
*fused* gain mostly comes from that:
- *fused* says `open_far` on 55% of strips, against 47% for *orig*;
- balanced accuracy (the mean recall over the three classes) moves only +0.5 pts, 53.8% → 54.3%.

The same holds for C1's +7.7: there, balanced accuracy moved +1.7. The 1–3 m `open_near` class is
also barely read by any variant (recall 1–32%). The 3 m cut does not match what the model calls
`bottom`.

The robust question for flying is walls. "Missed wall" means the strip is truly blocked (< 1 m) but
is read as open. "Phantom wall" means the strip is truly open (≥ 1 m) but is read as `no_floor`.

| Read | Missed wall, C2 (n = 171) | Phantom wall, C2 (n = 1329) | Phantom, image-left strips / image-right strips | Missed wall, C1 (n = 186) | Phantom wall, C1 |
|---|---|---|---|---|---|
| *orig* (g05) | 17.0% | 14.6% | 17.4 / 15.4 | 21.5% | 14.4% |
| *orig2* | 13.5% | 15.3% | 18.2 / 17.1 | 17.7% | 15.2% |
| *fused* | 19.9% | 13.5% | — | 24.2% | 12.6% |
| *nr* (g05-nr) | **2.9%** | 27.2% | **41.8 / 22.8** | **4.3%** | 26.9% (39.5 / 23.4) |
| *nr_mirror* (sides as the model saw them) | 2.9% | 28.4% | **47.3 / 19.7** | — | — |
| ***fused_nr*** | **3.5%** | **18.4%** | 19.7 / 22.8 | — | — |

For *nr_mirror* the left/right column is by image side: the world-right strips sat on the image's
left.

**Reading:**
- **g05 fusion does nothing for walls.** Missed walls rise from 17.0% to 19.9%, and phantom walls
  fall from 14.6% to 13.5%. g05's "left-of-image lean" is a near-vs-far shift: it under-calls `far`
  on the image's left. It is not a wall error, and *fused* only moves answers toward `far`. Together
  with the doorway loss, **image-right fusion of g05 is dropped.**
- **g05-nr is the strong reader for walls.** It misses 2.9–4.3% of real walls, against 17–22% for
  g05. That replicates on both samples (C1 and C2).
- **g05-nr's cost is phantom walls on the image's left.** It reads 40–42% of open image-left strips
  as walls, on both samples. The mirrored *nr* read moves that error to the other side (47% on
  world-right strips), so it sits in the image, not the room.
- **fused_nr removes that cost:**
  - phantom walls drop from 27% to 18.4%, against 14.6% for *orig*;
  - missed walls stay at 3.5%;
  - doorway −1.1 and goal +2.3 against *orig*;
  - two g05-nr calls (about 1.7 s) against one g05 call (1.4 s).
- **Against today's perceiver,** *fused_nr* misses about **5× fewer real walls** (3.5% vs 17.0%), for
  +3.8 pts more phantom walls.
- **g05-nr never answers `bottom`** (`open_near` recall 1–2%). Its floor reads are effectively
  "wall or far".

**Status.** The gate's verdict is no call. The fused_nr wall result was read with a metric chosen
after the run, so it is a lead, not a gate pass. It is still the strongest perception lead of the
probes so far. Its parts replicate: *nr*'s missed-wall rate and its image-left phantom walls show
up in both C1 and C2. The next step would be a flight round with a perceiver of two g05-nr reads
(original and mirrored, image-right fusion), against a49. Whether 5× fewer missed walls turns into
solves is something only flights can show.
