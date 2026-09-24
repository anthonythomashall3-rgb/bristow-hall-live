# patch_feeds.py - 11 September 2026. Anthony: every series the rule reads must be shown on the page, with where it comes
# from, how often it updates, what it is through, and when it next updates - the daily ones (the S&P 500 close and the
# three search terms) included, which the "Next data" list did not name. Adds `feeds` to the state JSON and a table to the
# page. Idempotent; run from 105/workspace: python3 s2/patch_feeds.py
import os,sys
B='bhs_build.py'; T='../site/template.html'
s=open(B).read()
if 'feeds=FEEDS' in s: print('bhs_build already patched')
else:
    anchor="NEXT.sort(key=lambda z:(0,z['date']) if len(z['date'])==10 else (1,z['date']))\n"
    assert s.count(anchor)==1
    FEEDS='''
# ---- every feed the rule reads: where it comes from, how often it updates, what it is through, when it updates next ----
def _fthr(x):
    try: return lastv(x)[1]
    except Exception: return None
_h15next=next((c['date'] for c in CAL if c['kind']=='h15'),None)
_nxt=lambda w: next((n['date'] for n in NEXT if n['what'].startswith(w)),None)
FEEDS=[
 dict(name='Initial claims, continued claims, insured unemployment rate',source='Department of Labor (the UI claims news release; ALFRED vintages after it)',every='Weekly - Thursday 8:30 AM ET (Wednesday before a Thursday holiday)',through=_fthr(ICfp),next=_nxt('Weekly claims'),auto='yes'),
 dict(name='State insured unemployment rates (the breadth object)',source='Department of Labor',every='Weekly - Thursday 8:30 AM ET, two weeks behind initial claims',through=_fthr(RAW['B']),next=nxt_claims(_fthr(RAW['B']) or str(today),19),auto='yes'),
 dict(name='Unemployment rate, factory hours, nondurable employment',source='Bureau of Labor Statistics, Employment Situation',every='Monthly - usually the first Friday, 8:30 AM ET',through=_fthr(g_asof),next=_nxt('Employment Situation'),auto='yes'),
 dict(name='Job openings (the vacancy rate)',source='Bureau of Labor Statistics, JOLTS',every='Monthly - about five weeks after the month, 10:00 AM ET',through=_fthr(G),next=_nxt('JOLTS'),auto='yes'),
 dict(name='Housing starts and building permits',source='Census Bureau, New Residential Construction',every='Monthly - about the 17th, 8:30 AM ET',through=_fthr(MX),next=_nxt('Housing starts'),auto='yes'),
 dict(name='Commercial paper and three-month bill rates (the spread)',source='Federal Reserve, H.15 selected interest rates',every='Weekly - the first business day after the week, 4:15 PM ET',through=_fthr(cS),next=_h15next,auto='yes'),
 dict(name='S&P 500 daily close (the market gate of the sudden stop)',source='Yahoo Finance daily close',every='Every trading day - read at the 4:20 PM ET run, and again at 5:00 PM',through=_fthr(_SPX),next='the next weekday close',auto='yes'),
 dict(name='Sahm rule, real time (the comparator on the speed panel)',source='FRED SAHMREALTIME',every='Monthly - with the employment report',through=(SAHM.index[-1].strftime('%Y-%m') if len(SAHM) else None),next=_nxt('Employment Situation'),auto='yes'),
]
_TSRC={'unemp':'"unemployment"','layoffs':'"layoffs"','laidoff':'"laid off"'}
for _tg,(_a,_b,_r) in (GT_TERMS.items() if 'GT_TERMS' in globals() else []):
    FEEDS.append(dict(name=f'Search week: Google searches for {_TSRC.get(_tg,_tg)} (the sudden stop\\'s second labour datum)',source='Google Trends, United States, daily index stitched onto one scale and extended each day',every="Daily - the day's index is known the next morning; read at every weekday close",through=_fthr(_r),next='the next weekday close',auto='yes'))
'''
    s=s.replace(anchor,anchor+FEEDS)
    s=s.replace("next_releases=NEXT,calendar=CAL","next_releases=NEXT,feeds=FEEDS,calendar=CAL")
    assert 'feeds=FEEDS' in s
    open(B,'w').write(s); print('bhs_build patched')

t=open(T).read()
if 'id="feeds"' in t: print('template already patched'); sys.exit(0)
a='  <ul id="nextlist"></ul>\n'
assert t.count(a)==1
b=('  <ul id="nextlist"></ul>\n'
   '  <p class="kv"><b>Every series the rule reads</b> (what it is through, and when it next updates; the page fetches nothing itself '
   '— a job on the machine that runs the rule refreshes each of these on its own schedule and rebuilds this page):</p>\n'
   '  <div style="overflow-x:auto"><table id="feeds" style="border-collapse:collapse;font-size:12.5px;margin:2px 0 10px">'
   '<thead><tr><th style="text-align:left;padding:3px 10px 3px 0">Data</th><th style="text-align:left;padding:3px 10px 3px 0">Source</th>'
   '<th style="text-align:left;padding:3px 10px 3px 0">Updates</th><th style="text-align:left;padding:3px 10px 3px 0">In hand through</th>'
   '<th style="text-align:left;padding:3px 0">Next update</th></tr></thead><tbody></tbody></table></div>\n')
t=t.replace(a,b)
# render it from the JSON, next to the nextlist rendering
a2="const ul=$('#nextlist'); ul.innerHTML='';"
assert t.count(a2)==1
b2=("const fb=document.querySelector('#feeds tbody'); if(fb){ fb.innerHTML='';\n"
    "      for(const f of (S.feeds||[])){ const tr=document.createElement('tr');\n"
    "        const nx=(f.next&&/^\\d{4}-\\d{2}-\\d{2}$/.test(f.next))?fmtD(f.next):(f.next||'—');\n"
    "        const th=(f.through&&/^\\d{4}-\\d{2}-\\d{2}$/.test(f.through))?fmtD(f.through):(f.through&&/^\\d{4}-\\d{2}$/.test(f.through)?fmtM(f.through):(f.through||'—'));\n"
    "        tr.innerHTML='<td style=\"padding:3px 10px 3px 0;border-top:1px solid #eef1f4\">'+esc(f.name)+'</td>'\n"
    "          +'<td style=\"padding:3px 10px 3px 0;border-top:1px solid #eef1f4;color:#555\">'+esc(f.source)+'</td>'\n"
    "          +'<td style=\"padding:3px 10px 3px 0;border-top:1px solid #eef1f4\">'+esc(f.every)+'</td>'\n"
    "          +'<td style=\"padding:3px 10px 3px 0;border-top:1px solid #eef1f4\">'+th+'</td>'\n"
    "          +'<td style=\"padding:3px 0;border-top:1px solid #eef1f4\">'+nx+'</td>';\n"
    "        fb.appendChild(tr); } }\n"
    "    const ul=$('#nextlist'); ul.innerHTML='';")
t=t.replace(a2,b2)
# the dated list: show eight, and name the daily run first
a3="for(const n of up.slice(0,6)){"
assert t.count(a3)==1
b3=("{ const li=document.createElement('li'); li.innerHTML='<b>Every weekday, 4:20 PM ET</b> — the S&amp;P 500 close and the search week "
    "(Google searches for \"unemployment\", \"layoffs\" and \"laid off\"), read that evening; the day\\'s search index is known the next morning'; ul.appendChild(li); }\n"
    "    for(const n of up.slice(0,8)){")
t=t.replace(a3,b3)
open(T,'w').write(t); print('template patched')
