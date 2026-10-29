# R13 (a20) and R13G (a21) failure analysis: final and dynamic

Written 2026-10-29 by a Claude subagent as a read-only analysis of `eval/phase2/R13_verify` and
`eval/phase2/R13G_verify_goal_words`, read against R12 (`a19`) and R11 (`a16`), from the recorded
`decisions.jsonl` and `metrics.json` only (no model calls, no frames). It is analysis, not
pre-registration: nothing here changes a label or a result. Design: [README.md](README.md),
[R13G README](../R13G_verify_goal_words/README.md).

**Conventions.** Steps are the 0-based `step` of the records. Map coordinates: x = world x,
y = −world z. s02: divider x ∈ [−0.5, 0.5], doors A y = +9, B y = 0, C y = −9; "the mouth" is
(1.5, ±9), the start side of the open door. Ground truth is R11's 2D site model
(`R11_goal_default/analysis/geo.py`), `r12_probe.in_view`/`los`/`true_reach`. A sighting is
**genuine** if the goal is in line of sight within 60° of the heading, **stale** if it is on the
frame of the switch step (that frame still shows the old scene; the manifest is already
post-switch), else **hallucinated**. "Truly blocked" = the strip's centre ray meets a wall within
1.9 m (one 1.7 m move plus margin). **Observed** = counted from the records; **Inferred** = the
analyst's reading. "f+d" = the 12 final + dynamic runs of a round.

Scripts in [analysis/](analysis/), run from the repo root, e.g.
`python3 eval/phase2/R13_verify/analysis/verify.py`: `common.py` (loaders), `runs.py` (per-run
table), `tl.py` (timeline: `tl.py R13 s02a dynamic 0 20`), `verify.py`, `sight.py`, `strips.py`,
`floor_end.py`, `repeat.py`, `ta.py`, `strat.py` (`-v` lists every call), `nav.py`, `door.py`,
`chain.py`, `near.py`. Read-only; not part of the eval tooling.

---

## 0. The short version

The verify stage did what it was built to do and it was not the bottleneck. Both rounds failed
final and dynamic for the reason R12 did: **the drone never got out of the start room.**

- **Verify is a correct disproof, not a re-finder.** 26 `goal_lost` episodes across both rounds.
  Only 1 rested on a genuine sighting (R13 s02va initial, reacquired). The others: 4 stale
  (switch-step frames), 21 hallucinated. All 15 `verify_failed` check looks had the goal truly
  out of line of sight, so 0 were wrong (prediction ≤ 1: met). Reacquired: 1/15 and 0/11
  (prediction ≥ 1/3: not met). In final and dynamic there was never a genuine sighting left to
  re-find. Cost: 72 and 64 verify steps (7–8% of steps).
- **The world model is mostly false walls.** g05 + a19's floor map read 49% of strips
  `blocked_near`, and only 12% of those were truly blocked. 47% of truly open strips read
  blocked (R11: 17%, 78%, 5%). In f+d, 38% of looks had all five strips walled.
  - **Inferred:** g05's `floor_end` carries almost no distance information. `bottom`, `lower`
    and `middle` have the same true-clearance profile (61–76% clear past 8 m each).
  - Asked twice about the same view (same pose ±5 cm, heading ±2°), g05 gave the same answer on
    only 49% of strips, and the open/blocked class flipped on 40%.
- **What the walls do downstream:**
  - **Navigator:** 37% of f+d steps are turn-arounds (R11 15%), 96 of them back-to-back. 220 of
    263 turn-arounds came when every forward move carried "wall close", and 91% of those had a
    forward move truly clear for 1.9 m.
  - **Strategist:** menus are local, with a median pick 2.4 m away, and only 1 of 23 doorway
    items lay at the real open door.
  - **Overall:** mean max distance from start in f+d is 14–15 m (R11 22 m). Collisions are rare
    (5) because the drone barely moves.
- **R13G's goal words barely moved the strategist.** The best ≥ 3 m-nearer item was picked
  11/27 times (R13 7/32). Picks ≥ 3 m farther from the goal: 9 against R13's 24. But only 27 of
  163 menus held such an item, and success stayed at 0/12.
- **The one f+d success (R13 s02c dynamic, at step 60)** came after a hallucinated sighting and
  a verify fail. Then a local frontier happened to carry the drone south to (3.5, −10.9), where it
  saw the goal through door C. The navigator then ignored three strategist detours (steps 54, 56,
  59) that the false walls had triggered with the goal in view.

---

## 1. The final and dynamic failures, causal chains

Stage abbreviations: **P** perceiver (g05), **M** map (a19 floor map, a17 memory),
**SM** stage machine, **S** strategist, **N** navigator. Chain shorthand used below:
"**walls**" = P → M: ≥ 1/3 of looks all-walled, frontiers 2–3 m out, "wall close" on every
forward move, then turn-around. "**hv**" = a hallucinated sighting that verify correctly
disproved. Columns: end = distance to the goal at the end (m), maxd = max distance from start
(m), TA = turn-arounds (back-to-back pairs), C = collisions, all5 = all-walled looks of 60.

### R13 (a20): 11 failures (s02c dynamic succeeded)

| run | first | chain | end | maxd | TA | C | all5 |
|---|---|---|---|---|---|---|---|
| s01 final | P | walls. Closest 2.7 m to the cube's flank (s33–34, `X3 X4` with 10 m clear → TA). hv s19 → failed s23. 13 calls, 1 menu item near the flank. | 24.9 | 9.4 | 30 (12) | 0 | 28 |
| s02a final | P | walls. No menu item within 3 m of door A's mouth in 8 calls (6 picks mid-room, 2 on the C side). Closest 5.8 m. | 19.6 | 11.4 | 17 (6) | 0 | 25 |
| s02c final | P | walls. 4 picks on the door side, all 2–3 m. At s48 (1.6, −4.9), far-left `XD` with 7 m clear → TA. hv at s58. | 13.2 | 11.6 | 21 (10) | 0 | 23 |
| s02va final | P → SM | walls for 40 steps in x > 9. 10 door-side picks get it to A's mouth (1.0 m) at s58. hv at s57 puts it in verify, and verify turns it **away from the open door** (centre `F10` through it). | 16.8 | 19.9 | 18 (5) | 1 | 23 |
| s02vc final | P | walls. 6 calls, no item near C. Closest 8.9 m. | 17.1 | 20.6 | 16 (4) | 1 | 18 |
| s03 final | P | walls. Never past the crossbar (min x 7.8). 32 steps with no "toward" move. | 25.5 | 13.3 | 35 (21) | 3 | 32 |
| s01 dynamic | switch → P | Goal genuine through s8, stale s9 (cube drops), verify_failed s13 (correct). Then walls. Closest 0.8 m to the flank. | 14.0 | 10.7 | 23 (7) | 0 | 21 |
| s02a dynamic | switch → S | Genuine s0–2, stale s3, failed s7 (correct). 8 of 10 picks on the **C side**. Closest to A 2.9 m (s47–49). | 12.9 | 14.4 | 18 (4) | 0 | 22 |
| s02va dynamic | switch → P | Genuine s0–2, stale s3, hallucinated s4 (door just shut), failed s10 after 3 TAs in a row. 6 door-side picks, all short. Closest 4.5 m. | 17.4 | 16.8 | 25 (12) | 0 | 32 |
| s02vc dynamic | switch → P → SM | At s4 (goal still reported) all five strips walled → "way shut" detour behind holds the goal stage to s10. Verify reaches the vantage at s14 facing 43° off, leaves it, then 4 TAs in a row, timeout s20. hv s29 → failed s35. 26 goal + verify steps. Closest 7.8 m. | 17.1 | 19.4 | 19 (6) | 0 | 24 |
| s03 dynamic | P | hv s1 (facing the lobby's back wall) → timeout s11, never reached 1.7 m back (TA ping-pong). hv s22 → failed s26. Never left the lobby (min x 15.4). | 29.0 | 9.4 | 26 (8) | 0 | 20 |

### R13G (a21): 12 failures

| run | first | chain | end | maxd | TA | C | all5 |
|---|---|---|---|---|---|---|---|
| s01 final | P | walls. 6 calls, none near the flank. Closest 2.3 m. | 22.0 | 9.2 | 23 (10) | 0 | 22 |
| s02a final | P → S | At s12 at A's mouth (1.9, 9.0) heading 156: centre read `X` with 7 m clear through the door. The target (8.1, 3.8) was behind, so 4 TAs, then a blacklist. At s21 it picks (3.8, 9.8) by the door. Targets it for 35 steps and never arrives, because every look near it is walled. | 12.5 | 13.4 | 18 (5) | 1 | 25 |
| s02c final | P → S | walls. 18 calls, 13 mid-room picks. hv s44 → failed s48. Closest 5.8 m. | 16.3 | 10.4 | 20 (6) | 0 | 22 |
| s02va final | P → SM | walls. hv s48 near A (3.0, 6.4) → 9 verify steps, timeout s58. Closest 1.9 m. | 18.0 | 19.0 | 22 (9) | 0 | 19 |
| s02vc final | P | walls. Reached C's mouth (1.3 m) only at s59. hv s48 → failed s52. | 15.0 | 20.8 | 15 (2) | 2 | 20 |
| s03 final | P | hv s0 and s27–28: 10 goal + 15 verify steps. Never past x 13.5. | 31.0 | 7.6 | 23 (7) | 0 | 23 |
| s01 dynamic | switch → S | Genuine through s7, stale s8, failed s12 (correct). At s50 the drone is beside the cube (1.0, −6.2) on the right path, and the next frontier (4.7, −7.2) pulls it back east. | 17.0 | 13.6 | 23 (6) | 0 | 17 |
| s02a dynamic | switch → M | Failed s8 (correct). 12 of 22 calls "no unsearched ground reachable" (map closed in). At A's mouth (1.0 m) at s39, facing the side wall, with no target → TA. | 19.2 | 12.9 | 27 (10) | 4 | 26 |
| s02c dynamic | switch → P | Hallucinated at s4, failed s12 (6 steps to a vantage 1.7 m back). Closest 5.1 m. | 14.3 | 12.0 | 17 (3) | 0 | 22 |
| s02va dynamic | switch → SM | Reached the vantage at s7 but no check look within 39.5° before timing out at s14. 3 of 4 picks on the C side. Never within 12 m of A. | 26.3 | 15.8 | 22 (8) | 0 | 19 |
| s02vc dynamic | switch → SM/N | Stale s3, timeout s13 without reaching a vantage 1.7 m back (TA ping-pong). hv s36 → failed s40. | 14.7 | 20.6 | 22 (7) | 1 | 24 |
| s03 dynamic | P | walls. 33 all-walled looks, never left the lobby (min x 18.0). | 35.7 | 6.5 | 35 (16) | 6 | 33 |

- **Observed:** s03 never fired its door trigger in either round, so s03 dynamic was the
  initial layout. s03 failed all six arms in R13 and R13G, and in R12 too. R11 passed s03
  initial and final.
- **Inferred:** in 14 of 23 failures the first broken link is P → M ("walls"). The other 9
  are s01/s02 dynamic runs where the switch comes first, the verify verdict is correct, and the
  run then dies of walls or of a pick on the wrong side. No failure starts at the verify verdict
  itself. Verify's geometry (timeouts at or near the vantage) costs a further 6–12 steps in 5
  runs. Verify cuts one run short at an open door: R13 s02va final.

---

## 2. Verify stage

`verify.py`, `sight.py`. 26 episodes in all, 15 in R13 and 11 in R13G.

| | R13 | R13G |
|---|---|---|
| vantage sighting genuine / stale / hallucinated | 1 / 2 / 12 | 0 / 2 / 9 |
| episodes resting on a single hallucinated look (no genuine sighting at all) | 9 | 7 |
| ending reacquired / failed / timeout / run end | 1 / 8 / 4 / 2 | 0 / 7 / 4 / 0 |
| `verify_failed` with the goal truly in line of sight at the check look | **0 / 8** | **0 / 7** |
| perceiver said "not visible" at every failed check | yes | yes |
| vantage reached; median steps to it | 11/15; 2 | 10/11; 2 |
| episodes with ≥ 2 turn-arounds in a row | 5 | 6 |
| verify steps in the round | 72 | 64 |

- **Observed:** the s02 dynamic pattern is the same in all 8 runs. The goal is genuine at steps
  0–2, stale at step 3, and often hallucinated on the first post-switch frame (step 4: "a glowing
  red sphere located above the door", R13 s02a dyn). The vantage is that last report, and the
  check correctly finds a shut door.
- **Observed:** g05 never missed a goal that was in frame with line of sight (116 of 116 in
  R13, 98 of 98 in R13G). Hallucinations: 12 of 133 reports in R13 and 11 of 114 in R13G
  (R11: 21 of 170).
- **Observed:** 5 of 8 timeouts reached the vantage but never produced a check look:
  - R13 s02c dyn s17–26, R13 s02vc dyn, R13G s02va final, R13G s03 final, R13G s02va dyn.
  - Turning to face the seen bearing (|Δh| ≤ 39.5°) takes a fan move of 1.7 m, which leaves the
    1.5 m vantage circle. The target flips back to `verify_vantage` and the drone oscillates
    (R13G s02va dyn s7–13).
  - The other 3 timeouts never got back the 1.7 m because of turn-around ping-pong on all-walled
    looks (R13 s03 initial s1–10, R13 s03 dyn, R13G s02vc dyn).
- **Inferred:** the hypothesis assumed lost goals that were really there. Here the "lost" goals
  were either truly occluded by the switch or were never there. Verify cost about 3–10 steps per
  episode and saved none. It also pulled the drone off an open door once (R13 s02va final s58).

---

## 3. Walls, reach and turn-arounds: R13 against R12 and R11

`strips.py`, `floor_end.py`, `repeat.py`, `ta.py`. All 18 runs per round unless marked f+d.

| | R11 (g03) | R12 (a19) | R13 (a20) | R13G (a21) |
|---|---|---|---|---|
| strips read `blocked_near` | 17% | 48% | 49% | 47% |
| of those, truly blocked < 1.9 m | 78% | 13% | 12% | 12% |
| truly open strips (≥ 1.9 m) read `blocked_near` | 5% | 45% | 47% | 45% |
| looks with all 5 strips blocked | 10% | 35% | 38% | 36% |
| mean max distance from start, final / dynamic (m) | 24.0 / 20.3 | 11.8 / 14.6 | 14.4 / 15.5 | 13.4 / 13.6 |
| mean turn-arounds per run, final / dynamic | 5.2 / 9.7 | 19.2 / 21.8 | 22.8 / 21.0 | 20.2 / 24.3 |
| f+d: turn-arounds share of steps; back-to-back | 15%; 0 | 34%; 82 | 37%; 96 | 37%; 89 |
| f+d: turn-arounds with "wall close" on all 5 moves; of those with a move truly clear 1.9 m | 58; 33% | 211; 94% | 220; 91% | 218; 90% |
| f+d collisions | 53 | 3 | 5 | 14 |

g05's raw `floor_end` against true clear distance (R13, 4405 strips):

| answer | n | < 1 m | 1–1.9 | 1.9–4 | 4–8 | ≥ 8 m |
|---|---|---|---|---|---|---|
| no_floor | 489 | 26% | 19% | 12% | 8% | 35% |
| bottom | 1678 | 1% | 2% | 9% | 25% | 63% |
| lower | 604 | 2% | 2% | 14% | 22% | 60% |
| middle | 1634 | 0% | 1% | 8% | 18% | 72% |

- **Observed:** across R12, R13 and R13G, `no_floor` catches 82% of truly blocked strips under
  1 m. But 55% of `no_floor` reads are truly clear past 1.9 m.
- **Observed:** on 103 repeated identical views in R13, 49% of strips got the same `floor_end`
  answer (R12 53%, R13G 51%). 50 of the 103 looks flipped between all-walled and not.
- **Inferred:** with a18's map (`bottom` → open, as a22 and a23 fly in R14), R13's own f+d
  answers would give 37 all-walled looks of 720 instead of 284. That removes most forced
  turn-arounds. It still leaves `no_floor` as the only wall signal, at 45% precision, and leaves
  `bottom`, `lower` and `middle` indistinguishable for reach.

---

## 4. Strategist (q04 / q05)

`strat.py` (truth: site-model flood fill from the drone, gain = how much nearer the true goal).

| | R12 q04 | R13 q04 | R13G q05 |
|---|---|---|---|
| calls (initial / final / dynamic) | 208 (32/88/88) | 146 (31/62/53) | 163 (26/61/76) |
| picks: frontier / doorway / explore | 166 / 11 / 23 | 124 / 3 / 17 | 127 / 17 / 14 |
| pick truly reachable | 178/185 | 127/129 | 145/149 |
| pick ≥ 3 m nearer the goal / ≥ 3 m farther | 6 / 18 | 8 / 24 | 13 / 9 |
| menus with a ≥ 3 m-nearer item; that item picked | 31; 4 | 32; 7 | 27; 11 |
| mean gain of pick, final / dynamic (m) | −0.1 / −0.4 | +0.2 / −1.6 | +0.5 / +0.2 |
| median distance to pick, f+d (m) | 2.2 | 2.4 | 2.3 |
| doorway items within 2.5 m of the true open door (s02 f+d) | | 1 of 23 | 0 of 18 |

- **Observed:** a17's reachability fix holds: 98% of picks are truly reachable (R11: 34 of 37 frontier picks lay behind or inside a wall).
  But the menu is the walled map's, so items sit 2–3 m out.
- **Observed:** doorways are placed at the end of the (short) strip reach, not at the door.
  - When the open door was in frame, g05 flagged its strip a doorway in 74% (R13) and 76% (R13G)
    of those looks. Base rate: 16% of all strips.
  - So the signal exists, but the menu item lands in mid-room.
- **Observed:** R13G's strategist reads the goal words. 97 of 137 f+d reasons cite "nearer" and
  121 cite the known position. But 118 of 137 also repeat "the goal has not been seen yet", which
  stands next to "The goal's position is known" in the same text, and 131 of 137 choose mode
  `explore`.
- **Inferred:** goal truth moved picks toward the goal side when the menu offered one (11/27
  against 7/32) and halved the goal-ward losses (9 against 24). With a menu of 2–3 m frontiers
  inside the start room there was nothing on the goal side worth picking. R13G's prediction
  ("final higher") is not met: 0/6 both.
- **Observed:** with the goal in view, the goal stage sent "the way toward the goal is shut" to
  the strategist 30 times in R13, 28 of them with the goal truly in line of sight. So 32 of 116
  goal-in-view steps carried a detour target. Every one was a false wall. R13G: 21, 19, 21/98.

---

## 5. Navigator: "toward your target"

`nav.py`. The share of steps where the picked action carried the "toward" note.

| | R11 | R12 | R13 | R13G |
|---|---|---|---|---|
| "toward" on a forward move, followed (all arms) | 287/407 (71%) | 315/482 (65%) | 303/486 (62%) | 302/487 (62%) |
| same, f+d | 69% | 62% | 57% | 56% |
| "toward" on [0] (turn around), followed (all arms) | 43/228 (19%) | 145/197 (74%) | 149/218 (68%) | 149/200 (74%) |
| same, f+d | 18% | 78% | 70% | 80% |
| f+d steps with no "toward" on any action; turned around there | 68; 47 | 155; 91 | 155; 107 | 156; 100 |

- **Observed:** "toward" never sits on a "wall close" move, because wall-aware "toward" drops
  it. In R13, 155 of 720 f+d steps had no "toward" at all, and the navigator turned around on
  69% of them.
- **Observed:** when the navigator does not follow a forward "toward", it takes another
  forward move 137 of 163 times in R13 f+d and turns around 26 times. In the timelines that
  move is usually tagged "new ground".
- **Inferred:** the R11 navigator ignored "toward" on [0], which was right there because the
  targets were phantoms. The a20 navigator follows it 70–80% of the time, and on 91%-false walls
  that is the ping-pong. p15 and p16's aim (raise [0] following; p15's probe: 18% → 31% on R11)
  would worsen this agent family. For a20–a23 the turn-around is over-followed, not
  under-followed.

---

## 6. What to change next, ranked

1. **Perceiver: a floor reading that carries distance and is stable.**
   - **Evidence:** 47% of open strips read walled, and `bottom`/`lower`/`middle` share one
     profile. Self-agreement on identical views is 49%. 220 of 263 f+d turn-arounds were forced
     by "wall close" on all moves, 91% of them with a truly clear move. Max distance from start
     is 14 m against R11's 22 m.
   - R14 (a18's map) treats the symptom. It cuts all-walled looks from 284 to 37 of 720 on R13's
     answers, but `no_floor` stays the only wall signal (45% precise).
   - **Proposal:** fly g06 (wall_at_bottom, runs_on, bottom edge first). Better still, a
     perceiver question matched to the five fan moves: "does floor run at least 2 m this way?"
     (yes/no), since only the first 1.9 m decides a move's note.
   - **Gate it offline:** on the flight host's frames, score `floor_end`/clearance against
     `true_reach` (each answer class must separate by distance) and self-agreement on R13's 103
     repeated views (target ≥ 80%).
2. **Perceiver + map: place doorways where the door is.**
   - **Evidence:** g05 flags the open door's strip on 74–76% of looks where it is in frame, but
     only 1 of 41 doorway menu items lay within 2.5 m of a true open door. Four f+d runs came
     within 1.3 m of the open door's mouth and turned away from it: R13 s02va final, R13G s02a
     final, R13G s02vc final, R13G s02a dynamic.
   - **Proposal:** add a doorway range answer to the perceiver (near / mid / far, as
     `goal_range`) and place the opening at that range on the flagged strip, not at the strip's
     reach.
3. **Strategist: fewer, farther, goal-coherent options.**
   - **Evidence:** picks are a median 2.4 m away, the mean gain is about 0, and only 27–32
     menus per round held a goal-ward item. In R13G, 118 of 137 reasons say "not seen yet" next
     to the known position.
   - **Proposal:** after fix 1, offer one item per direction sector at ≥ 4 m, rank doorways by
     the new range, and in q05's text drop "has not been seen yet" when the position is known.
     With a17's reachable menu this cannot bring back R11's phantoms.
4. **Navigator / turn rule: stop the back-to-back turn-around.**
   - **Evidence:** 96 back-to-back turn-arounds (13% of R13 f+d steps) return the drone to a
     view it saw two steps earlier, and g05 flips its walls on 40% of re-read strips. The
     navigator follows "toward" on [0] 70–80% of the time.
   - **Proposal:** a navigator prompt (VLM side) saying that marker 0 right after a turn-around
     only shows the view just left, and that it should judge "wall close" against its own image,
     since it sees the frame. Rank "toward" on forward moves first, not p16's [0]-inclusive
     ranking.
   - The minimal code fallback: no turn-around twice in a row.
5. **Verify and goal stages: keep the disproof, fix the geometry, confirm sightings first.**
   - **Evidence:** 0 of 15 wrong failed checks, but 0 or 1 reacquired per round. 5 of 8
     timeouts reached the vantage and could not face the bearing within its 1.5 m circle using
     1.7 m moves. 21 of 26 episodes rested on hallucinated sightings. Verify took 136 steps in all. In
     the goal stage, 28 of 30 "way shut" asks came with the goal in line of sight.
   - **Proposal:**
     - Count the look after a turn-around at the vantage as the check, or widen the circle to
       ≥ 1.8 m.
     - Add a goal-confirm perceiver question on the reported strip (e.g. a crop: "is a glowing
       red sphere visible here?") before entering the goal stage. That is VLM-side and would
       remove most episodes before they start.
     - Do not ask for a detour while the perceiver reports the goal "about one move ahead".
