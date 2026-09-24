# Detector page (18 Sep 2026, site-UI chat, round 4): the "rule's record against the NBER's, and what it reads today"
# section removed (Anthony) - the details block, both tables and the code that filled them.
import sys, re
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
a = t.index("\n<details><summary>The rule's record against the NBER's, and what it reads today</summary>")
b = t.index("</details>\n", a) + len("</details>\n")
t = t[:a] + "\n" + t[b:]
a = t.index("  // ---- the record and the readings ----\n")
b = t.index("  // ---- how fast the rule speaks:")
block = t[a:b]
mdline = [L for L in block.split('\n') if L.strip().startswith('function md(a,b)')]
assert len(mdline) == 1
t = t[:a] + "  // months between two year-months (the speed panels' summaries)\n" + mdline[0] + "\n" + t[b:]
lines = t.split('\n'); keep = []; gone = 0
for L in lines:
    s = L.strip()
    if (s.startswith("document.querySelectorAll('#readings td[data-kind]')") or s.startswith("// a row's built 'next' date stands while it is still ahead")
            or s.startswith("// claims release, not the next one); once it has passed")):
        gone += 1; continue
    keep.append(L)
assert gone == 3, gone
t = '\n'.join(keep)
for ident in ['fmt(', 'sideName', 'errCell(', 'recb', '#record', '#readings']:
    rest = re.sub(r'function fmtD|fmtD\(|fmtM\(|fmtML\(|fmtT\(|fmtV\(|const fmt[A-Z]\w*=', '', t)
    if ident in ('fmt(',):
        assert not re.search(r'(?<![\w.])fmt\(', rest), 'fmt still used'
    else:
        assert ident not in t, ident + ' still referenced'
open(dst, 'w', encoding='utf-8').write(t)
print('record section removed; js block was', block.count('\n'), 'lines')
