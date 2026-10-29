"""Q1 support: for each final/dynamic failure, the way through (s02: the open door's mouth on the start
side; s01: past the cube; s03: progress down the fork), how close the drone came, whether the open door was
truly in frame and what the perceiver said about that strip, and the side of each strategist pick."""
import sys, math, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa

OFF = {'far_left': 43.5, 'left': 21.75, 'centre': 0.0, 'right': -21.75, 'far_right': -43.5}


def strip_of(rel):
    import math as m
    half = spatial.FOV_DEG / 2
    if abs(rel) > half:
        return None
    u = m.tan(m.radians(rel)) / m.tan(m.radians(half))
    return STRIPS[next((i for i, e in enumerate((0.6, 0.2, -0.2, -0.6)) if u > e), 4)]


for rnd in sys.argv[1:] or ['R13', 'R13G']:
    print('==', rnd)
    for arm in ('final', 'dynamic'):
        for site in SITES:
            rows, met = load(rnd, site, arm)
            s = summary(rows, met)
            minx = min(xyh(r)[0] for r in rows)
            out = f"{site:5s} {arm:7s} {'OK' if s['ok'] else '--'} dfin {s['dfin']:4.1f} maxd {s['maxd']:4.1f} TA {s['ta']:2d} C {s['coll']} minx {minx:5.1f}"
            if site.startswith('s02'):
                yd = 9.0 if site in ('s02a', 's02va') else -9.0
                mouth = (1.5, yd)
                dmin = min(math.dist(xyh(r)[:2], mouth) for r in rows)
                inframe = flagged = 0
                for r in rows:
                    x, y, h = xyh(r)
                    free = free_at(site, arm, r['step'])
                    if yd not in [9.0 * (1 if d == 'A' else -1) for d in geo.open_doors(site, arm, r['step']) if d != 'B']:
                        continue
                    gap = (0.0, yd)
                    rel = spatial.wrap(spatial.bearing((x, y), gap) - h)
                    st = strip_of(rel)
                    if st and geo.segment_clear(lambda a, b: free(a, b) or abs(a) <= 0.5, (x, y), (0.6 if x > 0 else -0.6, yd)):
                        inframe += 1
                        flagged += bool((lanes(r).get(st) or {}).get('doorway'))
                sides = collections.Counter()
                for r in rows:
                    st = r.get('strategist')
                    if not st:
                        continue
                    p = (st.get('result') or {}).get('target')
                    it = next((m for m in st.get('menu') or [] if m['id'] == p), None)
                    if it is None:
                        sides['explore'] += 1
                    else:
                        sides['door side' if it['y'] * yd > 1.5 * abs(yd) / 9 * 1 and abs(it['y']) > 1.5 else ('other side' if abs(it['y']) > 1.5 else 'middle')] += 1
                out += f" | open door mouth min {dmin:4.1f} m; door in frame {inframe} looks, doorway flagged on its strip {flagged}; picks {dict(sides)}"
            print(out)
