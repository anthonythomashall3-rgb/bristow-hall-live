"""DOL weekly claims NEWS RELEASE archive (report=press), Nov 2002 on: the national ADVANCE figures as first published -
seasonally adjusted initial claims, insured unemployment, the insured unemployment rate, and their unadjusted counterparts."""
import re, os, time, urllib.request, urllib.parse, csv
UA={'User-Agent':'Mozilla/5.0'}
def get(url,data=None,tries=4):
    for i in range(tries):
        try:
            req=urllib.request.Request(url,data=data,headers=UA); return urllib.request.urlopen(req,timeout=60).read().decode('latin-1')
        except Exception as e: time.sleep(3*(i+1)); err=e
    raise err
os.makedirs('dol_press/raw',exist_ok=True); links=[]
for y in range(2002,2027):
    h=get('https://oui.doleta.gov/unemploy/archive.asp',urllib.parse.urlencode({'report':'press','year':str(y),'submit':'Submit'}).encode())
    ls=sorted(set(re.findall(r'/unemploy/(?:press|archive)[^"\']*?%d[^"\']*?\.(?:html|htm|pdf)'%y,h)))
    if not ls: ls=sorted(set(re.findall(r'href="([^"]+)"',h)))
    print(y,len(ls),ls[:3],flush=True); links+=[l for l in ls if str(y) in l and ('press' in l or 'archive' in l)]
print('total',len(links),flush=True)
out=open('dol_press/national_first_prints.csv','w'); w=csv.writer(out); w.writerow(['file','ic_week_ended','icsa_adv','icnsa_adv','iu_week_ended','iur_sa_adv','iusa_adv','iunsa_adv','icsa_prev_revised'])
for l in links:
    f='dol_press/raw/'+l.split('/')[-2]+'_'+l.split('/')[-1]
    if os.path.exists(f): h=open(f,encoding='latin-1').read()
    else:
        h=get('https://oui.doleta.gov'+l if l.startswith('/') else l); open(f,'w',encoding='latin-1').write(h); time.sleep(0.3)
    t=re.sub(r'<[^>]+>',' ',h); t=re.sub(r'&nbsp;?',' ',t); t=re.sub(r'\s+',' ',t)
    def g(p):
        m=re.search(p,t,re.I); return m.group(1).replace(',','') if m else ''
    icw=g(r'week ending ([A-Za-z]+ \d{1,2})[^.]*?advance figure for seasonally adjusted initial claims was ([\d,]+)') 
    m=re.search(r'In the week ending ([A-Za-z]+ \d{1,2}(?:, \d{4})?),? the advance figure for seasonally adjusted initial claims was ([\d,]+)',t,re.I)
    icsa=m.group(2).replace(',','') if m else ''; icw=m.group(1) if m else ''
    m2=re.search(r'previous week.{0,40}?revised (?:up|down)? ?(?:by [\d,]+ )?(?:from [\d,]+ )?to ([\d,]+)',t,re.I); prev=m2.group(1).replace(',','') if m2 else ''
    icn=g(r'advance number of actual initial claims under state programs, unadjusted, totaled ([\d,]+)')
    m3=re.search(r'advance seasonally adjusted insured unemployment rate was ([\d.]+) percent for the week ending ([A-Za-z]+ \d{1,2}(?:, \d{4})?)',t,re.I)
    iur=m3.group(1) if m3 else ''; iuw=m3.group(2) if m3 else ''
    iusa=g(r'advance number for seasonally adjusted insured unemployment during the week ending [A-Za-z]+ \d{1,2}(?:, \d{4})? was ([\d,]+)')
    iun=g(r'advance unadjusted number for persons claiming UI benefits in state programs totaled ([\d,]+)')
    w.writerow([l.split('/')[-1],icw,icsa,icn,iuw,iur,iusa,iun,prev])
out.close(); print('done')
