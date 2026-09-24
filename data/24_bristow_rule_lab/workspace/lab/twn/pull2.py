import json, subprocess, pandas as pd, re
BASE='https://nstatdb.dgbas.gov.tw/dgbasall/webMain.aspx'
def get(url,out):
    subprocess.run(['curl','-s','-k','--max-time','90','-b','cj.txt','-c','cj.txt',
                    '-e',BASE+'?sys=100&funid=defjsp',url,'-o',out],check=True,cwd='/home/claude/lab/twn')
    return open('/home/claude/lab/twn/'+out,encoding='utf-8').read()
def roc(s):
    m=re.match(r'(\d+)年(\d+)月',s)
    return pd.Timestamp(int(m.group(1))+1911,int(m.group(2)),1) if m else None
def table(funid,cycle,nfld,tag,cod=''):
    fl='1'*nfld
    u=f'{BASE}?sys=220&funid={funid}&cycle={cycle}&outkind=1&outmode=8&fldlst={fl}'+cod
    j=json.loads(get(u,f'{funid}.json'))
    idx=[roc(r[0]) for r in j['row']]
    cols=[]
    for c in j['col']:
        nm=' / '.join([x for x in c if x])
        cols.append(nm)
    df=pd.DataFrame({cols[i]:j['orgdata'][i] for i in range(len(cols))},index=idx)
    df=df[[i is not None for i in idx]]; df.index.name='date'
    df.to_csv(f'/home/claude/lab/twn/TWN_{tag}.csv')
    print(f'{tag:10s} {funid} {df.shape} {df.index.min().date()}..{df.index.max().date()}')
    print('   cols:', cols[:8])
    return df
table('A120101010',1,5,'bci')
table('A050104010',41,10,'ip')
table('A040107010',41,12,'labour','&codlst0=100')
table('A081201010',41,2,'trade','&codlst0=110')
table('A046301010',41,4,'earnings','&codlst0=100')
table('A100101010',41,3,'tax')
