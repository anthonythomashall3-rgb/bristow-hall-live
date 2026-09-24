"""South African Reserve Bank composite business cycle indicators, monthly from 1960.

Public API, no key: https://custom.resbank.co.za/SarbWebApi/
  DIFN002A  composite coincident business cycle indicator (2019 = 100), seasonally adjusted
  DIFN003A  composite leading business cycle indicator
The SARB's own description of DIFN002A: "The coincident business cycle indicator is a
composite index comprising of time series, which tend to move in conjunction with the
business cycle.  Frequency = monthly.  The time series is seasonally adjusted."
"""
import json, os, subprocess, pandas as pd
OUT='/home/claude/lab/sarb'; os.makedirs(OUT,exist_ok=True)
BASE=('https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/'
      'GetTimeseriesObservations/{code}/1900-01-01/2026-12-31')
for code,name in (('DIFN002A','ZAF_coincident'),('DIFN003A','ZAF_leading')):
    p=subprocess.run(['curl','-sS','--max-time','120','-A','Mozilla/5.0',
                      BASE.format(code=code)],capture_output=True)
    d=json.loads(p.stdout.decode('utf-8','replace'))
    if not d: print(code,'empty'); continue
    s=pd.Series({pd.Timestamp(r['Period']).to_period('M').to_timestamp(): float(r['Value'])
                 for r in d}).sort_index()
    s.to_csv(f'{OUT}/{name}.csv',header=['value'])
    print(f'{code} {name}: {s.index.min().date()} .. {s.index.max().date()} n={len(s)}')
