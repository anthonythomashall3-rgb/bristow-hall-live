"""DOL 'Regular State Data' (page 8 of the weekly claims release), every week from the archive: the FIRST PRINT of each
state's initial claims and insured unemployment, as published the Thursday after the week.  Saved raw + parsed."""
import re, os, time, urllib.request, urllib.parse, csv, sys
UA={'User-Agent':'Mozilla/5.0'}
def get(url,data=None,tries=4):
    for i in range(tries):
        try:
            req=urllib.request.Request(url,data=data,headers=UA); return urllib.request.urlopen(req,timeout=60).read().decode('latin-1')
        except Exception as e: time.sleep(3*(i+1)); err=e
    raise err
os.makedirs('dol_page8/raw',exist_ok=True)
links=[]
for y in range(2002,2027):
    h=get('https://oui.doleta.gov/unemploy/archive.asp',urllib.parse.urlencode({'report':'page8','year':str(y),'submit':'Submit'}).encode())
    ls=sorted(set(re.findall(r'/unemploy/page8/%d/[0-9]+\.html'%y,h))); links+=ls; print(y,len(ls),flush=True)
print('total',len(links),flush=True)
out=open('dol_page8/state_first_prints.csv','w'); w=csv.writer(out); w.writerow(['release_file','ic_week_ended','iu_week_ended','state','ic_state','ic_chg_wk','ic_chg_yr','ucfe_ic','ucx_ic','iu_state','iur','iu_chg_wk','iu_chg_yr','ucfe_iu','ucx_iu','iu_all_ex_rr'])
n=0
for l in links:
    f='dol_page8/raw/'+l.split('/')[-2]+'_'+l.split('/')[-1]
    if os.path.exists(f): h=open(f,encoding='latin-1').read()
    else:
        h=get('https://oui.doleta.gov'+l); open(f,'w',encoding='latin-1').write(h); time.sleep(0.3)
    t=re.sub(r'<[^>]+>',' ',h); t=re.sub(r'\s+',' ',t)
    m1=re.search(r'Initial Claims Filed During Week Ended\s*([A-Za-z]+ \d+, \d{4})',t); m2=re.search(r'Insured Unemployment For Week Ended\s*([A-Za-z]+ \d+, \d{4})',t)
    d1=m1.group(1) if m1 else ''; d2=m2.group(1) if m2 else ''
    for row in re.findall(r'<TR[^>]*>(.*?)</TR>',h,re.S|re.I):
        cells=[re.sub(r'<[^>]+>','',c).replace('&nbsp','').replace(';','').strip() for c in re.findall(r'<T[DH][^>]*>(.*?)</T[DH]>',row,re.S|re.I)]
        if len(cells)<14 or not cells[0] or cells[0].upper()==cells[0]: continue
        vals=[c.replace(',','') for c in cells]
        w.writerow([l.split('/')[-1],d1,d2]+[vals[0]]+vals[1:6]+vals[7:16]); n+=1
    if len(links)>0 and links.index(l)%100==0: print(l,n,flush=True)
out.close(); print('rows',n)
