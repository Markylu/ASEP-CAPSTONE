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

**Failed** (2026-10-30), 3 of 5 checks. The gate was committed first (`f7e83e3`). Output:
[score.txt](score.txt).
- Set F: 576 frames, 1728 calls, none failed.
- Concurrency 1: half the frames on `:8004` with no flights running, half on a `:8006` copy on GPU 3,
  stopped afterwards.
- Median latency: `g05` 1.34–1.45 s, `g07` 0.83–0.95 s.

| Read | F missed | F phantom | F s03 phantom | F doorway | P missed | P phantom |
|---|---|---|---|---|---|---|
| `g05` (a49) | 16.5% | 9.4% | 9.7% | 89.9% | 16.5% | 11.7% |
| `g07` | 2.5% | 35.3% | 64.7% | 86.7% | 6.3% | 26.2% |
| `g07` mirrored | 2.5% | 36.3% | 64.4% | 85.6% | 2.5% | 26.4% |
| a60 (image-right) | 2.8% | 28.5% | 58.9% | 87.3% | 5.1% | 17.0% |
| **agree** | **3.8%** | **23.6%** | **55.3%** | 87.3% | **7.6%** | **11.8%** |

| | Gate | Value | |
|---|---|---|---|
| 1 | F missed ≤ half of `g05`'s | 3.8% vs 16.5% | pass |
| 2 | F phantom ≤ `g05` + 2 pts | +14.2 pts | FAIL |
| 3 | F s03 phantom ≤ `g05` + 4 pts | +45.6 pts | FAIL |
| 4 | F doorway ≥ `g05` − 2, goal ≥ `g05` − 1 | −2.6 / +1.4 pts | FAIL |
| 5 | P missed ≤ half, phantom ≤ `g05` + 2 | 7.6% vs 16.5%, +0.1 pts | pass |

Reading:
- **On the old sample the rule works.** On set P, `agree` brings phantom walls back to `g05`'s
  (11.8% vs 11.7%) and keeps most of the missed-wall gain (7.6% vs 16.5%).
- **On the frames a60 flew it does not.** On R27's s03 frames, both `g07` reads call about 65% of
  open strips walls, and they call the same ones. That is not the image-side bias the mirror was
  for, so neither fusion can remove it (a60 59%, agree 55%). `g05` reads the same frames at 9.7%.
- **The phantom walls come from the prompt.** `g07` is `g05` without the describe-first paragraph.
  On these views, dropping that paragraph is what produces the walls. The missed-wall gain and the
  phantom-wall cost come from the same change.
- **Not batching.** Fresh reads at concurrency 1 match the reads R27 recorded in flight (`g07`
  35.3% vs 36.0% phantom; a60 28.5% vs 28.2%).
- **Doorway** fell 2.6 pts against `g05` on these frames; on set P it was −1.7.

The agree rule does not fly.
