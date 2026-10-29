# s03 (tuning fork): why the known-goal agents fail

Written 2026-10-29 by a Claude subagent as a read-only analysis. No model calls were made and no
labels were changed. Throwaway scripts (not in the repo) replayed `decisions.jsonl` through
`server/decider/spatial.py` (`rebuild` + `project`). The replay reproduces the recorded tags on all
876 known-goal s03 steps. Geometry is from `R11_goal_default/analysis/geo.py`: `final` has door L
(y<0) closed, `dynamic` is open until the first tine is crossed.

Regions: lobby x≥15, stem 8≤x<15, crossbar ("xbar") 5≤x<8, tines −6≤x<5, exit wall x∈[−7,−6],
chamber x<−7. Goal (−12, 0), start (21, 0.17) facing the stem.

## 1. Per round

Columns: steps per region; the first step reached in stem→xbar→tine; TAs is turn-arounds, with
those against a forward "toward your target" in brackets.

**R11 (a16, 2/3).**

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | reached s38 | 0.6 | chamber | 4 | 4 | 9 | 18 (R) | 4→8→17 | 5 (0) |
| final | reached s38 | 0.6 | chamber | 4 | 4 | 9 | 18 (R) | 4→8→17 | 5 (0) |
| dynamic | fail | 8.3 | tine L | 4 | 4 | 14 | 33 (L) | 4→8→22 | 17 (0) |

**R15 (a25, 1/3).**

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | reached s35 | 0.2 | chamber | 4 | 9 | 11 | 7 (L) | 4→13→24 | 5 (2) |
| final | fail | 27.3 | lobby | 54 | 6 | 0 | 0 | 4→–→– | 13 (5) |
| dynamic | fail | 19.4 | xbar | 21 | 27 | 12 | 0 | 4→35→– | 16 (6) |

**R15N (a26, 0/3).**

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | fail | 8.1 | tine L | 35 | 6 | 6 | 13 (L) | 33→41→47 | 11 (6) |
| final | fail | 7.2 | exit (closed L) | 4 | 12 | 29 | 14 (L) | 4→16→45 | 18 (5) |
| dynamic | fail | 19.5 | xbar | 26 | 9 | 23 | 2 (R) | 4→33→46 | 19 (8) |

**R16 (a27, 0/3).** This agent searches for an unknown goal, so it is not a known-goal agent.

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | fail | 33.0 | lobby | 60 | 0 | 0 | 0 | – | 13 (7) |
| final | fail | 32.6 | lobby | 60 | 0 | 0 | 0 | – | 15 (7) |
| dynamic | fail | 31.0 | lobby | 53 | 7 | 0 | 0 | 4→–→– | 10 (5) |

**R16K (a28, 0/3).**

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | fail | 19.9 | xbar | 48 | 6 | 6 | 0 | 4→54→– | 14 (9) |
| final | fail | 18.0 | xbar | 35 | 7 | 18 | 0 | 16→42→– | 13 (5) |
| dynamic | fail | 36.6 | lobby | 42 | 18 | 0 | 0 | 17→–→– | 15 (3) |

**R17 (a31, 0/3).**

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | fail | 13.5 | tine L | 21 | 16 | 16 | 7 (L) | 21→37→53 | 16 (5) |
| final | fail | 23.8 | stem | 29 | 21 | 10 | 0 | 29→33→– | 13 (8) |
| dynamic | fail | 27.9 | lobby | 55 | 5 | 0 | 0 | 8→–→– | 16 (10) |

**R17K (a32, 0/3).**

| arm | result | end dg | ends in | lobby | stem | xbar | tine | stem→xbar→tine | TAs |
|---|---|---|---|---|---|---|---|---|---|
| initial | fail | 29.6 | lobby | 54 | 6 | 0 | 0 | 19→–→– | 16 (9) |
| final | fail | 7.7 | tine L (closed) | 35 | 10 | 9 | 6 (L) | 21→43→54 | 9 (6) |
| dynamic | fail | 7.6 | tine L | 34 | 8 | 11 | 7 (L) | 34→38→53 | 11 (6) |

**Known-goal runs together** (R15, R15N, R16K, R17, R17K: 15 runs, 876 steps):

| | known-goal runs | R11 |
|---|---|---|
| steps in the lobby | 497 (57%) | 12 of 159 |
| reached the crossbar | 11/15, median first step 37 (13–54) | step 8 in all 3 |
| entered a tine | 7/15 (6 into tine L, 1 into R for 2 steps) | 3/3 |
| reached the exit wall (x ≤ −5.5) | 2/15 | 2/3 |
| reached the chamber | 1/15 | 2/3 |

Where the 15 runs end:

| region | runs |
|---|---|
| lobby | 4 |
| stem | 1 |
| crossbar | 4 |
| tine L | 4 |
| exit (closed L) | 1 |
| chamber (win) | 1 |

Both wins in this set needed 23–30 steps from first reaching the crossbar to the goal (R15
initial 13→35; R11 8→38). A run that reaches the crossbar after about step 30 cannot finish.
Three runs ran out of steps in tine L with dg 7.6–13.5: R17 initial, R17K final and R17K dynamic.

## 2. Failure mechanism

### Stage 1 (dominant): a false "searched already this way" turns the drone around at the start

The first turn-around of every one of the 15 known-goal runs came in the same situation:
- step 0–7, at x 9–21, facing the stem;
- the perceiver read the floor ending at the bottom of every strip (`nnnnn`);
- straight was tagged "toward your target; searched already this way";
- straight was truly free for 4.1–12 m. In 13 of the 15 it was 9–12 m, down the lobby axis or the
  stem.

Examples:
- R17K initial s0 and R16K final s0: at the spawn.
- R17 initial/final/dynamic s1, R17K final/dynamic s1, R16K dynamic s1 and R15N initial s1: at
  (19.3, 0.2), 12 m free.
- R15 final/dynamic s4, R15N dynamic s4 and R16K initial s4: at the stem mouth (14.2, 0.4), 9.2 m
  free.

The navigator's reason is the same every time: "All available forward directions … have been
searched already … turning around is the only way to explore new ground". It is quoted here from
R17 initial s1.

**Where the note comes from.**
1. g05 answers `bottom` for a strip, and the agent's `floor_map` turns that into `open_near`.
2. a17's `_observe_cone` gives `open_near` a 2 m reach. Because `open_near` is in
   `PARAMS_A17["floor_ends"]`, it also writes a **wall cell at 2.5 m** at the end of each ray.
3. `_unsearched_ahead` looks 4 m past the move's landing point. It hits that wall and returns
   False, so the move gets "searched already this way" instead of "new ground".

R14 moved `bottom` from `blocked_near` to `open_near` because it is almost never a wall: 3.0% of
1574 strips are blocked within 1.9 m. The move left the wall-writing in place, 2.5 m out instead
of 0.75 m.

On s03 the `open_near` reads are mostly false:
- in the lobby, 735 of 1026 are truly clear for 5 m or more, and 70 are blocked within 2.5 m;
- in the stem, 101 of 226 are clear for 5 m or more.

**Replay** (the same states and tags, with `open_near` removed from `floor_ends`):

| measure (15 runs) | recorded | without the open_near wall |
|---|---|---|
| forward moves tagged "searched already" | 1410 | 412 |
| "toward" forward moves tagged "searched already" | 279 | 84 |
| steps with no forward "new ground" | 409 | 201 |
| first turn-arounds whose straight move becomes "toward; new ground" | – | **15/15** |

The planner's `walled` verdict is unchanged (78 and 78), so the change touches only the coverage
note and the frontiers.

- **Turn-arounds against a forward "toward".** There were 93 in the 15 runs (R11: 0). In 74 of
  them the toward move carried "searched already" and had 2.2 m or more of true free floor: 54 in
  the lobby, 12 in the stem, 8 at the crossbar.
- **After the turn-around.** The drone faces east in a 9×23 m lobby whose only exit is a 3 m stem
  mouth. "Toward" (sharp right or left back to the west) then lands it on the x=15 wall off the
  stem axis at y = ±3–7. That wall had 25 walled or blocked detour calls.
  - The strategist's picks there are lobby frontiers 2–5 m away. They are reached in 1–4 steps and
    hand back to a goal straight through the wall (lobby: 49 calls, mean 4.3 steps held, net
    −4.1 m).
  - This is mode B (no search along the wall) in front of the stem.
  - R16 (a27) shows the same note: 74 toward moves tagged "searched", 39 without the wall.
    It spent 173 of 180 steps in the lobby.

### Stage 2: the crossbar T-junction (mode H)

The drone reaches the crossbar facing the wall at x=5 between the tines (y ∈ [−3.5, 3.5]). The
tines are out of view, so they are not on the menu. There were 28 strategist calls there:
- 11 `explore`, with no target (held 1 step);
- 15 frontiers, mostly 1–3 m away, reached in about 2 steps (`detour_reached`). The goal is then
  straight into the wall again.
- Examples:
  - R17K final s44 picked `doorway_D` (7.93, 0.33), which is the stem mouth behind it.
  - R17K dynamic s39/s48/s50 picked frontiers 1–2 m away, each reached in 1–2 steps.
  - R17 final s44 picked `unexplored_1` (20.82, 4.67), 15 m back in the lobby (q07's "more ground
    first").

Mean time held at the crossbar was 3.0 steps. Crossbar time per run was 6–29 steps (mean 14).

The only two crossbar picks that carried the drone into a tine were frontier cells at x=4.67 on
the wall face, which cannot be reached, so the planner never hands them back:
- R15 initial s21: `unexplored_2` (4.67, −1.27), held 8 steps, +7.0 m. This led to the win.
- R17 initial s49: `unexplored_1` (4.67, −2.12), held 11 steps, +6.8 m.

**What R11 did.** At its crossbar block (s10, (5.2, 0.8)), q03 took `unexplored_1` (−0.42, 1.27).
That target is a phantom inside the solid block between the tines.
- No reachability check, so it was held 10 steps.
- a16's wall-aware "toward" slid the drone along the wall into tine R (s17) and down it.
- The hand-back came at s20 (goal_in_view).
- At the exit wall (s25), a second phantom (−10.62, 1.27) in the chamber held 10 steps and led it
  through the R door.

In short, R11 had a target that stays put on the far side of the wall. The new agents' reachable
detours end in 1–3 steps, and the drone walks back into the wall.

### Stage 3: tine side and dead ends

6 of the 7 tine entries were into **L**:
- The drone drifts to y≈+0.4…+1.3 down the stem (spawn y=+0.17), so the goal is slightly right of
  it.
- At the crossbar, "toward" is the right-hand move, which leads to tine L.
- L is the closed door in `final` and the slamming one in `dynamic` when it is the first tine
  crossed.
- R15N final s54–57 picked the closed door (`doorway_G`) three times and never backed out.

R11 went R only because its phantom sat at y=+1.27.

## 3. Would R21's along-the-wall items (a39/a40) help at the crossbar?

Mostly yes, with two limits. Method: `planner.along_wall` on the rebuilt memory at every recorded
detour call (the r21_along_probe `items` approach, restricted to s03), joined with R21's live q08
answers (`R21_along_wall/probe/q08_answers.jsonl`, which covers R15, R15N and R16K).

**At the crossbar wall** (x<6.6, |y|<3.5; 21 calls in 10 runs):
- The calls produced 34 items. 30 are clear on true floor, and 27 end at |y| ≥ 3, the tine mouths.
- Examples: R17K dynamic s39 gives (5.8, −5.6) and (6.2, 4.4); R16K initial s55 gives
  (5.5, ±4.9 or 5.1).
- q08 took an along item at **14 of 15** crossbar-wall calls.
  - 9 of those 14 end inside a tine mouth on clear floor, 3 end 0.5–0.7 m short (|y| 2.8–3.0) and
    2 end on a wall.
  - The sides split 7 L and 7 R.
- The hand-back rule helps here. At the tine mouth the heading is ±90° and the goal is about 180°,
  so the item is held to its end rather than handed back after 2 steps. "Toward" then points down
  the tine. This replaces the R11 phantom with a target that is real and reachable.

**At the lobby wall** (x=15, off the stem axis): q08 took along items at 11 of 12 calls, but only 4
of them pass the stem mouth. It is a coin flip there.

**The limits.**
1. On s03 the drone usually reaches the crossbar too late (median step 37). Along items cannot
   help a run that spends 21–55 steps in the lobby.
2. In `final`, the 50/50 side choice means about half the runs reach the closed L door first.
   They need q08's "follow one side to its end, then the other" and d01 (in a40) to drop the
   closed door. That costs about 15 more steps.

## 4. Proposed changes (ranked)

### 1. Stop writing a wall at the end of an `open_near` (g05 `bottom`) strip

**The change (code).** Use `floor_ends = ["blocked_near", "wall_far"]` in a new memory variant, for
example `a17b`, set through the agent's features so a17's sha and every flown agent stay as they
are. Put it on R21's a40/a41.

**Code is clearly better than a prompt here.**
- The false note is produced by code from a class that R14 already showed is a wall 3% of the time.
- p17 (queued in R19–R21) only asks the navigator to discount it. Its probe moved "toward"
  only from 23% to 55% on the recorded turn-around steps.
- The note also stays on 1193 "toward" moves across all sites of the 5 rounds, and it shapes the
  frontier menus.

**Evidence.**
- 15/15 first turn-arounds flip to "toward; new ground". "Toward" moves tagged "searched" on s03
  drop from 279 to 84.
- Across all sites (4004 steps of R15–R17K), steps with no forward "new ground" fall from 1550
  (39%) to 815 (20%). R11 was about 15%.
- Safety: "new ground" on a forward move truly blocked within 1.9 m stays at about the same rate,
  461/7502 (6.1%) against 749/11550 (6.5%). "Toward" on a truly blocked move is unchanged (278).
- With a straight stem run, the agent reaches the crossbar at about step 8, as R11 does. That
  leaves about 50 steps for stages 2 and 3, where the wins needed 23–30.

**Offline test before flying.**
1. Replay R15–R17K into the new memory, with no model, and gate on:
   - s03 "toward" moves tagged "searched" ≤ 100;
   - all 15 first turn-around steps carry "new ground" on straight;
   - the all-site blocked-but-"new ground" rate ≤ 7%.
2. Then a live text+frame navigator replay in the `r19_nav_probe` style, with the action lines
   re-rendered from the new tags at the 74 turn-around steps (p17). Gate: the toward move is
   picked on at least 75%.

### 2. Fly a40/a41 (along-the-wall + d01) with change 1 folded in

On its own, along-the-wall rarely gets a chance on s03, because the drone reaches the crossbar
late. Together with change 1 it is the mechanism that replaces R11's phantom at the crossbar. The
evidence is in §3: q08 picks along at 14 of 15 crossbar-wall calls, and 9 of those items end in a
tine mouth on clear floor.

**Offline test.** Add an s03 crossbar check to `r21_along_probe.py items`: for calls with the drone
within 1.6 m of the x=5 wall face and |y|<3.5, the share of items that end with
5≤x<8 and 3.5≤|y|≤6.5 and a clear segment. It is 27/34 at |y|≥3 today; the gate is ≥ 80% at ≥3.5.
Two cheap wording or geometry tweaks would lift it:
- let items run 0.5 m past the 5 m cap;
- end them at the side opening, not at `max_m`.

### 3. Dead-end exit (final/dynamic only)

The goal is to back out of a tine whose exit is closed rather than re-pick the closed door. d01 is
already in a40. What is still missing is a closed-door read at the exit wall feeding q08's "the
other side" item.

**Offline test.** Run `r20_door_probe` on the R15N final s54–57 and R17K final s59 frames. The gate
is that the closed door is refused.

This matters only once changes 1 and 2 bring the drone to a tine end with steps left. Note also
that the stem-drift bias sends about 6 in 7 known-goal runs into L, the closed side in `final`.
