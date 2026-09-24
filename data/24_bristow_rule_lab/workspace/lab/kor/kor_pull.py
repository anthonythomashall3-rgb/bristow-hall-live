"""Statistics Korea's own coincident composite index, cyclical component — the object
§12 item 1 has been waiting for, and it needs no registered key.

KOSIS's own table DT_1C8015 is behind a registration wall.  The same series is republished
by the Korean government's national indicator portal, 지표누리 / e-나라지표, as indicator
1057 「경기종합지수」, statistical table 105701, MONTHLY FROM JANUARY 1970, sourced there to
『산업활동동향』.  The portal's chart service returns it as JSON with no key:

    POST https://www.index.go.kr/unity/index/IndexTblGraphAjax.do
         sttsCd=105701&chartOrd=1&sDate=197001&eDate=<YYYYMM>&freq=M

and the response's resultList carries, for every month, 동행지수 순환변동치 (the coincident
index's cyclical component) and 선행지수 순환변동치 (the leading index's).  The cyclical
component is what Statistics Korea dates, and the growth-cycle branch is the branch the
rule already routes Korea to.
"""
import json, subprocess, pandas as pd, re
UA='Mozilla/5.0'; REF='https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=1057'
p=subprocess.run(['curl','-sS','-k','-L','--max-time','120','-A',UA,'-e',REF,'-X','POST',
                  '-d','idxCd=1057&sttsCd=105701&chartOrd=1&sDate=197001&eDate=202612&clasCd=011&freq=M',
                  'https://www.index.go.kr/unity/index/IndexTblGraphAjax.do'],capture_output=True)
j=json.loads(p.stdout.decode('utf-8','replace'))
rows=j['resultList']
print('rows',len(rows),'span',rows[0]['descDt'],'..',rows[-1]['descDt'])
names=sorted(set(r['valNm'] for r in rows)); print('series:',names)
out={}
for nm in names:
    d={}
    for r in rows:
        if r['valNm']!=nm: continue
        v=pd.to_numeric(r['nmbrVal'],errors='coerce')
        if pd.notna(v):
            t=r['descDt']; d[pd.Timestamp(int(t[:4]),int(t[4:6]),1)]=float(v)
    s=pd.Series(d).sort_index(); s.index.name='date'; s.name='value'
    out[nm]=s
    tag='coincident_cyclical' if '동행' in nm else 'leading_cyclical'
    s.to_csv(f'/home/claude/lab/kor/KOR_{tag}.csv',header=True)
    print(f'  {nm:24s} -> KOR_{tag}.csv   {s.index.min().date()}..{s.index.max().date()}  n={len(s)}')
