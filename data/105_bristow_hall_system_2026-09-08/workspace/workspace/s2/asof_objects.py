# asof_objects.py - THE MONTHLY OBJECTS AS OF THE RELEASE-DAY VINTAGE (Rule 23 clause 1, the audit of 10 September 2026).
# Each month's reading of the housing half, the rate half, the Sahm gap, the hours pair and the vacancy rate is computed
# from the whole series AS IT STOOD on the day that month's print first appeared - every earlier month at the value then
# current, not at its own first print. This is what a user computed that day. (walk39-walk44 read each month at its first
# print; the two differ where earlier months were revised, and the housing half differs at the line in eleven months.)
import csv as _csv, os as _os
_AL=AL; _VINTDIR=W+'/lab/rt/vint/'
def load_vintages(path):
    rows=list(_csv.reader(open(path))); h=rows[0]; dates=[pd.Timestamp(r[0]) for r in rows[1:]]
    M={}
    for j in range(1,len(h)):
        if '_' not in h[j]: continue
        vd=pd.Timestamp(h[j].split('_')[-1])
        s=pd.Series({dates[i]:float(rows[1+i][j]) for i in range(len(dates)) if rows[1+i][j] not in ('','.')}).sort_index()
        if len(s): M[vd]=s
    return M
VINT={s_:load_vintages(_AL+s_+'_all_vintages.csv') for s_ in ['HOUST','UNRATE','AWHMAN','NDMANEMP']}
_JV=_AL+'JTSJOL_all_vintages.csv' if _os.path.exists(_AL+'JTSJOL_all_vintages.csv') else _VINTDIR+'JTSJOL_all_vintages.csv'
if _os.path.exists(_JV): VINT['JTSJOL']=load_vintages(_JV)
def first_days(M):
    seen={}
    for vd in sorted(M):
        for m in M[vd].index:
            if m not in seen: seen[m]=vd
    return pd.Series(seen).sort_index()
FD={s_:first_days(VINT[s_]) for s_ in VINT}
def asof_object(series,fn,after=None):
    """fn(the series as it stood on the day month m first appeared), read at m; returns the readings and their release days"""
    M=VINT[series]; vds=sorted(M); out={}; pub={}
    for m,d in FD[series].items():
        if after is not None and m<after: continue
        d=pd.Timestamp(d); js=[v for v in vds if v<=d]
        if not js: continue
        s=M[js[-1]]
        if m not in s.index: continue
        val=fn(s)
        if m in val.index and not np.isnan(val[m]): out[m]=float(val[m]); pub[m]=d
    return pd.Series(out).sort_index(), pd.Series(pub).sort_index()
# the four monthly objects at the rule's fixed shapes (starts 29, minw 18, half 4, hours 2.0 x 1.2 are not in the grid)
hh_asof,hh_pub=asof_object('HOUST',lambda s:((np.log(s)*100).rolling(12).max()-(np.log(s)*100).rolling(3).mean())/BASE15['starts'])
rate_asof,rate_pub=asof_object('UNRATE',lambda s:(((s-s.rolling(BASE15['minw']).min())*10).round()/BASE15['half']))
g_asof,g_pub=asof_object('UNRATE',lambda s:((((s.rolling(3).mean()-s.rolling(3).mean().rolling(12).min().shift(1))*30).round()/30).round(4)))
def _hours_fn(s_awh,s_nd,h1,h2):
    AWHt=(s_awh*10).round().astype('Int64'); mx_=AWHt.rolling(12).max(); hf=(1000*(mx_-AWHt)>=int(h1*10)*AWHt).fillna(False).astype(bool)
    NDt=s_nd.round().astype('Int64'); nd3=NDt.shift(3); nf=(10000*(nd3-NDt)>=int(h2*100)*nd3).fillna(False).astype(bool)
    return pd.Series({m:(1.0 if (bool(hf.get(m,False)) and bool(nf.get(m,False))) else 0.0) for m in s_awh.index})
def hours_asof(h1,h2):
    MA=VINT['AWHMAN']; MN=VINT['NDMANEMP']; va=sorted(MA); vn=sorted(MN); out={}; pub={}
    for m,d in FD['AWHMAN'].items():
        d=pd.Timestamp(d); ja=[v for v in va if v<=d]; jn=[v for v in vn if v<=d]
        if not ja or not jn: continue
        sa=MA[ja[-1]]; sn=MN[jn[-1]]
        if m not in sa.index or m not in sn.index: continue
        out[m]=float(_hours_fn(sa,sn,h1,h2).get(m,0.0)); pub[m]=d
    return pd.Series(out).sort_index(), pd.Series(pub).sort_index()
hp_asof,hp_pub=hours_asof(BASE15['hrs'],BASE15['nd'])
# the vacancy rate as of the JOLTS release day (openings as they stood that day over the labor force as first printed
# month by month; the labor force is revised once a year and the rate moves by less than a hundredth), spliced onto the
# level file before July 2010 as in walk39; the 4-month-mean gap is computed on the series as it stood on each release day
V0_FP=V0.copy()
if 'JTSJOL' in VINT:
    _MJ=VINT['JTSJOL']; _vdj=sorted(_MJ); _CFf=_CF.reindex(pd.date_range(_CF.index.min(),_CF.index.max(),freq='MS')).ffill(limit=2)
    def vgap2_asof(k,back):
        out={}
        for m,d in FD['JTSJOL'].items():
            if m<pd.Timestamp('2010-07-01'): continue
            d=pd.Timestamp(d); js=[v for v in _vdj if v<=d]
            if not js: continue
            so=_MJ[js[-1]]; vr_=(so/_CFf.reindex(so.index)*100).dropna()
            v=pd.concat([V0_FP[V0_FP.index<vr_.index.min()],vr_]).sort_index()
            mm=v.rolling(k).mean(); gg=(mm.shift(1).rolling(back).max()-mm)
            if m in gg.index and not np.isnan(gg[m]): out[m]=float(gg[m])
        base=vgap2(k,back); base=base[base.index<pd.Timestamp('2010-07-01')]
        return pd.concat([base,pd.Series(out).sort_index()]).sort_index()
else:
    def vgap2_asof(k,back): return vgap2(k,back)
gpub_asof=pd.Series({pd.Timestamp(g_pub[m]):float(g_asof[m]) for m in g_asof.index}).sort_index()
def cosign_asof(day,thr=COS_THR):
    s=gpub_asof[gpub_asof.index<=day]; return len(s)>0 and float(s.iloc[-1])>=thr-EPS
def mkpair_asof(hline):
    hh=hh_asof; rate=rate_asof
    ev=[(pd.Timestamp(hh_pub[m]),'D',m) for m in hh.index]+[(pd.Timestamp(rate_pub[m]),'U',m) for m in rate.index if m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(hh.get(lastD,np.nan),rate.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=hline-EPS and key not in fires: fires[key]=d
    G_=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name='pair',gap=G_,line=hline,pubs=PB,mx=pd.Series(mx).sort_index())
def mkpair_sv_asof(G_,pubsV,vl):
    hh=hh_asof; vr_=(G_/vl)
    ev=[(pd.Timestamp(hh_pub[m]),'D',m) for m in hh.index]+[(pubsV[m],'V',m) for m in vr_.index if m in pubsV.index]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastV=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastV=m if (lastV is None or m>lastV) else lastV
        if lastD is None or lastV is None: continue
        v=min(hh.get(lastD,np.nan),vr_.get(lastV,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastV); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0-EPS and key not in fires: fires[key]=d
    Gp=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name='pairSV',gap=Gp,line=1.0,pubs=PB,mx=pd.Series(mx).sort_index())
HOURS_ASOF=dict(name='hours',gap=hp_asof,line=1.0,pubs=pd.Series({m:pd.Timestamp(hp_pub[m]) for m in hp_asof.index}))
