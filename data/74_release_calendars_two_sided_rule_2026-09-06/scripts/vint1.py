"""RULE ZERO CHECK ON THE CREDIT SUBINDEX. Anthony asked whether the tool is real-time or mixed. That question was put
to every object. The Chicago Fed's NFCI family FAILS it twice over: its ALFRED vintages begin 5 July 2012 (the index
was first published in 2011, so no reading of it existed in 1973), and the whole history is RE-ESTIMATED every week -
the August 1973 credit subindex reads -0.47 in the 2015 vintage, +0.18 in the 2020 vintage and -2.20 today. The memo's
claim that 'the reading that fires is the one that printed' is withdrawn. Here the tool is re-scored WITHOUT it."""
exec(open('fast50.py').read().split("full('v3.3r")[0].replace("out=open('fast50.out','w')","out=open('vint1.out','w')"))
P("v3.4 as shipped (credit subindex IN — not real-time before July 2012):")
full('  v3.4 (with credit subindex)',[CRD,SPR],look45=91)
P("\nv3.5 — the credit subindex REMOVED, the paper spread kept (H.15 rates, published daily, never revised):")
full('  v3.5 (paper spread only)',[SPR],look45=91)
P("\nAnd with the paper spread's line swept, to see whether it can carry 1973 on its own:")
def full2(nm,ln,look45=91):
    S2=dict(name='paper spread',gap=GSP,line=ln,pub_lag_days=1); full(nm,[S2],look45=look45)
qs=sorted([(float(wseg(GSP,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GSP,dd))],reverse=True)
P(f"   the paper spread's quiet maximum is {qs[0][0]:.3f} ({qs[0][1]}); 1973's window reaches {float(wseg(GSP,PK[5]).max()):.3f}")
for ln in [1.00,1.15,1.323,1.40]: full2(f'  paper spread at {ln}',ln)
out.close()
