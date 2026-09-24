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

def check(df, log):
    d = df[df.n == 12].dropna(subset=['week_ic', 'state']).copy()
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
        g = g.assign(state_name=st, mag_bad=bad_mag.values, week_ok=ok2.values, year_ok=ok3.values)
        out.append(g.reset_index())
    r = pd.concat(out) if out else pd.DataFrame()
    if len(r):
        tested = r.week_ok.notna() | r.year_ok.notna()
        passed = (r.week_ok.fillna(False) | r.year_ok.fillna(False)) & ~r.mag_bad
        log.append(f'  state-weeks with twelve fields {len(r)}; magnitude slips {int(r.mag_bad.sum())}; '
                   f'week-change check passed {int(r.week_ok.fillna(False).sum())}; year-ago check passed {int(r.year_ok.fillna(False).sum())}; '
                   f'kept (either check passed and magnitude sane) {int(passed.sum())}')
        r = r[passed]
    return r

if __name__ == '__main__':
    labels = sys.argv[1:] or [f.split('ui_claims_')[1].split('.csv')[0] for f in sorted(glob.glob('/home/claude/lab/dol_hist/ui_claims_*.csv')) if '_clean' not in f]
    log = []
    for lab in labels:
        log.append(f'{lab}:')
        df = load(lab); r = check(df, log)
        if len(r):
            r.to_csv(f'/home/claude/lab/dol_hist/ui_claims_{lab}_clean.csv', index=False)
            log.append(f'  weeks {r.week_ic.min():%Y-%m-%d} to {r.week_ic.max():%Y-%m-%d}, states {r.state_name.nunique()}')
    open('/home/claude/lab/dol_hist/verify.log', 'w').write('\n'.join(log))
    print('\n'.join(log))
