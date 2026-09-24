# Detector page (18 Sep 2026, site-UI chat, round 3b): the Notes' Units shortened like the header's; the two speed
# panels lined up - the same subtitle wording on both, and each panel's heading, subtitle, chart, summary and citation
# on shared rows (CSS subgrid), so the two charts start and end level whatever the text lengths.
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
def rep(old, new):
    global t
    n = t.count(old); assert n == 1, ('expected 1, found %d: ' % n) + old[:110]
    t = t.replace(old, new)
rep("<p class=\"kv\"><b>Units:</b> Index; 1.00 = the rule fired; above it, the recession's damage on a scale of 0 to 10</p>",
    "<p class=\"kv\"><b>Units:</b> Index, 1.00 = recession, 0&ndash;10 damage</p>")
rep("<p class=\"sub\">Months after the end of the peak month (for 2024, which the NBER has not dated, the peak month Paper 1 gives*)</p>",
    "<p class=\"sub\">Months after the end of the peak month (for 2024, the peak month Paper 1 gives*)</p>")
rep(".speed{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px}\n"
    ".speed .pan{flex:1 1 460px;min-width:0;background:#f5f6f8;border:1px solid #e3e6ea;padding:12px 14px 8px}\n",
    "/* the two panels side by side on shared rows: heading, subtitle, chart, summary and citation line up across them */\n"
    ".speed{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:18px;margin-top:10px}\n"
    ".speed .pan{display:grid;grid-row:span 5;grid-template-rows:subgrid;row-gap:0;align-content:start;min-width:0;background:#f5f6f8;border:1px solid #e3e6ea;padding:12px 14px 8px}\n"
    "@media (max-width:900px){ .speed{grid-template-columns:minmax(0,1fr);row-gap:18px} .speed .pan{display:block;grid-row:auto} }\n")
open(dst, 'w', encoding='utf-8').write(t)
print('speed panels patched', len(t))
