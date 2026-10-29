"""Q3: share of strips read blocked_near per round (and per arm), and how many were truly blocked
within 1.9 m (one move + margin) by the site model; plus max distance from start and turn-arounds."""
import sys, collections, statistics
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from r12_probe import true_reach  # noqa

OFF = {'far_left': 43.5, 'left': 21.75, 'centre': 0.0, 'right': -21.75, 'far_right': -43.5}
for rnd in sys.argv[1:] or ['R11', 'R12', 'R13', 'R13G']:
    agg = collections.Counter()
    per_arm = collections.defaultdict(collections.Counter)
    runs = []
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            c = collections.Counter()
            for r in rows:
                x, y, h = xyh(r)
                free = free_at(site, arm, r['step'])
                for s, l in lanes(r).items():
                    if s not in OFF:
                        continue
                    tr = true_reach(free, (x, y), h + OFF[s])
                    f = l.get('floor')
                    c['n'] += 1
                    c[f] += 1
                    if f == 'blocked_near':
                        c['bn_true'] += tr < 1.9
                    else:
                        c['open_but_true_blocked'] += tr < 1.0
                    c['true_open'] += tr >= 1.9
                    c['true_open_read_bn'] += (tr >= 1.9 and f == 'blocked_near')
            # all-five-blocked looks
            c['all5'] = sum(all((l.get('floor') == 'blocked_near') for l in lanes(r).values()) and len(lanes(r)) == 5 for r in rows)
            c['looks'] = len(rows)
            s = summary(rows, met)
            runs.append((site, arm, c['blocked_near'] / max(1, c['n']), s))
            agg.update(c)
            per_arm[arm].update(c)
            per_arm[arm]['maxd'] += s['maxd']
            per_arm[arm]['ta'] += s['ta']
            per_arm[arm]['runs'] += 1
    print(f"== {rnd}: strips {agg['n']}, read blocked_near {agg['blocked_near']/agg['n']:.0%}, "
          f"of those truly blocked <1.9 m {agg['bn_true']/max(1,agg['blocked_near']):.0%}; "
          f"truly open (>=1.9 m) strips read blocked_near {agg['true_open_read_bn']/agg['true_open']:.0%}; "
          f"looks with all 5 blocked_near {agg['all5']}/{agg['looks']} ({agg['all5']/agg['looks']:.0%})")
    for arm in ARMS:
        c = per_arm[arm]
        print(f"   {arm:7s} blocked_near {c['blocked_near']/c['n']:.0%}  all5 {c['all5']/c['looks']:.0%}  mean maxd {c['maxd']/c['runs']:.1f} m  mean TA {c['ta']/c['runs']:.1f}")
    print('   per run (bn share, maxd, TA):', ' '.join(f"{s}/{a[0]}:{b:.0%},{v['maxd']:.0f},{v['ta']}" for s, a, b, v in runs))
