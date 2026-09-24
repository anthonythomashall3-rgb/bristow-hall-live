# -*- coding: utf-8 -*-
"""One masthead across the whole site (idempotent; run from workspace/).

Every function the programme publishes or is building is named in the bar at the top right of every page, and
each one is a page you can click. The detector carried a two-item bar ("Home | Detector") while the front door
carried the full list; they are now the same bar, in the same type, on both. The type is set so the bar sits on
one line beside the wordmark at the site's own width instead of wrapping under it."""
import os,io,re
S=os.path.abspath('../site')
NAV=('  <nav class="nav" aria-label="Sections">'
     '<a href="/">Home</a>'
     '<a href="/detector/" aria-current="page">Recession Indicator</a>'
     '<a href="/disturbance/">Disturbance Detector</a>'
     '<a href="/state-onset/">State Onset</a>'
     '<a href="/stress-map/">Stress Map</a>'
     '<a href="/damage-index/">Damage Index</a>'
     '<a href="/chronology/">Chronology</a>'
     '<a href="/papers/recession-signals-without-recession-2024.pdf">Papers</a>'
     '</nav>\n')
p=os.path.join(S,'template.html'); t=io.open(p,encoding='utf-8').read(); o=t
t=re.sub(r'  <nav class="nav" aria-label="Sections">.*?</nav>\n', NAV.replace('\\','\\\\'), t, count=1, flags=re.S)
assert 'href="/chronology/"' in t, 'the detector nav was not replaced'
# the detector's bar in the front door's dress: uppercase, tracked, gold underline on the page you are on
t=t.replace('.nav{display:flex;flex-wrap:wrap;gap:18px;font-size:13.5px}\n.nav a{color:#1a5fb4;padding:2px 0}\n'
            '.nav a[aria-current="page"]{color:#0b2545;font-weight:700;border-bottom:2px solid #c9a227}',
            '.nav{display:flex;flex-wrap:wrap;gap:15px;font-size:11.5px;font-weight:700;letter-spacing:.05em}\n'
            '.nav a{color:#0b2545;text-transform:uppercase;padding:4px 0;border-bottom:2px solid transparent;white-space:nowrap}\n'
            '.nav a:hover{border-bottom-color:#cfd6de;text-decoration:none}\n'
            '.nav a[aria-current="page"]{border-bottom-color:#c9a227}',1)
assert 'text-transform:uppercase' in t, 'the detector nav style was not replaced'
io.open(p,'w',encoding='utf-8').write(t); print('detector masthead:',len(o),'->',len(t))

# the same type on the front door, so the bar sits on one line beside the wordmark
h=os.path.join(S,'template_home.html'); q=io.open(h,encoding='utf-8').read(); oq=q
q=q.replace('.nav{display:flex;flex-wrap:wrap;gap:20px;font-size:12.5px;font-weight:700;letter-spacing:.055em}',
            '.nav{display:flex;flex-wrap:wrap;gap:15px;font-size:11.5px;font-weight:700;letter-spacing:.05em}',1)
q=q.replace('<a href="/#papers">Papers</a>\n  </nav>','<a href="/#papers">Papers</a>\n  </nav>',1)
io.open(h,'w',encoding='utf-8').write(q); print('home masthead:',len(oq),'->',len(q))
