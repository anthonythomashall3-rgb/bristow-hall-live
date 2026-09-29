"""Record vetted candidates (from candidates_all.csv, produced by code) into found_prints.csv.
Each selection names the file/series/week/role; the value and strings come from the candidates file unchanged."""
import sys, pandas as pd
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from record import add
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
c = pd.read_csv(f'{W}/candidates_all.csv', dtype=str)
SEL = [  # raw_file, series, week, role, print_kind, note
    ('raw/upi_1992-12-24_8244725173200.html.gz', 'rate', '1992-12-05', 'latest', 'advance',
     'Department figure (Labor Department said Thursday). Release of Thu 1992-12-24, the first to carry insured-unemployment week Dec 5.'),
    ('raw/upi_1992-12-24_8244725173200.html.gz', 'rate', '1992-11-28', 'prior', 'prior-week figure quoted in the next release (revised or unrevised not stated)',
     'from "decreased to 2.7 percent from 2.8 percent"; the first print of week Nov 28 was the 1992-12-17 release (not found).'),
    ('raw/upi_1992-12-31_1232725778000.html.gz', 'rate', '1992-12-12', 'latest', 'advance',
     'Department figure (Labor Department said Thursday). Release of Thu 1992-12-31, the first to carry insured-unemployment week Dec 12.'),
]
for f, s, w, r, pk, note in SEL:
    x = c[(c.raw_file == f) & (c.series == s) & (c.week_ended == w) & (c.role == r)]
    assert len(x) >= 1, (f, s, w, r)
    x = x.iloc[0]
    ok = add(series=s, week_ended=w, value=x.value, value_string=x.value_string, print_kind=pk, pub_date=x.pub_date,
             source_url=x.source_url, source_name=x.source_name, year_proof=x.year_proof, raw_file=f,
             note=note + f' | week assignment: {x.week_how} | FRED now: {x.fred_value} | sentence: {x.sentence[:250]}')
    print(ok, s, w, x.value, x.value_string)
