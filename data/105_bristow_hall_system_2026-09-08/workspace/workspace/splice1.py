"""IS THE RECORD AN ARTEFACT OF THE SPLICE? The survey-week object joins this line's own transcription of the printed
releases to the Department's seasonally adjusted weekly rate. The join date is a choice. Here the record is rebuilt
with the join at 1971 (as shipped), at 1983 (the transcription used for its whole length), and with the transcription
dropped entirely, so that any dependence on the choice is visible."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('splice1.out','w')"))
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
def mk(joined):
    rows={}
    for t,v in joined.items():
        m=pd.Timestamp(t.year,t.month,1); d=abs((t-pd.Timestamp(t.year,t.month,12)).days)
        if m not in rows or d<rows[m][0]: rows[m]=(d,v,t)
    idx=sorted(rows); return pd.Series([rows[m][1] for m in idx],index=idx), pd.Series([rows[m][2] for m in idx],index=idx)
VAR={'join at 1971 (as shipped)':pd.concat([own[own.index<frd.index.min()],frd]).sort_index(),
     'join at 1983 (own transcription used to its end)':pd.concat([own,frd[frd.index>own.index.max()]]).sort_index(),
     'the transcription dropped, IURSA only':frd,
     'join at 1976':pd.concat([own[own.index<pd.Timestamp('1976-01-01')],frd[frd.index>=pd.Timestamp('1976-01-01')]]).sort_index()}
P(f"{'variant':50s}  onsets 1948..2024                                              others")
for nm,s in VAR.items():
    globals()['SI'],globals()['SW']=mk(s)
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.50; p['bshare']=0.50
    r,t=build9(p); lp=[r['lags_p'].get(i) for i in range(13)]
    P(f"{nm:50s}  {lp}  {[(d,lg) for d,_,lg in r['other']]}")
out.close()
