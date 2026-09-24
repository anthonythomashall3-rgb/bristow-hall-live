"""Stage 20b: RMV1-style provisional stamp + confirmation. Stamp = trigger day (unchanged). Confirmed if within H days either
(i) some channel is on for >= K consecutive days, or (ii) a second, different channel fires. Otherwise the watch is killed."""
exec(open("stage20_days.py").read().split("# ---------- (b) ADS daily reference")[0])
def confirm(eps, arrs, names, H=90, K=28):
    out=[]
    for e in eps:
        i=int(np.where(cal==e["onset"])[0][0]); first=[n for n,a in zip(names,arrs) if a[i]]
        raw=[a for a in arrs]; anyon=np.zeros(N,bool)
        for a in raw: anyon|=a
        seg=anyon[i:i+H+1]; run=0; best=0
        for v in seg:
            run=run+1 if v else 0; best=max(best,run)
        second=[n for n,a in zip(names,arrs) if n not in first and a[i:i+H+1].any()]
        # confirmation day: first day either condition holds
        cday=None
        run=0
        for k in range(H+1):
            run=run+1 if anyon[i+k] else 0
            sec=any(a[i:i+k+1].any() for n,a in zip(names,arrs) if n not in first)
            if run>=K or sec: cday=cal[i+k]; break
        out.append(dict(onset=str(e["onset"].date()), first=first, persist_days=best, second=second, confirmed=cday is not None, confirm_day=str(cday.date()) if cday is not None else None, lag_days=(cday-e["onset"]).days if cday is not None else None))
    return out
chs=[SAHM[0.35], ICmix, PAY, UM["um_d1_10"], HOU, IURmix]
for H,K in [(90,28),(60,28),(90,42)]:
    print(f"\nFIRST-PRINT replay, confirmation window H={H} d, persistence K={K} d:")
    for r in confirm(epsF, chs, namesF, H, K): print("  ", r)
print("\nCURRENT-VINTAGE replay (v2), H=90 K=28:")
chs2=[SAHM[0.35], IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU, IUR4]; names2=["Sahm","claims","payrolls","sentiment","housing","IUR4"]
for r in confirm(eps2, chs2, names2, 90, 28): print("  ", r)
