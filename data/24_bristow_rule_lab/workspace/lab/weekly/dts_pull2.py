"""Daily Treasury Statement, Table IV: withheld income and employment taxes.

A daily payroll-tax flow, published one business day after the day it covers, from October
2005.  It is the closest daily analogue of the concept the NBER's peak rests on - payroll
employment - and it needs no registered key.

The first pull of this series took it from the wrong table.  The
`deposits_withdrawals_operating_cash` endpoint carries "Individual Income and Employment
Taxes, NOT WITHHELD", which is a different and much smaller series; withheld taxes are in
`federal_tax_deposits` as "Withheld Income and Employment Taxes".  Verified on 15 March
2019: $11,736 million withheld against $270 million not withheld.
"""
import json, subprocess, pandas as pd
B=('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/'
   'federal_tax_deposits?fields=record_date,tax_deposit_type,tax_deposit_today_amt'
   '&filter=tax_deposit_type:eq:Withheld%20Income%20and%20Employment%20Taxes'
   '&page%5Bsize%5D=10000&page%5Bnumber%5D={p}&sort=record_date')
rows=[]
for p in range(1,40):
    r=subprocess.run(['curl','-sS','--max-time','180','-A','Mozilla/5.0',B.format(p=p)],capture_output=True)
    try: j=json.loads(r.stdout.decode('utf-8','replace'))
    except Exception as e: print('page',p,'parse fail',r.stdout[:200]); break
    d=j.get('data',[])
    print('page',p,'rows',len(d), d[0]['record_date'] if d else '', d[-1]['record_date'] if d else '',flush=True)
    if not d: break
    rows+=d
    if len(d)<10000: break
df=pd.DataFrame(rows)
df['d']=pd.to_datetime(df['record_date']); df['v']=pd.to_numeric(df['tax_deposit_today_amt'],errors='coerce')
s=df.groupby('d')['v'].sum().sort_index()
s.to_csv('/home/claude/lab/weekly/US_daily_withheld_taxes.csv',header=['value'])
print('daily withheld taxes:',s.index.min().date(),s.index.max().date(),len(s),
      'median $%.0fm'%s.median())
