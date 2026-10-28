from tl import *
from geo import *
from val import wfun
import collections, re
def side_of_wall(s,x):
    return x < -0.5 if s.startswith('s02') else None
for rnd in ['R11','R11C']:
    C=collections.Counter(); ex=[]
    for s in SITES:
      for a in ARMS:
        rows,met,G=load(rnd,s,a)
        prev=None
        for r in rows:
          S=r['strat']
          if not S: continue
          res=S.get('result') or {}
          menu={m['id']:m for m in S.get('menu') or []}
          f=wfun(rnd,s,a,r['step'])
          for mid,m in menu.items():
            kind=m['kind']
            inside=not f(m['x'],m['y'])
            clear=segment_clear(f,(r['x'],r['y']),(m['x'],m['y']))
            beyond = (s.startswith('s02') and m['x']<-0.5) or (s=='s03' and m['x']<-7) or (s=='s01' and f(m['x'],m['y']) and not clear)
            C[(kind,'offered')]+=1
            C[(kind,'offered','inside_obstacle')]+=inside
            C[(kind,'offered','straight_line_blocked')]+= (not clear)
            if s.startswith('s02'): C[(kind,'offered','s02_beyond_divider')]+= m['x']<-0.5
            if mid==res.get('target'):
              C[(kind,'picked')]+=1
              C[(kind,'picked','inside_obstacle')]+=inside
              C[(kind,'picked','straight_line_blocked')]+= (not clear)
              if s.startswith('s02'):
                C[(kind,'picked','s02')]+=1
                C[(kind,'picked','s02_beyond_divider')]+= m['x']<-0.5
              ex.append((s,a,r['step'],mid,m['x'],m['y'],inside,clear))
    print('==',rnd)
    for k,v in sorted(C.items(), key=lambda kv: str(kv[0])): print('  ',k,v)
    if rnd=='R11':
        for e in ex: print('   ',e)
