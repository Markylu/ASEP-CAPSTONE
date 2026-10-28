from tl import *
from geo import *
from val import wfun
import collections
FAILS=[('s02a','dynamic'),('s02c','final'),('s02c','dynamic'),('s02va','dynamic'),('s02vc','final'),('s02vc','dynamic'),('s03','dynamic')]
for rnd in ['R11','R11C']:
  tot=collections.Counter()
  for s in SITES:
    for a in ARMS:
      rows,met,G=load(rnd,s,a)
      c=collections.Counter()
      for r in rows:
        if r['dg_next'] is None: continue
        if r['target']=='goal': k='goal_behind' if abs(r['gbear'])>90 else 'goal_front'
        elif r['tkind']=='frontier':
          f=wfun(rnd,s,a,r['step'])
          k='frontier_blocked' if not segment_clear(f,(r['x'],r['y']),(r['tx'],r['ty'])) else 'frontier_clear'
        else: k=str(r['tkind'])
        c[k]+=1; c[k+'_dg']+=r['dg_next']-r['dg']; c[k+'_coll']+=bool(r['coll'])
        tot[k]+=1; tot[k+'_dg']+=r['dg_next']-r['dg']; tot[k+'_coll']+=bool(r['coll'])
      if rnd=='R11' and (s,a) in FAILS:
        print(s,a,{k:(round(v,1) if isinstance(v,float) else v) for k,v in sorted(c.items())})
  print('==',rnd,'TOTAL')
  for k in sorted(set(x.split('_dg')[0].split('_coll')[0] for x in tot)):
    n=tot[k]; print(f"   {k:18s} steps {n:4d}  m/step toward goal {-tot[k+'_dg']/n:+.2f}  collisions {tot[k+'_coll']}")
