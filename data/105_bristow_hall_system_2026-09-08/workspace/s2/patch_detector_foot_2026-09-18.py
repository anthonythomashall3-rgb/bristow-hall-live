# Detector page (18 Sep 2026, site-UI chat, round 5): the row under the graph laid out as FRED's - the source and the
# recession note on the left, the site name and the Fullscreen button on the right - and the recession note cut to
# one short line (Anthony: "as brief as possible").
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new):
    global t
    n = t.count(old); assert n == 1, ('expected 1, found %d: ' % n) + old[:110]
    t = t.replace(old, new)
NBER = 'https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions'
NOTE = 'Shaded areas indicate U.S. recessions. Lined areas: recessions dated only by the Bristow-Hall Rule.'
MAX = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>'
MIN = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"/></svg>'
# CSS: one row, left and right, as FRED's; FRED's type size; the button like the header's
rep(".plot .foot{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:6px 16px;font-size:13px;color:#333;margin-top:8px}",
    ".plot .foot{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:8px 24px;font-size:16px;color:#222;margin-top:10px}")
rep(".plot .foot .right{display:flex;align-items:center;gap:12px}",
    ".plot .foot .right{display:flex;align-items:center;gap:22px;margin-left:auto;color:#333}\n"
    ".plot .foot .src em a{color:#990000}\n"
    ".plot .foot .btn{font-size:16px;height:38px;padding:0 14px;border-radius:5px;border-width:1.5px;display:inline-flex;align-items:center;gap:9px}")
# HTML
a = t.index('<div class="foot"><div class="src">Source: Bristow, Duke and Hall, Anthony via the Bristow-Hall System<br><em>')
b = t.index('</div></div>', a) + len('</div></div>')
old = t[a:b]
assert 'bristowhallsystem' in old and 'id="fs"' in old
t = t[:a] + ('<div class="foot"><div class="src">Source: Bristow, Duke and Hall, Anthony via the Bristow-Hall System<br>'
             '<em><a href="' + NBER + '">Shaded areas indicate U.S. recessions.</a> Lined areas: recessions dated only by the Bristow-Hall Rule.</em></div>'
             '<div class="right"><span>bristowhallsystem</span><button class="btn ghost" id="fs" type="button">Fullscreen' + MAX + '</button></div></div>') + t[b:]
# JS: the button keeps its icon when it toggles
rep("fsBtn.textContent=isFS()?'Exit Fullscreen':'Fullscreen ⛶';",
    "fsBtn.innerHTML=isFS()?'Exit Fullscreen" + MIN.replace("'", "\\'") + "':'Fullscreen" + MAX.replace("'", "\\'") + "';")
# the image and PowerPoint downloads carry the same short note
a = t.index("Source: Bristow, Duke and Hall, Anthony via the Bristow-Hall System. Shaded areas: U.S. recessions as dated by the NBER")
b = t.index("drawn the same way.", a) + len("drawn the same way.")
t = t[:a] + "Source: Bristow, Duke and Hall, Anthony via the Bristow-Hall System. " + NOTE + t[b:]
assert 'drawn the same way' not in t and 'drawn as FRED draws them' not in t
open(dst, 'w', encoding='utf-8').write(t)
print('foot patched', len(t))
