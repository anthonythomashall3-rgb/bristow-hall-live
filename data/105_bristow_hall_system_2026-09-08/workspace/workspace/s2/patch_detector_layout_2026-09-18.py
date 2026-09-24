# Detector page (18 Sep 2026, site-UI chat): the controls sit in the same row as Observations, Units and Frequency,
# as FRED lays out a series page - the ranges over the dates in one column, Edit Graph over Download in the last.
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new):
    global t
    n = t.count(old); assert n == 1, ('expected 1, found %d: ' % n) + old[:100]
    t = t.replace(old, new)
# CSS
rep(".meta{display:flex;flex-wrap:wrap;border-top:1px solid #cfd6de;border-bottom:1px solid #cfd6de;margin-top:8px}\n"
    ".meta > div{padding:14px 18px 14px 0;border-right:1px solid #cfd6de;margin-right:18px;min-width:132px}\n"
    ".meta > div.obs{max-width:340px;min-width:270px}\n",
    ".meta{display:flex;flex-wrap:nowrap;border-top:1px solid #cfd6de;border-bottom:1px solid #cfd6de;margin-top:8px}\n"
    ".meta > div{padding:14px 18px 14px 0;border-right:1px solid #cfd6de;margin-right:18px;min-width:0}\n"
    "/* one row, as FRED lays out a series: observations, units, frequency, the ranges over the dates, the two buttons */\n"
    ".meta > div.obs{flex:3 1 auto;min-width:220px}\n"
    ".meta > div.unt{flex:3 1 auto;min-width:170px}\n"
    ".meta > div.frq{flex:1 1 auto;min-width:105px}\n"
    ".meta > div.rng{flex:2 0 auto;display:flex;flex-direction:column;align-items:center;gap:14px;padding-top:20px}\n"
    ".meta > div.btns{flex:none}\n")
rep(".controls{display:flex;flex-wrap:nowrap;align-items:center;gap:8px 10px;margin-left:auto;padding:10px 0}\n", "")
rep(".ranges a{color:#990000;padding:0 6px;border-left:1px solid #cfd6de;cursor:pointer;font-size:14px}",
    ".ranges{white-space:nowrap}\n.ranges a{color:#990000;padding:0 11px;border-left:1px solid #cfd6de;cursor:pointer;font-size:15px}")
rep(".btns{display:flex;flex-direction:column;gap:6px}", ".btns{display:flex;flex-direction:column;gap:8px}\n.btns .btn{width:100%}")
rep("@media (max-width:760px){ .meta > div{border-right:0;min-width:0} .controls{margin-left:0} }",
    "@media (max-width:1120px){ .meta{flex-wrap:wrap} .meta > div.frq{border-right:0;margin-right:0} .meta > div.rng{flex-grow:0;margin-left:auto} }\n"
    "@media (max-width:760px){ .meta > div{border-right:0;margin-right:0;min-width:0} .meta > div.rng{margin-left:0;align-items:flex-start;padding-top:8px} .ranges a:first-child{padding-left:0} }")
# HTML
rep("  <div><div class=\"lab\">Units:</div>", "  <div class=\"unt\"><div class=\"lab\">Units:</div>")
rep("  <div><div class=\"lab\">Frequency:</div><span id=\"freq1\"></span></div>\n  <div class=\"controls\">\n",
    "  <div class=\"frq\"><div class=\"lab\">Frequency:</div><span id=\"freq1\"></span></div>\n  <div class=\"rng\">\n")
a = t.index("    <div class=\"dates\"><input id=\"d0\"")
b = t.index("\n", a)
t = t[:b] + "\n  </div>" + t[b:]      # the rng column ends after the dates
rep("    <div class=\"btns\"><button class=\"btn\" id=\"eg\"", "  <div class=\"btns\"><button class=\"btn\" id=\"eg\"")
rep("        <div class=\"menu\" id=\"dlmenu\" hidden role=\"menu\">", "        <div class=\"menu\" id=\"dlmenu\" hidden role=\"menu\">")
# the old controls wrapper closed with two </div> after the btns block: one for .btns, one for .controls - drop the extra
old_tail = "</div></div>\n    </div>\n  </div>\n</div>\n"
assert t.count(old_tail) == 1, t.count(old_tail)
t = t.replace(old_tail, "</div></div>\n  </div>\n</div>\n")
rep("above it, the recession's damage, 0 to 10</div>", "above it, the recession's damage, 0&nbsp;to&nbsp;10</div>")
assert 'controls' not in t.split('<script>')[0].replace('aria-controls', ''), 'controls left'
open(dst, 'w', encoding='utf-8').write(t)
print('layout patched', len(t))
