# v3.76 (26 September 2026; collections 436, 440, 441 - option (a), the record on the data as printed): state breadth B reads each
# state's insured unemployment rate AS PRINTED on page 8 of the Department's weekly release (collection 45's parsed table, the insured
# weeks 2002-11-16 to 2020-04-18; the row of the earliest release of each state-week) in place of FRED's current file, wherever a print
# exists; FRED's current file stands before and after that span and where a state-week has no print. Executed by walk9.py right after
# ST is built (the walk and the build alike). B's release day stays the rule (rel_state: the week + 19), which is no earlier than the
# page-8 table's own release.
_N376 = {'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Puerto Rico':'PR','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virgin Islands':'VI','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
_p376 = W.replace('24_bristow_rule_lab/workspace', '45_dol_first_prints_2026-09/state_first_prints_clean.csv')
STATE_RATES_PRINTED = None
if os.path.exists(_p376):
    _d376 = pd.read_csv(_p376)
    _d376['_iu'] = pd.to_datetime(_d376['iu_week_ended'], errors='coerce'); _d376['_rel'] = pd.to_datetime(_d376['wk'], errors='coerce'); _d376['_v'] = pd.to_numeric(_d376['iur'], errors='coerce')
    _d376 = _d376.dropna(subset=['_iu', '_v']).sort_values(['state', '_iu', '_rel']).drop_duplicates(['state', '_iu'], keep='first')
    _d376['_st'] = _d376['state'].map(_N376)
    if _d376['_st'].isna().any(): raise SystemExit('v3.76: a state in 45/state_first_prints_clean.csv has no FRED code: %s' % sorted(_d376.loc[_d376['_st'].isna(), 'state'].unique()))
    _P376 = _d376.pivot(index='_iu', columns='_st', values='_v').sort_index(); _cells376 = 0; _diff376 = 0
    for _c376 in _P376.columns:
        if _c376 not in ST.columns: continue
        _s376 = _P376[_c376].dropna(); _i376 = ST.index.intersection(_s376.index)
        _cells376 += len(_i376); _diff376 += int((ST.loc[_i376, _c376] != _s376.loc[_i376]).sum()); ST.loc[_i376, _c376] = _s376.loc[_i376].values
    STATE_RATES_PRINTED = dict(cells=_cells376, differ=_diff376, first=str(_P376.index.min().date()), last=str(_P376.index.max().date()))
    print('v3.76: state rates as printed on', _cells376, 'state-weeks (', _diff376, 'differ from the current file)')
else:
    print('v3.76 WARNING: the states\' printed rates (45/state_first_prints_clean.csv) are missing - B reads the current file')
