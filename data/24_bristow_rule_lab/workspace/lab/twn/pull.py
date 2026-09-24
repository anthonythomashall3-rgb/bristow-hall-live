"""Taiwan, from the Directorate-General of Budget, Accounting and Statistics.

The DGBAS macro statistics database at nstatdb.dgbas.gov.tw serves its tables as JSON from
webMain.aspx?sys=220 once a session cookie is held; the table's field list and date range
come from webMain.aspx?sys=212&x=2100.  Dates are Republic of China years: ROC year + 1911.
"""
import json, subprocess, pandas as pd, re, os
BASE='https://nstatdb.dgbas.gov.tw/dgbasall/webMain.aspx'
def get(url,out):
    subprocess.run(['curl','-s','-k','--max-time','90','-b','cj.txt','-c','cj.txt',
                    '-e',BASE+'?sys=100&funid=defjsp',url,'-o',out],check=True,cwd='/home/claude/lab/twn')
    return open('/home/claude/lab/twn/'+out,encoding='utf-8').read()
def roc(s):
    m=re.match(r'(\d+)年(\d+)月',s)
    if not m: return None
    return pd.Timestamp(int(m.group(1))+1911,int(m.group(2)),1)
def table(funid,cycle,nfld,tag):
    fl='1'*nfld
    j=json.loads(get(f'{BASE}?sys=220&funid={funid}&cycle={cycle}&outkind=1&outmode=8&fldlst={fl}',f'{funid}.json'))
    idx=[roc(r[0]) for r in j['row']]
    cols=[c[0] for c in j['colh'][0]]
    df=pd.DataFrame({c:j['orgdata'][i] for i,c in enumerate(cols)},index=idx)
    df=df[[i is not None for i in idx]]
    df.index.name='date'
    df.to_csv(f'/home/claude/lab/twn/TWN_{tag}.csv')
    print(f'{tag:14s} {funid} {df.shape} {df.index.min().date()}..{df.index.max().date()}')
    print('   ', ' | '.join(cols[:8]))
    return df
table('A120101010',1,5,'bci')
table('A050104010',41,None or 0,'ip') if False else None
