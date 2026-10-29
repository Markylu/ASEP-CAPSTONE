# R23: R22 with the doorway tags fixed and navigator p18

**Agent:** `a44` (`30ea1bbd00f1`) · **Prompt:** `p18` (`ca21545ba479`) · **Memory:** `a17c` ·
**Status:** pre-registered 2026-10-29; **not flown, probe gate failed**

Written before flying. Spec: `docs/phase2-test-plan.md`. From the R19/R19K s02 failure analysis
([../R19_searched_defined/s02_failure_analysis.md](../R19_searched_defined/s02_failure_analysis.md),
proposal 2). R23K (`a45`, `1351a77e64f3`) is the same on `a43`; neither flies.

## Change

One against `a42` (R22), in two parts:
- **Memory `a17c`** (`spatial.A17C`): a17b with an open doorway and a closed door tagged apart,
  "open doorway (seen now)" and "closed door (seen now)" (`WORDS_A17C`, appended to the sha). a17
  tagged "doorway (seen now)" on any strip with a doorway, closed ones included: 362 of 1188 such
  tags in R19/R19K.
- **Navigator `p18`** = p17 with those tags defined ("a closed door is a wall") and a new rule 2:
  an "open doorway (seen now)" move at or beside the "toward your target" move goes first,
  straight through the opening; "toward your target" often cuts across the door frame there.

## Evidence

- Mode K in the analysis: from the side of the open door nearer closed door B, the straight line
  to the goal clips the door frame on 197 of 202 steps; primary in 4 of 12 failed s02
  final/dynamic runs, and 2 more crossed too late. 36 moves straight through the door were not
  taken near it.

## Probe gate

Set before the probe: on recorded s02 steps where a forward move's 3 m segment crosses the
divider through an open door (`through`), p18 takes such a move on ≥ 70%; on 150 steps with an
open-doorway tag and no such move (`control`), doorway-tag picks at most the recorded rate + 5
points and truly blocked picks not above it.

Probe (`eval/r23_nav_probe.py`, live, on the host's R19 and R19K frames; notes worked out again in
a17c, text rendered with p18; baseline the recorded p17 pick;
[probe/p18_r19_score.txt](probe/p18_r19_score.txt)), 184 calls, 0 failed:

| set | | through move taken | doorway-tag move | truly blocked within 1.9 m |
|---|---|---|---|---|
| through (34) | p17, recorded | 21 | 13 | 4 |
| | p18 + a17c | **22 (65%)** | 15 | 3 |
| control (150) | p17, recorded | – | 93 (62%) | 11 |
| | p18 + a17c | – | **114 (76%)** | 11 |

**Failed** on both: one more through move in 34, and 14 points more doorway picks where no
doorway leads through. R19 had no doorway confirmer, so its control doorways are mostly false
ones `d01` would remove; even so the wording does not find the door where it is, and the gain on
`through` is within noise. Not flown. The tag fix (`a17c`) stays in the code for a later
navigator; proposal 1 of the analysis (a through-the-doorway detour placed by code from confirmed
sightings) is the next candidate for mode K.

## Outcome

Not flown (probe gate failed).
