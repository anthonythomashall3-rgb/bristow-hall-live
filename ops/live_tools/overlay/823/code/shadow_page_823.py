# shadow_page_823.py (825; carried in the repo since 1153, ops/live_tools/overlay/823; no AI at run time): the site page /shadow/ for the best tool run beside v3.76, from 823/out/live_state_823.json.
# The page shell (head, USC header, nav, footer) is copied from the site's own /margins/ page; only the title and the body block change.
# Writes <live clone>/data/105_.../site/public/shadow/index.html; prints CHANGED or SAME.
import json, glob, os, html, datetime as dt
ROOT = '/Users/anthonyhall/Projects/Onset Detector Data'
PUB = glob.glob(ROOT + '/105_*/cloud/data/105_bristow_hall_system_2026-09-08/site/public')[0]
S = json.load(open(glob.glob(ROOT + '/823_*/out/live_state_823.json')[0]))
NB = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'), ('1969-12', '1970-11'), ('1973-11', '1975-03'),
      ('1980-01', '1980-07'), ('1981-07', '1982-11'), ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04')]   # 26 Nov 2026 (Anthony): the 2024 recession is not shownts March 2024, so the peak month is February (1154)
def fd(s): return dt.date.fromisoformat(s[:10]).strftime('%b %-d, %Y') if s else 'open'
def fm(m): return dt.date.fromisoformat(m + '-01').strftime('%b %Y')
# 1153 (19 Nov 2026): the NBER has dated no recession in 2024; the last row of NB is Paper 1's (Hall and Bristow: onset March 2024, end August 2024) and says so
def P1(k): return ''
src = open(PUB + '/margins/index.html').read().split('\n')
i = next(k for k, l in enumerate(src) if l.startswith('<div class="inner"><h2'))
st = S['state']; state = 'No recession' if st.startswith('NO RECESSION') else ('Recession' if st.startswith('RECESSION') else 'Watch')
rows = ''
for k, e in enumerate(S['episodes']):
    p, t = NB[k] if k < len(NB) else ('-', '-')
    rows += '<tr><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>' % (fd(e['start']), fd(e['end']), (fm(p) + P1(k)) if p != '-' else '-', (fm(t) + P1(k)) if t != '-' else '-')
body = ('<div class="inner"><h2 style="margin-top:30px">Shadow</h2><div class="rule"></div>'
        '<p style="font-size:22px;margin:14px 0 4px"><b>%s</b></p><p class="sub">%s</p>'
        '<div class="dwrap"><table class="dtab"><thead><tr><th class="num">Start</th><th class="num">End</th><th class="num">NBER peak</th><th class="num">NBER trough</th></tr></thead><tbody>%s</tbody></table></div></div>'
        % (html.escape(state), html.escape(fd(S['today'])), rows))
out = src[:i] + [body] + src[i + 1:]
out = '\n'.join(out).replace('Bristow-Hall Business Cycle Program — Margins', 'Bristow-Hall Business Cycle Program — Shadow').replace('Bristow-Hall System — Margins', 'Bristow-Hall System — Shadow').replace('aria-current="page"', '')
os.makedirs(PUB + '/shadow', exist_ok=True); p = PUB + '/shadow/index.html'
old = open(p).read() if os.path.exists(p) else None
if old != out: open(p, 'w').write(out); print('CHANGED', p)
else: print('SAME', p)
