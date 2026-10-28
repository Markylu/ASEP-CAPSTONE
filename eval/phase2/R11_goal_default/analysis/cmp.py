from tl import *
import sys
def first_div(s,a):
    A,_,_=load('R11',s,a); B,_,_=load('R11C',s,a)
    for x,y in zip(A,B):
        if x['idx']!=y['idx']: return x['step']
    return None
def show(s,a,pre=1,post=3):
    k=first_div(s,a)
    A,_,_=load('R11',s,a); B,_,_=load('R11C',s,a)
    print(f'##### {s}/{a} first divergent pick at step {k}')
    for rnd,R in (('R11',A),('R11C',B)):
        for r in R[max(0,k-pre):k+post]:
            S=r['strat']; st=''
            if S:
                st=f" STRAT[{(S.get('trigger') or '')[:40]}]->{(S.get('result') or {}).get('target')}"
            print(f"{rnd:4s} {r['step']:2d} ({r['x']:5.2f},{r['y']:5.2f}) h{r['h']:4.0f} gb{r['gbear']:5.0f} T={r['target']} pick {r['idx']}{r['word']} mv{(r['moved'] or 0):.2f}{' C' if r['coll'] else ''}{st}")
            print('      per', r['lanes'], r['pgoal'])
            print('      ', r['text'].split('Available actions this step:')[0].strip().split('\n')[0][:150])
            print('      ', ' | '.join(l.strip() for l in r['text'].split('Available actions this step:')[1].split('\n') if l.strip().startswith('['))[:600])
            print('       R:', (r['reason'] or '')[:220].replace('\n',' '))
if __name__=='__main__':
    show(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 1,int(sys.argv[4]) if len(sys.argv)>4 else 3)
