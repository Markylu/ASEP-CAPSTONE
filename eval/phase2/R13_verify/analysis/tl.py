"""Timeline dump: python3 eval/phase2/R13_verify/analysis/tl.py R13 s02a dynamic [from] [to] [reason_chars]"""
import sys, math
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from r12_probe import true_reach  # noqa

FAN = {43.5: 'sL', 21.75: 'sl', 0.0: 'S', -21.75: 'sr', -43.5: 'sR'}
OFF = {'far_left': 43.5, 'left': 21.75, 'centre': 0.0, 'right': -21.75, 'far_right': -43.5}
rnd, site, arm = sys.argv[1:4]
frm = int(sys.argv[4]) if len(sys.argv) > 4 else 0
to = int(sys.argv[5]) if len(sys.argv) > 5 else 999
rc = int(sys.argv[6]) if len(sys.argv) > 6 else 0
rows, met = load(rnd, site, arm)
G = goal_xy(rows[0])
print(f"== {rnd} {site}/{arm} reached={met['goal_reached']} coll={met['collisions']} dfin={met['final_goal_distance_m']}")
for r in rows:
    if not frm <= r['step'] <= to:
        continue
    x, y, h = xyh(r)
    free = free_at(site, arm, r['step'])
    L = lanes(r)
    lane = ' '.join(SHORT.get((L.get(s) or {}).get('floor'), '?') + ('D' if (L.get(s) or {}).get('doorway') else '') +
                    f"{true_reach(free, (x, y), h + OFF[s], cap=9.9):.0f}" for s in STRIPS)
    a = picked(r)
    w = '?' if a is None else ('TA' if a.get('turn_around') else FAN[min(FAN, key=lambda t: abs(t - a['theta_deg']))])
    tags = {int(i): v for i, v in (r.get('tags') or {}).items()}
    tw = ','.join(str(i) for i, v in sorted(tags.items()) if 'toward your target' in v)
    g = r['manifest']['goal']
    t = r.get('target') or {}
    st = r.get('stage') or {}
    s = r.get('strategist')
    sp = ''
    if s:
        res = s.get('result') or {}
        sp = f" STRAT[{s.get('trigger','')[:30]}]->{res.get('target')}"
    ev = ','.join(e for e in events(r) if e not in ('reached',))
    print(f"{r['step']:2d} ({x:6.2f},{y:6.2f}) h{h:5.0f} dg{math.dist((x, y), G):5.1f} gb{g['bearing_deg']:5.0f}{'L' if g['line_of_sight'] else ' '} "
          f"{(st.get('stage') or '')[:3]} T={str(t.get('id'))[:14]:14s}({t.get('x')},{t.get('y')}) [{lane}] g={str(pgoal(r))[:9]:9s} "
          f"pick {r.get('index')}{w} tw={tw:4s} ev={ev}{sp} tags={'; '.join(tags.get(r.get('index'), []))}")
    if rc:
        print('    N:', (r.get('reason') or '')[:rc].replace('\n', ' '))
        if s:
            print('    S:', ((s.get('result') or {}).get('reason') or '')[:rc].replace('\n', ' '))
