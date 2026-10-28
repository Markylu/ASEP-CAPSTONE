# R13: Lose sight, verify, then explore or pursue (a20; R13G flies a21 beside it)

**Agent:** `a20` (`ddcf9e3e806a`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) ·
**Perceiver:** `g05` (`133ed83db46b`, as `a19`) · **Strategist:** `q04` (`f8fdf4b5946c`, as `a19`) ·
**Spatial memory:** `spatial.A17` (as `a19`) · **Stage machine:** `planner_a17` `6eb22517c3e0` +
**verify** `planner_a20` `2ff7c48cdc16` ·
**Status:** pre-registered 2026-10-28, not flown. Probe gate passed ([probe/](probe/)).

Second agent, flown beside it at the same SHA: **R13G**, `a21` (`97790ec7c54e`), below and in
[R13G's README](../R13G_verify_goal_words/README.md). Spec: `docs/phase2-test-plan.md`.

## Operator's direction (2026-10-28)

> what if loosing sight of goal just switches you back to explore mode

refined, when asked, to: exploring → sees goal → pursues goal → loses track of goal → a
verification mode that goes to the last goal-seen position and bearing and double-checks for the
goal, overriding memory if it differs → back to either explore or goal-hunting. Built on `a19`
(R12), loss of sight immediate, and both explore variants (no goal truth, goal truth in the
strategist's text) flown in parallel. Read against the best round so far, R11, and against R12,
the base; no control (operator, 2026-10-28).

## Change

`a20` is `a19` with one change: the stage machine (`planner.staged_verify`). Perceiver, map,
strategist, navigator and turn rule are `a19`'s.

| | `a19` (R12) | `a20` |
|---|---|---|
| goal stage | head for the belief (rays since the last drop); kept until a look's cone covers the belief, a look faces it down an open strip, or the drone reaches it with no sighting for 3 looks | head for the belief **while the goal is reported on this look**; the first look without it goes to **verify**, unless a detour stands (the drone left the goal's view on purpose; a detour ends as `a19`'s). `a19`'s three disproof rules are not used. |
| verify | none | Target: the **vantage**, where the last sighting was taken from; within 1.5 m of it, a point 3 m along the seen bearing, so "toward your target" turns the drone to face it. Navigator mode word `verify`. |
| verify → goal | | the goal reported on any look (on the way, or at the check). If the new sighting disagrees with the old belief (the believed point lies more than 2 m off the new ray, or the bearing from the vantage has turned more than 15°), the old rays are dropped and the belief rests on the new sighting ("overriding memory"): `reacquired_moved`; else `reacquired`. |
| verify → explore | | **check look**: a look after verify began, within 1.5 m of the vantage, facing within 39.5° (`FOV/2 − 4°`, as `faces_unseen`) of the seen bearing, with no goal: `verify_failed`. Also no known path back (`verify_unreachable`) or more than 8 steps (`verify_timeout`). The sighting's rays are dropped and the strategist is asked with the reason in words. |

New thresholds and words (`STAGE_PARAMS_A20`, `ASKED_A20`, `SITUATION_A20`) are hashed into
`a20`'s sha as `planner_a20`; `a17`–`a19`'s shas are unchanged (checked), and `staged()` was
split into shared helpers with R12's open-loop replay byte-identical before and after.
`spatial.goal_belief` gains `until` (default unchanged).

## Two agents

| | `a20` (R13) | `a21` (R13G) |
|---|---|---|
| goal truth | none | **strategist text only** (`goal_truth: strategist`) |
| strategist | `q04` | **`q05`**: `q04` plus one paragraph; the situation adds "The goal's position is known: …" and each place "about N m nearer/farther the goal than you are" (`a16`'s wording) |

The menu is `a17`'s (reachable edges of unsearched ground, reachable doorways, a way back) in
both, so R11's goal-side frontier inside or behind walls cannot come back. `a21`'s manifest goes
through its stages without the goal block (as `a20`); the position is kept apart for the
strategist's situation only. The navigator's plan line for a belief target is `a20`'s in both.

## Evidence

- R12 [README, Outcome](../R12_staged_search/README.md#outcome): in `dynamic` the goal was reported
  at step 0 in 5 of 6 runs, then disproved or lost within a few steps and not found again;
  `final` + `dynamic` 0/12.
- R12 probe line 5: one look was enough to disprove 39 of 46 false sightings, at the cost of
  genuine ones lost while still in sight (12 of 285 on R11's paths); a belief from one sighting
  is a point 10 m out on the ray, which the drone then flies at.
- R11 failure analysis §0: 10 of 14 "goal in view" hand-backs were hallucinated sightings.

## Hypothesis

When the drone goes back to where it saw the goal and looks again instead of chasing or dropping
a remembered point, a goal seen once is found again more often, and `dynamic` (and `final` where
the goal is glimpsed) rises above R12.

## Predictions

| Measure | R12 (`a19`) | R11 (`a16`) | R13 / R13G |
|---|---|---|---|
| `initial` | 5/6 | 6/6 | ≥ 5/6 |
| `dynamic` | 0/6 | 1/6 | ≥ 2/6 |
| `final` | 0/6 | 4/6 | ≥ 1/6 (g05's walls still hold the drone near its start; verify does not touch that) |
| total | 5/18 | 11/18 | above R12; R11 is the bar to beat |
| verify episodes ending `reacquired*` | | | ≥ 1/3 |
| `verify_failed` with the goal truly in line of sight | | | ≤ 1 a round |
| R13G against R13 | | | `final` higher (the menu names the goal's side) |

## Manipulation check

From the decision records (`stage`, `evaluator.events`, `strategist.text`):
- stage per step (explore, goal, verify); verify episodes and how each ended;
- check looks taken; `verify_failed` scored against the manifest's line of sight;
- R13G: every strategist text carries the goal's position, no navigator text does.

## Drop criterion

Neither agent is carried forward if it does not beat R12's 5/18. One that beats R11's 11/18
becomes the agent to build on.

## Probe gate (passed 2026-10-28)

`eval/r13_probe.py`, outputs in [probe/](probe/):
1. **Transitions** (synthetic): reacquired, reacquired with the memory overridden, check fails,
   a fresh look needed for the check, 8-step timeout, unreachable vantage, detour holds goal,
   verify target. **PASS** ([transitions.txt](probe/transitions.txt)).
2. **Smoke** (the real step on R12's 862 recorded manifests, stub replies): 0 failed steps; `a20`
   the same with and without the goal block; `a21` the same as `a20` apart from the strategist's
   text; the goal's position in 126/126 of `a21`'s strategist texts and 0 navigator texts.
   **PASS** ([smoke.txt](probe/smoke.txt)).
3. **Open-loop count** on R12's paths, reported ([offline.txt](probe/offline.txt)): 10 losses of
   sight, all in `dynamic` but one; 8 end in `verify_timeout`, 1 `reacquired_moved`, 1
   `verify_failed` (goal not in line of sight). The recorded drone never turned back to a
   vantage, so this is a floor: the live navigator follows the verify target. Sightings 96
   genuine, 14 false.

```
python3 eval/r13_probe.py transitions
python3 eval/r13_probe.py smoke eval/phase2/R12_staged_search/runs
python3 eval/r13_probe.py offline
python3 eval/spatial_replay.py rerender eval/phase2/R12_staged_search/runs   # 862, 0 differ
python3 eval/spatial_replay.py rerender eval/phase2/R11_goal_default/runs    # 706, 0 differ
```

## Shakedown

One unscored `dynamic` run per site per agent on the flight host: `/health` reports `a20`'s and
`a21`'s shas; every record carries `stage` (with `vantage`, `verify_since`) and `evaluator`; at
least one `goal_lost` episode reaches a check look; no run passes 700 s.

## Host

sctsvr6 headless (Docker, Mesa lavapipe), as R7–R12. R13 and R13G fly at one SHA, 4 lanes each
(8 in all); if the host strains, 4 lanes, R13 first. The tunnel is the operator's.

## Builds on

- R12 (`a19`): perceiver, map, menu, evaluator, strategist; the goal stage's belief.
- R11 (`a16`): the "nearer the goal" wording (R13G only).

## Outcome

Not flown.
