#!/usr/bin/env python3
"""CH-R80 run-readiness census. Read-only. Joins CH-R71's 55 run-only cells to the
executable spine (planned_sources reservations + sources.v1.json adapters). No runs."""
import json, csv

gap = list(csv.DictReader(open('research/timemode_census/gap_rank.v1.csv')))
res_fams = [r['family'] for r in gap if r['status']=='RESERVED_ONLY']
planned = json.load(open('live_data/config/planned_sources.v1.json'))['sources']
by = {}
for s in planned:
    by[s['source_id']] = s
    for f in (s.get('coverage_source_family_ids') or []): by.setdefault(f, s)

# existing executable adapters (from the running spine)
srcs = json.load(open('live_data/config/sources.v1.json'))['sources']
existing_adapters = set(s.get('adapter') for s in srcs)

# publisher/shape -> existing adapter that could be REUSED (config+schema+test wrap, not new code).
# ASSUMPTION where inferred from adapter name; a real reuse still needs schema+parser_version+tests review.
REUSE = {
 'alfred_fred_vintages':'fred_json_api_vintages_deep','fred_md_official_panels':'fred_json_api',
 'fred_qd_official_panels':'fred_json_api',
 'bea_pio':'bea_api','bea_regional':'bea_api',
 'eia_natural_gas':'eia_v2_json','eia_petroleum':'eia_v2_json','eia_steo':'eia_v2_json',
 'bls_bed':'bls_json','bls_laus':'bls_json',
 'census_acs':'census_api','census_bfs':'census_api','census_construction':'census_api',
 'census_hvs':'census_api','census_m3':'census_api','census_marts':'census_api',
 'census_mtis_mwts':'census_api','census_saipe':'census_api','census_trade':'census_api',
 'richmond_mfg':'regional_survey_xlsx','richmond_services':'regional_survey_xlsx','kansascity_mfg':'regional_survey_xlsx',
 'treasury_tic':'fiscaldata_json','cfpb_complaints':'socrata_json',
}

rows = []
for f in res_fams:
    s = by[f]
    reg = s.get('registry_status'); auth = s.get('auth_env')
    est = s.get('endpoint_status') or ''
    cred = reg == 'RESERVED_CREDENTIAL_BOUND_NOT_ENABLED' or bool(auth)
    automatable = 'DISCOVERY_ONLY_NOT_AUTOMATABLE' not in est
    reuse = REUSE.get(f)
    reuse = reuse if (reuse in existing_adapters) else None
    needs_new_adapter = reuse is None
    # class: activation_contract makes every reservation NONEXECUTABLE (parser_version=null on all 55).
    # READY_TO_RUN=0 by contract. Primary blocker tag mirrors CH-R70's mutually-exclusive scheme.
    cls = 'NEEDS_CREDENTIAL' if cred else 'NEEDS_CODE'
    # every cell also needs an adapter -> code_also True for the credential class too
    note_bits = []
    if cred: note_bits.append('credential+code (adapter still required; key alone does not enable)')
    else:    note_bits.append('code (adapter/parser); no credential')
    if not automatable: note_bits.append('route DISCOVERY_ONLY_NOT_AUTOMATABLE -> reconfirm automatable URL before any adapter')
    if reuse: note_bits.append(f'existing adapter reusable: {reuse} (config+schema+tests wrap)')
    else:     note_bits.append('no existing adapter for shape -> new adapter')
    rows.append(dict(
        family=f, publisher=s.get('publisher',''), mode='current_revised',
        registry_status=reg, auth_env=auth or '', endpoint_status=est,
        parser_version='null', automatable=automatable,
        existing_adapter_candidate=reuse or 'NONE', needs_new_adapter=needs_new_adapter,
        readiness_class=cls, ready_to_run=False,
        ch_r71_claim='RESERVED_ONLY_just_needs_a_run', ch_r70_class=('needs_credential' if cred else 'technical_route_missing'),
        note='; '.join(note_bits)))

cols = ['family','publisher','mode','registry_status','auth_env','endpoint_status','parser_version',
        'automatable','existing_adapter_candidate','needs_new_adapter','readiness_class','ready_to_run',
        'ch_r71_claim','ch_r70_class','note']
with open('research/route_backlog/run_readiness.v1.csv','w',newline='') as fh:
    w=csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)

from collections import Counter
A=sum(1 for r in rows if r['ready_to_run'])
B=sum(1 for r in rows if r['readiness_class']=='NEEDS_CREDENTIAL')
C=sum(1 for r in rows if r['readiness_class']=='NEEDS_CODE')
reuse_n=sum(1 for r in rows if not r['needs_new_adapter'])
nonauto=sum(1 for r in rows if not r['automatable'])
print(f'total={len(rows)} A_ready={A} B_credential={B} C_code={C}')
print(f'adapter_reusable={reuse_n} needs_new_adapter={len(rows)-reuse_n} non_automatable_route={nonauto}')
print('publishers:', dict(Counter(r['publisher'].split()[0] if r['publisher'] else '?' for r in rows)))
