import json,os,glob,sys
B=glob.glob('/sessions/*/mnt/RecessionMonitor 2')[0]
S=os.path.join(B,'Recession Monitor V2/live_data/store')
NORM=os.path.join(S,'normalized/sha256')
SRCMAP=json.load(open('/tmp/srcmap.json'))
OUT='/tmp/rmv3/hist'; os.makedirs(OUT,exist_ok=True)

# series (or prefixes) to keep per source
WANT={
 'bls_core_live':['bls_core_live.'],
 'bls_mxp_current':['bls_mxp_current.EIUIR'],
 'dol_eta539_live':['.initial_claims','.insured_unemployment_rate_current_13_week','.covered_employment'],
 'fred_wei_current':['WEI'],'fred_cfnai_current':['CFNAI'],'fred_cfnaima3_current':['CFNAIMA3'],
 'tsa_throughput_current':['TSA.'],'bts_tsi_current':['BTS.TSI.TOTAL','BTS.TSI.FREIGHT'],
 'fred_truckd11_current':['TRUCKD11'],'chicago_carts_current':['CARTS.WEEKLY_INDEX_EX_AUTO'],
 'fhfa_hpi_monthly_us':['FHFA.HPI.PO.USA.SA'],
 'cfpb_credit_trends_current':['CFPB.CCT.CREDIT_TIGHTNESS_INDEX.MTG.SA.VALUE','CFPB.CCT.CREDIT_TIGHTNESS_INDEX.CRC.SA.VALUE'],
 'cfpb_mortgage_performance_state_90_plus_current':['CFPB.'],
 'fed_sloos_current':['FED.SLOOS.SUBLPDCILS_N.Q','FED.SLOOS.SUBLPDCISS_N.Q','FED.SLOOS.SUBLPDCLCS_N.Q','FED.SLOOS.SUBLPDCLAS_N.Q'],
 'fed_dsr_current':['FED.DSR.DSR_RATIO'],'fred_nfcicredit_current':['NFCICREDIT'],
 'fdic_banking_aggregate_quarterly':['FDIC.BANKS.NET_INCOME_YTD'],
 'treasury_curve_live':['treasury_curve_live.BC_10YEAR','treasury_curve_live.BC_2YEAR'],
 'fred_cpff_current':['CPFF'],
 'fred_rifsppna2p2d90nb_current':['RIFSPPNA2P2D90NB'],'fred_rifsppnaad90nb_current':['RIFSPPNAAD90NB'],
 'ofr_fsi_daily':['OFR.FSI.TOTAL','OFR.FSI.FUNDING','OFR.FSI.VOLATILITY','OFR.FSI.EQUITY_VALUATION'],
 'fred_t5yifr_current':['T5YIFR'],'fred_m2real_current':['M2REAL'],
 'census_btos_national_current':['CENSUS.BTOS.NATIONAL.INDEX.CURRENT_PERFORMANCE.ESTIMATE','CENSUS.BTOS.NATIONAL.INDEX.DEMAND.ESTIMATE','CENSUS.BTOS.NATIONAL.INDEX.EMPLOYEES.ESTIMATE'],
 'census_bds_national_current':['CENSUS.BDS.NATIONAL.ESTABS_EXIT_RATE'],
 'philly_mbos_diffusion_current':['PHILLY.MBOS.GAC','PHILLY.MBOS.NEC'],
 'dallas_tmos_diffusion_current':['DALLAS.TMOS.GENERAL_ACTIVITY'],
 'dallas_tssos_diffusion_current':['DALLAS.TSSOS.GENERAL_ACTIVITY'],
 'nyfed_business_leaders_current':['NYFED.BLS.BUSINESS_ACTIVITY.CURRENT.DIFFUSION','NYFED.BLS.EMPLOYMENT.CURRENT.DIFFUSION'],
 'chicago_cfsec_current':['CFSEC.ACTIVITY'],
 'fred_nfci_current':['NFCI'],'fred_nfcirisk_current':['NFCIRISK'],
 'fred_nfcileverage_current':['NFCILEVERAGE'],'fred_stlfsi4_current':['STLFSI4'],
}
def keep(sid,pats):
    for p in pats:
        if p.startswith('.'):
            if sid.endswith(p) or p in sid: return True
        elif sid==p or sid.startswith(p): return True
    return False

for src in sys.argv[1:]:
    dst=os.path.join(OUT,src+'.json')
    if os.path.exists(dst): print('skip',src); continue
    sha=SRCMAP.get(src)
    if not sha: print('NOSHA',src); continue
    p=os.path.join(NORM,sha[:2],sha+'.json')
    if not os.path.exists(p): print('MISSING',src); continue
    d=json.load(open(p))
    pats=WANT.get(src,[])
    acc={}
    meta={}
    for r in d.get('records',[]):
        sid=r.get('series_id')
        if not sid or not keep(sid,pats): continue
        if r.get('information_set_mode')!='current_revised': continue
        v=r.get('value'); op=r.get('observation_period')
        if v is None or op is None: continue
        try: v=float(v)
        except: continue
        acc.setdefault(sid,{})[op]=v
        if sid not in meta:
            meta[sid]={'unit':r.get('unit'),'label':r.get('label'),'source_id':r.get('source_id'),
                       'value_status':r.get('value_status'),'rights':r.get('rights_status')}
    out={'source_id':src,'series':{k:sorted(v.items()) for k,v in acc.items()},'meta':meta}
    json.dump(out,open(dst,'w'))
    print(f'{src}: {len(acc)} series, {sum(len(v) for v in acc.values())} obs')
