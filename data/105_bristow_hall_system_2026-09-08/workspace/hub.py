from mini import *
def leg_X2(sahm_line=0.5, vac=vr, vac_line=0.36, back=6, date_rule='minus3', vac_pub_day=30):
    """the hub: first month m with Sahm(fp) >= line and the vacancy gap >= its line in [m-back, m]; published when both
    are public (Sahm: the 5th of m+1; vacancy reading k: the (vac_pub_day)th of k+1); re-arms when Sahm < line."""
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sahm_line:
            win=vac[(vac.index>=m-pd.DateOffset(months=back))&(vac.index<=m)]; hit=win[win>=vac_line]
            if len(hit):
                k=hit.index[0]
                pub=max(pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4),
                        pd.Timestamp(k.year,k.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=vac_pub_day-1))
                dated={'minus3':m-pd.DateOffset(months=3),'month':m,'vac':k}[date_rule]
                calls.append((pub,pd.Timestamp(dated.year,dated.month,1))); armed=False
        elif not armed and v<sahm_line: armed=True
    return calls
if __name__=='__main__':
    X=leg_X2()
    print('hub calls:',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in X])
