# Probe a74: Round F replayed on a map where only visited ground is known

`python eval/probes/a74_replay.py` on `eval/phase2/final` (90 runs, 3304 steps), no model.
Readouts in [replay.txt](replay.txt); reading in
[R34's README](../../R34_visits_only_map/README.md#probe-gate). Open loop.

a74 against a73: s03 routes out of the shut tine 2% → 10%; the divider's walled rows on the map
at the end of failed s02 runs 65% → 73% (a66 58%); s02 routes through the true gap 8% → 9%.
Cost: true gap impassable on 11% of s02 near-side steps (6%), no route on 5% of all steps (0%).
Variants not carried: ray floor at 3 per metre; closing one- to three-cell holes in wall lines.
