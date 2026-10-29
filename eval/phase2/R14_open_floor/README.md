# R14: R13 with g05's floor read as open (a22; R14G flies a23 beside it)

**Agent:** `a22` (`3745a8728248`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) ·
**Perceiver:** `g05` · **Strategist:** `q04` · **Spatial memory:** `spatial.A17` ·
**Stage machine:** `planner_a17` + verify `planner_a20` (as `a20`) ·
**Status:** pre-registered 2026-10-29, built overnight without the operator (operator, 2026-10-28:
"fix any issues found in probing, any loops any errors and whatnot, then fly the agent ... DO NOT
WAIT FOR MY APPROVAL").

Second agent at the same SHA: **R14G**, `a23` (`5bbb755c939f`) = `a21` (goal truth in the
strategist's text) with the same two changes; [R14G's README](../R14G_open_floor_goal_words/README.md).

## Change against `a20` (R13)

| | `a20` | `a22` |
|---|---|---|
| g05 floor end → floor class | `no_floor`, `bottom` → `blocked_near`; `lower` → `open_near`; `middle` → `open_far` (`a19`'s) | `no_floor` → `blocked_near`; `bottom` → `open_near`; `lower`, `middle` → `open_far` (`a18`'s, probed in R12, never flown) |
| verify step limit | 8 | `max(8, ceil(4 + 0.8 × metres back))`, set when verify begins (feature `verify_budget`; recorded as `stage.verify_budget`) |

Everything else is `a20`'s. `a00`–`a21`'s shas are unchanged (checked); `a20`/`a21` never pass the
new budget argument, so their decisions are as before.

## Evidence

**g05's "bottom" is not a wall.** Every strip g05 answered in R12's 862 recorded steps, scored
against the site model (`analysis/geo.py`, true clear distance along the strip's centre ray;
[probe/floor_confusion_R12.txt](probe/floor_confusion_R12.txt), `eval/r14_floor_confusion.py`):

| g05 floor end | strips | truly blocked within 1.9 m (a 1.7 m move fails) | clear past 8 m |
|---|---|---|---|
| `no_floor` | 477 | 48.4% | 33% |
| `bottom` | 1574 | **3.0%** | 62% |
| `lower` | 526 | 6.5% | 57% |
| `middle` | 1733 | 1.1% | 76% |

`a19`/`a20` wall a `bottom` strip 0.75 m out, so 37% of all strips put "wall close (seen now)" on a
move that was open. That fits R12's "stayed within 6–18 m of its start, 12–35 turn-arounds a run"
and R13's shakedown ping-pong (three of six verify timeouts: the drone turned around on the way back
to its vantage, eight times in a row in s02va, over ground it had just flown). The other three
timeouts were trips back of 5–9 m that ran past 8 steps.

The camera is level at 1.75 m, so the floor is first visible 1.84 m out: floor at the bottom of a
strip means nothing stands within 1.84 m, more than a 1.7 m move. `a18`'s probe gate (walls under
1 m read open < 15%) failed narrowly at 16.2%; that gate measured the coverage map, not whether the
drone can move. The operator's aim is performance, so mobility wins here; a stopped-short move
still writes a stop wall (`a17` memory).

## Hypothesis

With walls that were never there gone, the drone leaves its start area and the verify stage gets
back to its vantage instead of ping-ponging, so `final` and `dynamic` rise above R12 and R13.

## Predictions

| Measure | R11 (`a16`) | R12 (`a19`) | R14 / R14G |
|---|---|---|---|
| total | 11/18 | 5/18 | above R13/R13G and R12 |
| strips read `blocked_near` | 8–36% (g03) | 39–67% | ≤ 20% |
| distance from start, max per run | 13–32 m | 6–18 m | median ≥ 13 m |
| turn-arounds per run | 1–17 | 12–35 | median ≤ 12 |
| verify episodes ending in timeout | | (R13 shakedown 6/18) | ≤ 1/4 |
| collisions | | | may rise; reported |

## Manipulation check

From the records: share of strips with `floor` `blocked_near`; `stage.verify_budget` on every verify
episode; turn-arounds and max distance from start per run.

## Drop criterion

Not carried forward if it does not beat the better of R13/R13G. One that beats R11's 11/18 becomes
the agent to build on.

## Probe gate

1. Transitions (`eval/r13_probe.py transitions`): PASS ([probe/transitions.txt](probe/transitions.txt)).
2. Smoke, `a22`/`a23` on R12's 862 manifests with stub replies: 0 failed steps; `a22` the same with
   and without the goal block; `a23` the same apart from strategist text; goal position in every
   `a23` strategist text and no navigator text ([probe/smoke.txt](probe/smoke.txt)).
3. Floor confusion, above (reported).

```
python3 eval/r13_probe.py transitions
python3 eval/r13_probe.py smoke eval/phase2/R12_staged_search/runs --agents a22 a23
python3 eval/r14_floor_confusion.py eval/phase2/R12_staged_search/runs
```

## Builds on

R13 (`a20`) and R13G (`a21`); `a18`'s floor map (R12 probe).

## Host

sctsvr6, 8 lanes (4 per agent); all model calls go to the existing vLLM on :8004 (3 H100s; the
operator's limit is 4). The tunnel is the operator's.

## Outcome

Flown 2026-10-29 03:05–03:49 UTC, 4 lanes, 18/18 valid. **7/18**: `initial` 5/6 (s03 failed),
`final` 1/6 (s02vc, 57 steps), `dynamic` 1/6 (s02c, 43 steps). R13 6/18, R13G 5/18, R12 5/18,
R11 11/18.

| Measure | R13 (`a20`) | R14 (`a22`) | predicted |
|---|---|---|---|
| total | 6/18 | 7/18 | above R13/R13G: **held, by one run** |
| strips read `blocked_near`, median per run | 48% | 13% | ≤ 20%: held |
| turn-arounds per run, median | 18 | 8 | ≤ 12: held |
| max distance from start, median | 18.1 m | 15.0 m | ≥ 13 m: held |
| losses of sight → reacquired / failed / timeout | 15 → 1 / 8 / 4 | 10 → 2 / 4 / 3 | timeout ≤ 1/4: not held (3/9) |

Per run: [manipulation.txt](manipulation.txt) (`eval/round_manipulation.py`). Stages over all steps:
explore 657, goal 135, verify 48 (R13: 646 / 163 / 72).

The floor fix took: walls that were never there are gone, the drone turns round half as often,
and it loses sight of the goal less. The score barely moved. s03 failed in every arm (12–13 m
from start at most, 13–15 turn-arounds); `final`/`dynamic` stay at 1/6 each. Carried forward
as the no-truth base (R16, `a27`), not as the best agent: R11 (11/18, goal truth) stays ahead.
