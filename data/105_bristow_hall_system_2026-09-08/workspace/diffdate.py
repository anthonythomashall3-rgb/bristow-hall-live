from mini import *
PAN=pd.read_csv(W+'/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
cols=[c for c in PAN.columns if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
Dx=B.claims_diffusion(PAN[cols],48.,13); pk=B.diffusion_peak_calls(Dx,phase_min=5); tr=B.diffusion_trough_calls(Dx)
print("Department's state diffusion index 48/13 (live leg A), peak calls (call month -> dated):",[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in pk])
print("  trough calls:",[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in tr])
errs=[]
for p,d in pk:
    near=min(PK,key=lambda k:abs(md(d,k))); errs.append((near.strftime('%Y-%m'),d.strftime('%Y-%m'),md(d,near),md(p,near)))
print("  vs committee (peak, dated, date err, call-month lag):",errs)
# the Fieldhouse A (36/8) for comparison
print("FH leg A dates:",[(d.strftime('%Y-%m')) for p,d in PL['A']])
