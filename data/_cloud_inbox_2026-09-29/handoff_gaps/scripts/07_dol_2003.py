"""2003-05-17 insured unemployment rate: DOL weekly claims news releases of 2003-05-29 (advance) and 2003-06-05 (revised)."""
import sys, re, html
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
from record import add
def txt(n):
    p, s, b = get(f'https://oui.doleta.gov/press/2003/{n}.html', f'dol_press_2003_{n}.html')
    t = html.unescape(re.sub(r'<[^>]+>', ' ', b.decode('latin-1'))); return p, re.sub(r'\s+', ' ', t)
p, t = txt('052903')
head = re.search(r'(?:Release Date|RELEASE)[^.]{0,80}?(May \d+, 2003|Thursday, May \d+, 2003)', t)
m = re.search(r'advance seasonally adjusted insured unemployment rate was ([\d][.,]\d) percent for the week ending (May 17)', t)
tab = re.search(r'Ins\. Unemployment Rate \( SA \) \d? ?([\d.]+)%', t)
yp = re.search(r'week ending May 24, 2003|May \d+, 2003', t)
print(m.group(0), '| table:', tab.group(0), '| year:', yp.group(0) if yp else None, head.group(0) if head else None)
add(series='rate', week_ended='2003-05-17', value=float(tab.group(1)), value_string=m.group(1) + ' percent (text); ' + tab.group(1) + '% (table)',
    print_kind='advance', pub_date='2003-05-29', source_url='https://oui.doleta.gov/press/2003/052903.html',
    source_name='DOL ETA weekly claims news release (oui.doleta.gov press archive)',
    year_proof=f'archive listing year=2003, file 052903; text: "{yp.group(0) if yp else ""}"', raw_file='raw/' + p.rsplit('/', 1)[1],
    note='Department figure. Text prints "3,0 percent" (typo for 3.0); table row "Ins. Unemployment Rate (SA)" advance column 3.0%. Cloud row 052903 lacks it because the text regex expected a period.')
p2, t2 = txt('060503')
m2 = re.search(r"prior week's revised rate of ([\d.]+) percent", t2)
wk = re.search(r'advance seasonally adjusted insured unemployment rate was [\d.]+ percent for the week ending (May 24)', t2)
print(m2.group(0), wk.group(0))
add(series='rate', week_ended='2003-05-17', value=float(m2.group(1)), value_string=m2.group(1) + ' percent',
    print_kind='revised (next release)', pub_date='2003-06-05', source_url='https://oui.doleta.gov/press/2003/060503.html',
    source_name='DOL ETA weekly claims news release (oui.doleta.gov press archive)',
    year_proof='archive listing year=2003, file 060503; prior week of the advance week ending May 24', raw_file='raw/' + p2.rsplit('/', 1)[1],
    note='Department figure; revision of the week of May 17')
