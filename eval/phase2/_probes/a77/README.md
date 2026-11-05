# Probe a77: doorway reads trusted by the look, replayed on flown runs

`python eval/probes/a76_replay.py --agent a77` on the change arms of `eval/phase2/final`, R32P
and R35 (110 runs), no model. Readouts in [replay.txt](replay.txt); reading in
[R37's README](../../R37_trusted_doorways/README.md#probe-gate). Open loop: a look's effect on
the next frame is not simulated.

Against a76 in lost s02 runs: approach steps on the true open door 15 → 22, on other doorways
190 → 28, plus 63 look steps (1 on the door). The trusted memory holds a doorway at the door
on 167 of 2480 near-side steps and 186 doorway-steps elsewhere (a66: 192 and 1532). Within 4 m
of the door the waypoint points at it on 29 of 175 steps (as flown 30). Won runs: the route
crosses inside the door's gap on 63 of 1066 steps against 85 as flown.

The trust rule (`python eval/probes/door_trust.py`): of 1675 strip reads of an open doorway,
856 on the door; centre strip with a level look 415 on the door and 54 off it.
