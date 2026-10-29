"""Loaders for R13/R13G failure analysis (read-only; run scripts from the repo root)."""
import json, math, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
for p in (REPO, REPO / 'eval', REPO / 'eval/phase2/R11_goal_default/analysis'):
    sys.path.insert(0, str(p))
from server.decider import spatial  # noqa: E402
import geo  # noqa: E402

ROUNDS = {'R11': 'R11_goal_default', 'R12': 'R12_staged_search',
          'R13': 'R13_verify', 'R13G': 'R13G_verify_goal_words'}
SITES = ['s01', 's02a', 's02c', 's02va', 's02vc', 's03']
ARMS = ['initial', 'final', 'dynamic']
STRIPS = ['far_left', 'left', 'centre', 'right', 'far_right']
SHORT = {'open_far': 'F', 'open_near': 'n', 'blocked_near': 'X'}


def rundir(rnd, site, arm):
    return REPO / 'eval/phase2' / ROUNDS[rnd] / 'runs' / site / arm / 'seed1'


def xyh(r):
    return spatial.pose_xyh(r['manifest']['pose'])


def picked(r):
    idx = r.get('index')
    for a in r['manifest'].get('actions') or []:
        if a.get('index') == idx:
            return a
    return None


def is_ta(r):
    a = picked(r)
    return bool(a and a.get('turn_around'))


def lanes(r):
    per = (r.get('perceiver') or {}).get('result') or {}
    return {l['strip']: l for l in per.get('lanes') or []}


def pgoal(r):
    return ((r.get('perceiver') or {}).get('result') or {}).get('goal')


def events(r):
    return (r.get('evaluator') or {}).get('events') or []


def stage(r):
    return (r.get('stage') or {}).get('stage')


def goal_xy(r):
    x, _, z = r['manifest']['goal']['position']
    return (x, -z)


def load(rnd, site, arm):
    d = rundir(rnd, site, arm)
    rows = [json.loads(l) for l in open(d / 'decisions.jsonl') if l.strip()]
    rows = sorted([r for r in rows if 'step' in r], key=lambda r: r['step'])
    met = json.load(open(d / 'metrics.json'))
    return rows, met


def free_at(site, arm, step):
    return geo.world(site, arm, step)


def summary(rows, met):
    p0 = xyh(rows[0])[:2]
    G = goal_xy(rows[0])
    maxd = max(math.dist(xyh(r)[:2], p0) for r in rows)
    tas = sum(is_ta(r) for r in rows)
    # longest run of consecutive turn-arounds
    best = cur = 0
    for r in rows:
        cur = cur + 1 if is_ta(r) else 0
        best = max(best, cur)
    mind = min(math.dist(xyh(r)[:2], G) for r in rows)
    return dict(ok=met['goal_reached'], steps=met['steps'], dfin=met['final_goal_distance_m'],
                dmin=mind, maxd=maxd, ta=tas, ta_run=best, coll=met['collisions'])
