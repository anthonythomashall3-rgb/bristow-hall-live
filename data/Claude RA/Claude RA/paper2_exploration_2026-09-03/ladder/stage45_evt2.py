exec(open("stage44_evt.py").read().split('print("\\n=== (C) MISS RATE')[0])
qy=pd.Series(cal[(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))]).dt.year
gy=pd.Series(cal[(~allowed)&(~openmask)&GATE[12]&(cal>=pd.Timestamp("1968-06-01"))]).dt.year
share=gy.nunique()/qy.nunique()
print(f"\n  quiet years 1968-2026: {qy.nunique()}; of those the curve gate is armed in {gy.nunique()} -> {100*share:.0f}%")
FASTN={"Sahm fast","IUR gap fast","payrolls fast","sentiment fast","housing fast","bill fast"}
adj={nm:(p*share if nm in FASTN else p) for nm,p in ps.items() if p==p}
print("  unconditional annual crossing probability (gated channels multiplied by the gate's share of years):")
for nm,p in sorted(adj.items(), key=lambda kv:-kv[1]): print(f"    {nm:20s} {p:.5f}   1 in {1/p:,.0f} yrs" if p>0 else f"    {nm:20s} 0")
pu=1-np.prod([1-p for p in adj.values()])
print(f"\n  UNION (independent): {pu:.4f} per year -> 1 in {1/pu:.0f} years; 10-year risk {1-(1-pu)**10:.3f}")
print(f"  UNION (perfectly dependent): {max(adj.values()):.4f} per year -> 1 in {1/max(adj.values()):.0f} years; 10-year risk {1-(1-max(adj.values()))**10:.3f}")
print(f"  Empirical: 0 crossings in {qy.nunique()} quiet years -> 95% upper bound {3/qy.nunique():.4f} per year -> at least 1 in {qy.nunique()/3:.0f} years")
# expected number of false alarms before the next recession (average expansion ~5 yrs)
for yrs in [5,10]:
    print(f"  expected false alarms in {yrs} years: {yrs*pu:.2f} (independent), {yrs*max(adj.values()):.2f} (dependent), <= {yrs*3/qy.nunique():.2f} (empirical 95% bound)")
