# R11 evidence: what R10's memory, planner and wording did

Written 2026-10-25 from R10 (`a14`), R10C (`a13`) and R9 (`a13`) records, before any R11 code.
It answers three questions from the operator: how well the memory works, where the agent can take
more abstraction and more subagents, and how and when to keep information from a part of it. The
R11 design that follows from it is in [README.md](README.md).

Every number comes from one of these, run at this branch's tip (evaluation only: the audit reads
the manifest's goal ground truth, the agent never does):

    python eval/spatial_replay.py audit eval/phase2/R10_goal_planner/runs
    python eval/spatial_replay.py audit eval/phase2/R10C_a13_control/runs
    python eval/spatial_replay.py audit eval/phase2/R9_hail_mary/runs
    python eval/spatial_replay.py manip eval/phase2/R10_goal_planner/runs

The audit prints the same JSON on every run. "Lift" is picks divided by the picks expected if the
navigator chose uniformly among the actions it was offered (hidden [0] excluded).

## 1. The memory

R10 has 755 decided steps (R10C 899, R9 871). The memory is `server/decider/spatial.py`, rebuilt
from `decisions.jsonl` each step; the navigator sees it only as notes against each action
(`project`, spatial.py:619) and the recent-moves line (`orchestrator.recent_moves`).

### 1.1 What works

**Notes that say "don't" are obeyed.** In R10:

| Note | Offered | Picked | Lift |
|---|---|---|---|
| goal about one move ahead | 104 | 104 | 5.95 |
| goal this way (seen now) | 63 | 62 | 5.89 |
| toward your target | 590 | 339 | 3.41 |
| doorway (seen now) | 498 | 209 | 2.49 |
| new ground | 2,937 | 594 | 1.20 |
| been there N times | 393 | 36 | 0.51 |
| behind you is ground you have covered | 645 | 55 | 0.51 |
| wall close (seen now) | 419 | 15 | 0.21 |
| blocked here before | 15 | 0 | 0 |
| stopped short here before | 8 | 0 | 0 |

R10C and R9 give the same picture (blocked picked 2 of 32 and 0 of 14; been there lift 0.50 and
0.46).

**Loops are gone.** Steps with loop score ≥ 0.5: R10 16, R10C 108, R9 61. Revisit rate 0.10
(R10C 0.16), longest run of turn-arounds 1 (R10C 12). Part of this is the turn rule, not the map.

### 1.2 What does not

**a. Block memory almost never warns about the collision that follows a collision.** R10 has 28
moves that stopped short. 9 started within 2 m and 45° of an earlier block, and none of the 9
carried a "blocked" or "stopped short" note. R10C: 19 of 20 un-noted; R9: 8 of 8. Over three rounds
36 of 37 near-repeat collisions had no warning. Two causes in `spatial.py`:
- `SpatialMemory.move` (291) stores the block at the pose the move *started* from. A move that
  stops short leaves the drone up to 1.5 m forward, and `block_for` (375) only matches within
  `BLOCK_NEAR_M` = 0.85 m. So the next decision, made at the wall, is outside the match radius.
- `BLOCK_WITHIN_DEG` = 15° is under the fan's 21.75° spacing, so a block on "straight" never
  warns "slight left" into the same wall.

The negative notes are obeyed but fire on 23 of 755 steps: the navigator's best-obeyed signal is
the one the memory gives least.

**b. "toward your target" is drawn from bearing alone.** `project` (619–642) puts it on the
forward action nearest the target's bearing, or on the turn-around when the target is behind,
without reading the other notes. In R10 it shared an action with "wall close", "blocked" or
"stopped short" 36 times; that action was picked 12 times and stopped short 4 times (R10C 44 / 21 /
7, R9 33 / 16 / 10). On the turn-around it is followed 38 of 132 times (forward 301 of 458).
Example: s03 `final` step 16, every forward move "wall close (seen now)" and [3] also "toward your
target"; the navigator reasoned "the straight path is noted as 'toward your target'" and moved
0.01 m.

**c. "new ground" says little.** It sits on 2,937 of the offered actions (3.9 a step), lift 1.20,
and is on 24 of the picks that stopped short. It cannot separate options when nearly every option
has it.

**d. The goal estimate (`a13`) is not usable, and range is why.** With no truth, the goal target is
`goal_belief` (388). R10C: median error 14.9 m, mean 17.4 m, within 2 m on 39 of 814 steps; the
median error is 0.88 of the drone's true distance to the goal (R9: 15.0 m, 0.85). The perceiver's
*direction* is good: goal strip within about 5° of the true bearing (median 5.2° R10, 5.0° R10C,
4.1° R9). Its *distance class* is not:

| Perceiver says | Map assumes (`GOAL_RANGE_M`) | True distance, median (R10 / R10C / R9) | n (R10) |
|---|---|---|---|
| touching | 1 m | 5.7 / 5.4 / 6.6 m | 62 |
| near | 4 m | 18.9 / 20.1 / 20.6 m | 61 |
| mid | 10 m | 16.3 / 16.7 / 16.7 m | 8 |
| far | 18 m | 20.6 / 20.6 / 20.6 m | 13 |

"near" is said most and means about 19 m. The classes do not order the distances. Any memory built
on the range class inherits this error; bearings alone are sound.

**e. Doorways stay on the menu long after they matter.** Age of doorway entries in the
strategist's menu: R10 median 4 steps, 123 of 417 over 10, oldest 54 (R10C median 10, 349 of 708
over 10). A doorway is struck only when the trail comes within 1.5 m (`settle`, 367) or a look
straight at it sees the floor end short (`_close_openings`, 355). Every doorway enters on one
sighting (`_add_opening`, 344), and "a new doorway is in view" is the strategist's most common
trigger (§2).

**f. Prompt size is not a problem.** Navigator text mean 553 characters (max 711), strategist
669 (max 1,095).

### 1.3 Did the memory have what the failures needed?

In each of R10's 7 failures the facts that would have kept the drone on course were in the
record: the goal's true position (on every strategist call), the visited cells, the open moves.
They were overridden by the strategist or misread by the navigator. The exception is §1.2a:
near-repeat collisions with no note (s03 `initial`/`dynamic` steps 48–49).
- s01 `final` step 50: the drone was flying straight at the goal, 26 m off. The strategist was
  asked because its target was reached; `q02` reasoned "the goal is known to be 26 meters ahead …
  since it is not visible, it may be obstructed" and chose explore. The navigator read "all forward
  directions (1–5) are blocked by walls" off a list where [3] had only "been there 1 time", turned
  around, and the run ended 34.8 m from the goal.
- s02va `final`: 21 strategist calls, 12 doorways; the goal was chosen at step 30 and dropped at 31
  for a new doorway.
- s02vc `final`: the last target was doorway C, first seen at step 1, chosen on a loop trigger.

**Verdict.** The memory is a good *negative* signal (what not to do), and it stopped loops. It is
a weak *positive* signal: "new ground" is everywhere, "toward" ignores walls, and the goal estimate
was wrong until R10 replaced it with the truth. Its blind spot is the most common collision, the
one straight after a collision.

## 2. The strategist

R10's strategist (`q02`) is told the goal's true position on every call and still chooses it on
70 of 229 (doorway 78, unexplored ground 54, explore 22, backtrack 5). What each standing target
did to the drone's distance from the goal, per step:

| Standing target | R10 steps | Goal gained per step (R10 / R10C / R9) |
|---|---|---|
| goal | 232 | +0.92 / +1.02 / +1.02 m |
| doorway | 171 | +0.95 / +0.62 / +0.84 m |
| unexplored ground | 208 | +0.14 / 0.00 / −0.17 m |
| backtrack | 21 | −0.34 / −0.09 / −0.08 m |
| none (explore) | 123 | −0.42 / −0.16 / −0.05 m |

Doorways do as well as the goal; unexplored ground, backtrack and explore do not move the drone
toward the goal. 352 of R10's 755 steps (47%) stood on one of those three.

**Why it leaves the goal.** Of the 159 calls that did not choose the goal, 157 give a reason that
mentions a wall, a block, an obstruction or the goal not being visible. Two lines of the
strategist's text (`spatial.situation`, 719) feed that:
- "The goal is not in the current image." (166 of 229 calls). With the position known, this line
  carries nothing the strategist can use, and it reads it as "a wall is in the way" (s01 `final`
  step 50 above; s03 `final` step 28 "not currently visible, suggesting an obstruction").
- "You have been within 2 m of this spot for N of the last 10 steps." (53 calls), read as "stuck":
  s01 `final` step 8 "previous moves toward the goal have been blocked", when the only block from
  there was behind.

**It is asked too often, mostly by doorways.** Triggers: a new doorway is in view 81 (35%), the
doorway you chose is closed or already passed 30, a regular check 25, the goal came into view 22,
out of view 21, start 18, target reached 16, blocked 13, loop 3. 162 target changes in 755 steps.
R10C's single "reached or no longer open" sentence fired 142 times; splitting it cut the calls
from 40% to 30% of steps.

## 3. When to keep information from a part of the agent

Phase 2 has tested this question many times without naming it:

| Round | Shown to the model | What happened |
|---|---|---|
| R0 (`a00`) | goal distance and bearing | followed the bearing into walls (`final` + `dynamic` 0/30) |
| R2 (`a02`) | its own full history | locked onto one marker within 10 steps, 596 collisions |
| R5 probe (`g01`) | annotated frame to the identifier | took the "0 TURN AROUND" marker for the goal |
| R6–R8 | ground-truth pose, degrees | heading arithmetic that turned it away from a goal in view |
| R9 (`a13`) | critic's note "memory says …" | changed 0 of 19 picks |
| R9 (`a13`) | goal estimate as a target | estimate 15 m off; `q01` distrusted it |
| R10 (`a14`) | truth to the planner only; [0] hidden after a turn-around | no spins; no pick named the hidden [0] |

From this, rules for what each part sees, in order of how often they have been tested:

- **O1. Verdicts, not data.** No model gets coordinates or degrees. Code compares positions; the
  model gets the verdict on the action it applies to (R6–R9).
- **O2. Each part sees what it can act on.** Perceiver: the clean frame, nothing else. Strategist:
  the goal's position and a summary of the map, in distances and eight directions. Navigator: the
  annotated frame and one note per fact per action; the target only as "toward your target".
- **O3. Remove a line a part has been seen to misread, once code holds the fact it stood for.**
  With the goal's position known, "the goal is not in the current image" and "within 2 m of this
  spot" no longer tell the strategist anything it needs, and it misreads both (§2). Loops reach it
  as the loop trigger.
- **O4. Do not show memory less accurate than the model's own guess.** The goal estimate's range
  is wrong by a factor of four or more (§1.2d). A part without the truth should get the goal as a
  direction, not a distance.
- **O5. Code resolves conflicts before the model sees them.** No action carries "toward your
  target" and "wall close" together (§1.2b). When the two disagree, code decides.
- **O6. Leaving an action off is the last resort.** It is the only cue that has changed behaviour
  every time (R10: [0] left off 65 times, never asked for), and also the one that takes a choice
  away. Use it only for a failure that has been measured and only when code is certain (the
  operator's reservation on the R10 turn rule stands).
- **O7. Privileged information is kept in by construction, and checked.** The goal's truth enters
  the agent in one place (`orchestrator.goal_at`) and must reach only the parts allowed it. Today
  that is kept by which function gets the `goal_at` argument. A role's view should be built from an
  allowlist and every rendered text scanned in the manipulation check (R10 already checks that no
  navigator text gives the goal a distance or direction).

**When.** O3 and O4 depend on the state of the run: a line is shown while it carries something
code does not already hold, and dropped once it doesn't. In `a14` the strategist still gets "not
in the image" after the truth made it redundant. In an agent without the truth, a bearing is still
the best goal cue it has.

**The goal's truth beyond the strategist (operator, 2026-10-26).** R10 gives it to `q02`'s prompt
only. Decided: code on the planner side may use it as well (keep the goal as the default target,
score detours by how much nearer the goal they lie, and spot a lack of progress), and it stays out
of every text the navigator and perceiver see. Every R11 part in [README.md](README.md) that
needs this is marked "truth".

## 4. More abstraction

`orchestrator.decide` (183–314) runs the five parts in a fixed order, and every round adds a flag
read inside it (`goal_truth`, `turn_rule`, `critic`). `spatial.py` takes `goal_at=` and `words=`
arguments in several functions and keeps two wording tables (`WORDS`, `WORDS_A14`) that `agent.sha`
joins by hand. Each new agent makes both longer. Proposed for R11's implementation:

- **Stage.** A part of a step is a `Stage`: its name, its prompt version, a view builder, its schema
  and validator, its token budget, the key it is recorded under, and when it runs (every step, or a
  trigger). An agent is a list of stages; the orchestrator runs the list. Code parts (mapper,
  projector, route planner, progress monitor) are stages with no model call.
- **RoleView.** Each model stage gets its input from a view built from an allowlist of what that role
  may see (O2, O7). The manipulation check scans each recorded text against the other roles'
  allowlists.
- **SpatialConfig.** The memory's parameters and wording as one object per agent, passed to
  `rebuild`, `project`, `targets`, `situation` and `trigger`, and hashed into `agent_sha`. For `a13`
  and `a14` it must hash the same blob `agent.sha()` builds today (`spatial:` + `wording_sha()`, and
  `spatial_a14:` + `wording_sha_a14()`), so both keep their shas.
- **TargetPolicy.** Who chooses the target: `llm_strategist` (`a13`, `a14`) or
  `goal_default_llm_detour` (`a15`, §5).
- **Note rules.** `project` as an ordered list of rules, so a rule can read the notes before it
  (the wall-aware "toward" in §5 needs this).

Constraint: the refactor ships only if every R9, R10 and R10C decision re-renders byte for byte (as
R10 checked for R9: navigator text, notes, strategist trigger and text) and `a13`/`a14` keep their
shas (`eval/phase2.py init` lock check).

## 5. More subagents

| Part | Kind | Does | Answers |
|---|---|---|---|
| Route planner | code, truth | keeps the goal as the standing target; hands over to the detour strategist only when the move toward it is walled or was blocked in the last 3 steps | §2: goal and doorway targets gain ~0.9 m a step, the rest ≤ 0.14 m |
| Detour strategist (`q03`) | model, text | asked only for a detour; each target worded with how much nearer the goal it lies; no "not in the image" or "within 2 m" lines | §2, O3 |
| Progress monitor | code, truth | no goal-distance gain over 6 steps → ask the detour strategist (replaces the critic) | R9 critic 0/19 |
| Doorway gate | code | a doorway enters the menu and the trigger only on its second sighting, and leaves after 10 steps without one | §1.2e; one perceiver answer can change a whole re-fly (R10C) |
| Block memory fix | code | a block is also recorded where the move ended, and matched on the landing cell; adjacent fan actions get the note too | §1.2a |
| Wall-aware toward | code | "toward your target" never on an action with a wall, blocked or stopped-short note; the next open action within ~55° instead, or none | §1.2b, O5 |

Not recommended: a model that writes a running summary of the run for the others to read. R2 gave
the model its own history and it repeated itself (1/18).

Fewer model calls per step should also help the run-to-run noise: `a13` makes two to four calls a
step and re-flying it unchanged moved 3 of 18 outcomes (R10C), where single-call `a11` moved none
(R9C). The route planner takes the strategist off most steps.
