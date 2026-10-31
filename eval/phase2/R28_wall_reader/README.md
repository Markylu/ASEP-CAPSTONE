# R28: R25D with each strip's floor from a wall reader (w01)

**Agent:** `a61` (`c4cf3f29bc27`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` +
wall reader `w01` · **Memory:** `a17b` · **Status:** pre-registered 2026-10-30, probe gate failed,
not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Comes from
[what-we-learned.md](../../../docs/research/what-we-learned.md), idea 1: separate the perceiver's
tasks into different agents, the wall reader first.

## Change

One change against `a49` (R25D, 14/18, the best round so far): each strip's floor comes from a
second model call with one job.

- **`w01`** (`prompt.W01`, `schema.wall_reader_schema`) is `g05`'s floor job alone: the same five
  strips, the same floor ends (`no_floor`, `bottom`, `lower`, `middle`) and wording, and the
  describe-first ending. The goal and the doorway questions are taken out. Its reply is `reason`
  and one `floor` per strip.
- **Two calls per step, at the same time** (`orchestrator.perceive_walls`): `g05` as in `a49`, and
  `w01`, both on the clean frame.
- **Merge** (`orchestrator.with_walls`): each strip's `floor` and `floor_end` from `w01`, through
  `a49`'s floor map. The doorways and the goal stay `g05`'s.
  - If `w01` fails, `g05`'s floors stand. If `g05` fails, there is no reading, as for `a49`.
- The door confirmer `d01`, the map, the planner, the strategist `q03` and the navigator `p17` are
  unchanged. `d01` checks `g05`'s doorway reports as before.
- The record keeps both reads: `perceiver.result` is the merged reading, `perceiver.result_own` is
  `g05`'s read, and `wall_reader.result` is `w01`'s.

## Evidence

The probes show the perceiver's three jobs want different prompts, and that a prompt sets the
missed-wall / phantom-wall trade-off for all of them at once
([what-we-learned.md](../../../docs/research/what-we-learned.md), "Ideas", table):

| Task | `g05` (describe-first) | `g07` (no describe-first) | Better |
|---|---|---|---|
| Phantom walls, R27's flight frames (AG) | 9.4% | 35.3% | `g05` |
| Missed walls, same frames | 16.5% | 2.5% | `g07` |
| Doorway, C2 / R27 gate / AG | 82.8 / 83.7 / 89.9% | 81.1 / 81.7 / 86.7% | `g05` |
| Goal strip, same three | 90.0 / 92.3 / 93.8% | 92.3 / 93.7 / 95.1% | `g07` |

- R27 ([README](../R27_mirrored_nr_perceiver/README.md)) and probe AG
  ([README](../_probes/agree/README.md)): the phantom walls come with dropping describe-first, so
  `w01` keeps it.
- Unneeded context costs accuracy (GSM-IC, ICML 2023), and format effects differ by task ("Let Me
  Speak Freely?", EMNLP 2024). A single-task prompt carries only its task's question
  ([spatial-memory-and-prompting.md](../../../docs/research/spatial-memory-and-prompting.md)).
- **Not yet known:** whether taking the goal and doorway out moves `g05`'s floor errors at all.
  That is what the probe gate measures. If `w01` reads walls like `g05`, R28 does not fly.

## Probe gate

Set before the probe runs. The probe is `eval/probes/w01.py`, committed before any call.

- **Frames, three recorded sets.** Only `w01` is called; `g05`'s reads are the ones already
  recorded on the same frames at concurrency 1.
  - **F:** R27's 576 s02*/s03 flight frames, the hard s03 views (probe AG, `g05` read).
  - **P:** R27's 300-frame probe sample (`R27…/probe`, `g05` read).
  - **C2:** C2's 300-frame sample (`_probes/c2`, read `orig`). Reported, not gated.
- **Reads:** one `w01` call at a time per instance: shard 0 on `:8004` with no flights running,
  shard 1 on a `:8006` copy on GPU 3, stopped afterwards.
- **Scored** as the merged reading `a61` would build (`orchestrator.with_walls` on the recorded
  `g05` read), truth as C1 (`c1f1.truth`).
- Dry run with `w01` set to `g05`'s own floors reproduces the recorded `g05` rows: F 16.5% missed /
  9.4% phantom / 9.7% s03 phantom; P 16.5% / 11.7%; C2 17.0% / 14.6%.

The gate passes only if all five hold (`w01` merged against `g05`, same frames):

| | Set | Check | `g05` |
|---|---|---|---|
| 1 | F | Missed walls ≤ half of `g05`'s | 16.5% |
| 2 | F | Phantom walls ≤ `g05` + 2 pts | 9.4% |
| 3 | F | s03 phantom walls ≤ `g05` + 4 pts | 9.7% |
| 4 | P | Missed walls ≤ half of `g05`'s | 16.5% |
| 5 | P | Phantom walls ≤ `g05` + 2 pts | 11.7% |

Doorway and goal are `g05`'s by construction, so they are not gated.

If it fails, R28 does not fly, the Outcome records the probe, and the next wall reader is a new
version (for example a narrower per-strip question), not an edit of `w01`. Output:
`_probes/w01/score.txt`.

**Result: failed** (2026-10-30), 3 of 5. Write-up: [_probes/w01](../_probes/w01/README.md).

| | Gate | Value | |
|---|---|---|---|
| 1 | F missed ≤ half of `g05`'s | 16.5% vs 16.5% | FAIL |
| 2 | F phantom ≤ `g05` + 2 pts | +0.2 pts | pass |
| 3 | F s03 phantom ≤ `g05` + 4 pts | +0.7 pts | pass |
| 4 | P missed ≤ half of `g05`'s | 19.6% vs 16.5% | FAIL |
| 5 | P phantom ≤ `g05` + 2 pts | −3.4 pts | pass |

## Probe gate, second attempt

Set 2026-10-30 after W01 failed, before any call. The round stays R28 (operator: "stay in this
round"). The probe is `eval/probes/r28_walls.py`, committed before any call.

**What W01 showed** (recorded reads, F/P/C2): about 84% of truly blocked strips are read
`no_floor`. Of the rest, 9–13 points are `bottom` and 5–8 are `lower`/`middle`. `bottom` can't be
remapped to a wall, because 31–50% of truly open strips are also read `bottom`. In two
missed-wall frames, one is an oblique dark wall at 0.8 m, dark on a dark floor. In the other, all
five strips are read `bottom` while a pillar fills the right strip: the bright floor elsewhere
carries over. Truth is one ray down the strip's centre. The camera can't see floor closer than
1.84 m.

**Candidates.** Each is merged with `g05`'s recorded read the way an agent would, and a failed
call leaves `g05`'s reading.
- **`k01`, wall confirmer** (`prompt.K01`, `schema.wall_confirmer_schema`,
  `orchestrator.walls_checked` / `with_walls_added`). A second look at the strips `g05` read
  `bottom`, `lower` or `middle`, as `d01` does for doorways. It asks: wall or floor at the middle
  of the strip's bottom edge? `wall` makes the strip `no_floor`.
- **`w02`, strip crops** (`prompt.W02`, `strips.crops`, a list of images in `vlm`). The five
  strips as five images in one call, each with the floor question. Floors replace `g05`'s, as
  `w01`.
- **`w03`, marked frame** (`prompt.W03`, `strips.marked`). The frame with the four strip
  boundaries drawn in yellow, and the floor question. Floors replace `g05`'s.
- **`w04`, code floor detector** (no model; `strips.bottom_features`). A logistic rule on the
  bottom twelfth of each strip: brightness, spread, edges, slanted edges, orange, and `g05`'s
  floor end. It adds a wall to a strip `g05` read open.
  - Fitted on C1's 300 frames only (`fit`), with C1's recorded `g05` reads.
  - The threshold keeps the walls it adds on truly open C1 strips at ≤ 1.5% of C1's open strips.
  - F, P and C2 are never used to fit.

**Frames and calls.** Sets F, P (gated) and C2 (reported), as W01. 3 model calls per frame,
1176 frames. Four shards, one call at a time each: `:8004` with no flights running, and three
copies on GPUs 3–5 (`:8006`–`:8008`), stopped afterwards.

**Gate.** The same five checks as W01, for each candidate against `g05` on the same frames:
- F and P missed walls ≤ half of `g05`'s;
- F and P phantom walls ≤ `g05` + 2 pts;
- F s03 phantom walls ≤ `g05` + 4 pts.

**Winner.** Among the candidates that pass all five, the one with the lowest F + P missed walls.
It gets an agent (`a62` on), its own smoke, and then the on-policy check below. If none passes,
R28 does not fly.

Dry run (stub replies equal to `g05`, k01 all `floor`, random w04 features): k01, w02 and w03
reproduce `g05`'s rows exactly. w04 adds +1.4 to +1.5 pts of phantom walls, its fitted cap, and
catches nothing.

**Result (2026-10-31): all four fail; no winner.** Write-up: [_probes/r28_walls](../_probes/r28_walls/README.md).

| Read | F missed | F phantom | F s03 phantom | P missed | P phantom | Checks passed |
|---|---|---|---|---|---|---|
| `g05` | 16.5% | 9.4% | 9.7% | 16.5% | 11.7% | |
| `k01` | 9.8% | 25.8% | 27.6% | 12.7% | 26.9% | 0 of 5 |
| `w02` | 23.1% | 22.0% | 34.2% | 29.7% | 21.6% | 0 of 5 |
| `w03` | 40.2% | 10.4% | 7.3% | 43.7% | 10.0% | 3 of 5 |
| `w04` | 12.3% | 10.7% | 10.8% | 13.3% | 12.8% | 3 of 5 |

## On-policy check

Only if the probe gate passes. A gate on recorded frames is an open-loop test of a closed-loop
change (R27). Before the 18 runs:
1. In a scratch clone (`~/r28_shake`, at the round's sha), fly one unscored `dynamic` run per site,
   s03 first: `phase2.py run --round R28 --only <site>/dynamic/1`. These runs never enter this
   folder.
2. Score them with `eval/r28_flight.py`.
3. Pass only if: merged missed walls ≤ 8%, phantom walls ≤ 15%, s03 phantom walls ≤ 20%, both reads
   on ≥ 95% of steps, and no turn-around streak of 10 or more.

If it fails, R28 does not fly; the Outcome records the check.

Baselines from `eval/r28_flight.py` on the flown rounds:

| Round | Missed | Phantom | s03 phantom | Longest turn-around streak |
|---|---|---|---|---|
| R25D (`a49`) | 17.3% | 12.7% | 16.2% | 3 |
| R27 (`a60`) | 2.5% | 28.2% | 59.8% | 36 |

## Hypothesis

A wall reader with one job misses at most half as many real walls as `g05` without adding phantom
walls, so the map stops opening floor that is not there, and R28 scores at least as well as R25D.

## Predictions

| Arm | Baseline (R25D, `a49`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 3 | 3 or 4 |
| dynamic | 5 | 4 or 5 |

Total ≥ 14/18.

**Noise.** R25D's 14 was partly luck: by
[why_14.md](../R25D_door_confirmer_open_near_unwalled/why_14.md), the `a17b` family expects
11.3 ± 1.4. Every flown round also carries batching noise: N1 found 16–28% of strip fields change
with 7 neighbours in the batch, and `a61` adds one more call per step to `:8004`'s batch. A single
18-run round cannot separate ±1 from noise.

## Manipulation check

In flight, on the s02 and s03 steps, scored by `eval/r28_flight.py` against geo:
- the merged reading misses ≤ 8% of real walls (R25D 17.3%);
- its phantom walls stay ≤ 15% (R25D 12.7%), and ≤ 20% on s03 (R25D 16.2%);
- both reads come back on ≥ 95% of steps.

## Drop criterion

Not carried forward if the total is below R25D's 14/18. At exactly 14, the manipulation check and
the moves into blocked headings decide whether it stands as the new base.

## Builds on

R25D (`a49`).

## Notes for the operator

- **Branch.** `phase2/r28-wall-reader`, branched from `research/probes` (`p2-r27`). Never merge.
- **Smoke (no model):** `VLM_AGENT=a61 python eval/probes/a61_smoke.py`. On R25D's 627 recorded
  steps with stub replies: 0 failed steps, 627 wall-reader calls, merged = recorded on 627/627
  (local run with stand-in frames; rerun on sctsvr6 for the real frames).
- **Preflight.** `python -m server.decider --profile remote --agent a61`; `/health` should report
  `c4cf3f29bc27`.
- **GPUs.** At most 4 Qwen instances including `:8004`; stop the `:8006` copy after the probe.

## Outcome

**Not flown: the probe gate failed.** `w01` misses real walls at `g05`'s rate (F 16.5% vs 16.5%,
P 19.6% vs 16.5%, C2 17.5% vs 17.0%), so taking the goal and doorway out of the question does not
change the wall reading. The missed walls come with describe-first wording itself: only dropping it
(`g07`) cut them, and that brought R27's phantom walls. 2.6% of `w01` calls also failed (reason past
the token limit). Probe write-up: [_probes/w01](../_probes/w01/README.md).

**Second gate failed too: none of `k01`, `w02`, `w03`, `w04` passes**, so R28 is not flown.
- `k01` (ask again about strips read open) cuts missed walls to 9.8% but adds 16 pts of phantom
  walls, the `g07` pattern.
- Crops (`w02`) make both errors worse.
- Drawn boundaries (`w03`) miss 40% of walls.
- The code detector `w04` is the only reader that trades well: missed 16.5 → 12.3% (F) and 13.3%
  (P) at +1.1 to +1.2 pts phantom. That is a quarter, not half. On its fit set C1, halving the
  missed walls would cost +3 pts of phantom walls, so no threshold passes.

The best agent is still `a49` (R25D, 14/18). Probe write-up:
[_probes/r28_walls](../_probes/r28_walls/README.md).
