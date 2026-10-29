# s03 after the crossbar: why `final` and `dynamic` still fail

Written 2026-10-29 by a Claude subagent as a read-only analysis. No model calls were made. Throwaway
scripts (not in the repo) read `decisions.jsonl` and replayed memory with `spatial.rebuild` and
`search_frontiers`. Geometry is from `R11_goal_default/analysis/geo.py`; regions as in
`R17_doorway_first/s03_analysis.md`.

## 1. Where the goal is and where the drones spent their time

The goal is **not in a tine**. It is in the chamber at (−12, 0), behind the exit wall
(x ∈ [−7, −6]). Each tine reaches it through a door at |y| = 5 (tine L, y < 0, through door L;
tine R through door R).
- `initial`: both doors open.
- `final`: door L shut from load (`final_closed: ["BranchL"]`, seed1), so the way is **tine R**.
- `dynamic`: the first tine crossed has its door slam (`doors_switched`) and the other bank
  disarms, so the way is **the other tine**.

Steps 8–59 per region; "dead end" is the tine whose exit door is shut.

| run | xbar | stem/lobby | dead-end tine (+ exit wall) | other tine | first tine @ | door shut | first at exit wall | steps left then |
|---|---|---|---|---|---|---|---|---|
| R22K final (a43), 9.4 m | 7 | 0 | **L 39 + 6** | 0 | L @15 | load | 21 | 39 |
| R22K dynamic (a43), 8.0 m | 15 | 3 | **L 28 + 6** | 0 | L @26 | @28 | 31 | 29 |
| R22 final (a42), 11.4 m | 6 | 0 | **L 36 + 10** | 0 | L @14 | load | 20 | 40 |
| R20K dynamic (a38), 8.0 m | 12 | 4 | **R 35 + 1** | 0 | R @24 | @27 | 30 | 30 |
| R20 dynamic (a37, extra), 10.9 m | 8 | 0 | **R 44** | 0 | R @16 | @19 | 22 | 38 |

- **R22 dynamic (18.5 m) is a different failure.** At s4, blocked at the stem mouth, q08 took
  `along_left` (15.5, −3.4) in the lobby. It then spent 45 steps there, reaching the crossbar only
  at s52. That is R17's stage-1 lobby-wall pattern, not covered here.
- **The five tine failures are one pattern.** The drone takes a tine, finds its exit door shut, and
  stays in that tine for the rest of the run (34–46 steps). It never returns past x = 5 and never
  enters the goal's tine.
- **A way back fit the budget.** Back to the crossbar, down the other tine and on to the goal is
  about 42 m, roughly 26–28 steps. Four runs had 30–40 steps left at the exit wall. R22K `dynamic`
  had 29, after 18 steps at the crossbar.
- **Contrast.** The solved `final` runs (R20K s34, R20 s53) took tine R first. No run in R20–R22K
  has backed out of a dead-end tine; R11 `dynamic` spent 32 steps in one.
- **Side choice.** a42/a43 always went L. At the first crossbar call (s9/s10), both `along` items
  read "about as far from the goal as you are", 5 m each, and q08 broke the tie to `along_left`.

## 2. Why they never got to the goal's tine

**1. The other tine's mouth was never seen. It was not falsely walled or searched.**
- At every strategist call, the replayed map has 0–9 known cells in the open side's crossbar half
  and tine, 0 wall cells and 0 visited cells.
- Two frames faced that mouth (R22K `dynamic` s20, R20K `dynamic` s11). Both read the floor as
  open; there is no doorway there to tag.
- The drone meets the crossbar facing the x = 5 wall, with the mouths at ±90°.

**2. The dead end was seen clearly, but the strategist was never told.** Closed-door strips /
steps / d01 "closed": R22K `final` 25/15/6, R22K `dynamic` 18/9/4, R22 `final` 24/13/8, R20K
`dynamic` 14/10/3, R20 `dynamic` 16/12/3.
- The map has it right: a17b writes a wall at a closed-door strip's end, and `goal_way` says
  `walled`/`blocked` at the exit wall.
- `detour_situation` has no line for a closed door, and closed openings are dropped from menus.
- The openings are misplaced anyway. In `final` the exit door was never added. In `dynamic`, C/D
  sit at (−1.4, −5.9) and (−3.6, −3.2) on the tine side walls, not at the door (−6.5, −5).

**3. A way out was listed on 25 of 33 dead-end calls and picked 0 times.**

| run | calls | way-out item listed | picks |
|---|---|---|---|
| R22K `final` | 7 | 3: frontier (6.4, 1.3), "17 m … behind; … farther from the goal" | along 5, local frontier 1, explore 1 |
| R22K `dynamic` | 4 | **0** | along 3, explore 1 |
| R22 `final` | 9 | 9: frontier (7.2, 1.3), 18 m | along 8, local frontier 1 |
| R20K `dynamic` | 6 | 6: frontier (6.4, −0.4) | local frontiers 3, backtrack 1, explore 2 |
| R20 `dynamic` | 7 | 7: frontier (6.4, 0.4) | local frontiers 5, explore 2 |

- **Why it is never picked.** q08 rule 4 allows unexplored ground "only when no along item is
  listed"; rule 1 says "follow the side you followed last time". q03 says "prefer nearer the goal".
- **The backtrack item is local:** the latest spot at least 3 m back, inside the same tine.
- **Missing in R22K `dynamic`.** The `failed_detours` blacklist removed its only frontier, so
  `search_frontiers` returned [].
- **The loop.** The `along` items run along the exit wall or the tine walls. They are handed back
  after 2–5 steps (R22K: `detour_stalled` 6, `along_way_open` 2, `detour_reached` 1). The goal line
  then points at the shut door again.
- **A pick would not have been enough.** The listed frontier is the crossbar centre, not the other
  tine. From there, q08's global side counts (`along_left` followed 4–8 times) would point back to
  L.

**4. No goal sighting was dropped.** `line_of_sight` was false on all steps of all five runs. c01
checked twice per R22K run (s2, s44/46) and rejected both, correctly. Perceiver false positives
(R20 `dynamic` s14, R22 `final` s56) had no effect.

## 3. Proposed change: a "back to the fork" item, and the rule for it

The cause is in the menu: nothing offers "the dead end is the wrong branch; take the other branch
at the junction". The change has three parts, on the a43 line:

1. **Memory and menu.**
   - At each detour call, add the newest `along` item from an earlier call made at least 6 m away
     whose end the trail never came within 1.5 m of. Word it `other_way_N`: "the other way along
     the wall you met at step N (never reached), about D m back over known floor".
   - Hold it until reached or stalled, exempt from `detour_max_steps` = 12 (the path is about 20 m,
     roughly 13 steps).
2. **Situation line** when the perceiver reported a closed door in the last 5 steps and d01
   agreed: "A closed door was seen in the wall ahead at steps …".
3. **q10 = q08 + rule 5:** "If a closed door stands in the wall between the drone and the goal and
   at most one way along it is listed, or both were followed twice, the drone is in a dead end:
   choose `other_way_*` even though it lies behind and farther from the goal."

- **Why this item.** The recorded crossbar `along_right` ends lie in the open tine's mouth:
  (4.97, 5.79) in R22K `final`, (5.62, 3.69) from s21 in R22K `dynamic`, (5.5, 5.76) in R22
  `final`. From there the goal line runs down tine R to door R, which is R11's phantom effect from
  a reachable point.
- **A prompt-only rule cannot fix R22K `dynamic`,** whose menu offered nothing out of the tine.
- **q03 line (R25's a48/a49).** It has no `along` items. Its analogue is rule 5 alone, with "choose
  the unexplored ground behind"; that frontier is listed on 13 of 13 of its dead-end calls.
- **s02 risk.** A closed door also stands ahead at the divider, hence the "at most one along way"
  clause and gate B.

## 4. Cheap offline check before flying

**A. Items, no model.** Prototyped on the recorded menus; to run it properly, rebuild with
`spatial.rebuild` (a17b) and check reachability with `mem.reach`.
- On R22/R22K's 20 s03 dead-end calls the item exists **20/20**, each ending in the open tine's
  mouth on true free floor (`geo.free_s03`, |y| ≥ 3.5, opposite side).
- Over R21–R22K s03 dead-end calls (x < −3), gated on at most one `along` item listed: 17 of 22,
  16 correct. Other s03 calls: 13 of 60.
- On s02, the same gate shows it on 59 of 226 calls, and only 28 of those lead toward an open door.
- Gates: item on ≥ 80% of s03 dead-end calls, correct on ≥ 90% of them, ≤ 25% of s02 calls.

**B. Live, text only** (`r21_along_probe run`/`score` style). Run q10 on the recorded situations
with the item and the closed-door line rendered in. Gates:
- `other_way` picked on ≥ 75% of the 20 s03 dead-end calls;
- on s02, ≤ 10% picks of a shown `other_way` that does not lead toward an open door;
- divider `along` picks at least q08's 14 of 15 (R21 probe).

**C. Budget.** Geo BFS path from each first dead-end call to the item end, plus about 12 steps to
the goal, must fit in 60. Estimated arrival is about s34, s44 and s33 for R22K `final`, R22K
`dynamic` and R22 `final`.

## Summary

1. The goal is in the chamber at (−12, 0) behind the exit wall: tine R is the way in `final` (door L shut), the untaken tine in `dynamic`.
2. All five 8–11 m failures went into the shut tine (a42/a43 L at s14–26; a37/a38 R) and spent 34–46 steps there, 0 in the open tine; R22 `dynamic` (18.5 m) is a separate lobby-wall failure.
3. The dead end was seen (closed-door strips on 9–15 steps/run, d01 agreed 3–8 times); the map was not falsely walled, the other tine was never seen; no goal sighting was dropped.
4. A way out was listed on 25/33 dead-end calls and picked 0 times (q08 rules 1/4, q03 "nearer the goal"); absent in R22K `dynamic`, and only the crossbar centre when listed.
5. Fix: an `other_way_N` item (earlier never-reached `along` end; in the open tine 20/20), a closed-door line and q10 rule 5; gate offline on item correctness and s02 exposure, then a live text probe.
