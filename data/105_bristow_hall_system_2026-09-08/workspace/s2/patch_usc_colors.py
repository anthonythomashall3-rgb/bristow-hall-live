# -*- coding: utf-8 -*-
"""The site in the university's colours (idempotent; run from workspace/).

Duke Bristow and Anthony Hall are both at the University of Southern California, and the site now says so without
saying it: cardinal where the navy was, the university's gold where the old gold was, white behind everything, and
a gold stripe across the top of every page. The palette is USC's own — cardinal #990000 (PMS 201) and gold #FFCC00
(PMS 123) — used the way the university uses it: gold on cardinal, cardinal on white, never small gold type on white,
which no one can read.

The semantic colours are left alone on purpose: the green of "no recession open" and of a zero error still mean what
they meant, and the red of a reading over its line is darkened to #7f0000 so that it cannot be mistaken for a link now
that links are cardinal."""
import os,io,sys
S=os.path.abspath('../site')
MAP=[('#0b2545','#990000'),   # the navy of the masthead, the wordmark, the headings and the footer
     ('#1a5fb4','#990000'),   # links
     ('#1f6fd1','#990000'),   # the plotted line and the bars
     ('#c9a227','#FFCC00'),   # the accent: the monogram's bar, the current-page underline, the 1.00 reference
     ('#eef4fb','#fdf2f2'),   # hover
     ('#dbe8f8','#f7dede'),   # selected
     ('#b3261e','#7f0000'),   # a reading over its line, and a negative error
     ('#dbe4ee','#f3e3e3'),   # the footer's text on cardinal
     ('#b9c6d6','#edcaca')]
for name in ('template.html','template_home.html'):
    p=os.path.join(S,name); t=io.open(p,encoding='utf-8').read(); o=t
    if '/* USC */' in t: print(name,'already in the university\'s colours'); continue
    for a,b in MAP: t=t.replace(a,b); t=t.replace(a.upper(),b); t=t.replace(a.lower(),b)
    # gold is unreadable as small type on white: the wordmark's second line goes cardinal, the gold moves to the rules
    t=t.replace('.l2{letter-spacing:.34em;font-size:11px;color:#FFCC00','.l2{letter-spacing:.34em;font-size:11px;color:#990000')
    t=t.replace('.l2{letter-spacing:.28em;font-size:11.5px;color:#FFCC00','.l2{letter-spacing:.28em;font-size:11.5px;color:#990000')
    # the gold stripe across the top of every page, and gold on cardinal in the footer
    t=t.replace('.bh{background:#ffffff;border-bottom:3px solid #990000}','/* USC */\n.bh{background:#ffffff;border-top:5px solid #FFCC00;border-bottom:3px solid #990000}',1)
    t=t.replace('.bh{background:#fff;border-bottom:1px solid #dfe4ea}','/* USC */\n.bh{background:#fff;border-top:5px solid #FFCC00;border-bottom:2px solid #990000}',1)
    t=t.replace('.foot .t{font-weight:800;letter-spacing:.12em;font-size:13.5px;color:#fff}','.foot .t{font-weight:800;letter-spacing:.12em;font-size:13.5px;color:#FFCC00}')
    assert '/* USC */' in t, ('the masthead rule was not found in '+name)
    io.open(p,'w',encoding='utf-8').write(t); print(name,'recoloured:',len(o),'->',len(t))
