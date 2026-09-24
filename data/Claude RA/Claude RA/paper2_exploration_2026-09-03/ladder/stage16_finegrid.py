exec(open("stage15_housing.py").read().split("base=[SAHM[0.35]")[0])
def persist2(s, x):
    c=(s<=-x/100); return D(c & c.shift(1).fillna(False))
for p in [0.25]:
    IC["ic8_25_k1"]=wk(r8>=p)
SAHM[0.30]=D(Srel>=0.30-1e-9)
UMx={x: mo(um-um.shift(1)<=-x, 0) for x in [8,9,10,12]}
HSx={x: persist2(h3,x) for x in [18,20,22,25]}
rows=[]
for th in [0.30,0.35,0.40]:
  for icn in ["ic8_25_k1","ic8_30_k1","ic4_30_k2"]:
    for ux in [8,9,10,12]:
      for hx in [18,20,22,25]:
        for fd in [90,120,180]:
          chs=[SAHM[th], IC[icn], PAY, UMx[ux], HSx[hx]]
          eps=replay3(chs, GATE[12], fd); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
          if any(l is None for l in L): continue
          rows.append(dict(sahm=th,ic=icn,um=ux,hs=hx,fresh=fd,n_false=len(false),false=false[:3],lags=L,sum_abs=sum(abs(x) for x in L),n_out2=sum(abs(x)>2 for x in L),n_le1=sum(abs(x)<=1 for x in L),
                           end=[r["end_lag"] for r in res], tr=[r["tr_err"] for r in res], onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); df.to_csv("stage16_fine.csv",index=False); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",130)
z=df[df.n_false==0].sort_values(["n_out2","sum_abs"]); print(z.drop(columns=["onsets","end","tr","false"]).head(15).to_string())
print("\nfrontier n_false->min n_out2:", df.groupby("n_false").n_out2.min().head(3).to_dict())
for _,r in z.head(3).iterrows(): print(dict(r[["sahm","ic","um","hs","fresh"]]), r.onsets, "end", r.end, "tr", r.tr)
