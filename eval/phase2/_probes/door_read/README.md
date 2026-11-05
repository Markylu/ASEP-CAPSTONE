# Probe door_read: how g05 and d01 read the s02 doors, by range and angle

`python eval/probes/door_read.py` on the s02 runs of `eval/phase2/final`, R30, R32P and R35
(4256 near-side frames, every arm), no model: the reads are the ones recorded in flight.
Tables in [door_read.txt](door_read.txt). Angle is between the line of sight and the door's own
line (0 = square on). A door is read open when its centre's strip or a neighbour says so.

At 2–9 m:

| Angle off square | Open door read open, `g05` | After `d01` | Shut door read open after `d01` | Blank wall strip read open, `g05` | After `d01` |
|---|---|---|---|---|---|
| 0–20° | 158/158 | 157/158 | 1/283 | 15/366 | 1/366 |
| 20–40° | 40/41 | 36/41 | 1/89 | 40/939 | 17/939 |
| 40–60° | 90/92 | 67/92 | 3/131 | 73/346 | 33/346 |
| 60–90° | 162/231 | 112/231 | 79/522 | 133/393 | 76/393 |

- The reading is not weak at 2–4 m. Square on, the open door is read at every range from 2 m
  out (2–4 m: 27 of 28 after `d01`), and wall or a shut door is read open about once in 300.
- The reading fails with angle. Beyond 60° the open door is read half the time, and a fifth of
  wall strips and a seventh of shut doors come back open after `d01`.
- `d01` costs the open door from 40° on: it closed the door's own strip on 46 of 323 looks
  there, against 3 of 199 inside 40°.
- Under 2 m the door is read open on 14 of 21 square looks and 9 of 68 beyond 20°.
- The drone seldom looks square: 58 of 4256 frames are within 20° of square at 2–6 m.
