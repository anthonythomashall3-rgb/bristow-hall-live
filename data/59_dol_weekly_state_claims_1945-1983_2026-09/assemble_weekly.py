"""Weekly state panels of both fields, 1945-1983, from the readers that are right for each layout (5 Sep 2026):
  1945-09 .. 1954-03  parse_early_verified.py  (columns identified by the table's own arithmetic; 'verified' tier,
                      plus the 'partial' tier of the 1950-52 layout whose first triple is initial claims)
  1954-03 .. 1983-05  the reconciled positional readers (ic_weekly_state_1945_1983_wide.csv from reconcile_ic.py,
                      iu_weekly_state_1945_1983_wide.csv from reconcile_iu.py) - the first token of the 1955-83 layout
Where two prints of one state-week disagree by more than 2 per cent both are dropped (the cell is 'conflict').
Outputs weekly_ic_1945_1983.csv and weekly_cc_1945_1983.csv (state abbreviations as columns)."""
import pandas as pd, numpy as np, glob
NAME2AB={'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Puerto Rico':'PR','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virgin Islands':'VI','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
CUT=pd.Timestamp('1954-03-13')
E=pd.concat([pd.read_csv(f,parse_dates=['week']) for f in sorted(glob.glob('early_verified_v*.csv'))])
E=E[(E.week>='1945-06-01')&(E.week<CUT)]
E=E[(E.tier=='verified')|((E.tier=='partial')&(E.layout=='L9'))]
import re
def yrs(lab):
    m=re.search(r'_(19\d\d)_(\d\d)',lab); a=int(m.group(1)); b=int(m.group(1)[:2]+m.group(2)); return a-1,b+1
lo=E.volume.map(lambda l:yrs(l)[0]); hi=E.volume.map(lambda l:yrs(l)[1]); E=E[(E.week.dt.year>=lo)&(E.week.dt.year<=hi)]
E['st']=E.state.map(NAME2AB); E=E.dropna(subset=['st'])
out={}
for field,late,col in [('ic','ic_weekly_state_1945_1983_wide.csv','ic'),('cc','iu_weekly_state_1945_1983_wide.csv','iu')]:
    e=E[E.field==field]
    g=e.groupby(['st','week']).value.agg(['median','min','max','count'])
    ok=(g['max']-g['min'])<=np.maximum(2,0.02*g['median'])
    early=g['median'].where(ok).dropna().unstack(0)
    print(field,'early: state-weeks',int(g.shape[0]),'conflicts dropped',int((~ok).sum()),'weeks',early.shape[0],early.index.min().date(),early.index.max().date())
    L=pd.read_csv(late,index_col=0,parse_dates=True).rename(columns=NAME2AB); L=L[L.index>=CUT]
    W=pd.concat([early,L]).sort_index(); W=W.groupby(level=0).first()
    W.to_csv(f'weekly_{field}_1945_1983.csv'); out[field]=W
    cov=W.notna().sum(axis=1); print(field,'panel',W.shape,'median states/week by year',cov.groupby(cov.index.year).median().astype(int).to_dict())
