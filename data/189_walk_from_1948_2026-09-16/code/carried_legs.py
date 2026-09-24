"""v3.55 -- every vetted mechanism channel carried as a live leg; the record must not move (16 September 2026).

Protocol, declared before running:
  1. Channels: the survivors of the span-matched null by mechanism (FINDING-mechanism-survivors), 36 channels.
  2. Configuration per channel: among its strict-admission configurations (every matched firing inside
     [-92, -1], zero quiet firings) the one reaching the most peaks; ties by the highest proposer quantile,
     the longest proposer horizon, the longest proposer hold, then the confirmer name alphabetically.
  3. Each becomes a leg exactly as legs E/S/T/Z/c/m are built (`_load_leg86`), subject to the same record bar
     and 400-day arming bar. A carried leg can only accelerate a core call.
  4. The walked record of walk 94 is recomputed cut by cut with every carried leg active. A carried leg that
     changes any call in that record is NOT carried (it would be an in-sample improvement) and is listed.
  5. Every leg proposal from 1962 that a real-time reader would have seen and later watched lapse (passed
     the record bar, failed the 400-day test) is counted, with and without the carried legs.
Run: python3 carried_legs.py
"""
import sys, os, io, contextlib, pickle, json, time
import pandas as pd
os.chdir('/home/claude/ws'); sys.path.insert(0, '/home/claude/ws')
OUT = '/mnt/user-data/outputs/v355'; os.makedirs(OUT, exist_ok=True)

# ---- 2. configurations
SURV = ['DFF','DPRIME','DTB1','T10Y3M','T10Y2Y','TOTRA','LOLAOL','M14064USM144NNBR','BORROW','TOTBORR','CASACBW027NBOG','WLCFLSCL',
        'VIXCLS','NASDAQCOM','HOUST1F','PERMIT1','WTISPLC','WB_CRUDE_OIL_AVERAGE','WB_CRUDE_OIL_DUBAI','DCOILWTICO','WPU101','WB_NICKEL',
        'WB_LEAD','IPDCONGD','BUSINV','LNS11300001','LNS12032194','BSCICP02DEM460S','DEXSLUS','DTWEXM','IR','TSIFRGHT','EPUMONETARY',
        'IPMAN','UMCSENT','CCNSA']
MECH = {'DFF':'A1','DPRIME':'A1','DTB1':'A1','T10Y3M':'A1','T10Y2Y':'A1','TOTRA':'A2','LOLAOL':'A2','M14064USM144NNBR':'A2','BORROW':'A2/B1',
        'TOTBORR':'A2','CASACBW027NBOG':'A2','WLCFLSCL':'A2','VIXCLS':'A3','NASDAQCOM':'A3','HOUST1F':'A4','PERMIT1':'A4','WTISPLC':'A5',
        'WB_CRUDE_OIL_AVERAGE':'A5','WB_CRUDE_OIL_DUBAI':'A5','DCOILWTICO':'A5','WPU101':'A5','WB_NICKEL':'A5','WB_LEAD':'A5','IPDCONGD':'A6',
        'BUSINV':'A6','LNS11300001':'A8/A9','LNS12032194':'A8/A9','BSCICP02DEM460S':'B2','DEXSLUS':'B2','DTWEXM':'B2','IR':'B3','TSIFRGHT':'B4',
        'EPUMONETARY':'C4','IPMAN':'activity','UMCSENT':'consumer','CCNSA':'core labour'}
d = pd.read_csv('/mnt/user-data/outputs/late_full/late_full_strict92.csv')
d = d[d.proposer.isin(SURV)].copy()
d['npk'] = d['wide'].apply(lambda s: len(json.loads(s)) if isinstance(s, str) else 0)
d = d.sort_values(['proposer', 'npk', 'p_q', 'p_horizon', 'p_hold', 'confirmer'], ascending=[True, False, False, False, False, True])
PICK = d.groupby('proposer').head(1).set_index('proposer')
print('picked', len(PICK), 'configurations', flush=True)

# ---- the preamble of walk 94 with a `carry` axis added to the leg loop
src = open('walk94.py').read()
old = "    for _L in ((p.get('newlegs') or '') + (p.get('extra') or '')):"
assert src.count(old) == 1
src = src.replace(old, "    for _L in ((p.get('newlegs') or '') + (p.get('extra') or '') + (p.get('carry') or '')):")
# instrument the lapsed proposals
old_l = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs[_L] = _keep; _added = True"
assert src.count(old_l) == 1
src = src.replace(old_l, old_l + "\n            LAPSED.extend([(a, b, _L) for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])")
old_n = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs['N'] = _keep; _added = True"
assert src.count(old_n) == 1
src = src.replace(old_n, old_n + "\n            LAPSED.extend([(a, b, 'N') for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])")
tail_line = "exec(open('walk39.py').read().split(_MARK)[1].split(\"\\n\", 1)[1])"
assert src.count(tail_line) == 1
src = src.replace(tail_line, "")
sys.argv = ['walk94.py', '2027', '2026', 'wcarry']
LAPSED = []
t0 = time.time(); buf = io.StringIO()
with contextlib.redirect_stdout(buf): exec(compile(src, 'walk94_head', 'exec'))
print('preamble %.0f s' % (time.time() - t0), flush=True)

# ---- 3. build the carried legs
_CONF86.update({
 'mfg_emp_falling':      ('MANEMP',  _PCTDN),
 'unrate_rising':        ('UNRATE',  _RISE),
 'overtime_falling':     ('AWOTMAN', _FALL),
 'freight_cars_falling': ('M03002USM544NNBR', _PCTDN),
})
DFN = {'rise': _RISE, 'fall': _FALL, 'pct_up': _PCTUP, 'pct_down': _PCTDN}
LETTERS = [c for c in '0123456789abdefghijklnopqrstuvwxyz!@#$%^&*'][:len(PICK)]
CARRY = {}; TABLE = []
for L, (sid, r) in zip(LETTERS, PICK.iterrows()):
    props = _load_leg86(sid, DFN[r['direction']], int(r['p_horizon']), int(r['p_q']), int(r['p_win']), int(r['p_hold']),
                        r['confirmer'], int(r['c_horizon']), int(r['c_q']), int(r['c_hold']))
    CARRY[L] = props; NEW_LEGS[L] = props
    TABLE.append(dict(letter=L, channel=sid, mechanism=MECH[sid], direction=r['direction'], p_horizon=int(r['p_horizon']), p_q=int(r['p_q']),
                      p_win=int(r['p_win']), p_hold=int(r['p_hold']), confirmer=r['confirmer'], c_horizon=int(r['c_horizon']), c_q=int(r['c_q']),
                      c_hold=int(r['c_hold']), screen_peaks=r['wide'], n_proposals=len(props),
                      proposals=' '.join(a.strftime('%Y-%m-%d') for a, b in props)))
print('carried legs built:', {k: len(v) for k, v in CARRY.items()}, flush=True)
ALL = ''.join(CARRY.keys())

# ---- 4/5. recompute the walked record of walk 94 with and without the carried legs, cut by cut
chosen = pickle.load(open('cache/w94_chosen_1962.pkl', 'rb'))
def record(with_carry, carry_letters=ALL):
    log = []; lapsed = []
    for cut in sorted(chosen):
        p = dict(chosen[cut]); Y = cut.year
        if with_carry: p['carry'] = carry_letters
        LAPSED.clear(); r, t = build_v(p)
        for x in t:
            if x['kind'] in ('peak', 'trough') and cut <= x['published'] < pd.Timestamp(Y + 1, 1, 1):
                log.append((x['published'].strftime('%Y-%m-%d'), 'OPEN' if x['kind'] == 'peak' else 'CLOSE', x['date'].strftime('%Y-%m'), x['leg']))
        for a, b, L in LAPSED:
            if a.year == Y: lapsed.append((cut.year, a.strftime('%Y-%m-%d'), b.strftime('%Y-%m'), L))
    return sorted(log), sorted(lapsed)
base_log, base_lapsed = record(False)
carry_log, carry_lapsed = record(True)
print('walk 94 record:'); [print('  ', x) for x in base_log]
print('with every carried leg:'); [print('  ', x) for x in carry_log]
changed = [x for x in carry_log if x not in base_log] + [x for x in base_log if x not in carry_log]
print('record changed by carrying:', changed)
print('lapsed proposals without carry:', len(base_lapsed)); [print('  ', x) for x in base_lapsed]
print('lapsed proposals with carry:', len(carry_lapsed)); [print('  ', x) for x in carry_lapsed]
# which carried legs are responsible for any change -- test one at a time
bad = []
if changed:
    for L in CARRY:
        lg, lp = record(True, L)
        if lg != base_log: bad.append(L); print('  leg', L, PICK.index[LETTERS.index(L)], 'changes the record:', [x for x in lg if x not in base_log])
keep = ''.join(L for L in CARRY if L not in bad)
final_log, final_lapsed = record(True, keep)
print('carried after exclusion:', len(keep), 'record identical to walk 94:', final_log == base_log, 'lapsed:', len(final_lapsed))
for row in TABLE:
    row['carried'] = row['letter'] in keep
    row['lapsed_proposals'] = ' '.join(a for (y, a, b, L) in final_lapsed if L == row['letter'])
pd.DataFrame(TABLE).to_csv(os.path.join(OUT, 'v355_carried_legs.csv'), index=False)
json.dump(dict(walk94=base_log, carried=final_log, changed_by_all=changed, excluded=bad, kept=keep,
               lapsed_walk94=base_lapsed, lapsed_carried=final_lapsed), open(os.path.join(OUT, 'v355_record.json'), 'w'), indent=1, default=str)
pickle.dump(dict(CARRY={L: CARRY[L] for L in keep}, TABLE=TABLE), open('cache/v355_carry.pkl', 'wb'))
print('written', OUT, flush=True)
