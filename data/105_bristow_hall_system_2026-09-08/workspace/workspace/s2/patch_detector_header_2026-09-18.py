# Detector page (18 Sep 2026, site-UI chat): the part above the graph made to look like FRED's series page - the title
# with its star and rule, one row of observations | units | frequency | ranges over dates | Edit Graph over Download,
# the Observations list (the latest five and View All), Updated with its time, and the next release counting the
# daily close. Applied after patch_detector_ui and patch_layout.
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new):
    global t
    n = t.count(old); assert n == 1, ('expected 1, found %d: ' % n) + old[:110]
    t = t.replace(old, new)
def cut_lines(starts, expect):
    global t
    keep = []; gone = 0
    for L in t.split('\n'):
        if any(L.startswith(s) for s in starts): gone += 1; continue
        keep.append(L)
    assert gone == expect, (gone, starts); t = '\n'.join(keep)

STAR = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2.6 14.9 8.5 21.4 9.4 16.7 14 17.8 20.4 12 17.4 6.2 20.4 7.3 14 2.6 9.4 9.1 8.5"/></svg>'
CHEV = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="5 9 12 16 19 9"/></svg>'
EDIT = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-6"/><path d="M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4z"/></svg>'
DOWN = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'

# ---------------- CSS
rep("h1{font-size:29px;font-weight:400;margin:24px 0 10px;display:flex;align-items:center;gap:8px;color:#222;flex-wrap:wrap}\n"
    "h1 .id{font-size:15px;color:#444}\n"
    "h1 .star{color:#990000;font-size:20px}\n",
    "h1{font-size:28px;font-weight:400;line-height:1.25;margin:26px 0 0;padding-bottom:12px;border-bottom:3px solid #4d5760;display:flex;align-items:baseline;gap:10px;color:#222;flex-wrap:wrap}\n"
    "h1 .id{font-size:18px;color:#222}\n"
    "h1 .star{color:#990000;align-self:center;display:inline-flex}\n")
a = t.index(".meta{display:flex;flex-wrap:nowrap;border-top:1px solid #cfd6de;")
b = t.index(".meta .standing{margin-top:6px;font-size:13px;color:#333}\n") + len(".meta .standing{margin-top:6px;font-size:13px;color:#333}\n")
t = t[:a] + (
    "/* the row above the graph, as FRED lays out a series: observations | units | frequency | the ranges over the dates | the two buttons */\n"
    ".meta{display:flex;flex-wrap:nowrap;margin-top:16px;font-size:16px;line-height:1.65;color:#222}\n"
    ".meta > div{padding:0 20px 0 30px;border-left:1px solid #b9c0c7;min-width:0}\n"
    ".meta > div:first-child{padding-left:0;border-left:0}\n"
    ".meta > div:last-child{padding-right:0}\n"
    ".meta > div.obs{flex:4 1 auto;min-width:235px;position:relative}\n"
    ".meta > div.unt{flex:4 1 auto;min-width:190px}\n"
    ".meta > div.frq{flex:1 1 auto;min-width:125px}\n"
    ".meta > div.rng{flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:14px;padding-right:30px}\n"
    ".meta > div.btns{flex:0 0 auto}\n"
    ".meta .lab{font-style:italic;color:#222}\n"
    ".meta .obslab{display:inline-flex;align-items:center;gap:7px;color:#990000;font-style:italic;cursor:pointer;user-select:none}\n"
    ".meta .obslab:focus-visible{outline:2px solid #990000;outline-offset:2px}\n"
    ".meta #next a{color:#990000}\n"
    ".meta b{font-weight:700}\n"
    "/* the Observations list, as FRED's: the latest five, then View All */\n"
    ".obspop{position:absolute;left:-16px;top:28px;z-index:40;background:#fff;border:1px solid #d6dbe0;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.13);padding:14px 20px 16px;font-size:16px;line-height:1.5;white-space:nowrap}\n"
    ".obspop .rows{display:grid;grid-template-columns:auto auto;column-gap:12px}\n"
    ".obspop .d{color:#555;text-align:right}\n"
    ".obspop .v{font-weight:700;text-align:right;font-variant-numeric:tabular-nums}\n"
    ".obspop .btn{display:block;width:100%;margin-top:12px;font-size:17px;height:38px;padding:0 12px;border-radius:6px;text-align:center}\n"
) + t[b:]
rep(".ranges{white-space:nowrap}\n.ranges a{color:#990000;padding:0 11px;border-left:1px solid #cfd6de;cursor:pointer;font-size:15px}",
    ".ranges{display:flex;align-items:center;height:38px;white-space:nowrap}\n.ranges a{color:#990000;padding:3px 17px;border-left:1.5px solid #4d5760;cursor:pointer;font-size:17px;line-height:1.35}")
rep(".ranges a[aria-pressed=\"true\"]{font-weight:700;text-decoration:underline}\n", "")
rep(".dates input{font:inherit;font-size:12.5px;width:96px;padding:6px 6px;border:1px solid #cfd6de;border-radius:3px;color:#222}\n"
    ".dates{display:flex;align-items:center;gap:6px;color:#555}",
    ".dates input{font:inherit;font-size:16px;width:118px;height:42px;padding:6px 11px;border:1px solid #8a9199;border-radius:4px;color:#222;background:#fff}\n"
    ".dates{display:flex;align-items:center;gap:10px;color:#222;font-size:16px}")
rep(".btns{display:flex;flex-direction:column;gap:8px}\n.btns .btn{width:100%}",
    ".btns{display:flex;flex-direction:column;gap:16px}\n"
    ".meta .btns .btn{width:100%;font-size:16px;height:38px;padding:0 14px;border-radius:5px;border-width:1.5px;display:inline-flex;align-items:center;justify-content:center;gap:9px}")
rep("@media (max-width:1120px){ .meta{flex-wrap:wrap} .meta > div.frq{border-right:0;margin-right:0} .meta > div.rng{flex-grow:0;margin-left:auto} }\n"
    "@media (max-width:760px){ .meta > div{border-right:0;margin-right:0;min-width:0} .meta > div.rng{margin-left:0;align-items:flex-start;padding-top:8px} .ranges a:first-child{padding-left:0} }",
    "@media (max-width:1180px){ .meta{flex-wrap:wrap;row-gap:18px} .meta > div.rng{margin-left:auto;border-left:0} }\n"
    "@media (max-width:760px){ .meta{display:block} .meta > div{padding:0;border-left:0;margin:0 0 14px} .meta > div.rng{align-items:flex-start} .ranges a:first-child{padding-left:0} .meta .btns{flex-direction:row;gap:10px} .meta .btns .btn{width:auto} }")

# ---------------- HTML
rep('<h1 id="series"><span class="star">☆</span> Real-time', '<h1 id="series"><span class="star">' + STAR + '</span>Real-time')
rep('<div class="obs"><div class="lab"><a>Observations</a> ⌄</div>',
    '<div class="obs"><div class="lab"><span class="obslab" id="obslab" role="button" tabindex="0" aria-expanded="false" aria-controls="obspop">Observations' + CHEV + '</span></div>'
    '<div class="obspop" id="obspop" hidden><div class="rows" id="obsrows"></div><button class="btn" id="obsall" type="button">View All</button></div>')
rep('id="eg" type="button" aria-expanded="false">Edit Graph ✎</button>', 'id="eg" type="button" aria-expanded="false">Edit Graph' + EDIT + '</button>')
rep('aria-haspopup="true" aria-expanded="false">Download ⤓</button>', 'aria-haspopup="true" aria-expanded="false">Download' + DOWN + '</button>')

# ---------------- JS: Updated with its time; the next release counts the daily close; the Observations list
rep("  $('#upd').textContent='Updated: '+fmtD(S.built);\n",
    "  // Updated, as FRED writes it: the day and the time of the build, Eastern\n"
    "  { const ba=String(S.built_at||''); const mt=ba.match(/^(\\d{4})-(\\d{2})-(\\d{2}) (\\d{2}):(\\d{2})/); let s='Updated: '+fmtD(mt?ba.slice(0,10):S.built);\n"
    "    if(mt){ const hh=+mt[4]; let tz='ET'; try{ const z=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',timeZoneName:'short'}).formatToParts(new Date(Date.UTC(+mt[1],+mt[2]-1,+mt[3],hh+5,+mt[5]))).find(x=>x.type==='timeZoneName'); if(z) tz=z.value; }catch(e){} s+=' '+((hh%12)||12)+':'+mt[5]+' '+(hh<12?'AM':'PM')+' '+tz; }\n"
    "    $('#upd').textContent=s; }\n")
rep("  function nextByKind(kind,now){",
    "  // the daily inputs (the S&P 500 close and the search day) are read at 4:20 PM ET on every day the NYSE trades\n"
    "  function easterT(y){ const a=y%19,b=Math.floor(y/100),c=y%100,d=Math.floor(b/4),e=b%4,f=Math.floor((b+8)/25),g=Math.floor((b-f+1)/3),h=(19*a+b-d-g+15)%30,i=Math.floor(c/4),k=c%4,l=(32+2*e+2*i-h-k)%7,m=Math.floor((a+11*h+22*l)/451),n=h+l-7*m+114; return Date.UTC(y,Math.floor(n/31)-1,(n%31)+1); }\n"
    "  function nyseClosed(t){ const D=new Date(t), y=D.getUTCFullYear(), m=D.getUTCMonth()+1, d=D.getUTCDate(), w=D.getUTCDay(); if(w===0||w===6) return true;\n"
    "    const nth=(mm,wd,n)=>{ const f=new Date(Date.UTC(y,mm-1,1)).getUTCDay(); return 1+((wd-f+7)%7)+7*(n-1); };\n"
    "    const lastWd=(mm,wd)=>{ const L=new Date(Date.UTC(y,mm,0)).getUTCDate(), lw=new Date(Date.UTC(y,mm-1,L)).getUTCDay(); return L-((lw-wd+7)%7); };\n"
    "    const fixed=(mm,dd)=>{ const x=new Date(Date.UTC(y,mm-1,dd)).getUTCDay(); return x===6?[mm,dd-1]:x===0?[mm,dd+1]:[mm,dd]; };\n"
    "    const H=[[1,nth(1,1,3)],[2,nth(2,1,3)],[5,lastWd(5,1)],[9,nth(9,1,1)],[11,nth(11,4,4)],fixed(6,19),fixed(7,4),fixed(12,25)];\n"
    "    const nj=new Date(Date.UTC(y,0,1)).getUTCDay(); if(nj!==6) H.push(nj===0?[1,2]:[1,1]);\n"
    "    const gf=new Date(easterT(y)-2*86400000); H.push([gf.getUTCMonth()+1,gf.getUTCDate()]);\n"
    "    return H.some(h=>h[0]===m&&h[1]===d); }\n"
    "  function nextClose(now){ const p=now.slice(0,10).split('-').map(Number); let t=Date.UTC(p[0],p[1]-1,p[2]); if(now.slice(11)>='16:20') t+=86400000; for(let k=0;k<15;k++,t+=86400000){ if(!nyseClosed(t)) return new Date(t).toISOString().slice(0,10); } return null; }\n"
    "  function nextByKind(kind,now){")
rep("    $('#next').innerHTML='<a>Next Release Date: '+(first?fmtD(first.date):'—')+'</a>'+(first?' <span style=\"color:#555;font-size:12px\">('+(KIND[first.kind]||first.kind)+', '+fmtT(first.time)+(first.expected?', expected':'')+')</span>':'');\n",
    "    let nd=first?first.date:null; const nc=nextClose(now); if(nc&&(!nd||nc<nd)) nd=nc;\n"
    "    $('#next').innerHTML='<a>Next Release Date: '+(nd?fmtD(nd):'—')+'</a>';\n")
rep("    let toNext=toMidnight; if(nxt){",
    "    let toNext=toMidnight; { const hm=now.slice(11).split(':').map(Number); const mins=(16*60+20)-(hm[0]*60+hm[1]); if(mins>0) toNext=Math.min(toNext,mins*60000+1000); }\n    if(nxt){")
rep("  const FREQTXT=",
    "  // ---- Observations: the latest five, as FRED shows them, and View All: every observation on a page of its own ----\n"
    "  { const lab=$('#obslab'), pop=$('#obspop'); const rows=[]; for(let k=N-1;k>=0&&rows.length<5;k--){ const v=SER.values[k]; if(v===null||v===undefined||!isFinite(v)) continue; const dd=SER.dates[k]; rows.push('<span class=\"d\">'+(dd.length>7?fmtD(dd):fmtM(dd))+':</span><span class=\"v\">'+(+v).toFixed(2)+'</span>'); }\n"
    "    $('#obsrows').innerHTML=rows.join('');\n"
    "    const openPop=o=>{ pop.hidden=!o; lab.setAttribute('aria-expanded',String(o)); };\n"
    "    lab.addEventListener('click',e=>{ e.stopPropagation(); openPop(pop.hidden); });\n"
    "    lab.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openPop(pop.hidden); } });\n"
    "    pop.addEventListener('click',e=>e.stopPropagation());\n"
    "    document.addEventListener('click',()=>openPop(false)); document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&!pop.hidden) openPop(false); });\n"
    "    $('#obsall').addEventListener('click',()=>{ openPop(false); viewAll(); }); }\n"
    "  function viewAll(){ let rows=''; for(let k=0;k<N;k++){ const v=SER.values[k]; rows+='<tr><td>'+SER.dates[k]+'</td><td class=\"n\">'+((v===null||v===undefined||!isFinite(v))?'.':Math.max(0,+v).toFixed(3))+'</td></tr>'; }\n"
    "    const html='<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>BHRREALTIME</title>'\n"
    "      +'<style>body{font-family:Arial,Helvetica,sans-serif;color:#222;margin:24px 5%}h1{font-size:22px;font-weight:400;margin:0 0 8px}p{margin:2px 0;font-size:14px}table{border-collapse:collapse;margin-top:14px;font-size:14px}th,td{padding:3px 22px 3px 0;text-align:left;border-bottom:1px solid #e3e6ea}th{border-bottom:2px solid #cfd6de}.n{text-align:right;font-variant-numeric:tabular-nums}</style></head><body>'\n"
    "      +'<h1>Real-time Bristow-Hall Rule Recession Indicator (BHRREALTIME)</h1><p>Units: Index, 1.00 = the rule fired; above it, the recession\\'s damage, 0 to 10</p><p>Frequency: '+esc(SER.frequency||'Daily, on release days')+'</p><p>'+esc($('#upd').textContent)+'</p>'\n"
    "      +'<table><thead><tr><th>DATE</th><th class=\"n\">VALUE</th></tr></thead><tbody>'+rows+'</tbody></table></body></html>';\n"
    "    try{ const url=URL.createObjectURL(new Blob([html],{type:'text/html'})); const w=window.open(url,'_blank'); if(w) return; }catch(e){}\n"
    "    dataPanel('csv'); }\n"
    "  const FREQTXT=")
assert '⌄' not in t and '☆' not in t
open(dst, 'w', encoding='utf-8').write(t)
print('header patched', len(t))
