"""The 1979 half-volume (v.34 nos 27-52, computer-printed uppercase layout) - heading repair (6 September 2026).
The table rows read cleanly (twelve tokens a state) but the OCR of the table HEADING is poor ('FLED DURING EEK ENDEC
APRIL 14, 1579', a date split across lines), so the readers, which date a page by its heading, see 20 of 40 table pages.
Two repairs, both to headings only, never to data: (1) fixed OCR spellings in the heading zone (FLED/FILED, EEK/WEEK,
ENDEC/ENDED, 1579/1979 after 'ENDED <month> <day>,'); (2) each issue's cover carries a clean 'Reference Week: <date>'
line - a claims-table page inside that issue with no readable heading receives a synthetic heading with that date
(initial claims for the reference week, insured unemployment for the week before), unless a day number printed in its
own heading zone contradicts it.  Usage: python3 anchor_v34.py <pages-dir-in> <pages-dir-out>"""
import re, os, sys, glob, shutil
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import parse_ic_tolerant as P
from parse_ui_claims_eras import H1955, to_date
SUBS=[(r'\bF[IL1]?[LE]D\s+DURING',' FILED DURING'),(r'\bFLED\b','FILED'),(r'\bF1LED\b','FILED'),(r'DURING\s+[A-Z]{1,5}EK\s+END','DURING WEEK END'),
      (r'\bENDE[CDOG0]\b','ENDED'),(r'\bEN[D0O]ED\b','ENDED'),(r'\bUNEMPL[A-Z]{4,9}\s+FOR\s+WEEK','UNEMPLOYMENT FOR WEEK'),(r'\bINSUREO\b','INSURED'),
      (r'\bINSURE[D0]\s+UNEMPL','INSURED UNEMPL'),(r'(ENDED\s+[A-Z]{3,9}\.?\s+\d{1,2}[,.]?\s*)1[^\d\s]?[9S5]?7[9S]\b',r'\g<1>1979'),
      (r'(ENDED\s+[A-Z]{3,9}\.?\s+\d{1,2}[,.]?\s*)[1I]979\b',r'\g<1>1979'),(r'(ENDED\s+[A-Z]{3,9}\.?\s+\d{1,2})\.\s*(1979)',r'\1, \2')]
REF=re.compile(r'Reference\s+Week\s*:?\s*((?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s*19\d\d)',re.I)
def main(src,dst):
    shutil.rmtree(dst,ignore_errors=True); shutil.copytree(src,dst); nfix=0
    for p in sorted(glob.glob(dst+'/0*.txt')):
        t=open(p,errors='ignore').read(); t0=t
        for a,b in SUBS: t=re.sub(a,b,t)
        if t!=t0: nfix+=1; open(p,'w').write(t)
    cur=None; inj=0; covers=0; skipped=[]
    for p in sorted(glob.glob(dst+'/0*.txt')):
        txt=open(p,errors='ignore').read(); m=REF.search(txt)
        if m and 'Vol' in txt[:3000]:
            d=to_date(m.group(1))
            if pd.notna(d): cur=d; covers+=1
            continue
        U=txt.upper(); nst=sum(1 for l in txt.split('\n') if P.state_of(l))
        if nst>=15 and 'INITIAL CLAIMS' in U and 'INSURED UNEMPL' in U and 'EXTENDED BENEFIT' not in U and not H1955.search(txt) and cur is not None:
            ok=True
            for mm,dd in re.findall(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\.?\s*\|?\s*(\d{1,2})\b',U[:600].replace('\n',' | ')):
                if int(dd) not in (cur.day,(cur-pd.Timedelta(days=7)).day): ok=False
            if not ok: skipped.append(os.path.basename(p)); continue
            head=f"Initial claims filed during week ended {cur.strftime('%B %-d, %Y')} and insured unemployment for week ended {(cur-pd.Timedelta(days=7)).strftime('%B %-d, %Y')}\n"
            open(p,'w').write(head+txt); inj+=1
    print(f'heading spellings repaired on {nfix} pages; covers read {covers}; synthetic headings injected {inj}; skipped (day mismatch) {skipped}')
if __name__=='__main__': main(sys.argv[1],sys.argv[2])
