# Probe a73: Round F replayed under the wall-turn rule and the a73 cost map

`python eval/probes/a73_replay.py` on `eval/phase2/final` (90 runs, 3304 steps), no model.
Readouts in [replay.txt](replay.txt); gates and reading in
[R33's README](../../R33_wall_turn_costmap/README.md#probe-gate). Open loop: a66 flew the
recorded picks; a73's memory, route and tags are computed from where a66 stood.

| Readout | a66 | a73 |
|---|---|---|
| Steps after a turn-around taken facing a wall | 327 | 327 |
| "toward your target" on the turn-around again | 33 | 9 (24 moved to an open move) |
| a66 turned around again | 41 | 30 of those turn-arounds hidden by a73's turn rule |
| s02 near-side routes crossing the divider inside the open door's gap | 85/1638 (5%) | 134/1638 (8%) |
| s03 shut-tine routes leaving by the crossbar after the closed read | 0/223 | 4/223 (2%) |

Cell classes under the route's wall crossings (a73's map, 1634 s02 crossings): strong floor
to strong floor 766, unknown to unknown 397, visited to strong floor 340, the rest suspects.
Offset of the crossing from the open door's centre: in the gap 67, under 3 m 131, under 6 m
244, six metres or more 1192. s03 shut-tine routes: 205 of 223 leave through strong-floor
cells (divider 141, outer wall 37, exit wall 27).
