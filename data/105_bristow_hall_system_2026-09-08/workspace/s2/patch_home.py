# patch_home.py - 11 September 2026. The site gets a home page: the programme's front door at /, the indicator at
# /detector/, and a navigation bar carrying Home and Detector on both (more tools join the bar as they are built).
# Idempotent; run from 105/workspace: python3 s2/patch_home.py
import os,sys
T=os.path.abspath('../site/template.html'); S=os.path.abspath('bhs_site.py'); A=os.path.abspath('s2/audit_site.py')

# 1. the indicator page gets the same masthead nav, with Detector as the current page
t=open(T).read()
if 'class="nav"' in t: print('template: nav already there')
else:
    a='<header class="bh"><div class="inner bhrow">\n  <div class="logo" aria-label="The Bristow-Hall System"><div class="mono">BH<span></span></div><div class="wm"><div class="l1">BRISTOW-HALL</div><div class="l2">SYSTEM</div></div></div>\n</div></header>'
    assert t.count(a)==1, 'masthead not found'
    b=('<header class="bh"><div class="inner bhrow">\n'
       '  <div class="logo" aria-label="Bristow-Hall Business Cycle Program"><div class="mono">BH<span></span></div><div class="wm"><div class="l1">BRISTOW-HALL</div><div class="l2">BUSINESS CYCLE PROGRAM</div></div></div>\n'
       '  <nav class="nav" aria-label="Sections"><a href="/">Home</a><a href="/detector/" aria-current="page">Detector</a></nav>\n'
       '</div></header>')
    t=t.replace(a,b)
    c='.bhrow{display:flex;align-items:center;justify-content:space-between;padding:12px 20px}'
    assert t.count(c)==1
    t=t.replace(c,c+'\n.nav{display:flex;flex-wrap:wrap;gap:18px;font-size:13.5px}\n.nav a{color:#1a5fb4;padding:2px 0}\n.nav a[aria-current="page"]{color:#0b2545;font-weight:700;border-bottom:2px solid #c9a227}')
    open(T,'w').write(t); print('template: nav added')

# 2. bhs_site.py writes the home page at public/index.html and the indicator at public/detector/index.html
s=open(S).read()
if 'template_home.html' in s: print('bhs_site: already patched')
else:
    a="""open(os.path.join(SITE,'public','index.html'),'w',encoding='utf-8').write(full.replace('__SITE__','true'))  # for Cloudflare Pages
json.dump(state,open(os.path.join(SITE,'public','bhs_state.json'),'w'))                                     # the data beside the page"""
    assert s.count(a)==1, 'bhs_site anchor'
    b = """os.makedirs(os.path.join(SITE,'public','detector'),exist_ok=True)
open(os.path.join(SITE,'public','detector','index.html'),'w',encoding='utf-8').write(full.replace('__SITE__','true'))  # the indicator, for Cloudflare Pages
json.dump(state,open(os.path.join(SITE,'public','bhs_state.json'),'w'))                                     # the data beside the page
json.dump(state,open(os.path.join(SITE,'public','detector','bhs_state.json'),'w'))

# ---- the home page: the programme's front door, carrying only what the programme publishes today ----
_sp=[(d,v) for d,v in zip(state['series']['dates'],state['series']['values'])] if 'series' in state else []
if not _sp:
    _S=state.get('daily') or {}; _sp=[(d,v) for d,v in zip(_S.get('dates',[]),_S.get('values',[]))]
_sp=[p for p in _sp if p[0]>='1975-01-01']
_step=max(1,len(_sp)//420); _sp=_sp[::_step]
_bands=[]
for _r in state.get('nber',[]):
    try:
        _y,_m=[int(x) for x in _r['trough'].split('-')]; _e=(f'{_y+1}-01-01' if _m==12 else f'{_y}-{_m+1:02d}-01')
        _bands.append([_r['peak']+'-01',_e])
    except Exception: pass
for _e in state.get('episodes',[]):
    if _e.get('open_month') and _e.get('close_month'): _bands.append([_e['open_month']+'-01',_e['close_month']+'-28'])
home=dict(version=state['version'],built=state['built'],built_at=state.get('built_at',''),standing=state['standing'],
          last_date=(_sp[-1][0] if _sp else None),last_value=(_sp[-1][1] if _sp else None),
          through_claims=state['through'].get('claims'),through_sp500=state['through'].get('sp500'),
          spark=dict(dates=[p[0] for p in _sp],values=[p[1] for p in _sp]),bands=_bands)
_h=open(os.path.join(SITE,'template_home.html'),encoding='utf-8').read()
assert _h.count('__HOME__')==1, 'the home template needs exactly one __HOME__ token'
_hh,_hb=_h.replace('__HOME__',json.dumps(home,separators=(',',':'))).split('</style>',1)
_full_home='<!doctype html>\\n<html lang="en">\\n<head>\\n<meta charset="utf-8">\\n<meta name="viewport" content="width=device-width, initial-scale=1">\\n'+_hh+'</style>\\n</head>\\n<body>\\n'+_hb+'\\n</body>\\n</html>\\n'
open(os.path.join(SITE,'public','index.html'),'w',encoding='utf-8').write(_full_home)
print('home built: standing',state['standing']['state'],'| public/index.html',len(_full_home),'bytes')"""
    s=s.replace(a,b); open(S,'w').write(s); print('bhs_site: patched')

# 3. the audit reads the indicator page where it now lives
a2=open(A).read()
o2="'site','public','index.html'"
if o2 in a2:
    a2=a2.replace(o2,"'site','public','detector','index.html'"); open(A,'w').write(a2); print('audit: reads public/detector/index.html')
else: print('audit: already pointed at the detector page')
