# 1D Split Path (s03): summary

**Citable.** Flown at `78c1867`. Runs 1–12 flew on 2026-10-05, 00:29–01:04 UTC. The tunnel
dropped at run 13; runs 13–15 flew after it came back, 13:19–13:29 UTC, at the same SHA. The
runs used `Qwen3-VL-30B-A3B` on the remote profile, at temperature 0 with prompt `p02`
(`26260774b60e`). They covered s03 v2 × {initial, final, dynamic} × seeds 1–5.

- **15 / 15 runs are valid.** Every replay was exact, and every run passes §10.
- Labels were reviewed by Claude on the operator's behalf. **They still need confirmation from Markus Lu.**

Site hypothesis (`site.json`): after the corridor it committed to becomes a dead end, the
agent will keep pressing against the closed exit rather than back out and take the other
branch. **Not tested:** the agent never entered a corridor, so the dead end never formed.

## Result

| Arm | n | SR | 95% CI (Wilson) | success | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| initial | 5 | **0.00** | 0.00–0.43 | 0 | – | 5 | 0 | 0 | – | 1.63 / 8.04 s |
| final | 5 | **0.00** | 0.00–0.43 | 0 | – | 5 | 0 | 0 | – | 1.72 / 4.77 s |
| dynamic | 5 | **0.00** | 0.00–0.43 | 0 | 0 | 0 | 0 | 0 | **5** | 1.66 / 2.47 s |

Planned contrasts (§11, Fisher's exact test, two-sided):

- **a. dynamic vs initial:** 0/5 vs 0/5, p = 1.0, ΔSR = 0.
- **b. dynamic vs final:** 0/5 vs 0/5, p = 1.0, ΔSR = 0.
- **d. s03 L vs R:** not testable. No run entered either tine.

### Per run

All 15 runs did the same thing. From spawn at x = 21 the agent flies straight down the
approach, following the goal bearing (0°: the goal at x = −12 is out of sight behind the
fork). It hits the divider wall between the two tines at x = 5.2 on step 10 and stays
pinned there until the step limit: 60 steps, 49–51 collisions, final distance 17.2 m. No
run moved more than 1.6 m sideways. The tine mouths are at |z| = 3.5–6.5.

- `dynamic`: no change event in any run (empty `events.jsonl`). The triggers sit mid-tine
  (x = 0, z = ±5) and were never reached.
- `final` seed 4 turns around in place twice and then resumes. No other run turns around.

## What the model did

The reasons describe the divider as open corridor: "The drone is currently facing a
corridor that appears to be straight ahead, with no visible obstacles" (`initial` seed 2,
step 1). While pinned, 13–23 decisions per run still call the corridor or path clear. In
900 decisions, one reason (`dynamic` seed 2, step 5) says the path is "blocked by a wall
on the left and a corner ahead", and it changes nothing.

- **initial and final → `replan_failure`** (10/10). This is the §9 static-arm label for
  "never found the available route": neither tine was ever entered.
- **dynamic → `pre_change_failure`** (5/5). This is §9 label 1: the change never fired.
- Tag on all 15: `path_hallucination`.

**H1 reading.** s03 cannot speak to H1. It fails before any change, in the control arm
too. This is the risk §7.5 named ("uncertain: blind turn at crossbar"), and it is the
cleanest instance of the pattern behind every Phase 1 failure. The policy follows the goal
bearing and has no lateral search. When the route requires going sideways around
geometry, whether a cube (s01), a closed door (s02/s02v) or a fork divider (s03), it does
not, even when nothing changes.

## Validity notes

- Rungs: 886 of 900 decisions used `json_schema`. 14 fell back to `json_object` (10
  initial, 2 final, 2 dynamic). Every run is above the 90% bar.
- **Tunnel drop mid-phase.** `final` seed 1 attempts a01–a03 failed at step 0, every rung
  `ReadError`/`ConnectError`, with the port-8004 forward down. The runner gave up after 3
  attempts. These are transport failures, not model behaviour. They are kept in
  `_attempts/`, and a04 flew valid after the tunnel returned. Same SHA, so §7.1 holds.
- No §10 change-step check applies to s03 (`TRIGGER_X` is `None`), and no run had a change
  to check.
- Latency normal (p50 1.6–1.7 s). The `initial` p95 of 8.0 s comes from occasional slow
  decisions.

## Issues found

1. **s03 is uninformative for H1 as designed.** A follow-up site with a tine visible from
   spawn, or the goal beam visible down one tine, would let the agent reach the dead end.
   That would be a new site version and a new, separately reported mini-phase, not a change
   to 1D.
2. Auto pre-label negation (1A issue 1, still open). All 15 runs got a spurious
   `ack_step`. No label changed: s03's rubric outcome does not depend on acknowledgement
   here.

## Attempts

`final` seed 1 a01–a03: transport failures (tunnel down), kept in `_attempts/s03/final/seed1/`.
