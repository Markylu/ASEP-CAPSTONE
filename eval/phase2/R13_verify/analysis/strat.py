"""Q4: strategist calls: what was picked (kind), how much nearer the true goal the pick is (gain),
whether the best-gain item was on the menu and picked, whether the pick is truly reachable (site model flood),
and per arm. Usage: strat.py [R13 R13G ...] [-v]"""
import sys, math, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from r12_probe import flood  # noqa

verbose = '-v' in sys.argv
rounds = [a for a in sys.argv[1:] if not a.startswith('-')] or ['R13', 'R13G']


def key(p, res=0.25):
    return (int(math.floor(p[0] / res)), int(math.floor(p[1] / res)))


for rnd in rounds:
    c = collections.Counter()
    gains = collections.defaultdict(list)
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            G = goal_xy(rows[0])
            for r in rows:
                s = r.get('strategist')
                if not s:
                    continue
                x, y, h = xyh(r)
                res = s.get('result') or {}
                menu = s.get('menu') or []
                pick = res.get('target')
                c[(arm, 'calls')] += 1
                c['calls'] += 1
                free = free_at(site, arm, r['step'])
                fl = flood(free, (x, y))
                item = next((m for m in menu if m['id'] == pick), None)
                kind = 'explore' if pick == 'explore' or item is None else item['kind']
                c['pick_' + kind] += 1
                if not menu:
                    c['empty_menu'] += 1
                gl = {m['id']: math.dist((x, y), G) - math.dist((m['x'], m['y']), G) for m in menu}
                rch = {m['id']: key((m['x'], m['y'])) in fl for m in menu}
                c['menu_items'] += len(menu)
                c['menu_unreach'] += sum(not v for v in rch.values())
                if menu:
                    best = max(gl, key=gl.get)
                    c['best_ge3'] += gl[best] >= 3
                    if pick == best and gl[best] >= 3:
                        c['picked_best_ge3'] += 1
                if item is not None:
                    gains[arm].append(gl[pick])
                    c['pick_gain_ge3'] += gl[pick] >= 3
                    c['pick_gain_le-3'] += gl[pick] <= -3
                    c['pick_reach'] += rch[pick]
                    c['pick_item'] += 1
                if verbose and arm != 'initial':
                    ms = ' '.join(f"{m['id'][:4]}{m['id'][-1]}({m['x']:.0f},{m['y']:.0f}){gl[m['id']]:+.0f}{'' if rch[m['id']] else '!'}" for m in menu)
                    print(f"{rnd} {site:5s} {arm[:3]} s{r['step']:2d} ({x:5.1f},{y:5.1f}) [{s.get('trigger','')[:28]:28s}] pick={pick} | {ms}")
    n = c['pick_item']
    print(f"== {rnd}: calls {c['calls']} (initial {c[('initial','calls')]}, final {c[('final','calls')]}, dynamic {c[('dynamic','calls')]}); "
          f"empty menu {c['empty_menu']}; picks: frontier {c['pick_frontier']}, opening {c['pick_opening']}, back {c['pick_back']}, explore {c['pick_explore']}, other {c['calls']-c['pick_frontier']-c['pick_opening']-c['pick_back']-c['pick_explore']}")
    print(f"   picks with a place: {n}; >=3 m nearer goal {c['pick_gain_ge3']} ({c['pick_gain_ge3']/max(1,n):.0%}); >=3 m farther {c['pick_gain_le-3']}; truly reachable {c['pick_reach']}/{n}; "
          f"menu items truly unreachable {c['menu_unreach']}/{c['menu_items']}")
    print(f"   calls whose menu held a >=3 m-nearer item: {c['best_ge3']}; picked that best item: {c['picked_best_ge3']}")
    for arm in ARMS:
        g = gains[arm]
        if g:
            print(f"   {arm:7s} mean gain of pick {sum(g)/len(g):+.1f} m over {len(g)}")
