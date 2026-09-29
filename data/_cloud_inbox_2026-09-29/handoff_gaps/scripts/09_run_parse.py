"""Apply parse_news.extract to every downloaded wire-story page (UPI, Deseret); compare each candidate with the cloud
table (same week/series) and the current FRED series; write candidates_all.csv. Nothing is written to found_prints here."""
import sys, os, re, gzip, csv, glob, datetime as dt
import pandas as pd
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from parse_news import extract
from upitext import upi_text
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
B = '/home/user/bristow-hall-live/data/105_bristow_hall_system_2026-09-08/workspace'
FW = '/home/user/bristow-hall-live/data/24_bristow_rule_lab/workspace/lab/data/fred_weekly'
exec(open(f'{W}/scripts/06_deseret_fetch.py').read().split("if __name__")[0])  # ds_text

man = {r['raw_file']: r['url'] for r in csv.DictReader(open(f'{W}/MANIFEST.csv'))}
early = pd.read_csv(f'{B}/s2/first_prints_early_1975_2002.csv')
live = pd.read_csv(f'{B}/cache/national_first_prints_1985_live.csv')
cl = pd.concat([early, live[live.release_date > early.release_date.max()]], ignore_index=True)
cl['fills'] = cl.fills.fillna('')
gaps = pd.read_csv(f'{W}/gaps_all.csv')
gapset = set(zip(gaps.series, gaps.week_ended))
fred = {s: pd.read_csv(f'{FW}/{f}.csv').set_index('date')['value'] for s, f in [('claims', 'ICSA'), ('level', 'CCSA'), ('rate', 'IURSA')]}


def cloud(series, week):
    if series == 'claims':
        r = cl[cl.ic_week_ended == week]; col = 'icsa'
    else:
        r = cl[cl.iu_week_ended == week]; col = 'iur_sa' if series == 'rate' else 'iusa'
    r = r[r[col].notna()]
    if not len(r): return '', ''
    return r[col].iloc[0], r.fills.iloc[0][:60]


rows = []
files = sorted(glob.glob(f'{W}/raw/upi_[12]*_*.html*') + glob.glob(f'{W}/raw/deseret_[12]*_*.html*'))
for f in files:
    rel = 'raw/' + os.path.basename(f)
    b = gzip.open(f).read() if f.endswith('.gz') else open(f, 'rb').read()
    m = re.search(r'_(\d{4}-\d{2}-\d{2})_', os.path.basename(f))
    pub = dt.date.fromisoformat(m.group(1))
    if os.path.basename(f).startswith('upi'):
        ti, dline, body = upi_text(b); src = 'UPI Archives'
        proof = f'UPI article-date line "{dline}"; URL path /Archives/{pub:%Y/%m/%d}/'
    else:
        ti, pdate, body = ds_text(b); src = 'Deseret News (AP/wire story)'
        proof = f'Deseret datePublished {pdate[:10]}; URL path /{pub.year}/{pub.month}/{pub.day}/'
    for c in extract(body, pub):
        cv, cf = cloud(c['series'], c['week_ended']) if c['week_ended'] else ('', '')
        fv = fred[c['series']].get(c['week_ended'], '') if c['week_ended'] else ''
        rows.append(dict(raw_file=rel, source_url=man.get(rel, ''), source_name=src, title=ti[:80], pub_date=pub.isoformat(),
                         year_proof=proof, **{k: c[k] for k in ['series', 'week_ended', 'value', 'value_string', 'role', 'week_how']},
                         is_gap=(c['series'], c['week_ended']) in gapset, cloud_value=cv, cloud_fill=cf, fred_value=fv,
                         sentence=c['sentence'][:400]))
out = pd.DataFrame(rows)
out.to_csv(f'{W}/candidates_all.csv', index=False)
print(len(out), 'candidates;', out.is_gap.sum(), 'on gap weeks')
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 40)
print(out[['raw_file', 'series', 'week_ended', 'value', 'role', 'week_how', 'is_gap', 'cloud_value', 'fred_value']].to_string())
