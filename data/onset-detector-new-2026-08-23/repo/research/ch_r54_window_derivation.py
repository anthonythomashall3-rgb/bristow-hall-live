import csv, json
ch4=list(csv.DictReader(open('research/ch4_persistence_universe_v1.csv')))
idx={(r['series_id'],r['transform']):r for r in ch4}
ch3=list(csv.DictReader(open('research/ch3_factor_structure_v1.csv')))
mp={r['member']:r for r in csv.DictReader(open('research/member_persistence_v1.csv'))}

# ch3 base -> member (model actually feeds this member's transformed signal)
BASE2MEMBER={'ICSA':'ICSA','IURSA':'IURSA','SAHMREALTIME':'SAHM','UNRATE':'UNRATEv',
 'INDPRO':'INDPRO','CMRMTSPL':'CMRMT','CMRMTSPLx':'CMRMT','TCU':'TCU','NFCI':'NFCI',
 'PERMIT':'PERMIT','HOUST':'HOUST','UMCSENT':'UMCSENT','W875RX1':'W875'}
def fnum(x):
    try: return float(x)
    except: return None
def strip(s): return s.split('.')[0]

rows=[]; disc=[]
for r in ch3:
    base=r['base']; rep=r['rep_series']; mt=r['transform']
    mem=BASE2MEMBER.get(base)
    persist_t=persist_r=deriv=span=None; stat=adf=kpss=''; src=''
    lrow=idx.get((rep,'level')) or idx.get((strip(rep),'level')) or idx.get((base,'level'))
    trow=idx.get((rep,mt)) or idx.get((strip(rep),mt)) or idx.get((base,mt))
    # RAW persistence = level series (CH4), fallback member raw
    if lrow: persist_r=fnum(lrow['persist_1e_days'])
    # stationarity from the model-transform row if available (that is what is fed)
    if trow:
        stat=trow['stationarity']; adf=trow['adf_stationary']; kpss=trow['kpss_stationary']
        span=fnum(trow['n'])*fnum(trow['spacing_days'])
    elif lrow:
        stat=lrow['stationarity']; adf=lrow['adf_stationary']; kpss=lrow['kpss_stationary']
        span=fnum(lrow['n'])*fnum(lrow['spacing_days'])
    if mem and mem in mp:  # MODEL MEMBER: transformed = model rolling-window signal
        src='member_persistence(model-fed)'
        persist_t=fnum(mp[mem]['persistence_1e_days'])
        if persist_r is None: persist_r=fnum(mp[mem]['raw_persistence_1e_days_ch1'])
        if span is None: span=fnum(mp[mem]['n_transformed_obs'])*fnum(mp[mem]['obs_spacing_days'])
        deriv=persist_t
        # report divergence from CH4 ch3-transform
        if trow:
            ch4t=fnum(trow['persist_1e_days'])
            if ch4t and persist_t and abs(ch4t-persist_t)/persist_t>0.15:
                disc.append(f"{base}: model-fed transformed persist {persist_t}d (member_persistence, {mp[mem]['transform_window_days']}d window) vs CH4 {mt} {ch4t}d — model transform != CH4 {mt}")
    elif trow:  # non-member: model transform = ch3 transform, CH4 authoritative
        src='ch4(ch3-transform)'
        persist_t=fnum(trow['persist_1e_days']); deriv=persist_t
    else:  # vintage lane, no CH4, no member
        src='UNAVAILABLE'
        disc.append(f"{base}: rep_series {rep} absent from CH4, no model-member fallback; derived window UNAVAILABLE (vintage-only as-of lane)")
    inh=None
    if mem and mp[mem]['transform_window_days']: inh=fnum(mp[mem]['transform_window_days'])
    ratio_inh=(inh/deriv) if (inh and deriv) else None
    ratio_rt=(persist_r/persist_t) if (persist_r and persist_t) else None
    exceeds=(deriv is not None and span is not None and deriv>span)
    rows.append(dict(base=base,rep_series=rep,model_transform=mt,src=src,
        persist_raw_d=persist_r,persist_transformed_d=persist_t,derived_window_d=deriv,
        inherited_window_d=inh,inherited_member=mem if inh else '',
        ratio_inherited_over_derived=round(ratio_inh,3) if ratio_inh else '',
        ratio_raw_over_transformed=round(ratio_rt,3) if ratio_rt else '',
        raw_vs_transformed_disagree_2x=(ratio_rt is not None and (ratio_rt>=2 or ratio_rt<=0.5)),
        stationarity=stat,adf_stationary=adf,kpss_stationary=kpss,
        history_span_d=round(span) if span else '',exceeds_history=exceeds,
        instrumentable=r['instrumentable'],top_factor=r['top_factor']))

cols=['base','rep_series','model_transform','src','persist_raw_d','persist_transformed_d',
 'derived_window_d','inherited_window_d','inherited_member','ratio_inherited_over_derived',
 'ratio_raw_over_transformed','raw_vs_transformed_disagree_2x','stationarity','adf_stationary',
 'kpss_stationary','history_span_d','exceeds_history','instrumentable','top_factor']
with open('research/window_derivation_v1.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

from collections import Counter
avail=[r for r in rows if r['derived_window_d'] is not None]
inh_rows=[r for r in rows if r['inherited_window_d']]
exceed=[r for r in rows if r['exceeds_history']]
disagree=[r for r in rows if r['raw_vs_transformed_disagree_2x']]
stat_counts=Counter(r['stationarity'] for r in rows if r['stationarity'])
biggest=sorted(avail,key=lambda r:r['derived_window_d'],reverse=True)[:12]
inh_ranked=sorted(inh_rows,key=lambda r:abs((r['ratio_inherited_over_derived'] or 1)-1),reverse=True)
summary=dict(n_bases=len(rows),n_with_derived=len(avail),n_unavailable=len(rows)-len(avail),
 n_inherited_carriers=len(inh_rows),stationarity_counts=dict(stat_counts),
 n_nonstationary_or_ambiguous=sum(1 for r in rows if r['stationarity'] in('nonstationary','ambiguous')),
 n_raw_transformed_disagree_2x=len(disagree),
 disagree_examples=[(r['base'],r['persist_raw_d'],r['persist_transformed_d'],r['ratio_raw_over_transformed']) for r in sorted(disagree,key=lambda r:r['ratio_raw_over_transformed'] or 0,reverse=True)[:12]],
 n_exceeds_history=len(exceed),
 exceeds_history_bases=[(r['base'],r['derived_window_d'],r['history_span_d'],r['model_transform'],r['stationarity']) for r in exceed],
 largest_derived_windows=[(r['base'],r['derived_window_d'],r['history_span_d'],r['stationarity'],r['model_transform']) for r in biggest],
 inherited_vs_derived_ranked=[(r['inherited_member'],r['base'],r['inherited_window_d'],r['derived_window_d'],r['ratio_inherited_over_derived']) for r in inh_ranked],
 nasdaq_baa_vix_note='Members NASDAQ(370),BAAAAA,BAA10Y,VIX have no CH3-R2 base (non-FRED-MD market series); only NASDAQ carries a window(370); reported not derived.',
 anchors=dict(ICSA_raw=idx[('ICSA','level')]['persist_1e_days'],INDPRO_raw=idx[('INDPRO','level')]['persist_1e_days'],TCU_raw=idx[('TCU','level')]['persist_1e_days'],note='CH4 level==CH1 raw anchors reproduced (ICSA 77, INDPRO 8835, TCU 620); UNRATEv 806/IURSA 308 raw from member_persistence (vintage lanes absent from CH4 universe)'),
 discrepancies=disc)
json.dump(summary,open('research/window_derivation_v1.json','w'),indent=1)
print('bases',len(rows),'derived',len(avail),'unavail',len(rows)-len(avail),'inh',len(inh_rows),'exceeds',len(exceed),'disagree2x',len(disagree))
print('stat',dict(stat_counts))
