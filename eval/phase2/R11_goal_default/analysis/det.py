from tl import *
import hashlib
same=diff=0; ex=[]
navsame=navdiff=0
for s in SITES:
  for a in ARMS:
    A,_,_=load('R11',s,a); B,_,_=load('R11C',s,a)
    for x,y in zip(A,B):
      fx=rundir('R11',s,a)/x['raw']['clean_frame']; fy=rundir('R11C',s,a)/y['raw']['clean_frame']
      if hashlib.md5(fx.read_bytes()).digest()!=hashlib.md5(fy.read_bytes()).digest(): break
      px=x['raw']['perceiver']['raw']; py=y['raw']['perceiver']['raw']
      if px==py: same+=1
      else:
        diff+=1; ex.append((s,a,x['step'],x['lanes'],x['pgoal'],'|',y['lanes'],y['pgoal']))
      if x['idx']!=y['idx']: break
print('identical clean frame, perceiver raw same',same,'different',diff)
for e in ex: print(e)
