from tl import *
from geo import *
from val import wfun
import collections
STR=['far_left','left','centre','right','far_right']
def tclass(d):
    return 'blocked_near' if d<1.5 else ('open_near' if d<4.0 else 'open_far')
for rnd in ['R11','R11C']:
    cm=collections.Counter(); per_run=collections.Counter()
    goalh=collections.Counter()
    picked=collections.Counter()
    for s in SITES:
      for a in ARMS:
        rows,met,G=load(rnd,s,a)
        for r in rows:
          per=(r['raw'].get('perceiver') or {}).get('result') or {}
          lanes={l['strip']:l for l in per.get('lanes') or []}
          f=wfun(rnd,s,a,r['step'])
          for st in STR:
            l=lanes.get(st)
            if not l: continue
            d=ray(f,r['x'],r['y'],(r['h']+spatial.strip_offset(st))%360)
            cm[(tclass(d),l['floor'])]+=1
            if d<1.0 and l['floor']=='open_far': per_run[(s,a,'F_at_<1m')]+=1
          # goal sightings
          if per.get('goal') in spatial.STRIPS:
            goalh['sighting']+=1
            goalh['los' if r['los'] else 'no_los']+=1
            if not r['los']:
              goalh['no_los_'+('goal' if r['target']=='goal' else 'other')]+=1
          # picked forward action: wall note vs outcome
          if r['idx'] is not None and r['word']!='TA' and r['moved'] is not None:
            wn='wall close (seen now)' in r['ptags']
            act=r['acts'][r['idx']]
            d=ray(f,r['x'],r['y'],spatial.action_heading(act,r['h']))
            picked[(wn, r['moved']<1.5)]+=1
    print('==',rnd)
    tot=sum(cm.values())
    for t in ['blocked_near','open_near','open_far']:
        row=[cm[(t,p)] for p in ['blocked_near','open_near','open_far']]
        print(f'  truth {t:12s} -> X {row[0]:5d} n {row[1]:5d} F {row[2]:5d}  (n={sum(row)})')
    print('  goal sightings',dict(goalh))
    print('  picked fwd (wall note, stopped short):',dict(picked))
    print('  F reads with wall <1 m by run:',sorted(per_run.items(), key=lambda x:-x[1])[:10])
