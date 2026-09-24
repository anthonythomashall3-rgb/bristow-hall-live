"""THE BRISTOW HALL SYSTEM — build the page. Injects site/bhs_state.json into site/template.html and writes
site/index.html (the copy the artifact publisher wraps in its own document; downloads there open on the page) and
site/public/index.html (a complete document for Cloudflare Pages; downloads there save files). Run from the
collection 105 workspace after bhs_build.py:
    python3 bhs_site.py
Then, if a Cloudflare token is configured, deploy.sh publishes the site folder."""
import os, json
HOME=os.path.expanduser('~'); COL=os.path.join(HOME,'mnt','Onset Detector Data','105_bristow_hall_system_2026-09-08')
SITE=os.path.join(COL,'site')
state=json.load(open(os.path.join(SITE,'bhs_state.json')))
t=open(os.path.join(SITE,'template.html'),encoding='utf-8').read()
assert t.count('__STATE__')==1 and t.count('__SITE__')==1, 'template must contain exactly one __STATE__ and one __SITE__ token'
page=t.replace('__STATE__',json.dumps(state,separators=(',',':')))
# the artifact publisher wraps the file in a document skeleton; a web server does not, so the standalone copy gets one
head,body=page.split('</style>',1); head=head+'</style>'
full='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+head+'\n</head>\n<body>\n'+body+'\n</body>\n</html>\n'
os.makedirs(os.path.join(SITE,'public'),exist_ok=True)
open(os.path.join(SITE,'index.html'),'w',encoding='utf-8').write(page.replace('__SITE__','false'))          # for the artifact publisher
os.makedirs(os.path.join(SITE,'public','detector'),exist_ok=True)
open(os.path.join(SITE,'public','detector','index.html'),'w',encoding='utf-8').write(full.replace('__SITE__','true'))  # the indicator, for Cloudflare Pages
json.dump(state,open(os.path.join(SITE,'public','bhs_state.json'),'w'))                                     # the data beside the page
json.dump(state,open(os.path.join(SITE,'public','detector','bhs_state.json'),'w'))

# ---- the home page: the programme's front door, carrying only what the programme publishes today ----
_sp=[(d,v) for d,v in zip(state['series']['dates'],state['series']['values'])] if 'series' in state else []
if not _sp:
    _S=state.get('daily') or {}; _sp=[(d,v) for d,v in zip(_S.get('dates',[]),_S.get('values',[]))]
_sp=[p for p in _sp if p[0]>='1975-01-01']
_last=_sp[-1] if _sp else (None,None)
_step=max(1,len(_sp)//420); _sp=_sp[::_step]
if _sp and _last[0]!=_sp[-1][0]: _sp.append(_last)   # keep the newest observation whatever the decimation
_bands=[]
for _r in state.get('nber',[]):
    try:
        _y,_m=[int(x) for x in _r['trough'].split('-')]; _e=(f'{_y+1}-01-01' if _m==12 else f'{_y}-{_m+1:02d}-01')
        _bands.append([_r['peak']+'-01',_e])
    except Exception: pass
for _e in state.get('episodes',[]):
    if _e.get('open_month') and _e.get('close_month'): _bands.append([_e['open_month']+'-01',_e['close_month']+'-28'])
_tp=os.path.join(HOME,'mnt','Onset Detector Data','109_home_tiles_2026-09-11','home_tiles.json')
_tiles=(json.load(open(_tp))['tiles'] if os.path.exists(_tp) else [])
home=dict(standing=state['standing'],tiles=_tiles,
          last_date=_last[0],last_value=_last[1],
          spark=dict(dates=[p[0] for p in _sp],values=[p[1] for p in _sp]),bands=_bands)
_h=open(os.path.join(SITE,'template_home.html'),encoding='utf-8').read()
assert _h.count('__HOME__')==1, 'the home template needs exactly one __HOME__ token'
_hh,_hb=_h.replace('__HOME__',json.dumps(home,separators=(',',':'))).split('</style>',1)
_full_home='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+_hh+'</style>\n</head>\n<body>\n'+_hb+'\n</body>\n</html>\n'
open(os.path.join(SITE,'public','index.html'),'w',encoding='utf-8').write(_full_home)
print('home built: standing',state['standing']['state'],'| public/index.html',len(_full_home),'bytes')
print('site built:',state['built'],'| standing',state['standing']['state'],'since',state['standing']['since'],'| public/detector/index.html',len(full),'bytes')
