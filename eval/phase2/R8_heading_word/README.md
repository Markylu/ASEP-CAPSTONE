# R8: Heading as a compass word

**Agent:** `a11` (`3859d0345560`) · **Prompt:** `p12` (`f24e2855bfbe`) · **Identifier prompt:**
`g02` (`bf175c973dfb`) · **Status:** flown (18/18 valid)

Written before the probe and before flying. Spec: `docs/phase2-test-plan.md`. The shas above are
re-checked against `config.lock.json` before the round flies. R8 flies beside **R8N**
([README](../R8N_noop_control/README.md)), a no-op edit of the same base agent, on the same host
at the same SHA, and is read against it (Attribution rule).

## Change

`a11` builds on `a10` (`p11`: pose log with comparison lines, no sighting line, identifier `g02`
on the clean frame; the agent R7 flew). **One change:** the log gives the heading as one of eight
compass words instead of degrees.

- Each pose reads `(x, y), facing <word>` where `p11` read `(x, y), heading <N> degrees`: the
  nearest of east, north-east, north, north-west, west, south-west, south, south-east (45-degree
  bins centred on the cardinals; `_compass()` in `server/decider/prompt.py`).
- The pose paragraph's heading sentence becomes: east is +x and north is +y; "facing" is the
  compass direction to the nearest of eight; turning left goes from east toward north, then west,
  then south; turning around gives the opposite direction. No other sentence changes.
- Neither the system prompt nor the log contains "degrees". Comparison lines, actions and the
  identifier line are as in `p11`.

Example (R7 s02vc `initial`, step 12, as `p12` renders it):

```
Start: at (20.0, 0.2), facing west.
Step 0: flew straight. Ended at (18.3, 0.2), facing west, moved 1.7 m.
```

`a00`–`a10` and `p02`–`p11` keep their shas: all 31,428 `p08`–`p11` renders of the recorded R6,
R7 and R7C decisions are byte-identical before and after the change.

## Evidence

- **Arithmetic on the heading turns the drone away from a goal in view.** R6 s02va and s02vc
  `initial`, step 12, goal 12.0 m right: "facing 221 degrees … turning around (0), which would
  reorient the drone to face 41 degrees (221 + 180)". It never saw the goal again
  ([R6 reasoning analysis](../R6_pose_log/reasoning_analysis.md) §3). R7 repeated it at the same
  site and step ([R7 reasoning analysis](../R7_comparison_lines/reasoning_analysis.md) §1, §4).
- **Turn-arounds with the goal in view** (`eval/agent_evidence.py`, new column): R6 3 of 104
  in-view decisions, R7C 0 of 138, R7 3 of 134.
- **Degrees in nearly every reason, and sums on them.** Reasons citing degrees: R6 855 / 894,
  R7C 829 / 867, R7 810 / 858. Reasons with heading arithmetic: R6 22, R7C 25, R7 23 (new column,
  every R7 hit read by eye; the R7 analysis's narrower count was 11, so compare with this one).
  Some sums are wrong ("194 + 180 = 174", R7).
- **Its own degree-to-compass conversions are 17% wrong** (R6: 247 of 299 right; "358 degrees,
  which is nearly due north", which is east). The word removes that step.
- Not addressed: the heading is a map direction while markers and identifier are image-relative.
  The word removes the arithmetic, not that translation.

## Hypothesis

With the heading given as a compass word, the model stops doing arithmetic on it and no longer
turns around on a goal it can see to the side, without losing R7's blocked-move behaviour.

## Predictions

Per arm, 6 sites, seed 1, on sctsvr6. R0 is Phase 1's seed-1 baseline; R7 is `a10` on this host.

| Arm | R0 | R7 | Predicted R8 |
|---|---|---|---|
| initial | 5/6 | 4/6 | 4–6/6, s02vc ✓ |
| final | 0/6 | 0/6 | within R8N's spread of R7 |
| dynamic | 0/6 | 2/6 | within R8N's spread of R7 |

- Turn-arounds with the goal in view: at most 1 (R7 3).
- Reasons with heading arithmetic: at most 3 (R7 23). Reasons citing degrees: under 10% (R7 94%).
- s02vc `initial` succeeds (R6 and R7 fail it at step 12).
- R7's blocked-move behaviour holds: same pick after a blocked move at most 15% (R7 8%),
  collisions at most 80 (R7 60), progress claimed after a blocked move below 30% (R7 20%).
- `final` and `dynamic` are not targeted; predicted to move no more than R8N moves.

## Attribution rule

Pre-registered, for R8 against R7, with R8N against R7 as the noise floor:
- A cell's outcome change counts toward the heading only if **R8 changes more cells than R8N**
  and the cell's first different pick from R7 is at a step where the goal was in view or the
  reason cites the heading.
- Every other change is read as noise, in either direction.
- The first different pick of every cell pair (R8N vs R7, R8 vs R7, R8 vs R8N) is reported in
  the reasoning analysis.

## Manipulation check

Written into `eval/agent_evidence.py` before the probe: four new columns, plus R7's.
- **Reason cites degrees:** a number followed by "degree(s)" or "°". Expected to collapse.
- **Reason uses a compass word:** already 34% in R7 (the model converts on its own); expected to
  rise.
- **Heading arithmetic:** two- or three-digit numbers either side of a plus or minus, step ranges
  excluded.
- **Turn-around with the goal in view:** turn-around picked while `true_goal()` says ahead, left
  or right.
- Comparison line shown after a blocked move (`p12` is in `COMPARE_PROMPTS`): stays 100%.

## Drop criterion

`a11` is not carried forward if two or more of these hold:
- turn-arounds with the goal in view not below R7's 3;
- collisions above 80 (R7 60);
- `final` + `dynamic` below R8N's;
- `initial` below R8N's.

## Probe gate

Required: the change alters what the model is shown at every step. Run on sctsvr6 against the
model at 127.0.0.1:8004, in a scratch directory; results copied back to `probe/`.

Sets (`eval/goal_probe.py`):
- `lost` and `offcentre`: resampled with `sample-r7` from R5, R6, R7 and R7C, so `offcentre`
  grows past R7's 11 frames.
- spin: R6's `spin_set.jsonl`, 80 frames (`run-spin`).
- step 0: the 18 step-0 frames of R7, one per cell; reported as picks identical to `a10`.

Agents: `a10` (calibration, the base), `a11`, `a12` (R8N's control, reported, not gated), and a
second `a10` spin pass to re-measure temperature-0 noise on the server (R7: 2 of 80 picks).

**Thresholds for `a11`,** relative to `a10` on the same sets, with R7's margins:
- spin turn-around at most `a10` + 5 of 40;
- `lost` turn-around at most `a10` + 3;
- `offcentre` turn-around no more than `a10`'s;
- a valid reply on every frame.

If the gate fails, R8 does not fly; R8N still flies alone as the noise-floor round.

**Result: gate passed.** [probe/probe_r8.md](probe/probe_r8.md), run 2026-10-22 on sctsvr6.

| Agent | spin turn-around | `lost` turn-around | `offcentre` turn-around | step 0, same pick as `a10` | spin, same pick as `a10` |
|---|---|---|---|---|---|
| a10 | 5/40 | 3/25 | 3/25 | 18/18 | 80/80 (rerun) |
| **a11** | **8/40** (limit 10) | **5/25** (limit 6) | **1/25** (limit 3) | 12/18 | 44/80 |
| a12 (no-op) | 7/40 | 4/25 | 1/25 | 15/18 | 45/80 |

0 errors on every frame; the server's `a11` and `a12` shas matched the locks.

What the probe says before flight:
- **The server is deterministic.** A second `a10` spin pass gave the same pick on 80 of 80 frames,
  and `a10` repeated its recorded R7 step-0 pick in 18 of 18 cells. The 2-in-80 noise of R7's
  probe is not there now. Differences between agents are the prompt, not sampling.
- **A content-free sentence moves picks as much as the heading change.** On the spin frames `a12`
  agrees with `a10` on 45 of 80 picks, `a11` on 44. At step 0, `a12` changes 3 cells (s02c,
  s02va, s02vc `final`), `a11` 6 (s02a, s02c, s02vc `final`; s03 all arms, one shared frame).
  This is the noise floor R8N is flown to measure, seen offline.
- **Off-centre turn-arounds fell from 3 to 1 for both `a11` and `a12`.** So the probe does not
  credit the drop to the heading. `a11` no longer turns around on R7 s02vc `initial` step 12
  (it picks the right-hand marker); `a12` still does. `a11` adds one on R7 s02vc `dynamic`
  step 14: "facing west… the goal is to the right… must turn to face east".
- **The compass word brings its own frame error.** `a11` maps image-relative "right" onto the map
  with the word, and sometimes wrongly ("facing south, so 'to the right' means east", R6 s02va
  `dynamic` step 23; it is west, though the pick was right). The arithmetic is gone, but the
  translation the Evidence section left unaddressed now shows up in words.

## Host

sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R7 and R7C. R8 and R8N fly at one SHA,
R8N first. The final round is flown on the Mac.

## Builds on

R7 and agent `a10` (`p11` + `g02`). Branch cut from `phase2/r7-comparison-lines` (`4d82a10`),
tag `p2-r7`.

## Outcome

The mechanism held, the success count did not move. Heading arithmetic 23 → 2, goal-in-view turn-arounds 3 → 0, s02vc `initial` ✓; success 6/18 as R7 and R8N. R8 changed 4 cells against R7, the no-op R8N changed 6, so by the attribution rule no outcome change is credited to the heading. Drop criterion: 1 of 4 met; carried forward. [summary.md](summary.md), [reasoning_analysis.md](reasoning_analysis.md).
