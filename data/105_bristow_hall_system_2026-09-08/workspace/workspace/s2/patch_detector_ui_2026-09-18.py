# Detector page look (18 Sep 2026, site-UI chat): the patch applied to site/template.html. Usage: python3 patch_detector_ui_2026-09-18.py <in template> <out template>
import sys, re
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new, count=1):
    global t
    n = t.count(old)
    assert n == count, ('expected %d, found %d: ' % (count, n)) + old[:90]
    t = t.replace(old, new)

# 1. Units box: drop "(10 = the Great Depression)"
rep("above it, the recession's damage, 0 to 10<br>(10 = the Great Depression)</div>",
    "above it, the recession's damage, 0 to 10</div>")

# 2. Notes > Units: drop ", 10 = the Great Depression on the same arithmetic:" and the damage arithmetic after it
DMG = ("the unemployment rate (as published today; the open recession's latest weeks carried by insured claims) above its "
       "pre-recession low &mdash; its deepest point and its sum week by week in point-months, geometric mean, relative to "
       "1929&ndash;33 on a logarithmic scale (each point a fixed multiple of the damage) &mdash; complete on the close day")
rep("<p class=\"kv\"><b>Units:</b> Index; 1.00 = the rule fired; above it, the recession's damage on a scale of 0 to 10, "
    "10 = the Great Depression on the same arithmetic: " + DMG + "</p>",
    "<p class=\"kv\"><b>Units:</b> Index; 1.00 = the rule fired; above it, the recession's damage on a scale of 0 to 10</p>")

# 3. Notes: the damage arithmetic, moved here
rep("A recession is dated the month the rule fired, at both ends.</p>\n  <p class=\"kv\"><b>Citation:</b></p>",
    "A recession is dated the month the rule fired, at both ends.</p>\n  <p>Damage: " + DMG + ".</p>\n  <p class=\"kv\"><b>Citation:</b></p>")

# 4. the Next data block
rep("<div class=\"notes\" style=\"padding-top:10px\">\n  <p class=\"kv\"><b>Next data</b> (Eastern time; from the page's own clock and the release calendar):</p>\n  <ul id=\"nextlist\"></ul>\n</div>\n", "")

# 5. Pending proposal line and the carried-legs list under the standing
lines = t.split('\n'); keep = []; gone = []
for L in lines:
    s = L.strip()
    if (s.startswith("// v3.55: a leg proposal is a provisional open") or s.startswith("// a pending proposal is shown here;")
            or s.startswith("if(S.pending_proposals&&S.pending_proposals.length){")
            or s.startswith("if(S.carried_legs&&S.carried_legs.length){")):
        gone.append(s[:60]); continue
    keep.append(L)
assert len(gone) == 4, gone
t = '\n'.join(keep)

# 6. the Next data list in tick()
lines = t.split('\n'); keep = []; gone = []
for L in lines:
    s = L.strip()
    if (s == "const ul=$('#nextlist'); ul.innerHTML='';" or s.startswith("{ const li=document.createElement('li'); li.innerHTML='<b>Every weekday, 4:20 PM ET</b>")
            or s.startswith("for(const n of up.slice(0,8)){ const li=document.createElement('li');")):
        gone.append(s[:60]); continue
    keep.append(L)
assert len(gone) == 3, gone
t = '\n'.join(keep)
rep("The page reads the current time in Eastern time, lists what comes next, and says what has come out\n  // since it was built.",
    "The page reads the current time in Eastern time and says what comes next and what has come out\n  // since it was built.")
assert 'nextlist' not in t

# 7. Data through: the latest day the data reach, one date
rep("$('#ver').textContent='claims '+(S.through&&S.through.claims?S.through.claims:'')+(S.through&&S.through.sp500?', the S&P 500 close '+S.through.sp500:'')+(S.through&&S.through.search?', the search week '+S.through.search:'')+'.';",
    r"{ const ds=[]; const walk=o=>{ for(const k in o){ const v=o[k]; if(v&&typeof v==='object') walk(v); else if(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)) ds.push(v); } }; walk(S.through||{}); if(!ds.length) ds.push(ld.length>7?ld:ld+'-01'); ds.sort(); $('#ver').textContent=fmtD(ds[ds.length-1]); }   // the latest day the data reach")

# 8. fullscreen CSS
rep(".chart svg{display:block;height:auto;width:100%}\n",
    ".chart svg{display:block;height:auto;width:100%}\n"
    "/* fullscreen: the graph fills the screen and is redrawn at its size */\n"
    ".plot:fullscreen{display:flex;flex-direction:column;width:100%;height:100%;overflow:hidden}\n"
    ".plot:-webkit-full-screen{display:flex;flex-direction:column;width:100%;height:100%;overflow:hidden}\n"
    ".plot.pfs{position:fixed;left:0;top:0;right:0;bottom:0;z-index:1000;display:flex;flex-direction:column;overflow:hidden}\n"
    ".plot:fullscreen .chart{flex:1 1 0;min-height:0}\n"
    ".plot:-webkit-full-screen .chart{flex:1 1 0;min-height:0}\n"
    ".plot.pfs .chart{flex:1 1 0;min-height:0}\n")

# 9. isFS + the size the graph is drawn at
rep("const tip=$('#tip'); const chartEl=$('#chart'); const plotEl=$('#plot');",
    "const tip=$('#tip'); const chartEl=$('#chart'); const plotEl=$('#plot');\n"
    "  function isFS(){ const f=document.fullscreenElement||document.webkitFullscreenElement; return (!!f&&f===plotEl)||plotEl.classList.contains('pfs'); }")
rep("    const W=opts.width||FMT.width||Math.max(600,chartEl.clientWidth||1160);\n    const H=opts.height||FMT.height||470;\n",
    "    // fullscreen (18 September 2026): drawn at the screen's own size, so the graph fills it and its text and lines keep their size\n"
    "    const FS=!opts.width&&!opts.height&&isFS(); const fsK=FS?Math.max(1,600/Math.max(1,chartEl.clientWidth)):1;\n"
    "    const W=opts.width||(FS?Math.round(chartEl.clientWidth*fsK):0)||FMT.width||Math.max(600,chartEl.clientWidth||1160);\n"
    "    const H=opts.height||(FS?Math.max(200,Math.round(chartEl.clientHeight*fsK)):0)||FMT.height||470;\n")

# 10. the cursor: every point reachable
a = t.index("  // the cursor: a vertical line at the nearest observation")
b = t.index("    const at=PTS.filter(p=>p.date===best.date&&p.L.freq===best.L.freq);")
NEWCUR = (
"  // the cursor: a vertical line at the chosen observation, a marker on each line, and a box above with the date and value.\n"
"  // EVERY POINT IS REACHABLE (18 September 2026; the sticky peak of 17 September jumped over the points beside a peak):\n"
"  // the points within half a pixel of the nearest one across, and of those the one nearest the pointer's height, so where\n"
"  // a pixel holds several days the pointer's height picks among them; the marker then glides through every point between\n"
"  // where it was and where the pointer is, one a frame, when they lie within a few pixels (a slow sweep lands on every\n"
"  // observation even where a pixel holds several); the arrow keys step one observation at a time.\n"
"  let CUR=null, OVER=false, GT=null, GR=0;\n"
"  function pickAt(px,py,tol){\n"
"    let bd=Infinity; for(const p of PTS){ const d=Math.abs(p.x-px); if(d<bd) bd=d; } if(!(bd<=40)) return null;\n"
"    const lim=bd+tol; let best=null,by=Infinity,bx=Infinity;\n"
"    for(const p of PTS){ const dx=Math.abs(p.x-px); if(dx>lim) continue; const dy=Math.abs(p.y-py); if(dy<by||(dy===by&&dx<bx)){ best=p; by=dy; bx=dx; } }\n"
"    return best; }\n"
"  function cursorAt(px,py,tol){\n"
"    const g=chartEl.querySelector('#cur'); if(!g||!GEO) return; if(!FMT.tooltip||px===null){ g.innerHTML=''; CUR=null; GT=null; return; }\n"
"    const best=pickAt(px,py,tol||0.5); if(!best){ g.innerHTML=''; CUR=null; GT=null; return; } glideTo(best,(tol||0.5)*2); }\n"
"  function glideTo(tp,k){ if(!CUR||CUR.L!==tp.L||PTS[CUR.k]!==CUR||Math.abs(CUR.x-tp.x)>3*k||Math.abs(tp.k-CUR.k)<=1){ GT=null; showPoint(tp); return; } GT=tp; if(!GR) GR=requestAnimationFrame(glide); }\n"
"  function glide(){ GR=0; if(!GT||!CUR||PTS[CUR.k]!==CUR||PTS[GT.k]!==GT){ GT=null; return; } if(CUR===GT){ GT=null; return; } const dir=GT.k>CUR.k?1:-1; let j=CUR.k+dir; while(j!==GT.k&&PTS[j].L!==CUR.L) j+=dir; showPoint(PTS[j]); if(PTS[j]!==GT) GR=requestAnimationFrame(glide); else GT=null; }\n"
"  function stepPoint(dir){ GT=null; if(!CUR||PTS[CUR.k]!==CUR) return false; for(let j=CUR.k+dir;j>=0&&j<PTS.length;j+=dir){ if(PTS[j].L===CUR.L){ showPoint(PTS[j]); return true; } } return false; }\n"
"  function showPoint(best){\n"
"    const g=chartEl.querySelector('#cur'); if(!g||!GEO||!best||!FMT.tooltip) return; CUR=best;\n")
t = t[:a] + NEWCUR + t[b:]
assert 'the peak is sticky' not in t

# 10b. each point carries its position in PTS
rep("for(const p of P){ if(p[4]>=t0&&p[4]<=t1) pts.push({x:p[0],y:p[1],i:p[2],v:p[3],L:L,date:D.dates[p[2]]}); }",
    "for(const p of P){ if(p[4]>=t0&&p[4]<=t1) pts.push({x:p[0],y:p[1],i:p[2],v:p[3],L:L,date:D.dates[p[2]],k:pts.length}); }")

# 11. pointer events on the graph (fractional positions where the screen has them)
rep("    sv.addEventListener('mousemove',e=>{ if(dragging) return; const rc=sv.getBoundingClientRect(); cursorAt((e.clientX-rc.left)*(GEO.W/rc.width)); });\n    sv.addEventListener('mouseleave',()=>cursorAt(null));\n",
    "    CUR=null; GT=null; const PE=!!window.PointerEvent;\n"
    "    sv.addEventListener(PE?'pointermove':'mousemove',e=>{ if(dragging) return; OVER=true; const rc=sv.getBoundingClientRect(); const k=GEO.W/rc.width; cursorAt((e.clientX-rc.left)*k,(e.clientY-rc.top)*(GEO.H/rc.height),0.5*k); });\n"
    "    sv.addEventListener(PE?'pointerleave':'mouseleave',()=>{ OVER=false; cursorAt(null); });\n")

# 12. fullscreen: the real thing where the browser has it, the page's own where it does not (iPhone)
rep("  // ---- fullscreen ----\n"
    "  $('#fs').addEventListener('click',()=>{ const p=$('#plot'); if(document.fullscreenElement){document.exitFullscreen();} else if(p.requestFullscreen){p.requestFullscreen().then(()=>setTimeout(draw,300)).catch(()=>{});} });\n"
    "  document.addEventListener('fullscreenchange',()=>setTimeout(draw,300));\n",
    "  // ---- fullscreen: the graph fills the screen (the browser's own fullscreen; where there is none, the page's) ----\n"
    "  const fsBtn=$('#fs');\n"
    "  function fsDraw(){ fsBtn.textContent=isFS()?'Exit Fullscreen':'Fullscreen ⛶'; draw(); requestAnimationFrame(draw); setTimeout(draw,250); setTimeout(draw,700); }\n"
    "  function pageFS(on){ plotEl.classList.toggle('pfs',on); document.documentElement.style.overflow=on?'hidden':''; fsDraw(); }\n"
    "  fsBtn.addEventListener('click',()=>{\n"
    "    if(plotEl.classList.contains('pfs')){ pageFS(false); return; }\n"
    "    const f=document.fullscreenElement||document.webkitFullscreenElement; if(f){ (document.exitFullscreen||document.webkitExitFullscreen).call(document); return; }\n"
    "    const req=plotEl.requestFullscreen||plotEl.webkitRequestFullscreen; if(!req){ pageFS(true); return; }\n"
    "    try{ const r=req.call(plotEl); if(r&&r.catch) r.catch(()=>pageFS(true)); }catch(e){ pageFS(true); } });\n"
    "  document.addEventListener('fullscreenchange',fsDraw); document.addEventListener('webkitfullscreenchange',fsDraw);\n"
    "  // the arrow keys step the marker one observation at a time; Escape leaves the page's own fullscreen\n"
    "  chartEl.tabIndex=0; chartEl.addEventListener('blur',()=>{ if(!OVER) cursorAt(null); });\n"
    "  document.addEventListener('keydown',e=>{\n"
    "    if(e.key==='Escape'&&plotEl.classList.contains('pfs')){ pageFS(false); return; }\n"
    "    if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight') return; if(!(OVER||document.activeElement===chartEl)) return;\n"
    "    const tg=e.target; if(tg&&/^(INPUT|SELECT|TEXTAREA)$/.test(tg.tagName)) return;\n"
    "    if(!CUR){ if(PTS.length){ showPoint(PTS[PTS.length-1]); e.preventDefault(); } return; }\n"
    "    if(stepPoint(e.key==='ArrowRight'?1:-1)) e.preventDefault(); });\n")

for bad in ['Great Depression', 'Pending:', 'Mechanism legs carried', 'Next data', 'nextlist', 'the S&P 500 close \'+']:
    assert bad not in t, bad
assert t.count('__STATE__') == 1 and t.count('__SITE__') == 1
open(dst, 'w', encoding='utf-8').write(t)
print('patched OK', len(t))
