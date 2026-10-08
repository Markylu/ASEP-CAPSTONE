# P2.0 Shakedown: summary

**Not citable.** Flown at `92b3a2b` on 2026-10-08, 15:07–15:12 UTC. The runs used the fake
decider: `server/decider/fake_litellm.py` with `FAKE_PICK=straight`, which always picks the
straight-ahead action (index 3). The decider ran on :8010 with `--profile remote --agent a00`,
`VLM_MODEL=stub`, `VLM_STREAM=0` and `VLM_RTT_PROBE=0`, against the fake router on :4001.

The shakedown had two jobs: prove the Phase 2 runner (`eval/phase2.py` over `eval/phaselib.py`)
end to end, and prove that agent versions are recorded and checked. Both hold.

## Result

- **18 / 18 runs valid on the first attempt.** Every replay reproduced its run with 0.0 m drift,
  and the events matched.
- Every `run.json` and `metrics.json` carries `agent_version` `a00` and `agent_sha`
  `fb65adbe3317`, and §10 checked both against the round lock.
- Each `dynamic` arm on s01, s02a/c and s02va/vc logged its change event at step 3. No `initial`
  or `final` arm logged one. s03 never reached a tine, as in 1.0.
- Spawn jitter for seed 1: dz -0.170 m, dyaw -2.23°, identical on all 18 runs.
- **Identical to Phase 1's 1.0 shakedown on every run:** collisions, final distance and auto label.
  Same fake decider, same seed, so this is the regression check that the shared runner and the
  agent plumbing changed nothing about how a run is flown or scored.

| Site | Arm | Label (auto) | Collisions | Final dist (m) |
|---|---|---|---|---|
| s01 | dynamic | ignore_change | 55 | 14.23 |
| s01 | final | replan_failure | 55 | 14.23 |
| s01 | initial | collision | 39 | 12.18 |
| s02a | dynamic | ignore_change | 54 | 12.48 |
| s02a | final | replan_failure | 54 | 12.48 |
| s02a | initial | collision | 39 | 12.18 |
| s02c | dynamic | ignore_change | 54 | 12.48 |
| s02c | final | replan_failure | 54 | 12.48 |
| s02c | initial | collision | 39 | 12.18 |
| s02va | dynamic | ignore_change | 49 | 12.49 |
| s02va | final | replan_failure | 49 | 12.49 |
| s02va | initial | collision | 35 | 12.23 |
| s02vc | dynamic | ignore_change | 49 | 12.49 |
| s02vc | final | replan_failure | 49 | 12.49 |
| s02vc | initial | collision | 35 | 12.23 |
| s03 | dynamic | pre_change_failure | 51 | 17.23 |
| s03 | final | replan_failure | 51 | 17.23 |
| s03 | initial | replan_failure | 51 | 17.23 |
