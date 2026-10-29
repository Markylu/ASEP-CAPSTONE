from nav import *
import contextlib, io
for rnd in ['R11','R11C']:
    with contextlib.redirect_stdout(io.StringIO()):
        C,ex=classify(rnd)
    cache={}
    def get(s,a):
        if (s,a) not in cache: cache[(s,a)]=load(rnd,s,a)[0]
        return cache[(s,a)]
    mis_ta=sum(1 for (s,a,st) in ex['misattr'] if get(s,a)[st]['acts'][[k for k in get(s,a)[st]['toward']][0]].get('turn_around'))
    union=set(ex['misattr'])|set(ex['phantom_toward'])|set(ex['clear_but_short'])
    # add wall-note picks
    wallp=set(); shortinfo=collections.Counter()
    for s in SITES:
      for a in ARMS:
        for r in get(s,a):
          if r['idx'] is None: continue
          if any(t.startswith('wall close') for t in r['ptags']): wallp.add((s,a,r['step']))
          if r['word']!='TA' and r['moved'] is not None and r['moved']<1.5:
            act=r['acts'][r['idx']]
            st=spatial.strip_for(float(act['theta_deg']))
            per=(r['raw'].get('perceiver') or {}).get('result') or {}
            lane={l['strip']:l for l in per.get('lanes') or []}.get(st,{})
            shortinfo[lane.get('floor')]+=1
            shortinfo['target_'+str(r['tkind'])]+=1
            shortinfo['picked_toward' if r['idx'] in r['toward'] else 'not_toward']+=1
    union|=wallp
    print(rnd,'misattr',len(ex['misattr']),'of which toward on TA',mis_ta,'| union contradiction steps',len(union),'/',C['n'],f"{len(union)/C['n']:.1%}")
    print('   stopped-short picks: perceiver lane on picked strip / target kind / toward:',dict(shortinfo))
