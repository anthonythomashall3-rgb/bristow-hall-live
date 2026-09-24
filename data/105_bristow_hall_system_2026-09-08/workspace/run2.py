from mini import *
# Leg X: the hub -- Sahm's gap on the first-print unemployment rate >= 0.50 (published the 5th of m+1) AND the
# vacancy (2,6) gap >= 0.36 at some reading in [m-6, m] (public by the 30th of m+1 -> at Sahm's publication all
# readings through m-1 are public; reading m is public on the 30th).  Re-arms when the Sahm gap falls below 0.50.
def leg_X(date_rule='minus3'):
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=0.5:
            win=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]
            hit=win[win>=0.36]
            if len(hit):
                last=hit.index[-1]
                pub=max(pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4),
                        pd.Timestamp(last.year,last.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29))
                dated={'minus3':m-pd.DateOffset(months=3),'month':m,'vac':hit.index[0]}[date_rule]
                calls.append((pub,pd.Timestamp(dated.year,dated.month,1)))
                armed=False
            # if Sahm crossed but vacancy not yet at line: stay armed (a later vacancy reading inside +4 could confirm; handled below)
        elif not armed and v<0.5: armed=True
    return calls
X3=leg_X('minus3'); Xm=leg_X('month')
print('leg X (Sahm 0.50 fp AND vacancy(2,6) 0.36 in prior 6 months), dated crossing-3:')
print(' ',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in X3])
def table(nm,turns):
    r=score13(turns)
    print(f"\n--- {nm}")
    for i,(p,t) in enumerate(zip(PK,TR)):
        if i in r['opens']:
            o=r['opens'][i]; s=f"  {p:%Y-%m}  onset {o['published']:%Y-%m-%d} by {o['leg']:2} dated {o['date']:%Y-%m}  lag {r['lags_p'][i]:4d} d err {r['errs_p'][i]:+d}"
            s+= (f"   | trough lag {r['lags_t'][i]:4d} d err {r['errs_t'][i]:+d}" if i in r['lags_t'] else "   | trough: not closed")
        else: s=f"  {p:%Y-%m}  MISSED"
        print(s)
    print('  other calls:',r['other'])
    lp=list(r['lags_p'].values()); lt=list(r['lags_t'].values())
    print(f"  peaks {len(lp)}/13 median {np.median(lp):.0f} mean {np.mean(lp):.1f} worst {max(lp)} in-month {sum(1 for l in lp if l<=0)} <=31 {sum(1 for l in lp if l<=31)} exact {sum(1 for e in r['errs_p'].values() if e==0)} | troughs {len(lt)}/13 median {np.median(lt):.0f} worst {max(lt)} exact {sum(1 for e in r['errs_t'].values() if e==0)}")
    return r
PLX=dict(PL); PLX['X']=X3
KJH={k:TLG[k] for k in 'KJH'}; KJHS={k:TLG[k] for k in 'KJHS'}; KS={k:TLG[k] for k in 'KS'}; Sonly={'S':TLG['S']}; Konly={'K':TLG['K']}
table("X alone (Sahm AND vacancy), closers K,J,H,S", chron({'X':X3},KJHS,['S','V']))
table("U + X, confirm Sahm|vacancy, closers K,J,H,S", chron({'U':PLX['U'],'X':X3},KJHS,['S','V']))
table("U + X, closers K,S", chron({'U':PLX['U'],'X':X3},KS,['S','V']))
table("U + C + X, confirm Sahm|vacancy, closers K,J,H,S", chron({'U':PLX['U'],'C':PL['C'],'X':X3},KJHS,['S','V']))
table("U + X + housing/hours pairs as extra confirmers, closers K,J,H,S", chron({'U':PLX['U'],'X':X3},KJHS,['S','V','H','P']))
table("v8 + X, closers K,J,H,S", chron({**{k:PL[k] for k in 'ABCMU'},'X':X3},KJHS,['S','V','H','P']))
