"""Counterfactual memory replays at R11's q03 calls (code only, no model)."""
import copy, collections
from tl import *
from geo import *
from val import wfun
STR=['far_left','left','centre','right','far_right']
def tclass(d): return 'blocked_near' if d<1.5 else ('open_near' if d<4.0 else 'open_far')
def truthify(raw_rows, s, a, rnd='R11'):
    out=[]
    for r in raw_rows:
        r2=copy.deepcopy(r)
        per=(r2.get('perceiver') or {}).get('result')
        if per:
            here=spatial.pose_xyh(r2['manifest']['pose']); f=wfun(rnd,s,a,r2['step'])
            for l in per.get('lanes') or []:
                d=ray(f,here[0],here[1],(here[2]+spatial.strip_offset(l['strip']))%360)
                l['floor']=tclass(d)
        out.append(r2)
    return out
def frontier_eval(variant):
    C=collections.Counter()
    saved=dict(spatial.FLOOR_RANGE_M)
    if variant.get('far') is not None: spatial.FLOOR_RANGE_M['open_far']=variant['far']
    if variant.get('near') is not None: spatial.FLOOR_RANGE_M['open_near']=variant['near']
    try:
      for s in SITES:
        for a in ARMS:
          rows,met,G=load('R11',s,a)
          raw=[r['raw'] for r in rows]
          if variant.get('truth'): raw=truthify(raw,s,a)
          for k,r in enumerate(rows):
            if not r['strat']: continue
            mem=spatial.rebuild(raw[:k], raw[k]['manifest'], (raw[k].get('perceiver') or {}).get('result'), cfg=spatial.A16)
            here=spatial.pose_xyh(raw[k]['manifest']['pose'])
            fr=mem.frontiers(here[:2], goal=G)
            f=wfun('R11',s,a,r['step'])
            C['calls']+=1
            if not fr: C['no_frontier']+=1; continue
            top=fr[0]
            C['top_blocked']+= not segment_clear(f,here[:2],top)
            gain=math.dist(here[:2],G)-math.dist(top,G)
            C['top_gain_ge3']+= gain>=3
    finally:
      spatial.FLOOR_RANGE_M.clear(); spatial.FLOOR_RANGE_M.update(saved)
    return C
for name,v in [('as flown',{}),('open_far 4.0 m',{'far':4.0}),('open_far 3.5/near 2.0',{'far':3.5,'near':2.0}),('perceiver = truth',{'truth':True}),('truth + far 4.0',{'truth':True,'far':4.0})]:
    print(name, dict(frontier_eval(v)))
