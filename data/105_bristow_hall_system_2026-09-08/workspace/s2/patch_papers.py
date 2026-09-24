# -*- coding: utf-8 -*-
"""The papers section of the front door (idempotent; run from workspace/).

Three papers and the pre-registration, each named for what it establishes rather than for the file it happens to be:

  Paper 1  Recession Signals Without Recession and the Case of 2024 - the case that started the programme; live as a PDF.
  Paper 2  The Bristow-Hall Rule: A New Methodology for Detecting and Dating Recessions in Real Time - the rule itself,
           its pre-registered clauses, the walk-forward record and the speed against the committee. (Was carried as
           "The Bristow Rule Generalized: a mechanical dating of the American business cycle", which named the lineage
           and not the contribution.)
  Paper 3  The Damage Index: A Richter Scale for Recessions - how deep, how broad and where, with the state and
           industry disturbances a national date hides, on one scale fixed in advance.
  (the pre-registration was listed as a fourth entry for four minutes and removed at Anthony's instruction,
  11 September 2026, 11:14 UTC; it stays on file in Recession Papers.)

Each line carries a status so nothing on the page can be read as published when it is not."""
import os,io,sys
H=os.path.abspath('../site/template_home.html')
s=io.open(H,encoding='utf-8').read()
if 'A Richter Scale for Recessions' in s: print('papers already renamed'); sys.exit(0)
old_start=s.index('  <div class="papers">'); old_end=s.index('  </div>\n</div>\n',old_start)+len('  </div>\n')
new=('  <div class="papers">\n'
 '    <div class="paper"><div class="t"><a href="/papers/recession-signals-without-recession-2024.pdf">'
 'Recession Signals Without Recession and the Case of 2024</a></div>'
 '<div class="a">Hall &amp; Bristow &middot; FBE Working Paper &middot; September 2026 &middot; '
 '<a href="/papers/recession-signals-without-recession-2024.pdf">PDF</a></div></div>\n'
 '    <div class="paper"><div class="t">The Bristow-Hall Rule: A New Methodology for Detecting and Dating Recessions '
 'in Real Time</div><div class="a">Bristow &amp; Hall &middot; the rule, its pre-registered clauses, and the '
 'walk-forward record &middot; in preparation</div></div>\n'
 '    <div class="paper"><div class="t">The Damage Index: A Richter Scale for Recessions</div>'
 '<div class="a">Hall &amp; Bristow &middot; how deep, how broad and where - the state and industry disturbances a '
 'national date hides &middot; in preparation</div></div>\n'
 '  </div>\n')
s=s[:old_start]+new+s[old_end:]
io.open(H,'w',encoding='utf-8').write(s); print('papers section rewritten; 4 entries')
