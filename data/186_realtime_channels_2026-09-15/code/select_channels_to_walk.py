#!/usr/bin/env python3
"""Choose which transmission channels are worth walking, from the frozen screen.

WHY NOT WALK THEM ALL. A walk takes half an hour to two hours and each extra leg multiplies the search
space. 573 channels cannot be walked and do not need to be: the frozen screen -- every channel priced
as an armed leg over the whole sample -- already says which ones can possibly help, and a channel that
cannot cover a peak cleanly when it is allowed to see the whole sample will certainly not do it inside
a walk. The frozen screen is an upper bound, so it is a valid filter: it can only be too generous,
never too strict, and anything it rejects is safely rejected.

WHAT "BEST" MEANS HERE, AND WHY IT IS NOT "MOST PEAKS". Ranking by peaks covered picks five channels
that all cover 2007 and none that covers 1973. What the rule needs is the opposite: a channel that
covers a peak nothing else covers is worth more than the fifth one that covers a peak already well
served. So the ranking is by MARGINAL contribution -- greedy set cover over the peaks -- and the report
also gives, for each peak, how many causally distinct channels reach it. A peak covered by one channel
is a single point of failure. A peak covered by six is safe.

That second number is the one that bears on the requirement that the rule keep working. A future
recession will not arrive through the channel that happens to have been picked; it will arrive through
whichever one is live at the time. Breadth of coverage per peak is the closest thing this programme can
measure to that.
"""
import os, re, json, collections, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
OUT = os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'out')
SRC = os.path.join(OUT, 'all_channels_as_legs.csv')
PEAKS = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07',
         '1990-07','2001-03','2007-12','2020-02','2024-04']

# The mechanism each series belongs to, from MECHANISM-MAP-2026-09-15.md. Prefixes, matched longest
# first, so a channel's mechanism is declared rather than guessed at from its behaviour.
MECH = [
 ('DGS','A1 monetary'),('DFII','A1 monetary'),('DPRIME','A1 monetary'),('DFF','A1 monetary'),
 ('T10Y','A1 monetary'),('T5Y','A1 monetary'),('THREEFY','A1 monetary'),('MORTGAGE','A1 monetary'),
 ('DTB','A1 monetary'),('EFFR','A1 monetary'),('SOFR','A1 monetary'),('IORB','A1 monetary'),
 ('DRTS','A2 credit'),('DRSD','A2 credit'),('DR','A2 credit'),('COR','A2 credit'),('TOTBKCR','A2 credit'),
 ('BUSLOANS','A2 credit'),('TOTCI','A2 credit'),('TOTLL','A2 credit'),('NDF','A2 credit'),
 ('COMPOUT','B1 plumbing'),('ABCOMP','B1 plumbing'),('FINCPN','B1 plumbing'),('WLCFL','B1 plumbing'),
 ('BORROW','B1 plumbing'),('WRESBAL','B1 plumbing'),('RRPONT','B1 plumbing'),('RPONT','B1 plumbing'),
 ('SP500','A3 equity'),('NASDAQ','A3 equity'),('DJIA','A3 equity'),('VIX','A3 equity'),
 ('BAML','A3 equity'),('GVZ','A3 equity'),
 ('HOUST','A4 housing'),('PERMIT','A4 housing'),('MSACSR','A4 housing'),('HSN','A4 housing'),
 ('AUTHNOT','A4 housing'),('CSUSHPI','A4 housing'),('TLNRES','A4 housing'),('PRRES','A4 housing'),
 ('TTLCONS','A4 housing'),('COMPUTSA','A4 housing'),('UNDCONT','A4 housing'),
 ('WTI','A5 energy'),('DCOIL','A5 energy'),('DHHNGSP','A5 energy'),('GAS','A5 energy'),
 ('DDFUEL','A5 energy'),('WB_','A5 energy'),('PNGAS','A5 energy'),
 ('ISRATIO','A6 inventory'),('BUSINV','A6 inventory'),('AMTM','A6 inventory'),('NEWORDER','A6 inventory'),
 ('ACOGNO','A6 inventory'),('DGORDER','A6 inventory'),('A34S','A6 inventory'),('I42IM','A6 inventory'),
 ('MTSDS','A7 fiscal'),('FYFSD','A7 fiscal'),('GFDEBTN','A7 fiscal'),('DTS_','A7 fiscal'),
 ('LNS','A8/A9 labour supply'),('LNU','A8/A9 labour supply'),('CIVPART','A8/A9 labour supply'),
 ('EMRATIO','A8/A9 labour supply'),('NILFWJN','A8/A9 labour supply'),
 ('ICSA','core labour'),('IC4W','core labour'),('CCSA','core labour'),('ICNSA','core labour'),
 ('CCNSA','core labour'),('IUR','core labour'),('JTS','core labour'),('JTU','core labour'),
 ('TEMPHELP','core labour'),('AWH','core labour'),('CES','core labour'),('PAYEMS','core labour'),
 ('UNRATE','core labour'),('MANEMP','core labour'),('ADPW','core labour'),('USINFO','core labour'),
 ('XTEXVA','B2 external'),('VALEXP','B2 external'),('DEX','B2 external'),('DTWEX','B2 external'),
 ('RTWEX','B2 external'),('TWEXB','B2 external'),('NETEXP','B2 external'),('CPB_','B2 external'),
 ('EXP58','B2 external'),
 ('IR','B3 tariffs'),('IQ','B3 tariffs'),('CHNTOT','B3 tariffs'),
 ('GSCPI','B4 supply chain'),('TRUCK','B4 supply chain'),('RAILFRT','B4 supply chain'),
 ('TSIFRGHT','B4 supply chain'),('ENPLANE','B4 supply chain'),
 ('EIA930','C1 grid'),('IPG22','C1 grid'),('IPUTIL','C1 grid'),
 ('FEMA','C3 climate'),
 ('WTREGEN','C4 sovereign'),('WDTGAL','C4 sovereign'),('TREAST','C4 sovereign'),('D2WLT','C4 sovereign'),
 ('USEPU','C4 sovereign'),('EPU','C4 sovereign'),('EMV','C4 sovereign'),('GEPU','C4 sovereign'),
 ('WPU','A5 energy'),('PPI','A5 energy'),('CPI','A5 energy'),('CU','consumer'),
 ('UMCSENT','consumer'),('MICH','consumer'),('RSAFS','consumer'),('RSXFS','consumer'),
 ('CARTS','consumer'),('PCE','consumer'),('TOTALSA','consumer'),
 ('BUSAPP','C2 formation'),('HBUSAPP','C2 formation'),('WBUSAPP','C2 formation'),('CBUSAPP','C2 formation'),
 ('BAHBA','C2 formation'),('BAWBA','C2 formation'),('INDEED','C2 formation'),
 ('INDPRO','activity'),('IPMAN','activity'),('TCU','activity'),('BBKM','activity'),('CFNAI','activity'),
 ('WEI','activity'),('ADS','activity'),('BSC','B2 external'),('BCOB','B2 external'),('BSFG','B2 external'),
 ('M0','pre-1960 NBER'),('M1','pre-1960 NBER'),('Q0','pre-1960 NBER'),
 ('NFCI','A2 credit'),('ANFCI','A2 credit'),('STLFSI','A2 credit'),
 # DATA FETCHED AFTER THE FIRST SCREEN, AND MISCLASSIFIED BY IT. The first run reported grid and
 # climate as having no admissible channel. Climate had none because NOAA's disaster data had not been
 # fetched yet; grid appeared to have none because the EIA Monthly Energy Review series are named
 # EIA_MER_* and the map only knew the EIA930 prefix, so they fell into 'unclassified'. The first was a
 # real gap and is now filled; the second was a bug in this file, and a blind spot reported because of a
 # naming mismatch is worse than one reported honestly.
 ('EIA_MER','C1 grid'),('EIA930','C1 grid'),
 ('NOAA','C3 climate'),('FEMA','C3 climate'),
 ('PORTWATCH','B4 supply chain'),('GSCPI','B4 supply chain'),
 ('CPB_','B2 external'),('WB_','A5 energy'),('INDEED','C2 formation'),('DTS_','A7 fiscal'),
]
MECH.sort(key=lambda t: -len(t[0]))
def mech(sid):
    for p, m in MECH:
        if sid.startswith(p): return m
    return 'unclassified'

if not os.path.exists(SRC):
    raise SystemExit('the frozen screen has not finished: %s not found' % SRC)
# LEAKAGE. The candidate pool is built from every CSV in the data folders, and some of those files are
# recession indicators rather than economic data: USRECDP and USRECDM are the NBER's own daily and
# monthly recession dummies, RECPROUSM156N is a recession PROBABILITY, and several others encode the
# answer directly. A "channel" that is the recession indicator predicts recessions perfectly and means
# nothing. They are excluded here by name and by pattern, before anything is counted.
LEAK = re.compile(r'^(USREC|RECPRO|JHDUSRGDPBR|USARECD|NBERREC|CANREC|.*RECD[MPQ]$|.*RECESSION.*)', re.I)
D = pd.read_csv(SRC)
_n0 = len(D)
_dropped = sorted(set(D[D.proposer.str.match(LEAK)].proposer))
D = D[~D.proposer.str.match(LEAK)]
print('recession-indicator series excluded as leakage: %d configurations, %d series %s'
      % (_n0 - len(D), len(_dropped), _dropped[:12]))
D['peaks'] = D.inwindow.apply(lambda s: frozenset(json.loads(s).keys()) if isinstance(s, str) else frozenset())
D = D[D.peaks.apply(len) > 0]
D['mechanism'] = D.proposer.apply(mech)
pd.set_option('display.width', 270)
print('admissible leg configurations: %d over %d distinct channels' % (len(D), D.proposer.nunique()))

# one row per channel: its best configuration, measured by how many peaks it covers in window and then
# by how rarely it fires
best = (D.assign(n=D.peaks.apply(len))
          .sort_values(['n', 'n_fire'], ascending=[False, True])
          .groupby('proposer').head(1).reset_index(drop=True))
print('channels with at least one in-window call: %d' % len(best))

# how many causally distinct channels reach each peak -- the robustness number
cov = collections.Counter()
mcov = collections.defaultdict(set)
for _, r in best.iterrows():
    for p in r.peaks:
        cov[p] += 1; mcov[p].add(r.mechanism)
print('\nPER-PEAK BREADTH -- how many channels, and how many distinct mechanisms, reach each peak')
print('%-10s %8s %12s   %s' % ('peak', 'channels', 'mechanisms', 'which mechanisms'))
for p in PEAKS:
    ms = sorted(mcov.get(p, []))
    print('%-10s %8d %12d   %s' % (p, cov.get(p, 0), len(ms), ', '.join(ms)[:110] or '-- NONE --'))

# greedy set cover: the smallest set of channels that reaches the most peaks
remaining = set(PEAKS); chosen = []
pool = best.copy()
while remaining and len(chosen) < 14:
    pool['gain'] = pool.peaks.apply(lambda s: len(s & remaining))
    pool = pool.sort_values(['gain', 'n_fire'], ascending=[False, True])
    top = pool.iloc[0]
    if top['gain'] == 0: break
    chosen.append(top); remaining -= set(top.peaks)
    pool = pool.iloc[1:]
print('\nGREEDY COVER -- the fewest channels that reach the most peaks')
print('%-24s %-22s %-10s %6s %6s  %s' % ('channel', 'mechanism', 'direction', 'fires', 'new', 'covers'))
for c in chosen:
    print('%-24s %-22s %-10s %6d %6d  %s' % (c.proposer[:24], c.mechanism[:22], c.direction,
                                             c.n_fire, c['gain'], ','.join(sorted(c.peaks))))
print('\npeaks still uncovered by any admissible channel: %s' % (sorted(remaining) or 'NONE'))


# ---------------------------------------------------------------------------------------------
# COVER BY MECHANISM, NOT ONLY BY PEAK.
# Covering every past peak is not the same as being able to see every kind of recession. A peak can
# be covered five times over by five monetary channels while the supply-chain mechanism has no
# admissible channel at all -- and the next recession will not arrive through whichever mechanism
# happens to have produced the most past peaks. A mechanism with no admissible channel is a blind
# spot, and it is invisible in a peak-based count because no past peak came through it.
# So: the same greedy cover, run over MECHANISMS, and an explicit list of the mechanisms nothing
# reaches. The walk list is the union of the two covers.
ALL_MECH = sorted(set(m for _, m in MECH))
have = collections.defaultdict(list)
for _, r in best.iterrows():
    have[r.mechanism].append(r)
print('\nPER-MECHANISM COVER -- can the rule see this KIND of recession at all?')
print('%-24s %9s %7s   %s' % ('mechanism', 'channels', 'peaks', 'peaks reached'))
blind = []
for m in ALL_MECH:
    rs = have.get(m, [])
    pk = sorted(set().union(*[set(r.peaks) for r in rs])) if rs else []
    print('%-24s %9d %7d   %s' % (m[:24], len(rs), len(pk), ','.join(pk)[:94] or '-- NONE --'))
    if not rs: blind.append(m)
print('\nMECHANISMS WITH NO ADMISSIBLE CHANNEL -- the blind spots for a future recession:')
print('   %s' % (', '.join(blind) if blind else 'none'))

mech_need = set(m for m in ALL_MECH if have.get(m))
mech_chosen, seen_m = [], set(c.mechanism for c in chosen)
for m in sorted(mech_need - seen_m):
    rs = sorted(have[m], key=lambda r: (-len(r.peaks), r.n_fire))
    mech_chosen.append(rs[0])
if mech_chosen:
    print('\nADDED FOR MECHANISM COVER -- channels whose kind of recession nothing else in the list watches')
    print('%-24s %-22s %-10s %6s  %s' % ('channel', 'mechanism', 'direction', 'fires', 'covers'))
    for c in mech_chosen:
        print('%-24s %-22s %-10s %6d  %s' % (c.proposer[:24], c.mechanism[:22], c.direction,
                                             c.n_fire, ','.join(sorted(c.peaks))))
chosen = list(chosen) + mech_chosen
print('\nWALK LIST: %d channels -- %d for peak cover, %d added for mechanism cover' %
      (len(chosen), len(chosen) - len(mech_chosen), len(mech_chosen)))

rows = []
for c in chosen:
    rows.append(dict(channel=c.proposer, mechanism=c.mechanism, direction=c.direction, p_read=c.p_read,
                     p_q=c.p_q, p_win=c.p_win, p_hold=c.p_hold, confirmer=c.confirmer, c_q=c.c_q,
                     c_win=c.c_win, n_fire=c.n_fire, covers=','.join(sorted(c.peaks)),
                     reason=('peak cover' if c is not None and c.mechanism in
                             [x.mechanism for x in chosen[:len(chosen)-len(mech_chosen)]] else 'mechanism cover')))
pd.DataFrame(rows).to_csv(os.path.join(OUT, 'channels_to_walk.csv'), index=False)
best_out = best[['proposer','mechanism','direction','p_read','p_q','p_win','p_hold','confirmer','c_q','c_win','n_fire','n_peak','inwindow']]
best_out.to_csv(os.path.join(OUT, 'channel_best_per_series.csv'), index=False)
print('\nwritten: out/channels_to_walk.csv and out/channel_best_per_series.csv')
