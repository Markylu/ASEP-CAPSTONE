from tl import *
from geo import *
import collections
def wfun(rnd,s,a,step):
    if s=='s03':
        side={'R11':('L',25)}.get(rnd) if a=='dynamic' else None
        if side: return world(s,a,step,side[1],side[0])
        return world(s,a,step)
    return world(s,a,step)
if __name__=='__main__':
 for rnd in ['R11','R11C']:
  ok=collections.Counter()
  for s in SITES:
    for a in ARMS:
      rows,met,G=load(rnd,s,a)
      for r in rows:
        if r['idx'] is None or r['word']=='TA' or r['moved'] is None: continue
        act=r['acts'][r['idx']]
        h=spatial.action_heading(act,r['h'])
        d=ray(wfun(rnd,s,a,r['step']),r['x'],r['y'],h)
        pred_short = d-0.2 < 1.65
        ok[(s, pred_short, r['moved']<1.5)]+=1
  print(rnd)
  for k,v in sorted(ok.items()): print('  ',k,v)
