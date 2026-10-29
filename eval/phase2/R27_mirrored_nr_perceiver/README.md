# R27: R25D with the perceiver read twice, plain and mirrored (g07)

**Agent:** `a60` (`464cf29e24ed`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g07` ×2 ·
**Memory:** `a17b` · **Status:** pre-registered 2026-10-29, probe gate passed, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Comes from the research probes
([docs/research/probe-plan.md](../../../docs/research/probe-plan.md)): F1, C1 and C2.

## Change

One change against `a49` (R25D, 14/18, the best round so far): the perceiver.

- **`g07`** is `g05` with its closing "First say, for each strip … Then give the report." replaced by
  "Give the report.", and with no `reason` in the schema (`prompt.G07`, `schema.perceiver_schema`).
  Classes, wording and the floor map are otherwise the same.
- **Two reads per step, at the same time.**
  - One read is of the clean frame.
  - The other is of the clean frame mirrored left–right. Code does the mirroring
    (`server/decider/mirror.py`, stdlib only, pixel-identical to Pillow's flip, 0.3 s on sctsvr6),
    and the answer's strips are swapped back (`orchestrator.unmirrored`).
- **Fusion** (`orchestrator.image_right`): each strip comes from the read that saw it on the
  image's right half.
  - `far_left` and `left` come from the mirrored read.
  - `centre`, `right`, `far_right` and the goal come from the plain read.
  - If one read fails, the other stands alone.
- The door confirmer `d01`, the map, the planner, the strategist `q03` and the navigator `p17` are
  unchanged. `d01` checks the fused doorway reports on the clean frame.
- The record keeps both reads: `perceiver.result` is the fused reading, `perceiver.result_own` is
  the plain read, and `perceiver_mirror.result_unmirrored` is the mirrored read.

## Evidence

All from 600 recorded clean frames (s02* and s03, R22–R26N), scored against geo with each run's own
world. One call at a time on a quiet instance.
- Probes: [C1/F1](../_probes/c1f1/README.md) and [C2](../_probes/c2/README.md).
- "Missed wall": a strip truly blocked within 1 m but read as open.
- "Phantom wall": a strip truly open (≥ 1 m) but read as `no_floor`.

| Read | Missed wall, C2 | Phantom wall, C2 | Missed wall, C1 | Doorway, C2 | Goal strip, C2 |
|---|---|---|---|---|---|
| `g05` (a49) | 17.0% | 14.6% | 21.5% | 82.8% | 90.0% |
| `g07` | 2.9% | 27.2% | 4.3% | 81.1% | 92.3% |
| **`g07` ×2, image-right** | **3.5%** | **18.4%** | — | 81.7% | 92.3% |

- **a49 in flight shows the same rates.** R25D's 545 s02/s03 steps give missed walls 17.3%
  (63/364) and phantom walls 12.7% (301/2361).
- **The plain `g07` read has an image-side phantom-wall bias.** It reads 40–42% of open strips on the
  image's left half as walls, against 23% on the right half; the same holds on both samples. The
  mirrored read puts that error on the other world side, so fusing the two cuts it.
- **Calibration.** Floor truth is 78% `open_far`, so raw floor accuracy is not used here (C2's
  correction).
- **What is lost: `bottom`.** `g07` almost never answers it (`open_near` recall 1–2%), so with this
  agent `a17b`'s open_near path (no wall written at the end of an `open_near` strip, a49's change
  over a37) will rarely fire.
- **Latency.** The two `g07` calls take about 0.85 s each alone and run concurrently with the flip,
  against 1.42 s for one `g05` call. Each step adds one more request to the shared `:8004` batch.
- **Caveat.** The wall metric was chosen after C2 had run, which is why the probe gate below
  re-tests it on fresh frames before flying.

## Probe gate

Set before the probe runs. The probe is `eval/r27_probe.py` (to write, on the pattern of
`eval/probes/c2.py`).
- **Frames.** 300 fresh clean frames, drawn with the C1/C2 rules (s02* and s03, R22–R26N,
  stratified by site, arm and open door in view). The hash is salted `r27:`, and every frame in C1's
  and C2's samples is excluded.
- **Reads, per frame on one instance, one call at a time:**
  - `g05` (a49's read);
  - `g07` on the frame;
  - `g07` on the frame mirrored by `server/decider/mirror.py`.
- **Fusion** by `orchestrator.unmirrored` and `orchestrator.image_right`, the flight code.
- **Truth** as in C1 (`eval/probes/c1f1.truth`).

The gate passes only if all four hold, comparing the fused `g07` reading against `g05` on the same
frames:

| | Gate | C2 value |
|---|---|---|
| 1 | Missed walls ≤ half of `g05`'s | 3.5% vs 17.0% |
| 2 | Phantom walls no more than 6 pts above `g05`'s | +3.8 |
| 3 | Goal strip accuracy no more than 1 pt below `g05`'s | +2.3 |
| 4 | Doorway accuracy no more than 2 pts below `g05`'s | −1.1 |

If it fails, R27 does not fly, the Outcome records the probe, and the next idea is a new version.
Commit `probe/` before flying.

Smoke (no model): `eval/probes/a60_smoke.py`, run on sctsvr6, the real step on R25D's 627
recorded manifests and real clean frames with stub replies. The results were:
- 0 failed steps;
- 627 mirrored reads;
- the fused reading equals the recorded one on 627/627 steps (the stub answers the mirrored frame
  with the recorded reading mirrored);
- 0.31 s per step.

## Hypothesis

With about 5× fewer missed walls, the map stops opening floor that is not there. Fewer moves are
spent on blocked headings, and R27 scores at least as well as R25D.

## Predictions

| Arm | Baseline (R25D, `a49`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 3 | 3 or 4 |
| dynamic | 5 | 4 or 5 |

Total ≥ 14/18.

**Noise.** R25D's 14 was partly luck: by `why_14.md`, the `a17b` family expects 11.3 ± 1.4. Every
flown round also carries batching noise: N1 found 16–28% of strip fields change with 7 neighbours in
the batch. A single 18-run round cannot separate ±1 from noise.

## Manipulation check

In flight, on the s02 and s03 steps, scored as above against geo:
- the fused reading misses ≤ 8% of real walls (R25D 17.3%);
- its phantom walls stay ≤ 20% (R25D 12.7%);
- both reads come back on ≥ 95% of steps.

## Drop criterion

Not carried forward if the total is below R25D's 14/18. At exactly 14, the manipulation check and
the moves into blocked headings decide whether it stands as the new base.

## Builds on

R25D (`a49`).

## Notes for the operator

- **Branch.** The agent, the round and the probes are on `research/probes`, which is branched from
  `phase2/r13-verify`. Fly from that branch or merge it first.
- **Preflight.** `python -m server.decider --profile remote --agent a60`; `/health` should report
  `464cf29e24ed`.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to
[summary.md](summary.md).
