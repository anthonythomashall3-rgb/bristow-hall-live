# Detector page (18 Sep 2026, site-UI chat, round 3): the Observations column as FRED's - Updated on one line, Next
# Release Date plain text, the standing line removed, and the Observations list giving the last five changes.
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new):
    global t
    n = t.count(old); assert n == 1, ('expected 1, found %d: ' % n) + old[:110]
    t = t.replace(old, new)
# CSS: the column is never narrower than its longest line, and its lines do not wrap
rep(".meta > div.obs{flex:4 1 auto;min-width:235px;position:relative}",
    ".meta > div.obs{flex:4 1 auto;min-width:auto;position:relative}\n#obs,#upd,#next{white-space:nowrap}")
rep(".meta #next a{color:#990000}\n", "")
# HTML: no standing line
rep('<div id="next"></div><div class="standing" id="standing"></div></div>', '<div id="next"></div></div>')
# JS
rep("  const st=S.standing; $('#standing').innerHTML=(st.state==='open'?'<b style=\"color:#7f0000\">Recession open</b> since ':'<b style=\"color:#1b7f4b\">No recession open</b> since ')+fmtM(st.dated);\n", "")
rep("    $('#next').innerHTML='<a>Next Release Date: '+(nd?fmtD(nd):'—')+'</a>';\n",
    "    $('#next').textContent='Next Release Date: '+(nd?fmtD(nd):'—');\n")
a = t.index("  { const lab=$('#obslab'), pop=$('#obspop'); const rows=[];")
b = t.index("    $('#obsrows').innerHTML=rows.join('');\n")
t = t[:a] + (
    "  // the list gives the last five changes: each row is the day the reading (to two decimals) became what it shows\n"
    "  { const lab=$('#obslab'), pop=$('#obspop'); const rows=[]; const disp=k=>{ const v=SER.values[k]; return (v===null||v===undefined||!isFinite(v))?null:(+v).toFixed(2); };\n"
    "    let k=N-1; while(k>=0&&disp(k)===null) k--;\n"
    "    while(k>=0&&rows.length<5){ const val=disp(k); let j=k; while(j-1>=0&&(disp(j-1)===val||disp(j-1)===null)) j--; while(disp(j)===null) j++;\n"
    "      const dd=SER.dates[j]; rows.push('<span class=\"d\">'+(dd.length>7?fmtD(dd):fmtM(dd))+':</span><span class=\"v\">'+val+'</span>'); k=j-1; while(k>=0&&disp(k)===null) k--; }\n"
) + t[b:]
rep("@media (max-width:1180px){ .meta{display:grid;", "@media (max-width:1300px){ .meta{display:grid;")
# Units, shorter (Anthony): Index, 1.00 = recession, 0-10 damage - in the row above the graph and on the View All page
rep("<div class=\"unt\"><div class=\"lab\">Units:</div>Index,<br>1.00 = the rule fired;<br>above it, the recession's damage, 0&nbsp;to&nbsp;10</div>",
    "<div class=\"unt\"><div class=\"lab\">Units:</div>Index,<br>1.00 = recession, 0&ndash;10 damage</div>")
rep("<p>Units: Index, 1.00 = the rule fired; above it, the recession\\'s damage, 0 to 10</p>", "<p>Units: Index, 1.00 = recession, 0&ndash;10 damage</p>")
assert 'standing' not in t.split('<script>')[0] and "$('#standing')" not in t
open(dst, 'w', encoding='utf-8').write(t)
print('obs column patched', len(t))
