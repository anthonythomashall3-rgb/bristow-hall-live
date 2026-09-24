"""Daily Treasury Statement: withheld individual and FICA taxes, October 2005 on.

A daily payroll-tax flow published one business day after the day it covers, needing no
registered key.  It is the closest daily analogue of the concept the NBER's peak rests on.

THE SERIES LIVES IN TWO TABLES AND CHANGED ITS NAME.  Until 13 February 2023 it is Table
IV, `federal_tax_deposits`, category "Withheld Income and Employment Taxes"; from then it
is `deposits_withdrawals_operating_cash`, category "Taxes - Withheld Individual/FICA".
The first pull of this series took "Individual Income and Employment Taxes, NOT WITHHELD"
from the second table, which is a different and much smaller series - $270 million against
$11,736 million on 15 March 2019 - and the data built on it is withdrawn.
"""
import json, subprocess, pandas as pd, numpy as np
def pull(base,name):
    rows=[]
    for p in range(1,40):
        r=subprocess.run(['curl','-sS','--max-time','180','-A','Mozilla/5.0',base.format(p=p)],capture_output=True)
        j=json.loads(r.stdout.decode('utf-8','replace')); d=j.get('data',[])
        if not d: break
        rows+=d
        if len(d)<10000: break
    df=pd.DataFrame(rows); df['d']=pd.to_datetime(df['record_date'])
    v=[c for c in df.columns if c.endswith('today_amt')][0]
    df['v']=pd.to_numeric(df[v],errors='coerce')
    s=df.groupby('d')['v'].sum().sort_index()
    print(f'{name}: {s.index.min().date()}..{s.index.max().date()}  n={len(s)}  median ${s.median():,.0f}m')
    return s
A=pull(('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/'
        'federal_tax_deposits?fields=record_date,tax_deposit_type,tax_deposit_today_amt'
        '&filter=tax_deposit_type:eq:Withheld%20Income%20and%20Employment%20Taxes'
        '&page%5Bsize%5D=10000&page%5Bnumber%5D={p}&sort=record_date'),'Table IV, to 2023')
B=pull(('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/'
        'deposits_withdrawals_operating_cash?fields=record_date,transaction_catg,transaction_today_amt'
        '&filter=transaction_catg:eq:Taxes%20-%20Withheld%20Individual/FICA'
        '&page%5Bsize%5D=10000&page%5Bnumber%5D={p}&sort=record_date'),'operating cash, 2023 on')
ov=A.index.intersection(B.index)
if len(ov): print(f'   overlap {len(ov)} days, median ratio {float((B[ov]/A[ov]).median()):.4f}')
s=pd.concat([A[A.index<B.index.min()],B]).sort_index()
s.to_csv('/home/claude/lab/weekly/US_daily_withheld_taxes.csv',header=['value'])
print('spliced:',s.index.min().date(),s.index.max().date(),len(s))
m=s.resample('MS').sum(); m=m[m>0]
y=(np.log(m)-np.log(m.shift(12)))*100
print('\nyear-over-year, log x100, around the two peaks in question')
for lo,hi in [('2006-06','2010-06'),('2022-06','2026-08')]:
    t=y[lo:hi]
    for yr,g in t.groupby(t.index.year): print(' ',yr,' '.join(f'{v:6.1f}' for v in g.values))
    print('  --')
