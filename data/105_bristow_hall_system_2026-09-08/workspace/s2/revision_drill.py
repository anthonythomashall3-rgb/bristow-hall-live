# -*- coding: utf-8 -*-
"""THE REVISION DRILL (plan Step 5 item 13 and Step 6 R10; 23 September 2026, collection 334).

The rule reads first prints wherever they exist: the weekly claims family from 12 October 2002 (collection 45), the insured rate
1948-83 (the Department's own first prints), the monthly objects from ALFRED. Before those dates the objects stand on today's
revised histories (FRED's ICSA, CCSA and IURSA files), which the Department re-seasonalises every spring. The drill asks what a
revision of those histories would do to the record: each pre-first-print week is multiplied (the insured rate: shifted) by a
revision drawn from the REAL distribution of revisions the Department has made since 2002 - the ratio of today's value to the
first print, resampled within the same week of the year, so the seasonal shape of revisions is kept. Two draws: `typical` leaves
out the pandemic re-seasonalisation (the pairs of March 2020 to June 2021); `all` keeps it. The build then runs on the
perturbed histories through its own doors (BHS_REVISION_SEED=<n>[:all]); the walked diary cannot move (it is the record as
walked), the frozen replay (out/frozen_record.json) and the daily readings can - and the drill records what did.

Writes cache/revision_drill/<seed>/{ICSA.csv, CCSA.csv, objects.pkl} and returns the paths to redirect."""
import os, pickle, numpy as np, pandas as pd

def _od():
    for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')):
        if os.path.isdir(r): return r
    raise RuntimeError('the data root was not found')

def _iursa_file(W):
    # collection 371 (24 September 2026): the archive file is not in the cloud bundle (the freeze lists what the rule reads); the lab's
    # weekly file is, and agrees with it on every common week (2,903 weeks, 0 differences). The archive file when present, else the lab's.
    a = os.path.join(W, 'archive', 'data', 'fred', 'IURSA.csv')
    return a if os.path.exists(a) else os.path.join(W, 'lab', 'data', 'fred_weekly', 'IURSA.csv')

def revision_table(od):
    _pm = os.path.join('cache', 'national_first_prints_1985_live.csv')   # E66: the first-print boundary from the merged table when the build has made it
    _p45 = os.environ.get('BHS_FIRSTPRINTS') or (_pm if os.path.exists(_pm) and not os.environ.get('BHS_FIRSTPRINTS_OFF') else os.path.join(od, '45_dol_first_prints_2026-09', 'national_first_prints.csv'))
    N = pd.read_csv(_p45, parse_dates=['ic_week_ended', 'iu_week_ended'])
    W = os.path.join(od, '24_bristow_rule_lab', 'workspace')
    cur = dict(ICSA=pd.read_csv(os.path.join(W, 'lab', 'data', 'fred_weekly', 'ICSA.csv'), index_col=0, parse_dates=True).iloc[:, 0].dropna(),
               CCSA=pd.read_csv(os.path.join(W, 'lab', 'data', 'fred_weekly', 'CCSA.csv'), index_col=0, parse_dates=True).iloc[:, 0].dropna(),
               IURSA=pd.read_csv(_iursa_file(W), index_col=0, parse_dates=True).iloc[:, 0].dropna())
    fp = dict(ICSA=N.dropna(subset=['icsa']).drop_duplicates('ic_week_ended', keep='first').set_index('ic_week_ended')['icsa'],
              CCSA=N.dropna(subset=['iusa']).drop_duplicates('iu_week_ended', keep='first').set_index('iu_week_ended')['iusa'],
              IURSA=N.dropna(subset=['iur_sa']).drop_duplicates('iu_week_ended', keep='first').set_index('iu_week_ended')['iur_sa'])
    out = {}
    for k in cur:
        j = pd.concat([cur[k].rename('cur'), fp[k].rename('fp')], axis=1).dropna()
        r = (j['cur'] - j['fp']) if k == 'IURSA' else (j['cur'] / j['fp'])
        out[k] = pd.DataFrame(dict(rev=r.values, woy=j.index.isocalendar().week.values, date=j.index))
    return cur, fp, out, _p45

def draw(seed, mode='typical'):
    od = _od(); cur, fp, rev, p45 = revision_table(od); rng = np.random.default_rng(int(seed))
    outdir = os.path.join('cache', 'revision_drill', '%s_%s' % (seed, mode)); os.makedirs(outdir, exist_ok=True)
    info = dict(seed=int(seed), mode=mode, series={})
    pert = {}
    for k in ('ICSA', 'CCSA', 'IURSA'):
        R = rev[k]
        if mode == 'typical': R = R[~((R['date'] >= pd.Timestamp('2020-03-01')) & (R['date'] <= pd.Timestamp('2021-06-30')))]
        first = fp[k].index.min()
        s = cur[k].copy(); weeks = s.index[s.index < first]
        woy = weeks.isocalendar().week
        vals = []
        for w, wk in zip(weeks, woy):
            pool = R[R['woy'] == wk]['rev'].values
            if len(pool) == 0: pool = R['rev'].values
            vals.append(float(rng.choice(pool)))
        vals = np.array(vals)
        if k == 'IURSA': s.loc[weeks] = (s.loc[weeks].values + vals).round(1).clip(min=0.1)
        else: s.loc[weeks] = (s.loc[weeks].values * vals).round(0)
        pert[k] = s
        info['series'][k] = dict(weeks_perturbed=int(len(weeks)), through=str(weeks.max().date()) if len(weeks) else None, first_print_from=str(first.date()),
                                 draw_mean=float(vals.mean()), draw_sd=float(vals.std()), pool=int(len(R)))
    # the files the build reads through its doors
    p_ic = os.path.join(outdir, 'ICSA.csv'); p_cc = os.path.join(outdir, 'CCSA.csv'); p_obj = os.path.join(outdir, 'objects.pkl')
    pert['ICSA'].rename('value').to_frame().to_csv(p_ic, index_label='date'); pert['CCSA'].rename('value').to_frame().to_csv(p_cc, index_label='date')
    o = pickle.load(open(os.path.join('cache', 'objects.pkl'), 'rb'))
    base = o['iursa']; first = fp['IURSA'].index.min(); idx = base.index[(base.index < first) & (base.index >= pd.Timestamp('1984-01-01'))]   # the Department's own first prints cover 1948-83
    o['iursa'] = base.copy(); o['iursa'].loc[idx] = pert['IURSA'].reindex(idx).fillna(base.reindex(idx)).values
    info['series']['IURSA']['weeks_perturbed_in_objects'] = int(len(idx))
    pickle.dump(o, open(p_obj, 'wb'))
    info['paths'] = {'lab/data/fred_weekly/ICSA.csv': p_ic, 'lab/data/fred_weekly/CCSA.csv': p_cc, 'cache/objects.pkl': p_obj}
    # E66 (24 September 2026): the long first-print table carries weeks no source holds, filled from the current series and marked
    # source='current-fill' (initial claims) or fills='iusa from the current series' (continued claims). They are revised data standing
    # among first prints, so the drill perturbs them too - in a copy of the table that the build reads through the same door.
    Nraw = pd.read_csv(p45, dtype=str).fillna('')
    if 'source' in Nraw.columns:
        n_ic = n_cc = 0
        for i in Nraw.index:
            if Nraw.at[i, 'source'] == 'current-fill' and Nraw.at[i, 'icsa'] not in ('', 'nan'):
                w = pd.Timestamp(Nraw.at[i, 'ic_week_ended']); pool = rev['ICSA']; pl = pool[pool['woy'] == w.isocalendar()[1]]['rev'].values
                if len(pl) == 0: pl = pool['rev'].values
                Nraw.at[i, 'icsa'] = str(int(round(float(Nraw.at[i, 'icsa']) * float(rng.choice(pl))))); n_ic += 1
            if 'iusa from the current series' in Nraw.at[i, 'fills'] and Nraw.at[i, 'iusa'] not in ('', 'nan'):
                w = pd.Timestamp(Nraw.at[i, 'iu_week_ended']); pool = rev['CCSA']; pl = pool[pool['woy'] == w.isocalendar()[1]]['rev'].values
                if len(pl) == 0: pl = pool['rev'].values
                Nraw.at[i, 'iusa'] = str(int(round(float(Nraw.at[i, 'iusa']) * float(rng.choice(pl))))); n_cc += 1
        p_fp = os.path.join(outdir, 'national_first_prints_perturbed.csv'); Nraw.to_csv(p_fp, index=False)
        info['paths']['45_dol_first_prints_2026-09/national_first_prints.csv'] = p_fp
        info['series']['ICSA']['current_fill_rows_perturbed'] = n_ic; info['series']['CCSA']['current_fill_rows_perturbed'] = n_cc
    return info

if __name__ == '__main__':
    import sys, json
    seed = sys.argv[1] if len(sys.argv) > 1 else '1'; mode = sys.argv[2] if len(sys.argv) > 2 else 'typical'
    print(json.dumps(draw(seed, mode), indent=1, default=str))
