# Probe a76: the door approach pose replayed on flown runs

`python eval/probes/a76_replay.py` on the change arms of `eval/phase2/final`, R32P and R35 (110
runs: 88 s02, 22 s03), no model. Readouts in [replay.txt](replay.txt); reading in
[R36's README](../../R36_door_approach/README.md#probe-gate). Open loop.

s02 near side, lost runs: the rule fires on the true open door on 15 steps (4 of 45 runs), on
other doorways on 190. Won runs: 49 steps on the door, 154 on others. Within 4 m of the door
the waypoint points at it on 30 of 175 steps in lost runs with or without the rule, and on 63
of 206 against 72 in won runs. s03: 12 of 103 fires are on an exit door.

The door is rarely in the memory: a live doorway within 2 m of it on 8% of lost runs'
near-side steps, and `g05` with `d01` read it open on 33% of the steps it was within 45° of
the heading inside 4 m.
