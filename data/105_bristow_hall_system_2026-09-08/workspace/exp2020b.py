"""EXPERIMENT 2 (9 September 2026): the detail of the single-week proposer's extra calls at 35 percent, and the
confirmer that completed the 26 March 2020 call. Run: /opt/homebrew/bin/python3 exp2020b.py"""
import sys
sys.argv=['exp2020b.py','1962','2026','wexp']
exec(open('exp2020.py').read().split("base=build_x(p,None)")[0])
t=build_x(p,35)
print('all peak and trough calls with K at 35%, 1975 on:')
for x in t:
    if x['published'].year>=1975 and x['kind'] in ('peak','trough'): print('  ',x['kind'],x['published'].strftime('%Y-%m-%d'),'dated',x['date'].strftime('%Y-%m'),x['leg'])
print('raw K proposals at 35% (release day, data month):',[(a.strftime('%Y-%m-%d'),b.strftime('%Y-%m')) for a,b in leg_ic1(ICfp,35) if a.year>=1975])
# which confirmer completed the 26 March 2020 call: the I leg with each confirmer alone
G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs); Hh=mkhours(p['hrs'],p['nd']); SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
for nm,cf in (('vacancy',Vc),('hours',Hh),('spread',SP)):
    c=[(a.strftime('%Y-%m-%d'),b.strftime('%Y-%m')) for a,b,x in confirm_w(leg_ic(ICfp,p['ic']),[cf],'month') if a.year==2020]
    print('I leg confirmed by',nm,'alone, 2020 calls:',c)
print('I leg raw proposals 2019-2020:',[(a.strftime('%Y-%m-%d'),b.strftime('%Y-%m')) for a,b in leg_ic(ICfp,p['ic']) if a.year in (2019,2020)])
print('vacancy gap (4-month mean below prior 4-month high) 2019-07..2020-06:'); print(G['2019-07':'2020-06'].round(2).to_dict())
print('spread gap 2020-01..2020-04:'); print(GSP['2020-01':'2020-04'].round(2).to_dict())
