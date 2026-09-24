"""The high-frequency legs, chosen by the rule PREREG-v356-walk96 states, built exactly as hf_screen.one built them.
select()  -> DataFrame of admitted channels and their configuration (one per family), from out/hf_span_null.csv and
             out/hf_screen.csv
build(sel) -> {letter: [(published Timestamp, dated month Timestamp), ...]} proposals, using hf_screen's engine
Letters are symbols the walk and the carried legs never use: # $ % ^ & ( ) - + = ~ /"""
import os, sys, json, itertools
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hf_screen as H; L = H.L
OUT = H.OUT
FAMILY = {'DTSWITHHELD': 'withheld', 'DTSWITHHELD_S20': 'withheld', 'UIBENEFITS': 'uibenefits', 'UIBENEFITS_S65': 'uibenefits',
          'DTSCUSTOMS': 'customs', 'DTSCUSTOMS_S20': 'customs', 'DTSCUSTOMS_S65': 'customs', 'DTSCORP_S65': 'corptax',
          'EIA930DEMAND': 'electricity', 'EIA930DEMAND_S7': 'electricity', 'EIA930DEMAND_S28': 'electricity',
          'TSATHRU': 'tsa', 'TSATHRU_S7': 'tsa', 'TSATHRU_S28': 'tsa',
          'EIAWRPUPUS2': 'petroleum', 'EIAWGFUPUS2': 'petroleum', 'EIAWDIUPUS2': 'petroleum', 'EIAWGFUPUS2_M4': 'petroleum', 'EIAWDIUPUS2_M4': 'petroleum',
          'EIAWCESTUS1': 'crudestocks', 'EIAWGTSTUS1': 'gasolinestocks',
          'OFRFSI': 'ofr', 'OFRCREDIT': 'ofr', 'OFRFUNDING': 'ofr', 'OFRVOL': 'ofr', 'OFRSAFE': 'ofr', 'OFREQUITY': 'ofr',
          'INDEEDSA': 'indeed', 'INDEEDNSA': 'indeed', 'PMMS30W': 'mortgage', 'EPUDAILY': 'epu', 'GPRDAILY': 'gpr', 'SKEW': 'skew', 'VVIX': 'vvix'}
LETTERS = ['#', '$', '%', '^', '&', '(', ')', '-', '+', '=', '~', '/']
def select(pmax=0.05):
    N = pd.read_csv(os.path.join(OUT, 'hf_span_null.csv')); S = pd.read_csv(os.path.join(OUT, 'hf_screen.csv'))
    N = N[(N.p_exceed <= pmax) & (N.true_max_peaks >= 1)].copy(); N['family'] = N.channel.map(FAMILY)
    N = N.sort_values(['p_exceed', 'ratio'], ascending=[True, False]); pick = N.groupby('family').head(1)
    rows = []
    for _, r in pick.iterrows():
        d = S[S.proposer == r.channel].copy()
        d = d.sort_values(['n_wide', 'p_q', 'p_horizon', 'p_hold', 'p_win', 'confirmer'], ascending=[False, False, False, False, False, True])
        c = d.iloc[0].to_dict(); c.update(family=r.family, p_exceed=r.p_exceed, ratio=r.ratio); rows.append(c)
    P = pd.DataFrame(rows).reset_index(drop=True); P['letter'] = LETTERS[:len(P)]
    return P
def build(P):
    L.init(); legs = {}
    for _, r in P.iterrows():
        x, ny, how = L.as_of(r.proposer, L.DIRS[r.direction], int(r.p_horizon))
        Pb = L.hold_np(L.daily_np(L.over_q(x, int(r.p_q), max(12, int(int(r.p_win) * ny)))), int(r.p_hold))
        Cb = L.CB[(r.confirmer, int(r.c_horizon), int(r.c_q), int(r.c_hold))]
        legs[r.letter] = [(L.IDX[c], L.IDX[c].to_period('M').to_timestamp()) for c in L.episodes_np(Pb & Cb)]
    return legs
if __name__ == '__main__':
    P = select(); pd.set_option('display.width', 250)
    print(P[['letter', 'family', 'proposer', 'direction', 'p_horizon', 'p_q', 'p_win', 'p_hold', 'confirmer', 'c_horizon', 'c_q', 'c_hold', 'n_wide', 'wide', 'p_exceed', 'ratio']].to_string(index=False))
    legs = build(P)
    for k, v in legs.items(): print(k, [a.strftime('%Y-%m-%d') for a, b in v])
    P.to_csv(os.path.join(OUT, 'hf_legs_selected.csv'), index=False)
    json.dump({k: [(a.strftime('%Y-%m-%d'), b.strftime('%Y-%m')) for a, b in v] for k, v in legs.items()}, open(os.path.join(OUT, 'hf_legs_proposals.json'), 'w'), indent=1)
