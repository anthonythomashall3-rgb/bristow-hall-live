# Detector page (18 Sep 2026, site-UI chat): the marker holds at each recession's peak - within 6 px, capped at 36 days
# either side, and narrower as the graph is zoomed in, so that once the days stand apart every one is reachable - and
# the narrow-screen layout of the row above the graph keeps its three text columns on the first line.
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new):
    global t
    n = t.count(old); assert n == 1, ('expected 1, found %d: ' % n) + old[:110]
    t = t.replace(old, new)
# the peaks: the highest reading of each run above 1.00 (a recession, call to close); the last day of the highest value
rep("  const NB=S.nber.filter(r=>r.peak<'2024');",
    "  // each recession's peak: the highest reading of each run above 1.00 (the last day at that height)\n"
    "  const PEAKD=new Set(); { let bi=-1,bv=-Infinity; for(let k=0;k<=N;k++){ const v=k<N?SER.values[k]:null; if(v!==null&&v!==undefined&&v>1){ if(v>=bv){ bv=v; bi=k; } } else if(bi>=0){ PEAKD.add(SER.dates[bi]); bi=-1; bv=-Infinity; } } }\n"
    "  const NB=S.nber.filter(r=>r.peak<'2024');")
rep("    const pts=[]; const nL=data.length;", "    const pts=[]; const nL=data.length; let mainN=0;")
rep("      for(const p of P){ if(p[4]>=t0&&p[4]<=t1) pts.push({x:p[0],y:p[1],i:p[2],v:p[3],L:L,date:D.dates[p[2]],k:pts.length}); }",
    "      const isMain=L.src===CAT[0]&&L.units==='lin'&&L.units2==='lin'&&effFreq(L)==='Daily'&&(L.formula||'').replace(/\\s+/g,'').toLowerCase()===L.id;\n"
    "      for(const p of P){ if(p[4]>=t0&&p[4]<=t1){ pts.push({x:p[0],y:p[1],i:p[2],v:p[3],L:L,date:D.dates[p[2]],k:pts.length,pk:isMain&&PEAKD.has(D.dates[p[2]])}); if(isMain) mainN++; } }")
rep("geo:{ml:ml,pw:pw,mt:mt,ph:ph,t0:t0,t1:t1,W:W,H:H}};", "geo:{ml:ml,pw:pw,mt:mt,ph:ph,t0:t0,t1:t1,W:W,H:H,mainN:mainN}};")
rep("  let CUR=null, OVER=false, GT=null, GR=0;\n  function pickAt(px,py,tol){\n",
    "  let CUR=null, OVER=false, GT=null, GR=0, PKS=[];\n"
    "  // THE PEAKS HOLD THE MARKER (18 September 2026): within a few pixels of a recession's peak the marker stays on the\n"
    "  // peak, so it need not be hit exactly. Six pixels either side, never more than 36 days either side (zoomed all the\n"
    "  // way out that is about 4 px) while the days are packed at least one to a pixel; zoomed in further the hold narrows\n"
    "  // faster than the days spread, and once they are two pixels apart it takes none of them: every day is reachable.\n"
    "  function holdR(k){ const rho=(GEO.mainN||0)/Math.max(1,GEO.pw/k); if(!(rho>0)) return 0; return Math.min(6,6*rho*rho,36/rho)*k; }\n"
    "  function pickAt(px,py,tol){\n"
    "    if(PKS.length){ const R=holdR(tol*2); let hp=null,hd=Infinity; for(const p of PKS){ const d=Math.abs(p.x-px); if(d<=R&&d<hd){ hp=p; hd=d; } } if(hp) return hp; }\n")
rep("  function glideTo(tp,k){ if(!CUR||", "  function glideTo(tp,k){ if(tp.pk||!CUR||")
rep("    CUR=null; GT=null; const PE=!!window.PointerEvent;", "    CUR=null; GT=null; PKS=PTS.filter(p=>p.pk); const PE=!!window.PointerEvent;")
# narrow screens: the three text columns on the first line, the ranges and the buttons on the second
rep("@media (max-width:1180px){ .meta{flex-wrap:wrap;row-gap:18px} .meta > div.rng{margin-left:auto;border-left:0} }",
    "@media (max-width:1180px){ .meta{display:grid;grid-template-columns:auto auto auto;row-gap:18px} .meta > div.rng{grid-column:1 / span 2;justify-self:end;border-left:0} .meta > div.btns{grid-column:3} }\n@media (max-width:760px){ .meta > div.rng{justify-self:auto} }")
open(dst, 'w', encoding='utf-8').write(t)
print('peak hold patched', len(t))
