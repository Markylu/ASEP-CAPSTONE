# Probe AG: a wall only where both reads see one

Script: `eval/probes/agree.py`, which reuses `eval/r27_probe.py` (reads, calls) and
`eval/probes/c1f1.py` (truth). It follows from R27
([README](../../R27_mirrored_nr_perceiver/README.md), Outcome). Written before any call.

## Belief

R27 (`a60`: `g07` read plain and mirrored, image-right fusion) missed 2.5% of real walls in flight,
against R25D's 17.3%. But it read 28.2% of open strips as walls (60% on s03), and the s03 runs
ended stuck turning around. Each `g07` read sees too many walls, and the two reads do not always
see the same phantom ones. A wall that only one read sees is more often a phantom, so a strip
should be `blocked_near` only when both reads say so.

That should bring phantom walls back near `g05`'s while keeping most of the missed-wall gain.

## Method

- **Fusion `agree`.** Start from a60's image-right fusion (`orchestrator.image_right`). Where it
  reads `blocked_near` but the other read does not, take the other read's `floor` and `floor_end`.
  The doorway and the goal stay as in a60.
- **Set F: R27's own flight frames.** Every s02* and s03 step of R27 with a clean frame, from
  the lane checkouts on sctsvr6 (`~/asep-r27-l1..4`). These are the frames a60 met, including
  the s03 loops the earlier samples never had. Truth as in C1 (`c1f1.truth`), with each run's own
  world.
- **Reads on set F,** fresh, one call at a time per instance, on `:8004` (no flights running) and a
  `:8006` copy on GPU 3:
  - `g05` (a49's read);
  - `g07` on the frame;
  - `g07` on the frame mirrored by `server/decider/mirror.py`, swapped back.
- **Set P: R27's probe sample** (300 frames), scored again from its recorded calls. No new calls.
- **Also reported, not gated:** `agree` on the reads R27 recorded in flight (under batching).

## Gate

Set before any call. `agree` against `g05` on the same frames:

| | Set | Check |
|---|---|---|
| 1 | F | Missed walls ≤ half of `g05`'s |
| 2 | F | Phantom walls ≤ `g05`'s + 2 pts |
| 3 | F | Phantom walls on s03 ≤ `g05`'s on s03 + 4 pts |
| 4 | F | Doorway ≥ `g05` − 2 pts, goal strip ≥ `g05` − 1 pt |
| 5 | P | Missed walls ≤ half of `g05`'s, phantom walls ≤ `g05`'s + 2 pts |

If all hold, the next step is a round with `agree` fusion on a60, written up before it flies.
If not, the result is recorded here and the agree rule does not fly.

**Caveat.** Set F is a60's own path, which a60's phantom walls chose. An agent with `agree`
would fly other paths. Set F is a harder test than set P, not the same test as flying.

## Result

Not run.
