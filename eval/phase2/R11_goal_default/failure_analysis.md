# R11 (a16) failure analysis: reasoning and failure modes

Written 2026-10-28 by a Claude subagent, after the labels were confirmed, as a read-only analysis
of `eval/phase2/R11_goal_default` against `R11C_a14_control` from the recorded `decisions.jsonl`
and `steps.jsonl` (no model calls). It is analysis, not pre-registration: nothing here changes a
label or R11's result. Summary: [summary.md](summary.md); manipulation check:
[manipulation_check.md](manipulation_check.md).

**Conventions.** Steps are the 0-based `step` of `decisions.jsonl`. Map coordinates are the
memory's: x = world x, y = −world z. On the s02 sites the divider is x ∈ [−0.5, 0.5], door A is at
y = +9, B at y = 0 and C at y = −9, each with a gap |y − yd| < 1.2. "gb" is the goal's true bearing
relative to the heading, with left positive. The ground truth comes from a 2D model of each site that
was built from the site READMEs and `room.tscn` (`analysis/geo.py`). It predicts 53 of the 57 R11
stopped-short moves, which is good enough for counting but not exact. **Observed** means read from
the records. **Inferred** marks the analyst's interpretation.

Scripts are in [analysis/](analysis/), run from the repo root, e.g.
`python3 eval/phase2/R11_goal_default/analysis/decomp.py`: `tl.py` (timelines, loaders), `geo.py`
(site geometry), `val.py`, `strat.py`, `phantom.py`, `perc.py`, `nav.py`, `nav2.py`, `behind.py`,
`decomp.py`, `door.py`, `opn.py`, `det.py`, `cf.py`, `walled.py`, `cmp.py`, `hb.py`. Ad hoc and
read-only; not part of the eval tooling.

---

## 0. The short version

One mechanism explains most of R11. Call it the **phantom goal-side frontier**. It is code, not
model, and it is not what the summary describes.

- The memory marks free cells along every perceiver ray: 6 m for `open_far`, in 0.85 m cells.
  Collisions never write wall cells, and a newer look erases older wall marks. As a result there are
  free cells beyond the divider. They come from closed doors misread as open floor, and also from
  correct `open_far` reads that overshoot a wall 4–6 m away.
- a16 offers each frontier at its cell nearest the goal. Picking the minimum distance to the goal
  selects exactly the cell where those map errors sit: the free cell furthest toward the goal, which
  lies inside or beyond the wall.
  - **Observed:** in 34 of the 37 frontier picks, the straight line to the target crosses a wall.
  - In s02, 25 of the 27 frontier picks are at x < −0.5, that is, on the goal side of the divider.
  - 5 picks are inside a solid obstacle: the s01 cube and the s03 divider.
  - Only **1 of the 33 detour hand-backs was "reached"**. The others were "too long" (18) or "goal in
    view" (14, of which 10 were hallucinated sightings).
  - R11C's frontier picks were blocked this way 16 of 58 times, and 5 of 37 in s02 were beyond the
    divider.
- Counterfactual replay (`cf.py`): replace every perceiver lane with its ground-truth class and the
  top goal-side frontier is still beyond or inside a wall in 37 of 38 q03 calls. A better perceiver
  does not fix this. Reachability does.
- The steps that stood on unreachable frontiers make up most of the round's numbers:
  - 357 of 706 steps (51%).
  - +0.00 m per step toward the goal.
  - **37 of the 58 collisions** (decomp.py). The remaining collisions were 16 with the goal ahead and
    5 with the goal behind.

---

## Q1. The 7 failures, causal chains

Stage abbreviations: **P** = perceiver, **M** = memory/projector, **PL** = planner rules,
**S** = q03, **N** = navigator, **TR** = turn rule.

### s02a dynamic (door A opens at step 3; R11C also failed). Ends 29.3 m from the goal, 4 collisions.

1. **Steps 4–5 (P → M).** Door B is closed. The perceiver reads the frame toward it as `F F FD F F`.
   R11C read the **byte-identical** frames as `n n nD n n`. The 6 m free rays reach x ≈ −2.5, past
   the divider.
2. **Step 6 (PL → S).** At (1.81, 0.57) all lanes read X, so the planner reports `walled`.
   - q03's menu: `doorway_B` (5 m farther), `unexplored_1` at (−2.12, 0.42) (4 m nearer, behind the
     closed door B), `unexplored_2` (4 m nearer), backtrack (3 m farther).
   - q03 picks `unexplored_1`, the phantom.
3. **Steps 16–18 (S/PL → N).** The drone reaches (0.70, 7.38), 0.4 m from door A's gap.
   - It collides at step 16.
   - At step 17 the perceiver reports `X X nD F F`, with a doorway in the centre strip.
   - The target lies behind the wall, so "toward your target" sits on [0]. The navigator turns around
     at step 17, away from the open door.
   - The same thing happens at steps 43–46, at (0.80, 7.69).
4. **Steps 19, 34 (S).** q03 picks new phantoms: (−2.98, 0.42) and (−5.52, 0.42).
   - The real door A was in memory as opening E (0.68, 8.05). It was marked "passed" because the
     drone came within 1.5 m of the estimate, so it was not listed.
5. **Steps 47–52 (PL → N).** The detour hands back as "too long" and the goal becomes the target with
   gb ≈ −171.
   - "toward" sits on a visible [0]. The navigator ignores it six times. Its stated reason is that
     "straight … aligns with the planner's target".
   - It flies 11.6 m away from the goal (16.6 m → 28.2 m). The stall check fires at step 53.
6. **Correct move per the record:** at steps 16–17 or 43–44, go through door A on the right. The
   perceiver flagged the doorway, and the opening was in memory.

### s02c final (door C open throughout; R11C succeeded in 47 steps). Ends 12.8 m from the goal, 9 collisions.

1. **Step 3: first divergent pick (P → PL).** The perceiver reports `n n n XD X`. This is a false
   wall: the true free distance on [4] is 12 m and on [5] 8.2 m.
   - Wall-aware "toward" drops [5], the planner reports `walled`, and q03 is asked.
   - R11C, on the same frame, took [5] ("wall close; toward your target") and flew a full 1.7 m.
   - q03 chooses `unexplored_1` (+5 m nearer) over `doorway_C` at (7.35, −5.54), worded "as far from
     the goal". That doorway lay in the true direction of door C.
2. **Step 8.** The detour is reached, the only "reached" hand-back in the round. The goal becomes the
   target.
3. **Step 9 (P).** At 0.57 m from the closed door B the perceiver reports `F F F F F` ("dark,
   blurry … uniform"). The drone collides.
4. **Steps 10, 29, 48 (S).** q03 picks **the same phantom (−5.52, −0.42), behind door B, three
   times.**
5. **Steps 22–25 (PL → N).** The drone runs along the wall to (0.70, −7.38), 0.4 m from door C's jamb,
   and collides at step 23.
   - At that step the detour hands back as "too long".
   - The goal's bearing is −99, so the goal is "behind" and therefore counts as an open way.
     "toward" goes on [0].
   - The drone turns around at step 24 and leaves the door at step 25.
6. **Step 26 (P).** Hallucinated goal sighting ("far_right near", no line of sight).
7. **Steps 43–47 (N/TR).** At step 43 the navigator turns around although "toward" is on [3].
   - At step 44, [0] is hidden and the goal is behind, so no visible action carries "toward".
   - Four moves go away from the goal (15.3 m → 21.9 m).
8. **Correct move per the record:** at step 3, take [5]. At step 23/24, keep along the wall about one
   more move, then go right through door C.

### s02c dynamic (door C opens at step 3; R11C also failed). Ends 19.8 m from the goal, 7 collisions.

1. **Steps 4–5 (P → M).** Same misread of the closed door B as in s02a dynamic. R11C read the
   identical frames as `n n nD n n`.
2. **Step 6 (S).** q03 picks the phantom (−2.12, 0.42).
   - The detour leads toward the A side (y > 0), which is the wrong side.
   - Door C was **never** in memory at any q03 call. The closest the drone came to door C's mouth was
     9.7 m.
3. **Step 17 (P → PL).** Hallucinated "goal far_right near" (no line of sight, gb = 104) triggers a
   goal-in-view hand-back. The goal is now behind. Collisions follow at steps 19, 21, 23 and 25,
   near door A.
4. **Steps 22, 38, 57.** More phantoms.
5. **Steps 51–56 (TR → N).** After a turn-around, [0] is hidden and the goal is behind. Six moves go
   away from the goal (15.0 m → 23.1 m).
6. **Correct move per the record:** search toward −y for door C. The record never offered it. This
   failure is mostly search, as in R11C.

### s02va dynamic (door A opens in view; R11C succeeded in 48 steps). Ends 20.4 m from the goal, 4 collisions.

1. **Steps 4–10: first divergence at step 5 (PL).**
   - The goal stands because the way is genuinely open up to door B, 13 m ahead.
   - The perceiver flags doorways on the right strips. That is where door A is, and in this site it is
     visible at the switch.
   - R11C's q02 was asked at step 4 ("goal out of view") and chose `doorway_D` at (8.6, 2.39), which
     is toward A. That led it through A at step 34.
   - a16 has no such trigger, so the drone flies to the wall.
2. **Step 11 (S).** At (1.31, 0.90) the planner reports `walled`.
   - Menu: `doorway_C` (10 m farther), `unexplored_1` and `unexplored_2` (3 m nearer, at
     (−1.27, ±1.27), both behind B).
   - q03 picks `unexplored_2` on the C side (y < 0), away from A.
3. **Steps 24, 31 and 44.** Phantoms again. Steps 24 and 31 pick the same point, (−4.67, −0.42).
4. **Step 30.** Hallucinated goal sighting, no line of sight, gb = −77.
5. **Steps 57–59.** The goal is behind and the drone flies away.
6. The drone never came within 3.4 m of door A's mouth.
7. **Correct move per the record:** head for the doorway seen on the right at steps 4–5, as R11C did.

### s02vc final (door C open throughout; R11C also failed). Ends 14.4 m from the goal, 4 collisions.

1. **Step 11 (S).** The planner reports `walled` at the closed door B.
   - Menu: `doorway_C` (11 m farther), `doorway_F` (4 m farther), `unexplored_1` at (−2.12, 2.98)
     (3 m nearer).
   - q03 picks the phantom on the **A side** (y > 0), the wrong side.
2. **Steps 24 and 38.** q03 picks the same phantom twice, (−4.67, 6.38). At steps 26–27 the drone is
   at the closed door A.
3. **Step 34 (P → PL).** Hallucinated "goal centre far" with gb = −102, so the goal-in-view hand-back
   fires.
   - The drone flies along the wall toward C and collides at (1.38, −3.67) at step 37.
   - The `blocked` trigger fires, q03 sends it back to the A-side phantom, and the drone goes north.
4. **Step 38 (S).** `doorway_M` at (0.61, −7.73), the real door C, **was listed**, worded "about as
   far from the goal as you are". q03 did not pick it.
5. **Correct move per the record:** pick `doorway_M` at step 38.

### s02vc dynamic (door C opens in view; R11C succeeded in 38 steps). Ends 16.6 m from the goal, 4 collisions.

1. **Step 11 (S, code): first divergence at step 12.** q03 picks `unexplored_2` at (−1.27, −1.27),
   behind B.
   - R11C's `unexplored_2` was at a cluster centre in the room, about 7 m ahead-left (the a14 frontier
     rule). In R11C, "toward" landed on [2]. In R11, the target was behind the drone and [0] was
     hidden.
2. **Step 17 (P).** At (0.87, −6.09), with a wall face filling most of the frame and door C's
   architrave at the left edge (frame `c000017.png`, viewed on the Mac):
   - the perceiver reports `FD F F F F` (all open far);
   - it also hallucinates "glowing red sphere … far left";
   - the goal-in-view hand-back fires;
   - the navigator follows the goal note.
3. **Steps 18–20 (PL/N).** The drone flies straight along the wall and **past the open door**.
   - At step 19 it is at (0.91, −9.49), in front of the gap, **with line of sight** to the goal at
     gb = −127.
   - No forward action is within 55° of the goal, so "toward" goes on [0]. The navigator ignores it.
   - It collides at y = −11.5 at step 20.
4. **Steps 26 and 40.** Two more hallucinated hand-backs. Then at steps 41–45 the drone flies away
   from the goal (13.2 m → 19.1 m).
5. **Correct move per the record:** at step 18 or 19, turn right through the gap. The fan (±43.5°) has
   no action pointing at a door 90° to the side.

### s03 dynamic (R11C was a pre-change failure, so this is not comparable). Ends 8.3 m from the goal, 9 collisions.

1. **Steps 10–22 (S).** The drone is blocked at the stem's end. q03 picks `unexplored_2` at
   (0.42, −1.27), **inside the divider**. The detour runs 12 steps and hands back as "too long".
2. **Steps 23–27.** The goal stands and the drone enters the L tine. It crosses x = 0 at step 25, which
   closes the L exit door.
   - At steps 25–27 the perceiver reads `n n nD X X` and `FD F F n n`.
   - The 6 m rays mark free cells to x ≈ −9.8, beyond the closed exit door.
3. **Steps 28, 41 and 54 (S).** q03 picks (−9.78, −3.82) beyond the closed door, then (−7.22, −0.42)
   inside the exit wall, then (−9.78, −0.42).
   - `back_to_step_26` and `back_to_step_22` were on the menu, worded "3 m farther", and were never
     picked.
   - The drone spends 32 steps in the dead-end tine, with 8 collisions.
4. **Correct move per the record:** backtrack out to the crossbar and take the R tine.

---

## Q2. Navigator (p14) reasoning, R11 against R11C

| | R11 | R11C |
|---|---|---|
| picks | 706 | 721 |
| forward "toward" visible → picked | 287/407 (71%) | 327/460 (71%) |
| "toward" on a visible [0] → picked | **43/181 (24%)** | 34/135 (25%) |
| "toward" only on a hidden [0] | **47** | 12 |
| goal note offered → picked | 170/170 (26 without line of sight) | 162/162 (20 without line of sight) |
| picked "wall close" → stopped short | 4/17 | 6/17 |
| picked a blocked or stopped-short note | 1 (stopped short) | 1 |
| stopped-short picks with no wall note | **53/57** | 14/20 |
| ...of which the perceiver said `open_far` on that strip | 48/57 | 10/20 |
| reason says the pick is "toward the target" while "toward" is on another action | 126 (75 of them with "toward" on [0]) | 135 (56) |
| reason cites "toward" when no visible action has it | 25 | 12 |
| reason says path "clear/open/unobstructed", then stopped short | 16 | 7 |
| **any contradiction (notes or outcome)** | **169/706 (23.9%)** | 169/721 (23.4%) |
| turn-arounds | 96 (64 with every forward move noted not open) | 54 (34) |

**Observed:**

- The navigator behaves the same in both rounds:
  - It follows a forward "toward" 71% of the time.
  - It follows a goal note 100% of the time, including every hallucinated sighting.
  - It almost never takes a wall-noted move.
  - Its stated reasons contradict the notes or the outcome on about 24% of steps in both rounds.
- Its typical misstatement: when "toward" is on [0], it picks straight or a sharp turn and calls that
  move "toward the target". Examples: s02a dynamic steps 47–48, s02c dynamic steps 8 and 52, s02vc
  dynamic step 55.
- It reads "wall close; doorway (seen now)" as "the path is open through a doorway" (s02vc dynamic
  step 18).

**Inferred:** the navigator is not what separates R11 from R11C. What changed is how often a16 puts
it in the "target behind" situation, where "toward" sits on [0]:

- **185 steps in R11 that were not followed** (138 ignored plus 47 hidden). Over those steps the drone
  moved **+158.5 m away from the goal**.
- R11C: 113 such steps, +46.7 m (behind.py).
- On steps where the goal itself was the target and lay behind (|gb| > 90): 49 steps at −0.96 m per
  step in R11, against 39 steps at −1.14 m per step in R11C.

---

## Q3. Strategist q03 reasoning

- **Picks:** 38 calls, 37 frontier and 1 doorway. The mode was "explore" every time.
- **Doorways were on the menu in 19 of 38 calls** (28 entries), but they were worded as no better:
  - 7 entries read "about as far from the goal".
  - 14 entries read "3–11 m farther".
  - 7 entries read "nearer".
  - Frontier entries read "3–22 m nearer" on almost every menu.
- **Why the wording comes out this way (code):**
  - Doorways are placed 2 m or 5 m along the view ray (`OPENING_AT_M`), so they land on the near side
    of the wall.
  - Frontiers are placed at their cell nearest the goal (`frontier="goal_side"`), so they land beyond
    the wall.
  - The q03 prompt says "Prefer a detour that lies nearer the goal than the drone".
  - **35 of the 38 picks were the item with the largest gain** (ties included). In 38 of 38 menus,
    `unexplored_1` was the largest-gain item, by construction. 36 of 38 reasons cite "nearer" or the
    size of the reduction.
- **Menu order is not driving the picks.**
  - Order is fixed by `targets()`: doorways, then frontiers (nearest the goal first), then backtrack.
  - The pick was the first listed item in 18 of 38 calls. Every one of those menus had no doorway, so
    the first item was also the largest gain.
  - In the 19 menus that led with doorways, a first-listed doorway was picked 0 times.
  - The only doorway pick was s02va final step 23: `doorway_J`, worded "+5 m", over `unexplored_1`
    at "+9 m". The reason given was "doorways are known paths". That run succeeded.
- **Doorways were also hidden from the menu.**
  - At the 28 s02 calls, the real open door was in memory 14 times but listed only 4 times.
  - The rest were struck as "passed" because the trail came within 1.5 m of the doorway's near-side
    estimate even though the drone never went through.
  - Examples:
    - s02vc dynamic: G at (1.53, −7.05) and H at (0.20, −7.61), both marked passed after the
      drone ran past door C.
    - s02a dynamic: E at (0.68, 8.05), marked passed.
    - s02c final: D, marked passed.
- **The same target is re-picked after a failed detour.** 7 of 38 picks repeat exact coordinates.
  The same phantom recurs in s02c final, s02va dynamic, s02vc final (twice), s02vc dynamic and
  s02c dynamic.
- **Triggers were mostly genuine.**
  - At 30 of 38 calls, every forward move within 55° of the goal really was shut (walled.py).
  - The one false `walled` that mattered was s02c final step 3, a perceiver false wall.

---

## Q4. Perceiver (g03)

- **Floor classes against geometry**, per lane read:

  | True class (< 1.5 / 1.5–4 / > 4 m) | R11 | R11C |
  |---|---|---|
  | blocked_near (< 1.5 m) | **X 471, n 31, F 244** (33% read open far) | X 260, n 21, F 139 (33%) |
  | open_near (1.5–4 m) | 68 / 90 / 398 | 66 / 65 / 352 |
  | open_far (> 4 m) | 67 / 214 / 1947 | 79 / 247 / 2376 |

  The miss rate is the same in both rounds. R11 simply spent much more time near walls: 746 lane
  reads with a wall within 1.5 m, against 420.
- **The typical miss:** a featureless wall face within 1 m reported as "open far", with reasons like
  "dark, blurry … uniform". Examples: s02c final step 9 at 0.57 m from door B; s02vc dynamic step 17.
- **Stopped-short picks:** 48 of 57 had `open_far` on the picked strip, so the "wall close" note is
  absent for 53 of the 57.
- **False walls:** s02c final step 3 reported `XD X` where the true distances were 12 m and 8.2 m. It
  caused the first divergence of a lost cell.
- **Goal sightings without line of sight:** 26 in R11 (20 in R11C).
  - **10 of the 14 goal-in-view hand-backs were hallucinated**, 7 of them in failed runs: s02c dynamic
    17; s02va dynamic 30; s02vc final 34 and 53; s02vc dynamic 17, 26 and 40.
  - In every one of the 10, the claimed strip was more than 20° from the true goal bearing.
  - A gate "strip within 20° of the true bearing" keeps 140 of 144 genuine sightings.
- **Non-determinism at temperature 0.** On byte-identical clean frames (the shared prefix of R11 and
  R11C), **50 of 178 perceiver outputs differ**.
  - Examples: s02a and s02c dynamic steps 4–5, where the closed door B was read F (R11) against n
    (R11C). In R11 that read seeded the phantom frontier.
  - s03 initial step 5: `nD nD F nD nD` against `FD F F F F`.
  - So part of the R11/R11C difference is perceiver noise. The floor F = 6 is warranted.

---

## Q5. Cells that changed against R11C

Steps are 0-based, as in the summaries' "first pick that differs" brackets.

| Cell | First divergent step | What differed | Why |
|---|---|---|---|
| s02c final (lost) | 3 | R11 asked q03, which chose `unexplored_1`. R11C took [5] "wall close; toward" and flew 1.7 m. | A perceiver false wall, combined with wall-aware "toward", made the planner report `walled`. Later, the phantom behind B was picked 3 times. |
| s02va dynamic (lost) | 5 | R11 kept the goal and went straight. R11C's q02 chose `doorway_D` (toward A) and turned slight right. | a16 has no "goal out of view" or doorway trigger. With the goal standing, it ignored the door that was visible at the switch. |
| s02vc dynamic (lost) | 12 | Both asked at step 11 and both picked `unexplored_2`. a16's was a phantom behind B (target behind, [0] hidden). a14's was 7 m into the room. | The frontier placement rule (code). |
| s01 dynamic (gained) | 7 | R11 was on a detour to `unexplored_1`. R11C had the goal behind with [0] hidden. | R11's target was a phantom **inside the cube**, but it pulled the drone along the cube's side and round. R11C drifted 7 steps away from the goal behind it. **Inferred:** this gain was luck. |
| s02va final (gained) | 1 | R11 took straight toward the goal. R11C's q02 chose a frontier and went sharp left. | Goal by default where the way is open. The drone went through A at step 25. That was helped by the only doorway pick (step 23) and also by a hallucinated hand-back (step 17). |
| s03 initial (gained) | 5 | R11 kept the goal. R11C's q02 chose `doorway_C` (sharp left). The perceiver output also differed on the identical frame. | Goal by default. The detour at step 10 aimed inside the divider; a hallucinated hand-back at step 20 (true gb = 2°) put the goal back as target and it succeeded. |

---

## Q6. Failure modes ranked, and fixes for a17

| # | Mode | Failed runs | Collisions / cost | Fix (type) | Offline test |
|---|---|---|---|---|---|
| 1 | **Phantom goal-side frontier**: an unreachable target behind or inside a wall. Cause: 6 m free rays, collisions never write walls, newer looks erase walls, and the argmin-to-goal frontier rule. | **7/7** | **37/58** collisions; 357 steps at +0.00 m/step | **Code.** (a) A collision or stopped-short move writes wall cells at the stop point along that heading; looks may not erase them. (b) Frontier candidates must be reachable: breadth-first search over visited/free cells with a 1-cell margin from walls and blocks, cost = path + distance to goal. (c) Cap `open_far` at about 4 m. (d) Drop targets of failed detours. | Replay R11's 38 q03 calls (cf.py pattern). The top frontier beyond or inside a wall should drop from 37/38 to ≤ 5/38, and at least half should still offer ≥ 3 m gain. |
| 2 | **Target behind, "toward" on [0]**: hidden by the turn rule (47) or ignored (138). | 5/7 (s02a d, s02c f, s02c d, s02va d, s02vc d) | +158 m away from the goal; s02vc dynamic flew past the open door | **Code.** When nothing in the fan is within 55°, tag the sharpest forward action on the target's side "toward". Never hide [0] while it alone carries "toward". **Prompt** (optional): "[0] toward = the target is behind you". | Re-tag R11's steps. Steps with no visible forward "toward" while the target is behind should drop from 185 to about 0. A live probe on those frames should show a "toward" pick rate ≥ 70%. |
| 3 | **Doorways neither listed nor chosen**: near-side placement worded "as far", the "prefer nearer" prompt, and "passed" without crossing. | 4–5/7 (s02a d, s02c f, s02vc f, s02vc d; s02va d via no trigger) | R11C's doorway targets gained 0.86 m/step | **Code:** mark passed only on crossing the wall plane; when walled, list doorways first and word the gain from the doorway's bearing; re-add a doorway trigger when a doorway is seen while the goal stands. **Prompt (q03):** "when walled, prefer a doorway; 'nearer' unexplored ground can be behind the wall". | Re-run q03 text-only on R11's 19 menus that held doorways. Doorway picks should rise from 1/19 to ≥ 50%, and the true door should be listed in ≥ 12 of the 14 calls. |
| 4 | **Hallucinated goal sighting ends a detour** | 4/7 (s02c d, s02va d, s02vc f, s02vc d) | 10 hand-backs | **Code (truth is allowed in the planner):** accept a goal-in-view hand-back only if the claimed strip is within 20° of the true bearing. | On R11: all 10 hallucinated hand-backs rejected, all 4 genuine ones kept. This would also remove s03 initial's lucky one. |
| 5 | **Perceiver misses walls closer than 1 m** (33% read open far) | seeds #1 in s02a d, s02c d and s03 d; s02c f at steps 3 and 9 | 53/57 stops with no warning | **Code:** after a stopped-short or blocked move, force the strips on that heading to `blocked_near` for the next look. **Prompt (g03):** "a surface with no visible floor line across the strip is blocked_near". | Scored on R11 frames with the geometry: blocked_near read as F should fall below 15% (needs the model on sctsvr6; that is the operator's call). |
| 6 | **Hand-back placement**: "too long" after 12 steps wherever the drone is; a goal behind counts as open. | s02c f (step 23 at the door mouth), s02vc d (steps 17–19) | – | **Code:** when handing back with the goal behind and a doorway or gap within 3 m, keep the doorway; treat "goal behind" as not open for 2 steps after a turn-around. | Replay the planner on R11's records and count hand-backs within 3 m of the true open door. |
| 7 | **Backtrack never chosen** | s03 d | 8 collisions, 32 steps in a dead end | **Prompt (q03):** "in a dead end, go back"; word backtrack as "the way out". **Code:** fire a backtrack-only menu when blocked 3 or more times within 2 m. | – |

Shortening detours (the summary's item 2) does not appear here. On its own it only re-asks q03, which
re-picked the same phantom 7 times.

---

## Where the summary and manipulation check are wrong or incomplete

1. **"The cell nearest the goal lies against the wall in question."** The cell is not against the wall;
   it is beyond it or inside it.
   - 25 of the 27 s02 frontier picks were on the goal side of the divider, and 5 picks were inside a
     solid obstacle.
   - Only 1 of 33 detours was reached.
   - Even with a perfect perceiver, the top frontier would be beyond or inside a wall in 37 of 38 q03
     calls.
   - So "unexplored ground … with the goal off to one side" will not fix it without reachability.
2. **"Doorways were never chosen" is framed as q03's preference.** The real causes are the menu
   wording, the "prefer nearer" prompt line, and doorways struck as "passed". The true door was listed
   in only 4 of the 14 calls where it was in memory. Menu order is not the cause: doorways come first.
3. **"Shorter detours."** The detours end on "too long" or on hallucinated sightings because their
   targets cannot be reached. Shortening them does not change that.
4. **"The block note is not the lever … may need the perceiver's view."** The perceiver's view would
   not have helped: it said `open_far` on 48 of the 57 stopped-short moves. What is missing is that
   collisions are never written into the occupancy map as walls.
5. **Unreported, and they matter for credit:**
   - 10 of the 14 goal-in-view hand-backs were hallucinated.
   - 50 of 178 perceiver outputs differ on byte-identical frames. The s02a/s02c dynamic phantom seed is
     one such coin flip.
   - The s01 dynamic gain was luck.
6. **Indexing.** The R11 summary's "first pick that differs" numbers were 1-based, where R10, R10C
   and R11C use 0-based steps. Fixed in the summary on 2026-10-28.
7. **Numbers confirmed:**
   - 37 frontier and 1 doorway pick.
   - 96/706 turn-arounds (13.6%).
   - 58 collisions.
   - About 0.00–0.01 m/step on frontiers.
   - The 13% stopped-short rate under frontiers was not re-derived.
