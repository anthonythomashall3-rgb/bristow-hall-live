"""bhs_dol_press.py - the weekly claims FIRST PRINT read from the Department of Labor's own release (www.dol.gov/ui/data.pdf)
on the release day, so that the live system does not wait for FRED/ALFRED to post it (10 September 2026: FRED had not
carried the 8:30 release three hours later). The release is the first print by definition; ALFRED's initial release is
the same number, and bhs_update.py compares the two once ALFRED carries the week (logged, never silently replaced).
Appends one row to collection 45 (national_first_prints.csv, kind 'dol_pdf') when the release's claims week is not yet
there; keeps the PDF under collection 45 raw/press_live/<release date>.pdf. Import and call dol_press_extend(C45, say)."""
import os,re,subprocess,shutil,datetime
import pandas as pd
URL='https://www.dol.gov/ui/data.pdf'
MONTHS={m:i for i,m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
def _text(pdf):
    for exe in ('/opt/homebrew/bin/pdftotext','/usr/local/bin/pdftotext','pdftotext'):
        try: return subprocess.run([exe,'-l','2',pdf,'-'],capture_output=True,text=True,timeout=60).stdout
        except FileNotFoundError: continue
    raise RuntimeError('pdftotext not found')
def _date_for(monthday,release):
    """'September 5' -> the Saturday of that name nearest before the release day (the release's own year, or the prior one)."""
    m,d=monthday.split(); m=MONTHS[m]; d=int(d)
    for y in (release.year,release.year-1):
        t=pd.Timestamp(y,m,d)
        if t<=release: return t
    raise ValueError(monthday)
def parse(t,release):
    t=re.sub(r'\s+',' ',t)
    m=re.search(r'EMBARGOED UNTIL 8:30 A\.M\. \(Eastern\)\s*[A-Za-z]+,\s*([A-Za-z]+ \d{1,2}, \d{4})',t)
    rel=pd.Timestamp(m.group(1)) if m else release
    m=re.search(r'In the week ending ([A-Za-z]+ \d{1,2}(?:, \d{4})?),? the advance figure for seasonally adjusted initial claims was ([\d,]+)',t,re.I)
    if not m: raise ValueError('no advance initial claims sentence')
    icw=m.group(1).split(',')[0]; icsa=float(m.group(2).replace(',',''))
    m2=re.search(r"previous week'?s? level was revised (?:up|down) by [\d,]+ from [\d,]+ to ([\d,]+)",t,re.I); prev=float(m2.group(1).replace(',','')) if m2 else ''
    m4=re.search(r'advance number of actual initial claims under state programs, unadjusted, totaled ([\d,]+)',t,re.I); icn=float(m4.group(1).replace(',','')) if m4 else ''
    m3=re.search(r'advance seasonally adjusted insured unemployment rate was ([\d.]+) percent for the week ending ([A-Za-z]+ \d{1,2}(?:, \d{4})?)',t,re.I)
    iur=float(m3.group(1)) if m3 else ''; iuw=m3.group(2).split(',')[0] if m3 else ''
    m5=re.search(r'advance number for seasonally adjusted insured unemployment during the week ending [A-Za-z]+ \d{1,2}(?:, \d{4})? was ([\d,]+)',t,re.I); iusa=float(m5.group(1).replace(',','')) if m5 else ''
    m6=re.search(r'advance unadjusted number for persons claiming UI benefits in state programs totaled ([\d,]+)',t,re.I); iun=float(m6.group(1).replace(',','')) if m6 else ''
    icwe=_date_for(icw,rel); iuwe=_date_for(iuw,rel) if iuw else icwe-pd.Timedelta(days=7)
    return dict(release=rel.strftime('%m%d%y'),ic_week=icw,icsa=icsa,icsa_prev_rev=prev,icnsa=icn,iu_week=iuw,iur_sa=iur,iusa=iusa,iunsa=iun,kind='dol_pdf',
                release_date=rel.strftime('%Y-%m-%d'),ic_week_ended=icwe.strftime('%Y-%m-%d'),iu_week_ended=iuwe.strftime('%Y-%m-%d'))
def dol_press_extend(C45,say,today=None):
    today=pd.Timestamp(today or datetime.date.today())
    raw=os.path.join(os.path.dirname(C45),'raw','press_live'); os.makedirs(raw,exist_ok=True)
    tmp=os.path.join(raw,'latest.pdf')
    # curl's own user agent: the Department's site answers a browser or custom agent with 403 (10 September 2026); three tries
    r=subprocess.run(['curl','-sSL','-m','60','--retry','3','--retry-delay','5','--retry-all-errors','-o',tmp,URL],capture_output=True,text=True)
    ok=r.returncode==0 and os.path.exists(tmp) and os.path.getsize(tmp)>20000 and open(tmp,'rb').read(5)==b'%PDF-'
    if not ok: say(f'DOL release: not fetched ({r.stderr.strip()[:80] or "not a PDF"})'); return False
    row=parse(_text(tmp),today)
    keep=os.path.join(raw,f"{row['release_date']}.pdf"); shutil.copy(tmp,keep)
    N=pd.read_csv(C45,dtype=str)
    if row['ic_week_ended'] in set(N.ic_week_ended.dropna()): say(f"DOL release of {row['release_date']}: week ending {row['ic_week_ended']} already in collection 45"); return False
    N=pd.concat([N,pd.DataFrame([{k:('' if v=='' else str(v)) for k,v in row.items()}])],ignore_index=True)
    N['_rd']=pd.to_datetime(N.release_date); N=N.sort_values(['_rd','release']).drop(columns='_rd'); N.to_csv(C45,index=False)
    say(f"first prints: 1 release appended to collection 45 from the Department's own release: {(row['release_date'],row['ic_week_ended'],row['icsa'],row['iu_week_ended'],row['iur_sa'])}")
    return True
if __name__=='__main__':
    import sys; C45=sys.argv[1]; print(parse(_text(sys.argv[2]),pd.Timestamp(datetime.date.today())) if len(sys.argv)>2 else dol_press_extend(C45,print))
