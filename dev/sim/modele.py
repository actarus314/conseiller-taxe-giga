import math
# Barème complet (base, unlock, rate, click, pct, max) recopié du code, build 2026-11-03h
S=[('doigt',10,1,0,2,0,0),('stagiaire',15,10,.5,0,0,0),('chat',100,50,2,0,0,0),('hamster',600,200,8,0,0,0),('souris',500,300,0,20,0,0),
('bot',6000,1000,40,0,0,0),('fax',6e4,6e3,200,0,0,0),('commission',6e5,4e4,1100,0,0,0),('gant',15e4,5e4,0,600,0,0),('satellite',5e6,3e5,3000,0,0,0),
('trounoir',7.5e7,3e6,15000,0,0,0),('tampon',2e7,1e7,0,40000,0,0),('mainetat',5e8,2e8,0,0,.01,1),('decret',1e9,4e8,0,100000,0,0),
('datacenter',1e9,4e7,60000,0,0,0),('ia',1.2e10,5e8,250000,0,0,0),('recommande',5e9,2e9,0,0,.02,1),('art493',5e10,2e10,0,0,.04,1),
('ordonnance',5e10,2e10,0,200000,0,0),('multivers',1.5e11,8e9,1.2e6,0,0,0),('niche',5e11,2e11,0,0,.08,1),('quantique',2e12,1.5e11,6e6,0,0,0),
('directive',2.5e12,1e12,0,3e6,0,0),('mondial',5e12,2e12,0,0,.15,1)]
S=[dict(id=a,base=b,unlock=u,rate=r,click=c,pct=p,max=m) for a,b,u,r,c,p,m in S]
cost=lambda u,o:math.ceil(u['base']*1.15**o.get(u['id'],0))
def income(o,cps):
    rate=sum(u['rate']*o.get(u['id'],0) for u in S)
    if cps==0: return rate
    pct=.01+sum(u['pct']*o.get(u['id'],0) for u in S)
    cp=math.floor(1+sum(u['click']*o.get(u['id'],0) for u in S)+pct*rate)
    return rate+cp*cps
def gain(u,o,cps):
    o2=dict(o);o2[u['id']]=o2.get(u['id'],0)+1
    return income(o2,cps)-income(o,cps)
def run(heur,T,o0,w,c,cps,dt=1):
    o=dict(o0);t=0
    while t<T:
        while True:
            R=income(o,cps)
            av=[u for u in S if (c>=u['unlock'] or o.get(u['id'],0)>0) and not (u['max'] and o.get(u['id'],0)>=u['max'])]
            sc=[]
            for u in av:
                g=gain(u,o,cps)
                if g<=0: continue
                k=cost(u,o)
                if heur=='ratio': s=k/g
                elif heur=='temps': s=max(0,k-w)/R+k/g
                elif heur=='cc': s=k/R+k/g        # variante Cookie Clicker
                sc.append((s,u))
            if not sc: break
            u=min(sc,key=lambda x:x[0])[1]; k=cost(u,o)
            if k<=w: w-=k;o[u['id']]=o.get(u['id'],0)+1
            else: break
        R=income(o,cps);w+=R*dt;c+=R*dt;t+=dt
    return income(o,cps),c,o
if __name__ == '__main__':
    o0=dict(doigt=14,souris=6,gant=9,stagiaire=32,chat=29,hamster=25,bot=20,fax=15,commission=11,satellite=2)
    import sys
    cps=float(sys.argv[1]);w0=9847633;c0=41373467
    for T,dt in [(3600,1),(8*3600,2),(86400,5),(7*86400,20)]:
        res={h:run(h,T,o0,w0,c0,cps,dt) for h in ['ratio','temps','cc']}
        b=max(r[1] for r in res.values())
        print('%6.1fh'%(T/3600),'  '.join('%s: prod %.4g (%.2f%%) R=%.3g'%(h,r[1],100*(r[1]/b-1),r[0]) for h,r in res.items()))
