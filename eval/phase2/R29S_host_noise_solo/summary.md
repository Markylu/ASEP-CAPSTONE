# R29S a49, one lane per vLLM instance: summary

**14/18 (R29N 11, R25D 14). Gate check 1 failed: alone, the perceiver misses as many walls as it
does shared.** The same `a49`, each lane on its own vLLM instance so no call shared a batch:
- `initial`: 6/6.
- `final`: 4/6 (R29N 3, R25D 3). **s03 `final` solved at step 59**, the first time on the `a49`
  line; lost s02c and s02vc.
- `dynamic`: 4/6 (R29N 2, R25D 5). Lost s02va and s03.

## The gate

| | Check | R25D | R29N | R29S | |
|---|---|---|---|---|---|
| 1 | R29S missed walls ≤ 10% | 17.3% | 15.4% | **14.9%** | **FAIL** |
| 2 | R29S phantom walls ≤ 15% | 12.7% | 12.0% | 9.3% | pass |
| 3 | R29S s03 phantom walls ≤ 20% | 16.2% | 14.1% | 8.3% | pass |
| 4 | R29S success ≥ R29N | 14 | 11 | 14 | pass |
| 5 | R29N missed walls within 17.3 ± 4 | 17.3% | 15.4% | | pass |

`eval/r28_flight.py` on both `runs/` folders; longest turn-around streak 3 in both.

**What failed, and why it matters.** Probe LD's replay found two thirds of `g05`'s flight-time
missed walls when the same frames were read alone; in flight, alone, they are still there (14.9%
against 15.4% shared). The replay read each frame after its own first read, with the system prompt
and the image in the prefix cache; a flight frame is always new. So the LD gain was a warm-cache
effect, not a batching effect, and **the host is not the lever for missed walls.** The missed
walls that remain are the describe-first reading itself, which R27 and R28 already showed.

**What did move.** Phantom walls fell 12.0 → 9.3% and on s03 14.1 → 8.3%, with the same prompt
and the same kind of frames. One seed per cell, so this is a lead, not a result; it is in the
direction N1 predicted (a reading that is not jostled by its batch neighbours says *wall* on open
floor less often). The success difference, 14 against 11, is inside one round's noise (why_14:
11.3 ± 1.4 for the family), and this round's own s03 `final` win is a side choice (below).

**Determinism, seen in flight.**
- s02vc `final` ran the same 60 steps in R29N and R29S, pose for pose. When every perceiver call
  returns the same reading, the agent and the simulator reproduce the run exactly. All the
  round-to-round spread is in the model's answers.
- Every other cell split where one perceiver reading differed: at step 1 (s03 `dynamic`), 3, 5–11
  (most s02 cells), 14, 18. The step-0 reading alone differs from R29N's in 11 of 18 cells. Alone
  on an instance is not enough: the flight's calls are cold, and a cold call at temperature 0 is
  still a draw on this server.
- s03 `final`: R29S and R25D are pose-identical for 33 steps, to the crossbar. At step 34 R29S
  turned into tine R (open) and reached the goal at 59; R25D turned into tine L (shut) and spent
  the rest of its run there. Same agent, same map, one reading apart. The s03 `final` cell is a
  coin at the crossbar, which is what the tines analysis said a `q03` rule should decide instead.

## Cells

| site | arm | R25D | R29N | R29S |
|---|---|---|---|---|
| s01 | initial | ✓ 14 | ✓ 14 | ✓ 14 |
| s01 | final | ✓ 29 | ✓ 26 | ✓ 23 |
| s01 | dynamic | ✓ 39 | ✓ 23 | ✓ 26 |
| s02a | initial | ✓ 14 | ✓ 14 | ✓ 14 |
| s02a | final | ✓ 26 | ✗ 14.8 m | ✓ 49 |
| s02a | dynamic | ✓ 23 | ✗ 12.8 m | ✓ 23 |
| s02c | initial | ✓ 14 | ✓ 14 | ✓ 14 |
| s02c | final | ✗ 11.1 m | ✓ 58 | ✗ 16.6 m |
| s02c | dynamic | ✓ 27 | ✗ 1.4 m | ✓ 26 |
| s02va | initial | ✓ 19 | ✓ 19 | ✓ 19 |
| s02va | final | ✗ 16.1 m | ✓ 34 | ✓ 28 |
| s02va | dynamic | ✓ 34 | ✓ 51 | ✗ 17.1 m |
| s02vc | initial | ✓ 19 | ✓ 19 | ✓ 19 |
| s02vc | final | ✓ 43 | ✗ 19.1 m | ✗ 19.1 m |
| s02vc | dynamic | ✓ 36 | ✗ 12.8 m | ✓ 49 |
| s03 | initial | ✓ 50 | ✓ 39 | ✓ 25 |
| s03 | final | ✗ 9.2 m | ✗ 10.1 m | **✓ 59** |
| s03 | dynamic | ✗ 8.9 m | ✗ 7.3 m | ✗ 7.3 m |

Three a49 rounds now: 14, 11, 14, mean 13.0. Every s02 `final`/`dynamic` failure in all three is the
door-wall pattern (never across the divider, the open door seldom in view); every s03 failure is
the shut tine.

## What carries

- `a49` stays the base. Its rate is about 13 ± 1.7 over three rounds, not 14.
- The host layout does **not** change for missed walls (check 1). Flying alone is 35% faster per
  call (perceiver p50 1.21 s against 1.65 s) and cuts phantom walls; whether later rounds fly alone
  is the operator's call on GPU budget, and a round that does must say so in `phase.json`.
- Next lever is the s03 crossbar/dead end on the `q03` line (plan §3): the reading at step 33 of
  s03 `final` decides the cell; a rule should.

**Not citable.** Agent `a49` (`83f7a6a19b01`), prompt `p17`, perceiver `g05`, strategist `q03`,
door confirmer `d01`, memory `a17b`; `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6, lanes 1–4 (`~/asep-r29s-l1..4`), lane k on `:8004`, `:8006`, `:8007`, `:8008`
  (copies of `:8004`: same image `vllm/vllm-openai:v0.23.0`, weights and flags, one GPU each on
  GPUs 3–5), `LITELLM_BASE_URL` per lane, nothing else on any of the four. Copies stopped after.
- Flown at `822f1d7` on 2026-11-02, 16:34–16:55 UTC, 21 min. **18/18 valid**, 0 of 628 perceiver
  calls failed.
- Labels: Claude review, not yet confirmed by the operator.
