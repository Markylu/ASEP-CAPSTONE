# R29: the host, not the agent. a49 on a shared vLLM (R29N) and alone (R29S)

**Agent:** `a49` (`83f7a6a19b01`) in both rounds · **Prompt:** `p17` (`cb3578251cfe`) ·
**Perceiver:** `g05` · **Memory:** `a17b` · **Status:** pre-registered 2026-11-02, flown the same day, 18/18 valid in each round

Written before flying. Spec: `docs/phase2-test-plan.md`. This README covers both R29N (this
folder) and R29S ([R29S_host_noise_solo](../R29S_host_noise_solo/README.md)); they fly the same
agent and differ only in how the vLLM is shared.

## Change

**None to the agent.** `a49` is R25D's agent (14/18, the best Phase 2 score), unchanged, same sha.
What changes is the host:

| Round | Lanes | vLLM | What a perceiver call shares its batch with |
|---|---|---|---|
| R29N | 4 (`asep-r29n-l1..4`) | one, `:8004` | the other three lanes' calls, as in every flown round |
| R29S | 4 (`asep-r29s-l1..4`) | one per lane: `:8004`, `:8006`, `:8007`, `:8008` | nothing: every call is alone on its instance |

R29S's extra instances are copies of `:8004` (same image `vllm/vllm-openai:v0.23.0`, same weights
`Qwen3-VL-30B-A3B-Instruct-FP8`, same flags), one GPU each on GPUs 3–5, as probes N1, R28 and LD
ran them. Four instances in all, the limit; they are stopped after the round. Each lane's decider
is pointed at its instance with `LITELLM_BASE_URL=http://127.0.0.1:800N` in the lane's
environment (`eval/docker/sweep.sh` passes it into the decider container; a bare var wins over
the remote profile's default, `server/decider/config.py`). Nothing else runs on any of the four during R29S.

The model, temperature, frame, action fan and sites are the phase lock's. The lock does not name
the host layout; `phase.json` "lanes" records it, as every round has.

## Evidence

Why the host is the next lever, after seven failed attempts at the perceiver's wall reading
([R28](../R28_wall_reader/README.md), [R27](../R27_mirrored_nr_perceiver/summary.md),
[probe LD](../_probes/ld/README.md)):

1. **Alone, the model is deterministic.** Probe LD read 3,360 image/read pairs three times, one
   call at a time per instance, and 3,359 came back byte-identical, failures included
   ([LD README](../_probes/ld/README.md), "Three repeats, one answer").
2. **Shared, it is not.** The same step-0 frame with the same 999-token input read differently in
   R25, R25D, R26 and R26N at temperature 0 ([why_14.md](../R25D_door_confirmer_open_near_unwalled/why_14.md)
   §4). Probe N1 put the cause in the batch: with 7 neighbours, 16–28% of strip fields change;
   alone, 2–3% ([N1](../_probes/n1/README.md)). Every flown round ran 4 lanes on `:8004`.
3. **Two thirds of the flight misses are the host's.** On the 33 set-F frames where `g05` missed a
   wall in flight, the same frames read alone miss 32.5% of those strips
   ([LD README](../_probes/ld/README.md), "Two thirds of the flight misses do not come back").
   In flight `a49` missed 17.3% of real walls (`eval/r27_flight.py` on R25D); the part that
   survives being read alone is about 6%.
4. **Phantom walls were not helped by being read alone** (set B under L0: 13.8%, R25D in flight
   12.7%), so this is a one-sided gain: fewer missed walls at no phantom cost, if it carries.
5. **The a49 rate is unknown.** why_14 §4 gives the `a17b` family 11.3 ± 1.4 per 18 and asked for
   2–3 re-flights of `a49` before building on it. R29N is the first.

What a missed wall costs in flight: the map opens floor that is not there, the drone walks into it
(collision or blocked step), and `searched already` notes land on the wrong cells. R25D's lost
cells are s03 `final`/`dynamic` (the shut tine) and s02c/s02va `final` (the door wall).

## Hypothesis

With every perceiver call alone on its instance, `a49` misses fewer real walls in flight than it
does on a shared vLLM, and scores at least as well.

## Predictions

| Arm | R25D (`a49`, shared) | R29N (shared, again) | R29S (alone) |
|---|---|---|---|
| initial | 6 | 5 or 6 | 6 |
| final | 3 | 2 to 4 | 3 or 4 |
| dynamic | 5 | 3 to 5 | 4 or 5 |
| total | 14 | 10 to 14 (family 11.3 ± 1.4) | ≥ R29N |

Per site: no change expected on s01. The s03 `final`/`dynamic` failure is the dead-end pattern
([s03_tines_analysis.md](../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md)), not a
wall reading, so it should stay lost in both. Any gain should come on s02 `final`.

## Gate (set before flying)

Scored by `eval/r28_flight.py` on each round's `runs/` (missed / phantom walls on the s02 and s03
steps against geo, both reads, longest turn-around streak). R25D baselines, computed today:
missed 17.3%, phantom 12.7%, s03 phantom 16.2%, longest streak 3, 0 of 627 perceiver calls failed.

| | Check | R25D |
|---|---|---|
| 1 | R29S missed walls ≤ 10% | 17.3% |
| 2 | R29S phantom walls ≤ 15% | 12.7% |
| 3 | R29S s03 phantom walls ≤ 20% | 16.2% |
| 4 | R29S success ≥ R29N success | |
| 5 | R29N missed walls within 17.3 ± 4 pts (the shared host reproduces) | 17.3% |

- **All five hold:** the host is a lever. One lane per instance becomes the host setting for every
  later round and for the final 90 runs, written into each round's `phase.json` "lanes", and the
  test plan's changelog gets a line.
- **1 fails:** the flight misses do not fall when the call is alone; the LD replay gain was an
  artefact of a warm prefix cache (the replay read each frame after its own first read; a flight
  frame is always new). Recorded; the host is not the lever.
- **5 fails:** R25D's wall rates were themselves a draw; R29N stands as the second a49 data point
  and the gate is re-read against the pair.
- Checks 1–3 and 5 are about the reading and can hold while 4 fails: one seed cannot resolve ±1
  run (why_14). That outcome still changes the host setting, for the measurement's sake.

## Manipulation check

- Every `run.json` in both rounds carries `agent_version` a49 and `agent_sha` `83f7a6a19b01`.
- R29S: each lane's `decisions.jsonl` latency per perceiver call is at or under R29N's median
  (an instance with one client is never slower), and `nvidia-smi --query-compute-apps` during the
  round shows exactly four vLLM processes.
- R29N: four lanes started together, so `:8004`'s load matches R25D's.

## Drop criterion

Nothing is carried or dropped from the agent: `a49` stays the base either way. The host setting
changes only if checks 1–3 hold.

## Builds on

R25D (`a49`), unchanged.

## Also in this branch, not flown here

`a62` = `a49` + `reason_cap: 2000` (`server/decider/agent.py`, `schema.perceiver_schema`). About 2%
of the probes' `w01`/`ld01` calls ran the describe-first reason past the token budget, in a loop
of one sentence, and failed; the cap closes the string so the strips still arrive
([LD README](../_probes/ld/README.md), "Recall of the failed calls"). The cap was first added to
every agent's schema at once (`072e2e4`); it is now a feature flag, off for `a49`, so `a49`'s
schema is the one R25D flew. In R25D itself 0 of 627 perceiver calls failed, so `a62` is a safety
for later agents with longer reasons, not a fix for `a49`. It gets its own round only if a flown
round shows failed perceiver calls.

Also noted, not changed: probe LD measured the eye at 1.48 m and the nearest visible floor at
1.56 m; `prompt.py`'s g05 note and `agent.py:330` say 1.84 m (they assume a 1.75 m camera).
A wording fix is a new prompt version; it waits for one.

## Notes for the operator

- **Branch.** `phase2/r29n-host-noise`, from `fix/reason-maxlength` (LD, R28, the cap).
- **Order.** Fly R29N first, alone on `:8004`, as R25D and R27 were (4 lanes, nothing else on the
  instance). Then start the three copies and fly R29S. Flying them at the same time would put
  R29N's calls beside R29S's `:8004` lane and spoil both.
- **R29S lanes.** `LITELLM_BASE_URL=http://127.0.0.1:800{4,6,7,8} sh ~/round_lane.sh k 4 ~/asep-r29s-lk
  a49 83f7a6a19b01 R29S R29S_host_noise_solo`; each lane's `/health` reports `83f7a6a19b01`. Stop `:8006`–`:8008` after the round (GPU limit: 4 instances including `:8004`).
- **Preflight.** Clean tree, lock matches (`python eval/phase2.py init` says nothing), tunnel up
  (operator's).
- **After.** `python eval/r28_flight.py <R29N runs> <R29S runs>`; labels; summary; the gate table
  above filled in under Outcome; `python eval/phase2.py results`.

## Outcome

Flown 2026-11-02 at `822f1d7`, R29N 16:00–16:33 UTC then R29S 16:34–16:55 UTC. 18/18 valid in each.
**R29N 11/18, R29S 14/18 (R25D 14). Gate check 1 failed, checks 2–5 held.**

| | Check | R25D | R29N | R29S | |
|---|---|---|---|---|---|
| 1 | R29S missed walls ≤ 10% | 17.3% | 15.4% | **14.9%** | **FAIL** |
| 2 | R29S phantom walls ≤ 15% | 12.7% | 12.0% | 9.3% | pass |
| 3 | R29S s03 phantom walls ≤ 20% | 16.2% | 14.1% | 8.3% | pass |
| 4 | R29S success ≥ R29N | 14 | 11 | 14 | pass |
| 5 | R29N missed walls within 17.3 ± 4 | 17.3% | 15.4% | | pass |

Alone, the perceiver misses as many walls as shared: the LD replay's gain was a warm prefix cache
(each frame read after its own first read), not batching; a flight frame is always cold. The host
is not the lever for missed walls, so the host setting does not change. Phantom walls did fall
(12.0 → 9.3%, s03 14.1 → 8.3%), and alone is 35% faster per call: a lead, one seed. The step-0
reading differs between R29N and R29S in 11 of 18 cells, so a cold call at temperature 0 is still a
draw on this server; where every reading matched (s02vc `final`) the two rounds ran the same 60
steps pose for pose. R29S's s03 `final` win is the side choice at the crossbar at step 34 (R25D
pose-identical to step 33, then tine L). `a49`'s three rounds: 14, 11, 14.

Summaries: [R29N](summary.md), [R29S](../R29S_host_noise_solo/summary.md) (the gate reading and
the cells table). Labels: Claude review, not yet confirmed by the operator.
