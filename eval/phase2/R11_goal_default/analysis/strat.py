import re, collections
from tl import *
calls=[]
for s in SITES:
  for a in ARMS:
    rows,met,G=load('R11',s,a)
    for r in rows:
      if not r['strat']: continue
      S=r['strat']; res=S.get('result') or {}
      text=S.get('text','')
      items=[]
      for line in text.split('\n'):
        m=re.match(r'\s+(\S+): (.*)$',line)
        if m and m.group(1)!='explore':
          gw=re.search(r'about (\d+) m (nearer|farther)',m.group(2))
          g=0 if 'as far from' in m.group(2) else (int(gw.group(1))*(1 if gw.group(2)=='nearer' else -1) if gw else None)
          items.append((m.group(1),g,m.group(2)))
      pick=res.get('target')
      kinds=[i[0].split('_')[0] for i in items]
      gains=[i[1] for i in items]
      pk=[i for i in items if i[0]==pick]
      maxg=max([g for g in gains if g is not None],default=None)
      fr=[i for i in items if i[0].startswith('unexplored')]
      calls.append(dict(site=s,arm=a,step=r['step'],trig=S.get('trigger'),pick=pick,items=items,
        pickpos=[i[0] for i in items].index(pick) if pk else None, pickgain=pk[0][1] if pk else None, maxg=maxg,
        firstfr=fr[0][0] if fr else None, ndoor=sum(k=='doorway' for k in kinds), mode=res.get('mode'), reason=res.get('reason')))
print('calls',len(calls))
print('picks kind',collections.Counter(c['pick'].split('_')[0] for c in calls))
print('menus with a doorway',sum(c['ndoor']>0 for c in calls), 'doorways total', sum(c['ndoor'] for c in calls))
dg=[i[1] for c in calls for i in c['items'] if i[0].startswith('doorway')]
fg=[i[1] for c in calls for i in c['items'] if i[0].startswith('unexplored')]
print('doorway gain words',collections.Counter(dg)); print('frontier gain words',collections.Counter(fg))
print('pick == max gain item', sum(c['pickgain']==c['maxg'] for c in calls))
print('pick == first unexplored (unexplored_1)', sum(c['pick']==c['firstfr'] for c in calls))
print('pick position in menu',collections.Counter(c['pickpos'] for c in calls))
print('pick = first listed item', sum(c['pickpos']==0 for c in calls))
print('menus where unexplored_1 strictly max gain', sum(1 for c in calls if c['firstfr'] and [i for i in c['items'] if i[0]==c['firstfr']][0][1]==c['maxg']))
# reasons mention
for kw in ['nearer','door','wall','closest','most','reduction','explore']:
  print(kw, sum(kw in (c['reason'] or '').lower() for c in calls))
for c in calls:
  print(c['site'],c['arm'],c['step'],c['trig'][:30],'->',c['pick'],c['pickgain'],'| menu:',[(i[0],i[1]) for i in c['items']])
for c in calls:
  if c['pick'].startswith('doorway'): print('DOOR PICK', c)
