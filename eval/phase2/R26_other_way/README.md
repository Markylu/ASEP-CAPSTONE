# R26: R22K with the other way at the fork

**Agent:** `a50` (`122780a7de8a`) · **Prompt:** `p17` (`cb3578251cfe`) · **Strategist:** `q10` ·
**Memory:** `a17b` · **Status:** laid out 2026-10-29, probe gate pending

Written before flying. Spec: `docs/phase2-test-plan.md`. Built overnight without the operator
(operator, 2026-10-28: "mantain a prefrence for subagents over hard coded tasks": code lists one
more way, the strategist decides when to take it). Second agent at the same SHA: **R26N**, `a51`
(`d96785ba4e1c`) = `a42` (R22, no goal confirmer) with the same change.

## Change

One against `a43` (R22K, 12/18, level with the best), three parts:

- **Item (code, `planner.other_way`).** On every detour call, after the other items: the newest
  along-the-wall end offered at an earlier call made 6 m or more from here, that the drone never
  came within 1.5 m of, not left off as a failed detour, with known floor within 4 m of it. Worded
  "the other way along the wall you met at step N (you never went there), D m back over known
  floor". It stands for up to 24 steps (other detours 12).
- **Situation line (`planner.closed_door_line`).** "A closed door was seen ahead at step(s) …"
  when the doorway confirmer called a reported doorway closed in the last 5 steps.
- **Strategist `q10`** = `q08` + rule 5: a closed door seen and at most one along-the-wall item
  listed (or both followed twice) is a dead end; take the "other way" even though it lies behind.

Parameters and wording: `agent.OTHER_WAY_A50`, in the features, so the sha.

## Evidence

- s03 analysis (subagent, read-only):
  [../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md](../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md).
  The goal is in the chamber behind the exit wall, reached through the door at the end of one
  tine. All five failed s03 `final`/`dynamic` runs of R20, R20K, R22 and R22K that reached the
  crossbar spent 34–46 steps in the tine whose door was shut and 0 in the other. A closed door was
  reported there on 9–15 steps per run. A way out was listed on 25 of 33 dead-end calls and taken
  0 times, and none of those ways led to the other tine.
- Items, no model (`eval/r26_other_way_probe.py items` on R21, R21K, R22, R22K; memory rebuilt at
  every recorded call; [probe/items.txt](probe/items.txt)):

  | | calls | item listed | item good | dead-end cue (closed door, ≤ 1 along) | cue and good |
  |---|---|---|---|---|---|
  | s03, in a tine (`final`/`dynamic`) | 22 | 21 | 21 | 10 | 10 |
  | s02, at the divider | 189 | 108 | 56 | 26 | 19 |

  "Good" on s03 means on free floor in the other tine. On s02 it means 0.5 m or more nearer a door
  open at that step. The first version required known floor within 1.5 m of the end and listed
  the item on only 5 of 22 calls: the other tine had never been seen.
- Smoke (`smoke_run`, R22K's 706 manifests): `a50` 0 failed steps.

## Probe gate

Set before the live probe (`eval/r26_other_way_probe.py run`/`score`, `q10` on the recorded calls
with the item and line added, text only):
- s03 calls in a tine with the dead-end cue: "other way" chosen on ≥ 75%;
- s02: "other way" chosen where it is misleading on ≤ 10% of the s02 calls asked;
- s02 divider: along-the-wall picks no more than 10 points below the recorded `q08` picks.

**Result (`q10`, [probe/q10_score.txt](probe/q10_score.txt), 251 of 252 calls answered): failed.**
- s03 dead-end calls with the cue: "other way" 7/10 (gate 75%).
- s02: misleading "other way" picks 24 of 199 calls, 12% (gate 10%).
- Divider along picks 101/188 against `q08`'s 168/188.

`q10` took the item off the dead end too (36 of 82 divider calls without the cue), so `a50`/`a51`
are not flown.

### Second candidate: `a52`, `a53`

The item is listed only in a dead end (`planner.dead_end`: a closed door seen in the last 5
steps and at most one along item on the menu; `agent.OTHER_WAY_A52`). Strategist `q11` = `q08` +
rule 5, "listed only in a dead end; when listed, choose it". `a52` (`0621b10d620d`) is `a50` with
both changes; `a53` (`9d5f211ff902`) is `a51` with them. Items
([probe/items_a52.txt](probe/items_a52.txt)): s03 in a tine, listed 10 of 22, all 10 good; s02
divider, listed 26 of 189, 19 good. Smoke: `a52` 0 failed steps.

Gate, set before the `q11` probe:
- s03 calls in a tine with the item: "other way" chosen on ≥ 75%;
- s02: misleading "other way" picks on ≤ 10% of the calls asked;
- s02 divider: along-the-wall picks plus good "other way" picks no more than 10 points below
  `q08`'s along picks.

**Result (`q11`, [probe/q11_score.txt](probe/q11_score.txt), 202 of 202 answered): failed on the
first gate.**
- s03 dead end: "other way" 7/10 (gate 75%); the other 3 calls followed the one along item left.
- s02: misleading picks 6 of 188, 3%.
- Divider: along 144 + good "other way" 9 = 153/186, against `q08`'s 166/186: 7 points below.

### Third candidate: `a54`, `a55`

`q12` = `q11` with rule 5 put before rules 1–4, and "do not follow the wall here again". `a54`
and `a55` are `a52` and `a53` with `q12`. Same gate as `q11`, set before the `q12` probe.

**Result (`q12`, [probe/q12_score.txt](probe/q12_score.txt)): failed on the third gate.**
- s03 dead end: "other way" 9/10.
- s02: misleading 7 of 189.
- Divider: along 76 + good "other way" 18 = 94/187, against `q08`'s 167/187. The way back was
  taken on 82 divider calls: "do not follow the wall here again" was read off the dead end too.

### Fourth candidate: `a56`, `a57`

`q13` = `q11` with rule 5 put before rules 1–4 and nothing else. `a56` and `a57` are `a52` and
`a53` with `q13`. Same gate, set before the `q13` probe.

**Result (`q13`, [probe/q13_score.txt](probe/q13_score.txt)): failed on the third gate.**
- s03 dead end: "other way" 10/10.
- s02: misleading 7 of 188.
- Divider: along 92 + good "other way" 18 = 110/186, against `q08`'s 167/186, with the way back
  taken 63 times. The closed-door line stands on 117 of 189 divider calls, most with no "other
  way" listed; with rule 5 first, `q13` read those as dead ends and went back.

### Fifth candidate: `a58`, `a59`

`a56` and `a57` with the closed-door line shown only when the "other way" is listed
(`agent.OTHER_WAY_A58`). Strategist `q13`. Same gate, set before this probe.

## Hypothesis

At the s03 dead end the drone goes back to the other tine and reaches the chamber: R26 scores
above R22K.

## Predictions

| Arm | Baseline (R22K, `a43`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 3 | 3 or 4 (s03) |
| dynamic | 3 | 3 or 4 (s03) |

Total ≥ 13/18.

## Manipulation check

In s03 `final`/`dynamic`: an "other way" item chosen at least once, and steps in the open tine > 0.

## Drop criterion

Not carried forward if the total does not beat R22K's 12/18.

## Builds on

R22K (`a43`).

## Outcome

Not flown.
