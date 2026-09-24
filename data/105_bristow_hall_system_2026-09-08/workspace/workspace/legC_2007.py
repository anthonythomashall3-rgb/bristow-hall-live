exec(open('dominance.py').read().split('rows=[]')[0])
for legs in [('A','B','C','M','U'),('A','B','M','U'),('B','M','U')]:
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in legs},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
    on=[(o['published'],o['date'],o['leg'],o.get('condition'),o.get('claims_published')) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('2006-01-01') and o['published']<=pd.Timestamp('2009-12-31')]
    print(''.join(legs), [(str(p.date()),str(d.date())[:7],l,c,str(cp.date()) if cp is not None else None) for p,d,l,c,cp in on])
