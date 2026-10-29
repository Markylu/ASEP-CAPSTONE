"""Q1 support: each final/dynamic failure's closest approach to the way through (chain.way), with the look
there (g05 class + true clear metres per strip), the pick, its notes and the target."""
import sys, math
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from chain import way  # noqa
from r12_probe import true_reach  # noqa

OFF = {'far_left': 43.5, 'left': 21.75, 'centre': 0.0, 'right': -21.75, 'far_right': -43.5}
for rnd in sys.argv[1:] or ['R13', 'R13G']:
    print('==', rnd)
    for arm in ('final', 'dynamic'):
        for site in SITES:
            rows, met = load(rnd, site, arm)
            if met['goal_reached']:
                continue
            W = way(site)
            k = min(range(len(rows)), key=lambda i: min(math.dist(xyh(rows[i])[:2], w) for w in W))
            for r in rows[max(0, k - 1):k + 2]:
                x, y, h = xyh(r)
                free = free_at(site, arm, r['step'])
                L = lanes(r)
                ls = ' '.join(SHORT.get((L.get(s) or {}).get('floor'), '?') + ('D' if (L.get(s) or {}).get('doorway') else '')
                              + f"{true_reach(free, (x, y), h + OFF[s], cap=9.9):.0f}" for s in STRIPS)
                tags = {int(i): v for i, v in (r.get('tags') or {}).items()}
                t = r.get('target') or {}
                print(f"{site:5s} {arm[:3]} s{r['step']:2d} ({x:5.1f},{y:5.1f}) h{h:4.0f} [{ls}] {stage(r)} T={t.get('id')}({t.get('x')},{t.get('y')}) "
                      f"pick {r.get('index')}{'TA' if is_ta(r) else ''}: {'; '.join(tags.get(r.get('index'), []))}")
