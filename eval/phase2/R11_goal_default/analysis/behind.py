from tl import *
import collections
for rnd in ['R11','R11C']:
  C=collections.Counter()
  for s in SITES:
    for a in ARMS:
      rows,met,G=load(rnd,s,a)
      for r in rows:
        if r['idx'] is None or r['dg_next'] is None: continue
        vis=[k for k in r['acts'] if not (r['hidden'] and k in r['hidden'])]
        tw=r['toward']
        if not tw: continue
        k=tw[0]; isTA=r['acts'][k].get('turn_around')
        if not isTA: continue
        hid = r['hidden'] and k in r['hidden']
        key='TA_toward_hidden' if hid else ('TA_toward_picked' if r['idx']==k else 'TA_toward_ignored')
        C[key]+=1; C[key+'_dg']+=r['dg_next']-r['dg']
        C[key+'_goal']+= r['target']=='goal'
  print(rnd,{k:(round(v,1) if isinstance(v,float) else v) for k,v in sorted(C.items())})
