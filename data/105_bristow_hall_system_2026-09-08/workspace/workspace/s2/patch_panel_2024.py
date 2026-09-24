# The speed panel's reference for 2024 (idempotent string patch to site/template.html; run on the Mac from workspace/).
# Before: the 2024 row was measured against the rule's own dated month (May 2024 / September 2024), which is circular —
# the rule's month is derived from the same datum as the call, so the call is inside it by construction.
# After: the 2024 row is measured against the chronology of Paper 1 (Hall & Bristow, 2026): peak April 2024, trough
# August 2024 — the months the record (RECORD-w55) and the walk's scorer already use (PK/TR in the lab; the JSON's
# announcements carry them as a.peak / a.trough with source 'not dated by the NBER'). The footnote states the reference,
# the day the rule fired against it, and the Sahm rule's own crossing. The record table shows Paper 1's months for 2024.
import os,sys
T=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else '../site/template.html')   # run from 105/workspace: python3 s2/patch_panel_2024.py
s=open(T).read(); o=s
if 'the peak month Paper 1 gives*' in s: print('template already patched'); sys.exit(0)
def rep(a,b,n=1):
    global s
    assert s.count(a)==n, (s.count(a), a[:80])
    s=s.replace(a,b)
# 1. the sub-headings
rep("<p class=\"sub\">Months after the end of the peak month (the rule's own month for 2024)</p>",
    "<p class=\"sub\">Months after the end of the peak month (for 2024, which the NBER has not dated, the peak month Paper 1 gives*)</p>")
rep("<p class=\"sub\">Months after the end of the trough month (the rule's own month for 2024)</p>",
    "<p class=\"sub\">Months after the end of the trough month (for 2024, the trough month Paper 1 gives*)</p>")
# 2. the reference month of each row: the chronology's month for every row (Paper 1's for 2024), never the rule's own
rep("const ref=nb?(side==='peak'?a.peak:a.trough):(side==='peak'?ep.open_month:ep.close_month);",
    "const ref=side==='peak'?a.peak:a.trough;")
# 3. the row's note and the tooltip
rep("font-family=\"'+ff+'\">not dated by the NBER</text>'; }",
    "font-family=\"'+ff+'\">not dated by the NBER; reference '+fmtM(r.ref)+' (Paper 1)</text>'; }")
rep("+(r.nb?'':' (the rule\\'s own month; the NBER has not dated this recession)'))",
    "+(r.nb?'':' (the month Paper 1 gives — Hall & Bristow, 2026; the NBER has not dated this recession)'))")
# 4. return the rows so the footnote can be computed from the data
rep("return {svg:svg,sum:'The rule fired before the '+side+' month ended in '",
    "return {rows:rows,svg:svg,sum:'The rule fired before the '+side+' month ended in '")
rep("for(const side of ['peak','trough']){ const r=speedPanel(side); $('#sp-'+side).innerHTML=r.svg; $('#sum-'+side).textContent=r.sum; }\n  $('#speednote').textContent='* The NBER has not dated a recession in 2024; the rule\\'s own month is the reference.';",
    "const SPR={}; for(const side of ['peak','trough']){ const r=speedPanel(side); SPR[side]=r.rows; $('#sp-'+side).innerHTML=r.svg; $('#sum-'+side).textContent=r.sum; }\n"
    "  (function(){ const p=SPR.peak.find(r=>!r.nb), t=SPR.trough.find(r=>!r.nb); if(!p){ $('#speednote').textContent=''; return; }\n"
    "    const dd=(from,to)=>Math.round((toT(to)-toT(from))/DAY); const dm=m=>(m>0?'+':'')+m; const pe=monthEndISO(p.ref);\n"
    "    let txt='* The NBER has not dated a recession in 2024. The reference for 2024 is the chronology of Paper 1 (Hall & Bristow, 2026, \"Recession Signals Without Recession and the Case of 2024\"): peak '+fmtML(p.ref)+(t?', trough '+fmtML(t.ref):'')+'. The rule fired '+fmtD(p.ruleDay)+', '+dm(dd(pe,p.ruleDay))+' days from the end of that peak month'+(p.sahmDay?' and '+dd(p.ruleDay,p.sahmDay)+' days before the Sahm rule crossed 0.50 ('+fmtD(p.sahmDay)+')':'')+(t&&t.ruleDay?'; it closed '+fmtD(t.ruleDay)+', '+dm(dd(monthEndISO(t.ref),t.ruleDay))+' days from the end of the trough month':'')+'. Measured against the rule\\'s own dated months (May and September 2024) the call would sit inside each month by construction, which is why they are not the reference.';\n"
    "    $('#speednote').textContent=txt; })();")
# 5. the record table: Paper 1's months and the errors against them for the episode the NBER has not dated
rep("let n=null; for(const r of NB){ const ra=toT(r.peak+'-01')-183*86400000, rb2=monthEnd(+r.trough.slice(0,4),+r.trough.slice(5,7))+92*86400000; if(a<=rb2&&b>=ra){n=r;break;} }",
    "let n=null; for(const r of NB){ const ra=toT(r.peak+'-01')-183*86400000, rb2=monthEnd(+r.trough.slice(0,4),+r.trough.slice(5,7))+92*86400000; if(a<=rb2&&b>=ra){n=r;break;} }\n"
    "    let p1=null; if(!n){ const an=(S.announcements||[]).find(x=>x.rule_open===e.open_pub&&x.source==='not dated by the NBER'); if(an) p1={peak:an.peak,trough:an.trough}; }")
rep("const eo=n?md(e.open_month,n.peak):null; const ec=(n&&e.close_month)?md(e.close_month,n.trough):null;",
    "const rf=n||p1; const eo=rf?md(e.open_month,rf.peak):null; const ec=(rf&&e.close_month)?md(e.close_month,rf.trough):null;")
rep("(n?fmtM(n.peak)+' → '+fmtM(n.trough):'<span style=\"color:#555\">not dated by the NBER</span>')",
    "(n?fmtM(n.peak)+' → '+fmtM(n.trough):(p1?'<span style=\"color:#555\">not dated by the NBER; Paper 1: '+fmtM(p1.peak)+' → '+fmtM(p1.trough)+'</span>':'<span style=\"color:#555\">not dated by the NBER</span>'))")
if s!=o:
    open(T,'w').write(s); print('template patched:',T)
else: print('template unchanged (already patched)')
