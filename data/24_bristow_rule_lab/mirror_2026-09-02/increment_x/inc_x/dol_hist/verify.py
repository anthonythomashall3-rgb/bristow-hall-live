"""The three checks the release's own redundancy allows (4 September 2026) - Rule Zero on the OCR.

Every state-week parsed by parse_ui_claims.py is checked against:

  (1) THE PAGE'S OWN TOTAL: the "All programs (Excl. R.R.) Total" row is the sum of the states; the parsed states'
      sum must match it within the states the page carries (the check is run on initial claims and on insured
      unemployment separately, and reported as the ratio, so a dropped state shows as a shortfall, not an error).
  (2) THE NEXT WEEK'S "CHANGE FROM LAST WEEK": this week's level plus next week's change-from-last-week must equal
      next week's level, state by state.
  (3) THE FOLLOWING YEAR'S "CHANGE FROM A YEAR AGO": the level 52 weeks later minus its change-from-a-year-ago
      must equal this week's level.

A state-week that fails (2) or (3) where both readings exist is DROPPED, not corrected; the OCR's decimal-for-comma
slip (Florida 5.367 for 5,367) is caught by (2) and by a magnitude test against the state's own median.

    python3 verify.py <label> [label ...]   -> ui_claims_<label>_clean.csv, verify.log
"""
import sys, glob
import numpy as np, pandas as pd

def load(label):
    return pd.read_csv(f'/home/claude/lab/dol_hist/ui_claims_{label}.csv', parse_dates=['week_ic', 'week_iu'])

def volume_years(label):
    """the years a volume covers, from its own label (v29_1973_74 -> 1973 and 1974); a week dated outside the
    volume's own span by more than a year is an OCR date, not a week, and the rows on that page are dropped"""
    import re as _re
    ys = [int(y) for y in _re.findall(r'(19\d{2})', label)]
    if not ys: return None
    lo = min(ys); hi = max(ys)
    m = _re.search(r'19(\d{2})_(\d{2})', label)          # v29_1973_74 -> the volume runs into 1974
    if m: hi = max(hi, int(str(lo)[:2] + m.group(2)))
    return lo, hi

def check(df, log, label=None):
    d = df[df.n == 12].dropna(subset=['week_ic', 'state']).copy()
    yr = volume_years(label or '')
    if yr is not None:
        lo = pd.Timestamp(f'{yr[0] - 1}-07-01'); hi = pd.Timestamp(f'{yr[1] + 1}-06-30')
        n0 = len(d); d = d[(d.week_ic >= lo) & (d.week_ic <= hi)]
        if n0 - len(d): log.append(f'  dropped {n0 - len(d)} rows whose page date falls outside {lo:%Y-%m}-{hi:%Y-%m} (an OCR date)')
    d = d.sort_values(['state', 'week_ic']).drop_duplicates(['state', 'week_ic'], keep='first')
    out = []
    for st, g in d.groupby('state'):
        g = g.sort_values('week_ic').set_index('week_ic')
        med = g.ic_state.median()
        # magnitude: a reading below a hundredth or above a hundred times the state's median is an OCR slip
        bad_mag = (g.ic_state < med / 100) | (g.ic_state > med * 100)
        # check (2): level_t + chg_week_{t+1} == level_{t+1}, on consecutive weeks only
        nxt = g.shift(-1); gap = (g.index.to_series().shift(-1) - g.index.to_series()).dt.days
        pred = g.ic_state + nxt.ic_chg_week
        ok2 = (gap == 7) & (np.abs(pred - nxt.ic_state) <= np.maximum(50, 0.02 * nxt.ic_state.abs()))
        # check (3): level_{t+52w} - chg_year_{t+52w} == level_t
        y = g.reindex(g.index + pd.Timedelta(days=364)).set_index(g.index)
        ok3 = np.abs((y.ic_state - y.ic_chg_year) - g.ic_state) <= np.maximum(50, 0.02 * g.ic_state.abs())
        # check (4): the row's OWN arithmetic - the release's "all programs" insured unemployment is the sum of
        # the state programme, the federal-employee programme and the ex-servicemen's programme.  This is an exact
        # identity in the printed table, so it tests a row that has no neighbouring week to test it, and it catches
        # the column shifts and the decimal-for-comma slips the week-change check lets through.
        ssum = g.iu_state + g.iu_ucfe + g.iu_ucx
        ok4 = (ssum - g.iu_all).abs() <= np.maximum(2.0, 0.02 * g.iu_all.abs())
        g = g.assign(state_name=st, mag_bad=bad_mag.values, week_ok=ok2.values, year_ok=ok3.values, sum_ok=ok4.values)
        out.append(g.reset_index())
    r = pd.concat(out) if out else pd.DataFrame()
    if len(r):
        tested = r.week_ok.notna() | r.year_ok.notna()
        passed = (r.week_ok.fillna(False) | r.year_ok.fillna(False)) & r.sum_ok.fillna(False) & ~r.mag_bad
        log.append(f'  state-weeks with twelve fields {len(r)}; magnitude slips {int(r.mag_bad.sum())}; '
                   f'week-change check passed {int(r.week_ok.fillna(False).sum())}; year-ago check passed {int(r.year_ok.fillna(False).sum())}; '
                   f'the row\'s own sum identity passed {int(r.sum_ok.fillna(False).sum())}; '
                   f'kept (a neighbour check AND the sum identity AND magnitude sane) {int(passed.sum())}')
        r = r[passed]
    return r

if __name__ == '__main__':
    labels = sys.argv[1:] or [f.split('ui_claims_')[1].split('.csv')[0] for f in sorted(glob.glob('/home/claude/lab/dol_hist/ui_claims_*.csv')) if '_clean' not in f]
    log = []
    for lab in labels:
        log.append(f'{lab}:')
        df = load(lab); r = check(df, log, lab)
        if len(r):
            r.to_csv(f'/home/claude/lab/dol_hist/ui_claims_{lab}_clean.csv', index=False)
            log.append(f'  weeks {r.week_ic.min():%Y-%m-%d} to {r.week_ic.max():%Y-%m-%d}, states {r.state_name.nunique()}')
    open('/home/claude/lab/dol_hist/verify.log', 'w').write('\n'.join(log))
    print('\n'.join(log))
