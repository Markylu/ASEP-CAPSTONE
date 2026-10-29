"""Q1/Q3 table: per run outcome, distances, turn-arounds, collisions, stages, events."""
import sys, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa

rounds = sys.argv[1:] or ['R11', 'R12', 'R13', 'R13G']
for rnd in rounds:
    print('==', rnd)
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            s = summary(rows, met)
            st = collections.Counter(stage(r) for r in rows)
            ev = collections.Counter(e for r in rows for e in events(r))
            ev = {k: v for k, v in ev.items() if k in ('goal_sighted', 'goal_lost', 'verify_failed', 'verify_timeout', 'verify_unreachable', 'reacquired', 'reacquired_moved', 'lost')}
            print(f"{site:5s} {arm:7s} {'OK ' if s['ok'] else '-- '} st{s['steps']:3d} dfin{s['dfin']:5.1f} dmin{s['dmin']:5.1f} maxd{s['maxd']:5.1f} TA{s['ta']:3d} run{s['ta_run']:2d} C{s['coll']:2d} "
                  f"stages {dict(st)} ev {ev}")
