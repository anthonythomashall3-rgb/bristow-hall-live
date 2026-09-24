"""NAHB/Wells Fargo Housing Market Index (SA, monthly from Jan 1985; released the third week of the SAME month, taken as the 17th) as the demand
half of the low branch's pair with the unemployment rate four tenths above its low, real-time pairing. Readings: the level below a line, the
fall from the 12-month max, the 3-month mean level."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast32.py').read().split("res=[]")[0].replace("out=open('fast32.out','w')","out=open('fast34.out','w')"))
x=pd.read_excel(os.path.expandvars("$HOME/mnt/Onset Detector Data/74_release_calendars_two_sided_rule_2026-09-06/data/nahb_hmi_history_202608.xls"),header=None)
rows=[]
for i in range(3,len(x)):
    y=x.iloc[i,0]
    if pd.isna(y) or not str(y).strip().isdigit(): continue
    for j in range(1,13):
        v=x.iloc[i,j]
        if pd.notna(v) and str(v).strip()!='': rows.append((pd.Timestamp(int(y),j,1),float(v)))
hmi=pd.Series(dict(rows)).sort_index(); hmi.to_csv(os.path.expandvars("$HOME/mnt/Onset Detector Data/74_release_calendars_two_sided_rule_2026-09-06/data/nahb_hmi_monthly.csv"),header=['HMI'])
P("HMI span",hmi.index.min().date(),hmi.index.max().date(),len(hmi),"| 1990:",hmi['1990-06':'1990-10'].astype(int).tolist(),"| 2007-08:",hmi['2007-09':'2008-02'].astype(int).tolist(),"| 2022-23:",hmi['2022-10':'2023-03'].astype(int).tolist(),"| 2010:",hmi['2010-05':'2010-10'].astype(int).tolist())
relN=pd.Series({m:pd.Timestamp(m.year,m.month,17) for m in hmi.index})
def screen(nm,dem,reld):
    R=rt_reading(dem,reld); Q=0.0; Qm=None
    for d,key,v in R:
        if any(q-pd.DateOffset(months=6)<=key<=q+pd.DateOffset(months=4) for q in QP) and v>Q: Q=v; Qm=key
    X=Q*1.02 if Q>0 else 0.01; row=dict(series=nm,quiet_max=round(Q,2),quiet_at=Qm.strftime('%Y-%m') if Qm is not None else '',line=round(X,2))
    for y,(a,bb) in RW.items():
        if y<1985: continue
        f=[(d,key,v) for d,key,v in R if a<=key<=bb and v>=X]
        row[str(y)]=(f"{max(min(f)[0],PROP[y]):%Y-%m-%d} (reading {min(f)[2]:.0f} at {min(f)[1]:%Y-%m})"+("*" if max(min(f)[0],PROP[y])<CUR[y] else "")) if f else '-'
    return row
P("HMI level (reading = -HMI):", screen('HMI level',-hmi,relN))
P("HMI fall from 12-mo max:", screen('HMI fall',(hmi.rolling(12).max()-hmi.rolling(2).mean()).dropna(),relN))
P("HMI 3-mo mean level:", screen('HMI 3mo',-hmi.rolling(3).mean().dropna(),relN))
# with the rate half at two tenths (v14's line) for reference
rate4=(((UR-UR.rolling(12).min())*10).round()/2.0)
P("(rate half two tenths) HMI level:", screen('HMI level r2',-hmi,relN))
out.close()
out=open('fast34.out','a')
rate4=(((UR-UR.rolling(12).min())*10).round()/4.0)
P("\nHMI level, reading = 70 - HMI (HMI below L <=> reading >= 70-L):", screen('HMI 70-level',70-hmi,relN))
fall=(hmi.rolling(12).max()-hmi.rolling(2).mean()).dropna()
R=rt_reading(fall,relN)
P("HMI fall readings inside every low-branch quiet window (rate half at line):",sorted([(round(v,1),key.strftime('%Y-%m')) for d,key,v in R if v>0 and any(q-pd.DateOffset(months=6)<=key<=q+pd.DateOffset(months=4) for q in QP)],reverse=True)[:8])
P("HMI fall readings in the 1990 and 2007 windows by month:",{y:[(key.strftime('%Y-%m'),round(v,1),d.strftime('%m-%d')) for d,key,v in R if a<=key<=bb and v>0][:6] for y,(a,bb) in RW.items() if y>=1985})
P("HMI fall readings Oct 2023-Aug 2024 (rate half at line; no low-branch proposal exists there):",[(key.strftime('%Y-%m'),round(v,1)) for d,key,v in R if pd.Timestamp('2023-08-01')<=key<=pd.Timestamp('2024-08-01') and v>0])
P("HMI fall readings 2020:",[(key.strftime('%Y-%m'),round(v,1),d.strftime('%Y-%m-%d')) for d,key,v in R if pd.Timestamp('2020-01-01')<=key<=pd.Timestamp('2020-06-01') and v>0])
out.close()
