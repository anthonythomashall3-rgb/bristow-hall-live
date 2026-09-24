"""REAL-TIME AUDIT of v2.4: every object read as first published, and where no first print exists, said so.
 (1) the insured rate on the Department's ADVANCE figures (collection 45, 2002-2026) spliced with ALFRED IURSA vintages (2009-) as a check;
 (2) the record run on that spliced real-time series; (3) which of the thirteen calls rest on a revised number, object by object."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast37.py').read().split("RES={}")[0].replace("out=open('fast37.out','w')","out=open('rt1.out','w')"))
import json,urllib.request,urllib.parse,os
env=os.path.expandvars("$HOME/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
key=[l.split('=',1)[1].strip().strip('"').strip("'") for l in open(env) if l.startswith('FRED_API_KEY')][0]
CACHE='cache/iursa_alfred_firstprints.csv'
if not os.path.exists(CACHE):
    q=urllib.parse.urlencode(dict(series_id='IURSA',api_key=key,file_type='json',output_type=2,observation_start='2009-01-01'))
    d=json.load(urllib.request.urlopen("https://api.stlouisfed.org/fred/series/observations?"+q,timeout=180))
    rows=d['observations']; cols=[c for c in rows[0] if c.startswith('IURSA_')]
    fp={}
    for r in rows:
        for c in cols:
            if r.get(c,'.') not in ('.','',None): fp[pd.Timestamp(r['date'])]=(pd.Timestamp(c.split('_')[-1]),float(r[c])); break
    pd.DataFrame({'first_release':{k:v[0] for k,v in fp.items()},'first_print':{k:v[1] for k,v in fp.items()}}).sort_index().to_csv(CACHE)
al=pd.read_csv(CACHE,index_col=0,parse_dates=[0,1])
P("ALFRED IURSA first prints:",al.index.min().date(),"->",al.index.max().date(),len(al),"| release lag days: median",int((al['first_release']-al.index).dt.days.median()),"min",int((al['first_release']-al.index).dt.days.min()),"max",int((al['first_release']-al.index).dt.days.max()))
d45=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/national_first_prints.csv'),parse_dates=['release_date','iu_week_ended'])
adv=d45.dropna(subset=['iu_week_ended','iur_sa']).drop_duplicates('iu_week_ended',keep='first').set_index('iu_week_ended')['iur_sa'].sort_index()
j=pd.concat([adv.rename('dol'),al['first_print'].rename('alfred')],axis=1).dropna()
P(f"DOL advance vs ALFRED first print, {len(j)} overlapping weeks 2009-2026: identical {int((j.dol==j.alfred).sum())}, differ {int((j.dol!=j.alfred).sum())} (max |diff| {float((j.dol-j.alfred).abs().max()):.2f})")
RT=pd.concat([s_cur[s_cur.index<adv.index.min()],adv]).sort_index()   # spl already = this splice; verified
P("real-time insured rate = current file before 2002-10 + Department advance figures after; equals `spl`:",bool((RT.reindex(spl.index).fillna(-9)==spl.fillna(-9)).all()))
gb=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','74_release_calendars_two_sided_rule_2026-09-06/data/greenbook_insured_rate_first_prints.csv'))
P("Greenbook monthly first prints held:",len(gb),"rows,",gb.doc_date.min(),"->",gb.doc_date.max())
P("\nWHICH OBJECT CARRIES EACH CALL, AND IS IT REAL-TIME")
LP=leg_gapx(spl,0.25,rearm='window')+FH25; L=confirm_w(LP,[H35],'month'); X=hub_actual(0.43,vr,0.36); U1=confirm_w(leg_gapx(spl,0.45,rearm='zero')+FHz,[VJ36,Ppx],'month')
r=run3("v2.4 on the real-time insured rate (first prints where they exist)",{'U':U1,'L':L,'X':X})
P("\nvacancy object: JOLTS first prints from",relJ.index.min().strftime('%Y-%m'),"; before that the Barnichon/PNZ help-wanted reconstruction (NOT a vintage series) — which calls use it:")
cond={(p,dd):c for vv in [U1,L,X] for p,dd,c in [(a,b,c if len(str(c))>0 else '') for a,b,c in (vv if vv and len(vv[0])==3 else [])]} if False else {}
for i in range(13):
    if i in r['opens']:
        t=r['opens'][i]; c=[c for vv in [U1,L] for p,dd,c in vv if p==t['published'] and dd==t['date']]
        P(f"   {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} leg {t['leg']} by {c[0] if c else 'hub (Sahm first prints x vacancy)'}")
out.close()
