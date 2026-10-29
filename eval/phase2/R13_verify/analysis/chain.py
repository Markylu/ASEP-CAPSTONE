"""Q1 digest per final/dynamic failure: stage steps, all-five-walled looks, steps with no 'toward' move,
turn-arounds (and back-to-back pairs), strategist triggers, menu items at the way through, closest approach."""
import sys, math, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa


def way(site):
    """Points the drone must pass (map coords): s02 the open door's start-side mouth; s01 beside the cube;
    s03 the stem mouth then the crossbar."""
    if site in ('s02a', 's02va'):
        return [(1.5, 9.0)]
    if site in ('s02c', 's02vc'):
        return [(1.5, -9.0)]
    if site == 's01':
        return [(3.0, 6.0), (3.0, -6.0)]
    return [(15.5, 0.0), (6.5, 0.0)]


for rnd in (sys.argv[1:] or ["R13", "R13G"]) if __name__ == "__main__" else []:
    print('==', rnd)
    for arm in ('final', 'dynamic'):
        for site in SITES:
            rows, met = load(rnd, site, arm)
            if met['goal_reached']:
                continue
            s = summary(rows, met)
            st = collections.Counter(stage(r) for r in rows)
            all5 = sum(len(lanes(r)) == 5 and all(l.get('floor') == 'blocked_near' for l in lanes(r).values()) for r in rows)
            notw = sum(not any('toward your target' in t for v in (r.get('tags') or {}).values() for t in v) for r in rows)
            pairs = sum(is_ta(rows[i]) and is_ta(rows[i + 1]) for i in range(len(rows) - 1))
            trig = collections.Counter()
            near_way = 0
            W = way(site)
            for r in rows:
                sg = r.get('strategist')
                if not sg:
                    continue
                t = sg.get('trigger', '')
                trig[t.split(';')[0][:22]] += 1
                near_way += any(min(math.dist((m['x'], m['y']), w) for w in W) < 3.0 for m in sg.get('menu') or [])
            dway = min(math.dist(xyh(r)[:2], w) for r in rows for w in W)
            print(f"{site:5s} {arm:7s} dfin {s['dfin']:4.1f} maxd {s['maxd']:4.1f} TA {s['ta']:2d} (pairs {pairs:2d}) C {s['coll']} | "
                  f"stages e{st['explore']} g{st['goal']} v{st['verify']} | all5 {all5:2d} no-toward {notw:2d} | way min {dway:4.1f} m, "
                  f"calls {sum(trig.values())} w/ menu item <3 m of the way {near_way} | {dict(trig)}")
