"""Perceiver consistency: looks taken twice from the same pose and heading (after two turn-arounds in place):
how often g05's floor_end answer per strip is the same, and how often the mapped class flips blocked<->open."""
import sys, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa

for rnd in sys.argv[1:] or ['R12', 'R13', 'R13G']:
    c = collections.Counter()
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            for i in range(len(rows) - 2):
                a, b = rows[i], rows[i + 2]
                pa, pb = xyh(a), xyh(b)
                if math.dist(pa[:2], pb[:2]) > 0.05 or abs(spatial.wrap(pa[2] - pb[2])) > 2:
                    continue
                if b['step'] - a['step'] != 2:
                    continue
                La, Lb = lanes(a), lanes(b)
                c['pairs'] += 1
                for s in STRIPS:
                    fa, fb = (La.get(s) or {}).get('floor_end'), (Lb.get(s) or {}).get('floor_end')
                    c['strips'] += 1
                    c['same_end'] += fa == fb
                    ba, bb = (La.get(s) or {}).get('floor') == 'blocked_near', (Lb.get(s) or {}).get('floor') == 'blocked_near'
                    c['class_flip'] += ba != bb
                c['look_flip'] += (all((La.get(s) or {}).get('floor') == 'blocked_near' for s in STRIPS)
                                   != all((Lb.get(s) or {}).get('floor') == 'blocked_near' for s in STRIPS))
    print(f"{rnd}: repeated looks {c['pairs']}; strips with the same floor_end {c['same_end']/max(1,c['strips']):.0%}; "
          f"strips flipping blocked_near<->open {c['class_flip']/max(1,c['strips']):.0%}; looks flipping all-walled {c['look_flip']}/{c['pairs']}")
