"""THE CHRONOLOGY WATCH (plan L2; collection 331, 23 September 2026). Reads the committee's two pages and compares them with
chronology/announcements.json, the chronology the rule learns from. A peak or trough month the file does not carry, or an
announcement day the file lacks, is written to chronology/lesson_pending.json and printed for the run log; nothing else
changes - the walk re-runs only after Anthony confirms the entry (L3). Keyless; runs on the first run of each quarter and after
an employment situation release (the scheduler's business), or by hand: python3 s2/chronology_watch.py [--plant YYYY-MM]"""
import os, re, json, sys, datetime, urllib.request
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=os.path.join(HERE,'chronology','announcements.json'); P=os.path.join(HERE,'chronology','lesson_pending.json')
PAGES={'table':'https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions',
       'announcements':'https://www.nber.org/research/business-cycle-dating/business-cycle-dating-committee-announcements'}
MON={m:i for i,m in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'],1)}
def fetch(u):
    req=urllib.request.Request(u,headers={'User-Agent':'bhrrealtime chronology watch (python-urllib)'})
    return urllib.request.urlopen(req,timeout=60).read().decode('utf-8','replace')
def months_in(text):
    """every 'Month YYYY' in the page, as YYYY-MM, in order"""
    out=[]
    for m in re.finditer(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',text):
        out.append('%s-%02d'%(m.group(2),MON[m.group(1).lower()]))
    return out
def announcements_in(text):
    """(announcement day, kind, month) from the page's own announcement lines: 'Announcement of <Month YYYY> business cycle
    peak/trough' (1980-2010) and 'Determination of the <Month YYYY> Peak/Trough' (2020-); the committee's memos are not announcements"""
    t=re.sub(r'<[^>]+>',' ',text); t=re.sub(r'\s+',' ',t)
    out=[]
    pat=re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})(?:(?!Memo|January|February|March|April|May|June|July|August|September|October|November|December|\d{4}).){0,120}?(?:Announcement of|Determination of the)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s+(?:business cycle\s+)?(peak|trough|Peak|Trough)')
    for m in pat.finditer(t):
        day='%s-%02d-%02d'%(m.group(3),MON[m.group(1).lower()],int(m.group(2)))
        month='%s-%02d'%(m.group(5),MON[m.group(4).lower()])
        out.append((day,m.group(6).lower(),month))
    return out
def main(plant=None):
    doc=json.load(open(F)); known_peaks={r['peak'] for r in doc['recessions']}; known_troughs={r['trough'] for r in doc['recessions'] if r.get('trough')}
    known_days={r.get('peak_announced') for r in doc['recessions']}|{r.get('trough_announced') for r in doc['recessions']}
    pending=[]; errors=[]
    try:
        page=fetch(PAGES['announcements']); anns=announcements_in(page)
        for day,kind,month in anns:
            if day>='1980-01-01' and month and day not in known_days:
                if (kind=='peak' and month not in known_peaks) or (kind=='trough' and month not in known_troughs) or day not in known_days:
                    pending.append(dict(kind=kind,month=month,announced=day,source=PAGES['announcements']))
    except Exception as e: errors.append('announcements page: %s'%e)
    try:
        page=fetch(PAGES['table']); ms=[m for m in months_in(page) if m>='1948-01']
        newest=[m for m in ms if m>'2020-04']   # any turning-point month later than the last dated trough
        for m in sorted(set(newest)):
            if m not in known_peaks and m not in known_troughs and not any(p['month']==m for p in pending):
                pending.append(dict(kind='turning point (table)',month=m,announced=None,source=PAGES['table']))
    except Exception as e: errors.append('table page: %s'%e)
    if plant: pending.append(dict(kind='peak',month=plant,announced=datetime.date.today().isoformat(),source='PLANTED TEST ENTRY'))
    out=dict(checked=datetime.date.today().isoformat(),pending=pending,errors=errors)
    if pending:
        json.dump(out,open(P,'w'),indent=1); print('CHRONOLOGY: a dating lesson is pending Anthony\'s confirmation:',pending)
    else:
        if os.path.exists(P) and not plant:
            try: os.remove(P)
            except Exception: pass
        print('chronology watch: the committee\'s pages carry nothing the file lacks%s'%(' (errors: %s)'%errors if errors else ''))
    return out
if __name__=='__main__':
    main(plant=(sys.argv[2] if len(sys.argv)>2 and sys.argv[1]=='--plant' else None))
