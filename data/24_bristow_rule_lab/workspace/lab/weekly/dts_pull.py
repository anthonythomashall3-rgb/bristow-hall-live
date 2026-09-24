"""Daily Treasury Statement, withheld individual/FICA tax deposits: a daily payroll proxy.
Fiscal Data API, no registered key.  Category names changed in 2022, so both are taken."""
import json, subprocess, pandas as pd, urllib.parse
BASE=('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/'
      'deposits_withdrawals_operating_cash?fields=record_date,transaction_catg,'
      'transaction_today_amt&page%5Bsize%5D=10000&page%5Bnumber%5D={p}&sort=record_date')
rows=[]
for p in range(1,120):
    r=subprocess.run(['curl','-sS','--max-time','180','-A','Mozilla/5.0',BASE.format(p=p)],
                     capture_output=True)
    try: j=json.loads(r.stdout.decode('utf-8','replace'))
    except Exception: print('page',p,'parse fail',flush=True); break
    d=j.get('data',[])
    if not d: break
    rows+=[x for x in d if 'ithheld' in str(x.get('transaction_catg',''))]
    if p%10==0: print('page',p,'kept',len(rows),d[-1]['record_date'],flush=True)
    if len(d)<10000: break
df=pd.DataFrame(rows)
df['d']=pd.to_datetime(df['record_date'])
df['v']=pd.to_numeric(df['transaction_today_amt'],errors='coerce')
s=df.groupby('d')['v'].sum().sort_index()
s.to_csv('/home/claude/lab/weekly/US_daily_withheld_taxes.csv',header=['value'])
print('daily withheld taxes:',s.index.min().date(),s.index.max().date(),len(s))
