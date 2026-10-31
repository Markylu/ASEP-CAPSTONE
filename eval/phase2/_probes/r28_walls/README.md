# Probe R28 walls: four more wall readers (k01, w02, w03, w04)

Script: `eval/probes/r28_walls.py`, committed before any call (`9f694ce`). Gate and method:
[R28 README](../../R28_wall_reader/README.md), "Probe gate, second attempt". Output:
[score.txt](score.txt), w04's fit: [w04_fit.json](w04_fit.json).

## Belief

W01 showed the missed walls do not come from the task load: describe-first reads walls the same
with one job or three. So the next reader has to change what the model is asked or shown, or skip
the model:
- `k01` asks again only about the strips `g05` read open (wall or floor at the bottom edge);
- `w02` shows the five strips as five crops;
- `w03` draws the strip boundaries on the frame;
- `w04` is a code rule on the bottom twelfth of each strip, fitted on C1.

## Run

2026-10-30 to 2026-10-31, on `phase2/r28-wall-reader` at `9f694ce` (checkout `~/asep-r28-probe` on
sctsvr6).
- 3528 model calls (`k01`, `w02`, `w03` on F 576, P 300, C2 300) and w04's features on those
  frames and C1 300. `g05`'s reads are the recorded ones.
- Four shards, one call at a time each: `:8004` (no flights running) and three copies on GPUs 3–5
  (`:8006`–`:8008`, same image and flags), stopped afterwards. The SSH link dropped mid-run. The
  shards ran under nohup and all finished.
- 1 call failed (`w03`, set F). As in flight, a failed read leaves `g05`'s floors.
- Median latency: `k01` 1.19 s, `w02` 1.94 s, `w03` 1.58 s. `w04` is about 0.6 s of CPU per frame.
- w04 fit on C1 only: 1165 strips `g05` read open, 40 of them truly blocked. The threshold is 0.119,
  capped so its added C1 phantoms are ≤ 1.5% of C1's 1314 open strips.

## Result

**All four fail.** None meets both missed-wall checks. The winner rule picks none, so R28 does not
fly.

| Set | Read | Missed wall | Phantom wall | s03 phantom |
|---|---|---|---|---|
| F | `g05` | 16.5% | 9.4% | 9.7% |
| F | `k01` | 9.8% | 25.8% | 27.6% |
| F | `w02` | 23.1% | 22.0% | 34.2% |
| F | `w03` | 40.2% | 10.4% | 7.3% |
| F | `w04` | 12.3% | 10.7% | 10.8% |
| P | `g05` | 16.5% | 11.7% | 19.8% |
| P | `k01` | 12.7% | 26.9% | 42.4% |
| P | `w02` | 29.7% | 21.6% | 25.4% |
| P | `w03` | 43.7% | 10.0% | 9.6% |
| P | `w04` | 13.3% | 12.8% | 20.9% |
| C2 | `g05` | 17.0% | 14.6% | 9.1% |
| C2 | `k01` | 11.7% | 25.6% | 18.9% |
| C2 | `w02` | 24.0% | 21.4% | 24.4% |
| C2 | `w03` | 53.8% | 11.8% | 6.1% |
| C2 | `w04` | 11.1% | 16.4% | 10.4% |

| Gate | `k01` | `w02` | `w03` | `w04` |
|---|---|---|---|---|
| F missed ≤ half of `g05`'s (8.25%) | FAIL 9.8% | FAIL 23.1% | FAIL 40.2% | FAIL 12.3% |
| F phantom ≤ `g05` + 2 pts | FAIL +16.4 | FAIL +12.5 | pass +1.0 | pass +1.2 |
| F s03 phantom ≤ `g05` + 4 pts | FAIL +17.9 | FAIL +24.5 | pass −2.4 | pass +1.1 |
| P missed ≤ half of `g05`'s (8.25%) | FAIL 12.7% | FAIL 29.7% | FAIL 43.7% | FAIL 13.3% |
| P phantom ≤ `g05` + 2 pts | FAIL +15.2 | FAIL +9.9 | pass −1.7 | pass +1.1 |
| Checks passed | 0 of 5 | 0 of 5 | 3 of 5 | 3 of 5 |

Reading:
- **`k01` does what `g07` did.** Asked "wall or floor?" about strips already read open, the model
  says wall often enough to cut missed walls by 25–40%. It also says wall on 15–16 more points of
  truly open strips, and 28–42% of them on s03. That is R27's phantom-wall pattern, the one that
  brought the turn-around loops.
- **Crops (`w02`) make both errors worse.** Missed and phantom walls both rise, and s03 phantom
  walls reach 25–34%. A likely reason is that a crop loses the depth cues the full frame gives.
- **Drawn boundaries (`w03`) push the model toward open floor.** Phantom walls hold or fall, but it
  misses 40–54% of real walls.
- **`w04` is the only reader that trades well.** It cuts missed walls by a quarter on F and P (and
  by 35% on C2) for about +1 pt of phantom walls, inside the cap it was fitted to. That is still far
  from half.
- **No threshold would have saved `w04`.** On C1, its fit set (F and P were not used for this),
  catching a quarter of the walls `g05` reads open costs +0.2 pts of phantom walls; half costs +3.0;
  three quarters +11.1. Halving the missed rate needs about half of those walls caught, so it costs
  more than the gate's +2. The bottom band's brightness, edges and colour do not separate a near
  wall from near floor well enough.

## What this leaves

R28 has now probed five wall readers (`w01`, `k01`, `w02`, `w03`, `w04`). The model readers share
one trade-off:
- with describe-first wording (`g05`, `w01`), they read about 1 in 6 real walls as open;
- every way of making them say "wall" more often (`g07`, `k01`) adds phantom walls at a similar
  rate, on the same frames (s03).

`w04` is the only reader that moves off that line, and only a little. Candidates for a later round,
each a new version with its own gate:
- `w04` with features that carry depth: where the floor/wall edge sits in the strip against where
  floor 1 m away would appear. The camera height and FOV give that image row.
- A smaller cut, flown. R25D flew with `g05`'s 16.5% missed walls and scored 14/18. A reader that
  cuts that by a quarter at +1 pt of phantom walls might still help in flight, though it fails a
  halve-it gate. Only the on-policy check and a flown round can test that, and it would need a new
  gate. Whether a smaller cut is worth a round is the operator's call.
