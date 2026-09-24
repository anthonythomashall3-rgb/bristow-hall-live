import json
rows={r['base']:r for r in json.load(open('research/revision_rerank/rows_raw.json'))}
# CH-R20 flag sets carried VERBATIM; new bases assigned by identity (documented, reversible).
ZEROC={'NFCI','GACDFSA066MSFRBPHI'}          # series that take negative / centered values
REBASE={'CMRMTSPL','GDPC1','INDPRO','W875RX1','TCU',   # CH-R20 verbatim
        'CMRMTSPLx','W875RX1.FREDMD','RTDSM_M2'}       # new: rebasable real-levels / money redef
EXTREME_FLAG='PCT_UNRELIABLE_EXTREME'  # extension: non-flagged pp>=50 (never fires on CH-R20 15)
def klass(r):
    sr=r['share_revised']; pa=r['p95_abs_rev'] or 0.0; pp=r['p95_pct_of_level']
    b=r['base']; flags=[]
    if b in ZEROC: flags.append('ZERO_CENTERED_pct_meaningless')
    if b in REBASE: flags.append('REBASING_INFLATES_pct_and_share')
    if sr==0: return 'NEVER_REVISED',flags
    if pa==0: return 'NEGLIGIBLE',flags
    if 'ZERO_CENTERED_pct_meaningless' in flags: return 'LARGE',flags
    if 'REBASING_INFLATES_pct_and_share' in flags:
        return ('SMALL' if (pp is not None and pp<3.0) else 'LARGE_BUT_REBASING'),flags
    if pp is not None and pp<3.0: return 'SMALL',flags
    if pp is not None and pp>=50.0:
        flags.append(EXTREME_FLAG); return 'LARGE',flags
    return 'MODERATE',flags
# --- self-validate rule reproduces CH-R20's 15 klasses on CH-R20's ORIGINAL numbers ---
r20=json.load(open('research/revision_cert_r20/CH-R20_REVISION_CERTIFICATION_PROBE.v1.json'))
orig={c['base']:c for c in r20['series_certified']}
mism=[]
for b,c in orig.items():
    k,_=klass({'base':b,'share_revised':c['share_revised'],'p95_abs_rev':c['p95_abs_rev'],'p95_pct_of_level':c['p95_pct_of_level']})
    if k!=c['klass']: mism.append((b,c['klass'],k))
print("SELF-VALIDATION mismatches vs CH-R20 (must be []):",mism)
# --- classify current 22 ---
out=[]
for b in sorted(rows):
    r=rows[b]; k,fl=klass(r)
    prev=orig.get(b,{}).get('klass')
    usable='growth (rebased level)' if 'REBASING_INFLATES_pct_and_share' in fl else ('growth/level; pct unreliable (zero-centered)' if 'ZERO_CENTERED_pct_meaningless' in fl else 'level')
    out.append(dict(base=b,lanes=r['lanes'],floor_asof=r['floor_asof'],edge_asof=r['edge_asof'],
        n_obs_measurable=r['n_obs_measurable'],share_revised=r['share_revised'],
        rev_variance=round(r['rev_variance'],6),p95_abs_rev=r['p95_abs_rev'],
        p95_pct_of_level=r['p95_pct_of_level'],median_level=r['median_level'],
        klass=k,flags=fl,klass_ch_r20=prev,changed=(prev is not None and prev!=k),is_new=(prev is None),usable_form=usable))
json.dump(out,open('research/revision_rerank/classified.json','w'),indent=1)
print(f"\n{'base':20s} {'lanes':8s} {'floor':8s} {'shr':>7s} {'p95%lvl':>10s} {'klass':22s} {'R20':22s} chg")
for o in out:
    tag='NEW' if o['is_new'] else ('CHG' if o['changed'] else '')
    pp=o['p95_pct_of_level']; pps=f"{pp:.2f}" if pp is not None else "None"
    print(f"{o['base']:20s} {o['lanes']:8s} {str(o['floor_asof']):8s} {o['share_revised']:7.4f} {pps:>10s} {o['klass']:22s} {str(o['klass_ch_r20']):22s} {tag}")
