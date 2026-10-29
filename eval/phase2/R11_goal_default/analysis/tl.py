"""Timeline loader/dumper for phase-2 runs (read-only analysis)."""
import json, math, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from server.decider import spatial  # noqa

ROUNDS = {'R11': 'R11_goal_default', 'R11C': 'R11C_a14_control', 'R10': 'R10_goal_planner'}
SITES = ['s01', 's02a', 's02c', 's02va', 's02vc', 's03']
ARMS = ['initial', 'final', 'dynamic']
FAN = {43.5: 'sL', 21.75: 'sl', 0.0: 'S', -21.75: 'sr', -43.5: 'sR'}
SHORT = {'open_far': 'F', 'open_near': 'n', 'blocked_near': 'X'}


def rundir(rnd, site, arm):
    return REPO / 'eval/phase2' / ROUNDS[rnd] / 'runs' / site / arm / 'seed1'


def load(rnd, site, arm):
    d = rundir(rnd, site, arm)
    dec = [json.loads(l) for l in open(d / 'decisions.jsonl') if l.strip()]
    dec = sorted([r for r in dec if 'step' in r], key=lambda r: r['step'])
    st = [json.loads(l) for l in open(d / 'steps.jsonl') if l.strip()]
    met = json.load(open(d / 'metrics.json'))
    goal = dec[0]['manifest']['goal']['position']
    G = (goal[0], -goal[2])
    rows = []
    for k, r in enumerate(dec):
        m = r['manifest']
        here = spatial.pose_xyh(m['pose'])
        acts = {int(a['index']): a for a in m['actions']}
        idx = r.get('index')
        a = acts.get(idx) if idx is not None else None
        s = st[k] if k < len(st) else None
        nxt = None
        if s is not None:
            nxt = (s['position'][0], -s['position'][2])
        moved = math.dist(here[:2], nxt) if nxt else None
        word = None
        if a is not None:
            word = 'TA' if a.get('turn_around') else FAN[min(FAN, key=lambda t: abs(t - float(a['theta_deg'])))]
        per = (r.get('perceiver') or {}).get('result') or {}
        lanes = {l['strip']: l for l in per.get('lanes') or []}
        lane_s = ''.join(SHORT.get((lanes.get(x) or {}).get('floor'), '?') + ('D' if (lanes.get(x) or {}).get('doorway') else '')
                         + ' ' for x in ['far_left', 'left', 'centre', 'right', 'far_right'])
        tags = {int(i): v for i, v in (r.get('tags') or {}).items()}
        toward = [i for i, v in tags.items() if 'toward your target' in v]
        strat = r.get('strategist')
        rows.append(dict(
            step=r['step'], x=here[0], y=here[1], h=here[2], dg=math.dist(here[:2], G),
            dg_next=math.dist(nxt, G) if nxt else None,
            target=(r.get('target') or {}).get('id'), tkind=(r.get('target') or {}).get('kind'),
            tx=(r.get('target') or {}).get('x'), ty=(r.get('target') or {}).get('y'),
            mode=r.get('mode'), planner=r.get('planner'), strat=strat, idx=idx, word=word,
            ptags=tags.get(idx, []) if idx is not None else [], tags=tags, toward=toward,
            moved=moved, coll=s['collided'] if s else None, lanes=lane_s, pgoal=per.get('goal'),
            prange=per.get('goal_range'), preason=per.get('reason'), reason=r.get('reason'),
            hidden=(r.get('hidden') or {}).get('indices') if r.get('hidden') else None,
            text=r.get('navigator_text'), acts=acts, los=m['goal'].get('line_of_sight'),
            gbear=m['goal'].get('bearing_deg'), raw=r))
    return rows, met, G


def dump(rnd, site, arm, reason_chars=0, frm=0, to=999):
    rows, met, G = load(rnd, site, arm)
    print(f"== {rnd} {site}/{arm}: steps {met['steps']} coll {met['collisions']} reached {met['goal_reached']} final_d {met['final_goal_distance_m']}")
    for r in rows:
        if not (frm <= r['step'] <= to):
            continue
        p = r['planner'] or {}
        pl = ''
        if p:
            pl = f"{p.get('way','')[:1]}{'/ask:'+p['ask'] if p.get('ask') else ''}{'/hb:'+p['hand_back'] if p.get('hand_back') else ''}"
        st = ''
        if r['strat']:
            res = r['strat'].get('result') or {}
            st = f" STRAT->{res.get('target')}@({r['tx']},{r['ty']})"
        tw = ','.join(map(str, r['toward']))
        print(f"{r['step']:2d} ({r['x']:6.2f},{r['y']:6.2f}) h{r['h']:4.0f} dg{r['dg']:5.1f} gb{r['gbear']:5.0f}{'L' if r['los'] else ' '} "
              f"T={str(r['target'])[:14]:14s} {pl:18s} per[{r['lanes']}] g={str(r['pgoal'])[:6]:6s} "
              f"pick {r['idx']}{r['word']} tw={tw:3s} mv{(r['moved'] or 0):4.2f}{' C' if r['coll'] else '  '} {'H' if r['hidden'] else ' '} "
              f"tags={'; '.join(r['ptags'])}{st}")
        if reason_chars:
            print('     R:', (r['reason'] or '')[:reason_chars].replace('\n', ' '))


if __name__ == '__main__':
    a = sys.argv[1:]
    dump(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 0,
         int(a[4]) if len(a) > 4 else 0, int(a[5]) if len(a) > 5 else 999)
