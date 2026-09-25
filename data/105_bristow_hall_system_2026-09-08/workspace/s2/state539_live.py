"""Keep the Department's ETA 539 state panel current (the breadth object's data).

Collection 37 built `panel/panel_539_weekly.csv` once, on 4 September 2026, from the Department's keyless file
https://oui.doleta.gov/unemploy/csv/ar539.csv. Nothing refreshed it after that, so the state breadth object froze while
every other feed moved (found 11 September 2026, when the page began listing every feed with its own through-date).
This script appends the weeks the Department has published since, and saves the raw file beside the panel.

Causal: only weeks AFTER the panel's last week are appended, so the weeks already in hand keep the values they were
first published with; revisions to earlier weeks are not written back. Prints one line for the run log.
Run: python3 s2/state539_live.py
"""
import os,sys,shutil,subprocess,datetime,json
import pandas as pd

# The collection root. Tried at ~/Projects first, then derived from this file's own location, then the
# ~/mnt symlink. Hardcoding one of the three meant the chain worked on the Mac and failed anywhere else -
# the Linux side of the bridge, a second machine, a restored backup under a different home - and on
# 18 September s2/q41_data_check.py, the gate's own 113-check safety net, could not be run off the Mac
# at all. Written once here, the same three lines in every chain file that needs the root.
def _bhs_root():
    # __file__ is absent when a chain file is exec'd from a string, which walk94 does: the first version of this
    # helper raised NameError there and took the walk down with it. Every candidate is now guarded.
    import os as _o
    cands = [_o.path.expanduser('~/Projects/Onset Detector Data')]
    _f = globals().get('__file__')
    if _f:
        _d = _o.path.dirname(_o.path.abspath(_f))
        cands += [_o.path.abspath(_o.path.join(_d, '..', '..', '..')),
                  _o.path.abspath(_o.path.join(_d, '..', '..'))]
    cands += [_o.path.abspath(_o.path.join(_o.getcwd(), '..', '..')),
              _o.path.abspath(_o.path.join(_o.getcwd(), '..')),
              _o.path.expanduser('~/mnt/Onset Detector Data')]
    for c in cands:
        if _o.path.isdir(_o.path.join(c, '105_bristow_hall_system_2026-09-08')): return c
    return _o.path.expanduser('~/Projects/Onset Detector Data')
C37=os.path.join(_bhs_root(),'37_dol_eta5159_2026-09')
PANEL=os.path.join(C37,'panel','panel_539_weekly.csv'); RAW=os.path.join(C37,'raw','ar539.csv')
URL='https://oui.doleta.gov/unemploy/csv/ar539.csv'
STATES=set("""AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO
MT NE NV NH NJ NM NY NC ND OH OK OR PA PR RI SC SD TN TX UT VT VA VI WA WV WI WY""".split())
KEEP={'c3':'ic','c8':'cw','c17':'at','c18':'ce','c19':'iur13','c20':'ar'}

HDR=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'cache','ar539_headers.json')   # the headers of the file last read
def _head():
    """the Department's ETag, Last-Modified and size for the file, by a HEAD request; None when it did not answer"""
    r=subprocess.run(['curl','-sIL','--max-time','30',URL],capture_output=True,text=True)
    if r.returncode!=0: return None
    h={}
    for ln in r.stdout.splitlines():
        if ':' in ln: k,v=ln.split(':',1); h[k.strip().lower()]=v.strip()
    if not (h.get('etag') or h.get('last-modified')): return None
    return {'etag':h.get('etag'),'last-modified':h.get('last-modified'),'content-length':h.get('content-length')}
def _save_head(hd):
    if hd:
        try: json.dump(hd,open(HDR,'w'))
        except Exception: pass

def main():
    if not os.path.exists(PANEL): print('state 539: no panel at '+PANEL); return 1
    cur=pd.read_csv(PANEL,parse_dates=['week']); mx=cur['week'].max()
    age=(pd.Timestamp(datetime.date.today())-mx).days
    if age<10: print(f'state 539: no new week expected yet (through {mx.date()}, {age} days old)'); return 0
    tmp='/tmp/ar539_live.csv'; hd=None
    if len(sys.argv)>2 and sys.argv[1]=='--from':          # ingest a file already downloaded (same columns)
        tmp=sys.argv[2]
    else:
        # 17 September 2026 (Anthony: "as fast as possible, as safe as possible"): the 13 MB file is downloaded only when the
        # Department's own headers say it has changed since the file last read (--force, the day's first run, downloads regardless)
        hd=_head()
        if hd is not None and '--force' not in sys.argv and os.path.exists(HDR):
            try: old=json.load(open(HDR))
            except Exception: old={}
            if old and all(old.get(k)==hd.get(k) for k in ('etag','last-modified','content-length')):
                print(f"state 539: the Department's file is unchanged since last read (modified {hd.get('last-modified')}); panel stands through {mx.date()}"); return 0
        ok=False; err=''
        for k in range(3):                                  # the Department's file is 13 MB and times out now and then
            r=subprocess.run(['curl','-sSL','--max-time','300','--retry','2','--retry-delay','5','-o',tmp,URL],capture_output=True,text=True)
            if r.returncode==0 and os.path.exists(tmp) and os.path.getsize(tmp)>1_000_000: ok=True; break
            err=(r.stderr or 'short file').strip()[:80]
            import time as _t; _t.sleep(10*(k+1))
        if not ok:
            print(f'state 539: download failed ({err}); panel stands through {mx.date()}'); return 1
    if not os.path.exists(tmp) or os.path.getsize(tmp)<1_000_000:
        print(f'state 539: no usable file; panel stands through {mx.date()}'); return 1
    w=pd.read_csv(tmp,low_memory=False)
    w=w[w['st'].isin(STATES)].copy(); w['week']=pd.to_datetime(w['c2'],errors='coerce')
    ww=w[['st','week']+list(KEEP)].rename(columns=KEEP)
    for c in KEEP.values(): ww[c]=pd.to_numeric(ww[c],errors='coerce')
    ww=ww.dropna(subset=['week'])
    new=ww[ww['week']>mx].sort_values(['st','week'])
    if not len(new): _save_head(hd); print(f'state 539: nothing new (panel and the Department both through {mx.date()})'); return 0
    shutil.copy(PANEL,PANEL+'.bak'); shutil.copy(tmp,RAW+'.new') if os.path.exists(RAW) else None
    out=pd.concat([cur,new],ignore_index=True).sort_values(['st','week'])
    out.to_csv(PANEL,index=False)
    if os.path.exists(RAW):
        shutil.copy(RAW,RAW+'.bak'); shutil.move(RAW+'.new',RAW)
    else: shutil.copy(tmp,RAW)
    wk=sorted(new['week'].unique()); n=new['st'].nunique(); _save_head(hd)
    print(f'state 539: {len(new)} state-week rows appended for {len(wk)} week(s) through {pd.Timestamp(wk[-1]).date()} ({n} states reporting)')
    return 0

if __name__=='__main__': sys.exit(main())
