"""Q3b: g05's raw floor_end answers vs the site model's true clear distance along the strip's centre ray."""
import sys, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from r12_probe import true_reach  # noqa

OFF = {'far_left': 43.5, 'left': 21.75, 'centre': 0.0, 'right': -21.75, 'far_right': -43.5}
BINS = [(0, 1.0), (1.0, 1.9), (1.9, 4), (4, 8), (8, 99)]
for rnd in sys.argv[1:] or ['R12', 'R13', 'R13G']:
    t = collections.defaultdict(collections.Counter)
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            for r in rows:
                x, y, h = xyh(r)
                free = free_at(site, arm, r['step'])
                for s, l in lanes(r).items():
                    tr = true_reach(free, (x, y), h + OFF[s])
                    fe = l.get('floor_end')
                    b = next(i for i, (lo, hi) in enumerate(BINS) if lo <= tr < hi)
                    t[fe][b] += 1
                    t[fe]['n'] += 1
    print('==', rnd, 'floor_end: n | true clear <1, 1-1.9, 1.9-4, 4-8, >=8 m')
    for fe, c in t.items():
        print(f"  {str(fe):9s} {c['n']:5d} | " + ' '.join(f"{c[i]/c['n']:4.0%}" for i in range(len(BINS))))
