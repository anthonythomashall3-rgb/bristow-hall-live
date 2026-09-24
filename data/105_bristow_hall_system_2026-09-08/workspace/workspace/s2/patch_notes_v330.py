# -*- coding: utf-8 -*-
"""The detector page, refitted (idempotent string patch to site/template.html; run from workspace/).

Two changes, both asked for on 11 September 2026:

1. The Notes are read first and in full on the screen, as they are on the Sahm rule's FRED page: three short
   paragraphs — what the rule signals, what "real-time" means here and why every call was made blind, and the
   one sentence of evidence that neither half of the sudden stop would do alone. Nothing is deleted. The four
   long paragraphs that stood there are moved, word for word, into a disclosure beneath them ("The rule in
   full..."), so a reader who wants every clause, every line, every vintage and every release day still has it
   one click away and nothing on this page is hidden from anyone.
2. The page is fitted larger and wider, FRED's proportions rather than a cramped copy of them: 15px base,
   1280px measure, a taller graph, a heading scale that separates the sections, and a Notes column set to a
   readable width instead of running the whole way across.
"""
import os,sys,io
T=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else '../site/template.html')
s=io.open(T,encoding='utf-8').read(); o=s
if 'id="notesfull"' in s:
    print('template already refitted'); sys.exit(0)

# ---------- 1. the Notes ----------
A='  <p class="kv"><b>Notes:</b></p>\n'
B='  <p id="sahmnote"></p>'
ia=s.index(A)+len(A); ib=s.index(B)
longtext=s[ia:ib]                     # the four paragraphs, verbatim
assert longtext.count('id="vacnote"')==1 and longtext.count('id="linedmonths"')==1, 'the long notes changed shape'
longtext=longtext.replace('id="linedmonths"','class="linedmonths"')   # the short note now carries the id

short=(
'  <p>The Bristow-Hall Rule signals the start of a recession when a labor-supply object crosses its line — the '
'insured unemployment rate or initial claims rising off their lows, the share of states with the insured rate up, or '
'the Sahm gap with vacancies already falling — and a demand-side object confirms it within a window of six months '
'back and four forward: vacancies, factory hours and nondurable employment, housing starts or building permits with '
'the unemployment rate, or the commercial paper spread. A sudden stop is read the week it happens: initial claims, or '
'United States searches for "unemployment", for "layoffs" or for "laid off", 35 percent or more above base, with the '
'S&amp;P 500 20 percent or more below its high of the prior twenty trading days. It signals the end when the '
'three-week average of initial claims has fallen from its peak for three weeks running and the S&amp;P 500 stands '
'above its six-month low. A recession is dated the month the rule fired, at both ends.</p>\n'
'  <p>The indicator is based on "real-time" data, that is, each series as it stood on its release day, and the line is '
'rebuilt on every day a release the rule reads arrives. It begins in January 1962, the first January at which the '
'rule’s lines were chosen from the past alone; through January 2026 they were re-chosen each January using only the '
'recessions dated and announced by then, so every call on this page was made blind, and they are now fixed. Shaded '
'areas are the recessions dated by the NBER, drawn as FRED draws them; the lined area is the recession the rule dated '
'and the NBER has not (<span id="linedmonths">peak May 2024, trough September 2024</span>).</p>\n'
'  <p>Neither half of the sudden stop would do on its own, which is what "no false alarm" means here: since 1948 the '
'market gate alone has held in nine episodes, three of them outside any recession, and the claims week alone fires '
'eleven times since 1967, five outside one; together they fire twice — 7 October 2008 and 12 March 2020 — and never '
'outside a recession.</p>\n')

s=s[:ia]+short+('  <details id="notesfull"><summary>The rule in full: every clause, the real-time data behind each '
 'series, and how the line is built</summary>\n<div class="full">\n'+longtext+'</div></details>\n')+s[ib:]

# both copies of the lined months are filled
s=s.replace("if(missed.length){ $('#linedmonths').textContent=missed.map(r=>'peak '+fmtML(r.e.open_month+'-01')+', trough '+fmtML(r.e.close_month+'-01')).join('; '); }",
            "if(missed.length){ const lm=missed.map(r=>'peak '+fmtML(r.e.open_month+'-01')+', trough '+fmtML(r.e.close_month+'-01')).join('; ');\n"
            "    $('#linedmonths').textContent=lm; document.querySelectorAll('.linedmonths').forEach(n=>n.textContent=lm); }",1)
assert 'querySelectorAll(\'.linedmonths\')' in s, 'the lined-months line was not patched'

# ---------- 2. the fit ----------
def rep(a,b,n=1):
    global s
    assert s.count(a)==n,(s.count(a),a[:70])
    s=s.replace(a,b)
rep('font-family:Arial,"Helvetica Neue",Helvetica,sans-serif;font-size:14px;line-height:1.45}',
    'font-family:Arial,"Helvetica Neue",Helvetica,sans-serif;font-size:15px;line-height:1.55}')
rep('.inner{max-width:1200px;margin:0 auto;padding:0 20px}',
    '.inner{max-width:1280px;margin:0 auto;padding:0 28px}')
rep('.bhrow{display:flex;align-items:center;justify-content:space-between;padding:12px 20px}',
    '.bhrow{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;padding:14px 28px;max-width:1280px;margin:0 auto}')
rep('h1{font-size:22px;font-weight:400;margin:18px 0 8px;',
    'h1{font-size:29px;font-weight:400;margin:24px 0 10px;')
rep('h1 .id{font-size:14px;color:#333}','h1 .id{font-size:15px;color:#444}')
rep('h2{font-size:20px;font-weight:400;margin:26px 0 6px;border-bottom:1px solid #cfd6de;padding-bottom:6px}',
    'h2{font-size:22px;font-weight:700;color:#111;margin:36px 0 10px;border-bottom:2px solid #0b2545;padding-bottom:7px}')
rep('.meta > div{padding:12px 14px 12px 0;border-right:1px solid #cfd6de;margin-right:14px;min-width:118px}',
    '.meta > div{padding:14px 18px 14px 0;border-right:1px solid #cfd6de;margin-right:18px;min-width:132px}')
rep('.meta > div.obs{max-width:290px;min-width:250px}','.meta > div.obs{max-width:340px;min-width:270px}')
rep('.notes{padding:0 0 0 28px;max-width:1150px}','.notes{padding:0;max-width:900px;font-size:15px;line-height:1.62;color:#2b2b2b}')
rep('.notes p{margin:8px 0}','.notes p{margin:12px 0}')
rep('.notes .kv{margin:6px 0}','.notes .kv{margin:5px 0;color:#333}')
rep('details{margin-top:22px} summary{cursor:pointer;color:#1a5fb4;font-size:15px}',
    'details{margin-top:22px} summary{cursor:pointer;color:#1a5fb4;font-size:15px}\n'
    '#notesfull{margin:16px 0 4px;border-top:1px solid #e3e6ea;padding-top:12px}\n'
    '#notesfull summary{font-size:14px;font-weight:700}\n'
    '#notesfull .full{font-size:14px;line-height:1.6;color:#444;border-left:3px solid #e3e6ea;padding-left:16px;margin-top:10px}\n'
    '#notesfull .full p{margin:12px 0}')
rep("const H=opts.height||FMT.height||420;","const H=opts.height||FMT.height||470;")
io.open(T,'w',encoding='utf-8').write(s)
print('detector refitted: notes',len(short),'chars on screen,',len(longtext),'chars in the disclosure;',len(o),'->',len(s),'bytes')
