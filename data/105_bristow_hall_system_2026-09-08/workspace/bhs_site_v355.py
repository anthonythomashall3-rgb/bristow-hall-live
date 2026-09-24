"""THE BRISTOW HALL SYSTEM — build the page. Injects site/bhs_state.json into site/template.html and writes
site/index.html (the copy the artifact publisher wraps in its own document; downloads there open on the page) and
site/public/index.html (a complete document for Cloudflare Pages; downloads there save files). Run from the
collection 105 workspace after bhs_build.py:
    python3 bhs_site.py
Then, if a Cloudflare token is configured, deploy.sh publishes the site folder."""
import os, json
HOME=os.path.expanduser('~'); COL=os.path.join(HOME,'mnt','Onset Detector Data','105_bristow_hall_system_2026-09-08')
SITE=os.path.join(COL,'staged_v355','site')
state=json.load(open(os.path.join(SITE,'bhs_state.json')))
t=open(os.path.join(COL,'site','template_v355.html'),encoding='utf-8').read()
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
_h=open(os.path.join(COL,'site','template_home.html'),encoding='utf-8').read()
assert _h.count('__HOME__')==1, 'the home template needs exactly one __HOME__ token'
_hh,_hb=_h.replace('__HOME__',json.dumps(home,separators=(',',':'))).split('</style>',1)
_full_home='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+_hh+'</style>\n</head>\n<body>\n'+_hb+'\n</body>\n</html>\n'
open(os.path.join(SITE,'public','index.html'),'w',encoding='utf-8').write(_full_home)
print('home built: standing',state['standing']['state'],'| public/index.html',len(_full_home),'bytes')
print('site built:',state['built'],'| standing',state['standing']['state'],'since',state['standing']['since'],'| public/detector/index.html',len(full),'bytes')

# ---- the pages the masthead names but the programme has not published yet ----
# Every function in the top bar is clickable: each unbuilt one gets its own page, in the site's own dress,
# saying plainly what it will be and what it waits on. They are generated from the home template, so the
# masthead, the nav and the footer can never drift between the front door and these.
import re as _re2
_style=_re2.search(r'<style>.*?</style>',_h,_re2.S).group(0)
_header=_re2.search(r'<header class="bh">.*?</header>',_h,_re2.S).group(0)
_footer=_re2.search(r'<div class="foot">.*?</div></div>',_h,_re2.S).group(0)
_STUBS=[
 ('disturbance','Real-Time National Disturbance Indicator',
  'The national labour disturbance beneath a call: what moved, when it moved, and how far it went.',
  'The detector reads the same public releases as the recession indicator and asks a narrower question — not whether a recession has opened, but whether the labour market has been disturbed at all, and in which of its parts. It waits on the disturbance measure being written down and walked forward on the same terms as the rule: every clause fixed before it is scored, every number read as it stood on its release day.'),
 ('state-onset','Real-Time State Recession Indicator',
  'The same rule read state by state, so an onset is seen where it starts and not only in the aggregate.',
  'The weekly state claims and the state unemployment rates are already gathered and refreshed at every release (collections 37 and 45). What remains is the walk: the rule read on each state separately, from 1976 forward, with no line chosen from a state’s own future. Until that walk is finished and audited nothing is published here.'),
 ('stress-map','National Stress Map',
  'Labour-market stress across the fifty states and the District, on one scale, week by week.',
  'One scale, one week, fifty-one places. The map draws on the same weekly state claims as the state onset detector; it waits on the scale being fixed in advance, so that a state’s colour means the same thing in 1980 as in 2026.'),
 ('damage-index','Damage Index',
  'A Richter scale for recessions: how deep, how broad, and where — not only when.',
  'Dating a recession says when; it does not say how much. The index measures the depth of the fall and the breadth of the states and industries carrying it on one scale fixed in advance, so that two recessions can be compared without hindsight about either, and so that a disturbance a national date hides — one state, one industry — still has a number. It is the subject of Paper 3, <i>The Damage Index: A Richter Scale for Recessions</i>.'),
 ('chronology','Business-Cycle Chronology',
  'The programme’s dated chronology of peaks and troughs beside the committee’s and the OECD’s.',
  'The rule’s own peaks and troughs, 1948 to today, set beside the National Bureau’s and the OECD’s, with the days each was called and the days each was announced. The material exists in the record; the page is what remains.'),
]
for _slug,_name,_tag,_body in _STUBS:
    _nav=_header.replace(' aria-current="page"','').replace('href="/%s/"'%_slug,'href="/%s/" aria-current="page"'%_slug)
    _p=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Bristow-Hall Business Cycle Program — '+_name+'</title>\n'
        +_style+'\n<style>.stub{max-width:none;margin:38px 0 0}.stub h1{font-size:30px;color:#990000;margin:0 0 10px;line-height:1.2}'
        '.stub .tag{font-size:17px;color:#333;margin:0 0 18px;max-width:none}.stub p{color:#333;margin:0 0 14px}'
        '.stub .back{margin-top:26px;font-size:14px}</style>\n</head>\n<body>\n'
        +_nav+'\n<div class="inner"><div class="stub">'
        '<span class="badge dev">IN DEVELOPMENT</span>'
        '<h1>'+_name+'</h1><p class="tag">'+_tag+'</p><p>'+_body+'</p>'
        '<p>Nothing is published on a page here until its rule is written down, walked forward with no line chosen from the future, and audited. '
        'The recession indicator, which has been through that, is <a href="/detector/">live now</a>.</p>'
        '<p class="back"><a href="/">&larr; Back to the programme</a></p></div></div>\n'
        +_footer+'\n</body>\n</html>\n')
    os.makedirs(os.path.join(SITE,'public',_slug),exist_ok=True)
    open(os.path.join(SITE,'public',_slug,'index.html'),'w',encoding='utf-8').write(_p)
print('stub pages built:',', '.join('/'+s+'/' for s,_,_,_ in _STUBS))

# ---- /data/ : the inventory of every series the site stands on ----
# Built from the state file's own `feeds` block (the series the rule reads, with the value each stands at, the day
# each is in hand through, and the day its source next publishes) and from the front page's tiles (collection 109,
# the published series the reading is shown beside). Nothing here is typed: if the page and the inventory ever
# disagreed, they would be reading different objects, and they cannot - they read the same ones.
def _esc(x):
    return ('' if x is None else str(x)).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def _fmtd(d):
    try:
        y,m,dd=str(d).split('-'); return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m)-1]+' '+str(int(dd))+', '+y
    except Exception:
        try:
            y,m=str(d).split('-'); return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m)-1]+' '+y
        except Exception: return _esc(d)
def _row(name,url,value,through,nxt,src,every,note=None,period=None,obj=None):
    t1=('<a href="'+_esc(url)+'" target="_blank" rel="noopener">'+_esc(name)+' &#8599;</a>') if url else _esc(name)
    return ('<tr><td><b>'+t1+'</b><div class="src">'+_esc(src)+(' &middot; '+_esc(every) if every else '')+'</div>'
            +('<div class="note">'+_esc(note)+'</div>' if note else '')
            +'</td><td class="val">'+(_esc(value) if value else '<span class="na">&mdash;</span>')+'</td>'
            +'<td class="num">'+(_fmtd(through) if through else (_esc(period) if period else '<span class="na">&mdash;</span>'))+'</td>'
            +'<td class="num">'+(_fmtd(nxt) if nxt else '<span class="na">&mdash;</span>')+'</td></tr>')
_rule_rows=''.join(_row(f.get('name'),f.get('url'),f.get('value'),f.get('through'),f.get('next'),f.get('source'),f.get('every'),f.get('note'),None,
   ('<div class="obj">the rule reads it as: '+_esc(f['object'])+' &mdash; <b>'+('{:.2f}'.format(f['object_reading']))+'</b> of the line '+_esc(f['object_line'])+'</div>') if f.get('object') else None)
  for f in state.get('feeds',[]))
_tile_rows=''.join(_row(t.get('lab'),('https://fred.stlouisfed.org/series/'+t['sid']) if t.get('sid') else None,t.get('val'),None,t.get('next'),
                        ('FRED series '+t['sid']) if t.get('sid') else 'FRED',None,t.get('sub')) for t in _tiles)
_nav_data=_header.replace(' aria-current="page"','').replace('href="/data/"','href="/data/" aria-current="page"')
_datapage=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
 '<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Bristow-Hall Business Cycle Program — Data</title>\n'
 +_style+'\n<style>.dtab{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}'
 '.dtab th{text-align:left;font-weight:700;color:#222;border-bottom:2px solid #990000;padding:9px 10px 7px;background:#faf7f7;white-space:nowrap}'
 '.dtab th.num,.dtab td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}'
 '.dtab td{padding:11px 10px;border-bottom:1px solid #dfe4ea;vertical-align:top}'
 '.dtab td.val{font-weight:700;color:#111}'
 '.dtab .src{color:#666;font-size:12.5px;font-weight:400;margin-top:3px}'
 '.dtab .note{color:#7f0000;font-size:12.5px;margin-top:4px}'
 '.dtab .na{color:#999}.dtab .obj{font-weight:400;color:#555;font-size:12.5px;margin-top:5px}'
 '.dwrap{overflow-x:auto}.dlede{max-width:none;color:#333;margin:16px 0 0}</style>\n</head>\n<body>\n'
 +_nav_data+'\n<div class="inner">'
 '<h2 style="margin-top:30px">Data</h2><div class="rule"></div>'
 '<div class="dwrap"><table class="dtab">'
 '<thead><tr><th>Series</th><th>Where it stands</th><th class="num">In hand through</th><th class="num">Next published</th></tr></thead><tbody>'
 +_rule_rows+'</tbody></table></div>'
 '</div>\n'+_footer+'\n</body>\n</html>\n')
os.makedirs(os.path.join(SITE,'public','data'),exist_ok=True)
open(os.path.join(SITE,'public','data','index.html'),'w',encoding='utf-8').write(_datapage)
print('data inventory built:',len(state.get('feeds',[])),'rule series,',len(_tiles),'front-page series')
