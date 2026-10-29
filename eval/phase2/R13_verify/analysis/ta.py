"""Turn-arounds in final+dynamic: share of steps, back-to-back (a turn-around right after one: the view returns
to one already seen), the notes on the turn-around and on the forward moves when it was picked, and collisions."""
import sys, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa

for rnd in sys.argv[1:] or ['R11', 'R12', 'R13', 'R13G']:
    c = collections.Counter()
    for arm in ('final', 'dynamic'):
        for site in SITES:
            rows, met = load(rnd, site, arm)
            c['coll'] += met['collisions']
            prev = False
            for r in rows:
                c['steps'] += 1
                t = is_ta(r)
                c['ta'] += t
                c['ta2'] += t and prev
                if t:
                    tags = {int(i): v for i, v in (r.get('tags') or {}).items()}
                    fw = [tags.get(i, []) for i in range(1, 6)]
                    c['ta_allwall'] += all(any('wall close' in x for x in v) for v in fw)
                    c['ta_toward0'] += any('toward your target' in x for x in tags.get(0, []))
                prev = t
    print(f"{rnd:4s} final+dynamic steps {c['steps']}: turn-arounds {c['ta']} ({c['ta']/c['steps']:.0%}), back-to-back {c['ta2']}; "
          f"of the turn-arounds, every forward move 'wall close' {c['ta_allwall']}, [0] tagged toward {c['ta_toward0']}; collisions {c['coll']}")

# How often a turn-around forced by "wall close" on every forward move had a forward move truly clear for 1.9 m
# (the move's own heading, site model).
from r12_probe import true_reach  # noqa: E402
for rnd in sys.argv[1:] or ['R12', 'R13', 'R13G']:
    n = clear = 0
    for arm in ('final', 'dynamic'):
        for site in SITES:
            rows, met = load(rnd, site, arm)
            for r in rows:
                if not is_ta(r):
                    continue
                tags = {int(i): v for i, v in (r.get('tags') or {}).items()}
                if not all(any('wall close' in x for x in tags.get(i, [])) for i in range(1, 6)):
                    continue
                x, y, h = xyh(r)
                free = free_at(site, arm, r['step'])
                n += 1
                clear += any(true_reach(free, (x, y), h + a['theta_deg']) >= 1.9
                             for a in r['manifest']['actions'] if not a.get('turn_around'))
    print(f"{rnd}: all-'wall close' turn-arounds {n}, with a forward move truly clear >= 1.9 m {clear} ({clear/max(1,n):.0%})")
