"""Philadelphia Fed manufacturing business outlook survey, general activity diffusion index (SA, 1968-; FRED GACDFSA066MSFRBPHI, held in
lab/ind), released the third Thursday of the SAME month (taken as the 18th), as the demand half of the low branch's pair with the
unemployment rate four tenths above its low, real-time pairing; demand reading = the index level itself (below a line), and its fall from
its 12-month max. Quiet maxima in every low-branch proposal window and the firings at 1973/1981/1990/2007."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast32.py').read().split("res=[]")[0].replace("out=open('fast32.out','w')","out=open('fast33.out','w')"))
b=pd.read_csv(W+'/lab/ind/GACDFSA066MSFRBPHI.csv'); b.columns=['d','v']; b['d']=pd.to_datetime(b['d']); bos=b.set_index('d')['v'].astype(float)
relB=pd.Series({m:pd.Timestamp(m.year,m.month,18) for m in bos.index})
def screen(nm,dem,reld):
    R=rt_reading(dem,reld); Q=0.0; Qm=None
    for d,key,v in R:
        if any(q-pd.DateOffset(months=6)<=key<=q+pd.DateOffset(months=4) for q in QP) and v>Q: Q=v; Qm=key
    X=Q*1.02 if Q>0 else 0.01; row=dict(series=nm,quiet_max=round(Q,2),quiet_at=Qm.strftime('%Y-%m') if Qm is not None else '',line=round(X,2))
    for y,(a,bb) in RW.items():
        f=[d for d,key,v in R if a<=key<=bb and v>=X]
        row[str(y)]=(f"{max(min(f),PROP[y]):%Y-%m-%d}"+("*" if max(min(f),PROP[y])<CUR[y] else "")) if f else '-'
    # what the recession months read
    row['reads']={y:round(max([v for d,key,v in R if a<=key<=bb]+[0]),1) for y,(a,bb) in RW.items()}
    return row
P("BOS as a LEVEL below a line (reading = -index):", screen('BOS level',-bos,relB))
P("BOS fall from its 12-month max (points):", screen('BOS fall',(bos.rolling(12).max()-bos.rolling(2).mean()).dropna(),relB))
P("BOS 3-month mean level:", screen('BOS 3mo level',-bos.rolling(3).mean().dropna(),relB))
# the same three readings with the rate half at two tenths for reference (v8/v14's line)
rate4=(((UR-UR.rolling(12).min())*10).round()/2.0)
P("(rate half TWO tenths) BOS level:", screen('BOS level r2',-bos,relB))
out.close()
