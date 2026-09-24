#!/usr/bin/env python3
import json,hashlib,os,glob
def sh(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
os.chdir(os.path.dirname(os.path.abspath(__file__)))
m=json.load(open("results_main.json")); p2=json.load(open("results_2.json"))
p4=json.load(open("results_4.json")); p6=json.load(open("results_6d.json"))
SCR="research/channel_structure_ch1/scratch"
scratch=sorted(glob.glob("*.json")+glob.glob("*.py"))
evidence={f"{SCR}/work/{f}":{"bytes":os.path.getsize(f),"sha256":sh(f)} for f in scratch}
for extra in ("../verify_start.txt","../verify_end.txt","../vault_sha_start.txt","../vault_sha_end.txt"):
    if os.path.exists(extra):
        rel=f"{SCR}/{os.path.basename(extra)}"
        evidence[rel]={"bytes":os.path.getsize(extra),"sha256":sh(extra)}

R={
 "schema_version":"recession-monitor-v2.ch1-channel-structure-probe.v1",
 "batch_id":"CH1_CHANNEL_STRUCTURE_PROBE",
 "window":2,"writes_vault":False,"network":"none",
 "measured_on":"transformed signed-deterioration z as channel_score receives them (zval on the 1976-06-01..END daily grid); index_v1's own transform functions called, nothing re-derived",
 "sample_window":m["s0_window"],
 "note_nowcast":"Structural sections (§1-§6) measured with NOWCAST_DISABLE=1 (pure carry-forward published line); §6D measures nowcast ON vs OFF explicitly.",

 "s0_transformed_span_per_member":m["s0_span"],

 "s1_correlation":{
  "members_order":m["s1_members"],
  "raw_vs_transformed_named_pairs":m["s1_2_raw_vs_transformed"],
  "collinear_ge_0p80_transformed":m["s1_4_collinear_ge0p80"],
  "matrices_in_scratch":["pearson17.npy","spearman17.npy","nover17.npy"],
  "reading":"INDPRO~CMRMT 0.966->0.875 and PERMIT~HOUST 0.953->0.911: raw trend inflation shed a little but both remain real structural duplicates. BAA10Y~BAAAAA 0.816->0.816 unchanged (genuine credit duplicate). SAHM~UNRATEv 0.505->0.534 stays low (independent). New transformed collinear pairs surfaced by de-trending: INDPRO~TCU 0.90, IURSA~SAHM 0.857."},

 "s2_effective_independent_members":{
  "per_channel":m["s2_effN"],"formula":m["s2_effN_formula"],
  "nfci_first_nonnull_from_bytes":m["s2_3_nfci_first"],
  "nfci_finding":"§2.3 premise said NFCI non-null from 2011 per V1. BYTES (current_revised NFCI.csv) show first obs "+m["s2_3_nfci_first"]+" -> finconditions is populated across the ENTIRE 1976-06+ window in current-vintage mode; the 2011 floor is an as-of/archive-vintage fact, not current-vintage.",
  "reading":"Every 4-member channel carries ~1.5-2.4 independent signals, not 4. realactivity (1.55) and labor (1.65) are the most redundant; housingincome (2.44) the least."},

 "s3_variance_contribution":{**m["s3_var_share"],
  "equal_contribution_weight_vector":m["s3_4_equal_contribution_weights"],
  "equal_contribution_note":m["s3_4_note"],
  "headline_finding":"labor drives 0.75 of headline variance overall and 0.90 in recessions, at nominal weight 0.30. finconditions realized 0.03 vs nominal 0.10; creditequity 0.07 vs 0.20; housingincome 0.045 vs 0.15. The config's stated weights are NOT the realized influence. In expansions the split is far closer to nominal (labor 0.33)."},

 "s4_lead_lag":{
  "evidence_kind":p4["evidence_kind"],
  "reference_chronology":p4["reference_chronology"],
  "crossing_definition":p4["crossing_def"],
  "onsets_reached":p4["onsets_reached"],"onsets_reached_n":p4["onsets_reached_n"],
  "unreachable":p4["unreachable"],
  "per_episode_lead_days":p4["per_episode"],
  "per_channel_summary":p4["per_channel_summary"],
  "cap_caveat":"§19.4: search window capped at [onset-540d, onset+180d]; many crossings saturate at +540 (channel already elevated a full window before onset, e.g. back-to-back 1980->1981-82). Capped values are lower bounds on lead, not point leads. LABEL external_comparator MUST follow any weight derived from this section."},

 "s5_baseline_swap":{
  "estimator":m["s5_6_estimator"],
  "per_member_mu_sigma":m["s5_1_2_mu_sigma"],
  "headline":m["s5_3_headline"],
  "ordering":m["s5_4_ordering"],
  "ordering_meanstd_variant_rank":m["s5_alt_meanstd_ordering_rank"],
  "twenty22_24":m["s5_5_2022_24"],
  "headline_finding":"Switching to a statistical, NBER-free full-history robust baseline leaves the severity ORDERING IDENTICAL (current == robust-median/MAD == mean/sd): 2020 > 2007-09 > 1980 > 1981-82 > 2001 > 1990-91 > 2022-24*. Headline corr 0.988; max divergence 7.62 at 2020-05-01 (COVID spike rescaling). 2022-24* stays the smallest episode and sub-1sigma (0.74 current -> 0.62 statistical) with NO tuning. For the product's first requirement (ordering) the baseline choice is IMMATERIAL."},

 "s6_missing_channel":{**m["s6_missing_channel"],
  "wsum_distribution":m["s6_4_wsum_distribution"],
  "wsum_transitions":m["s6_4_wsum_transitions"],
  "headline_finding":"§6.5: the two treatments are IDENTICAL (corr 1.000, max div 0.000, ordering unchanged). Reason: achieved weight sum = 1.00 on ALL 18320 days -- every one of the 5 channels has >=1 member present from 1976-06 onward (finconditions via NFCI from 1971 in current-vintage). The pre-2011 0.90->1.00 rescale the section anticipated DOES NOT OCCUR in current_revised mode. The renormalize-vs-zero decision is immaterial here; it only bites in an as-of/archive-vintage build where NFCI is truly absent pre-2011."},

 "s6A_stationarity":{
  "note":p2["s6A_note"],
  "per_member":p2["s6A_stationarity"],
  "disagreements":[r["m"] for r in p2["s6A_stationarity"] if r["disagree"]],
  "transform_did_not_fix":[r["m"] for r in p2["s6A_stationarity"] if not r["transform_fixed"]],
  "reading":"6 code-vs-test disagreements. ICSA & PERMIT: raw already stationary on both tests, code still applies yoy (harmless de-trend). BAAAAA/BAA10Y/VIX/NFCI: code leaves untransformed but KPSS rejects level-stationarity while ADF accepts -> these are exactly the BORDERLINE members (§6A.4) whose 'none' is a genuine judgment call and must stay labelled. INDPRO, NASDAQ, W875, UMCSENT: transformed series still not stationary on both tests (near-unit-root yoy / persistent drawdown). No transform changed (§6A.5)."},

 "s6B_windows":{
  "note":p2["s6B_note"],
  "persistence_vs_window":p2["s6B_persistence"],
  "sensitivity":p2["s6B3_sensitivity"],
  "reading":"UNRATEv window=120d vs measured persistence ~806d and z-corr only 0.68 at 60d / 0.85 at 240d -> its window is an EFFECTIVELY FREE PARAMETER. INDPRO yoy also sensitive (z-corr 0.70-0.76 across 180-730d). IURSA (0.945-0.985), ICSA (0.96), NASDAQ & UMCSENT drawdown (~0.90) are window-robust -> their look-back barely matters. The 370 vs 120 rise_floor split (IURSA vs UNRATEv) has no traced origin and the shorter one is the sensitive one. No window changed (§6B.4)."},

 "s6C_staircase":{**p2["s6C_staircase"],"resolution_by_decade_median_age_days":p2["s6C_resolution_by_decade"],
  "reading":"Coarsest contributing channel is ~monthly in every era (median freshest-age 15d, p99 30d, max 57d). 84.6% of days SOMETHING changes (daily members ICSA/NASDAQ/VIX/BAA10Y), so only 15.4% are pure carry-forward repeats -- but the SLOW channels are monthly staircases jittered by the daily ones. Effective headline resolution: monthly spine + daily edge. Nothing interpolated (§6C.4)."},

 "s6D_nowcast_audit":{**{k:p6[k] for k in p6},
  "reading":"9 members receive live-edge fills over 2026-05..2026-07; 89 published days influenced (all >= nowcast_from 2026-05-01). Headline with vs without nowcast: corr 0.999997, max div 0.059 at 2026-07-02. §6D.4 CONFIRMED: history byte-identical before nowcast_from (max diff 0.0). §6D.3 FINDING: the revision-bias b_hat is a SECOND, undisclosed calibration channel fitted on KNOWN FINAL (revised) values (final_z - firstprint_z); it does NOT use recession labels or the target ledger; only NFCI's b_hat is applied at the live edge. OLS bridge coeffs frozen on <=2011-12-31, OOS-validated. Corroborates the prior 'unlabelled 2nd calibration channel' note."},

 "gates":{
  "verify_start":"PASS (mode=catalog files=27270 series=270)",
  "verify_end":"FAIL: 'handoff member exact set/order differs'",
  "verify_end_cause":"CONCURRENT-WRITER, NOT THIS PROBE. Unmanifested file data_vault/reports/html_masquerade_verdicts.v1.json (6567B) created 2026-08-05T09:43:37 -- AFTER this probe's start-verify (09:41:54, PASS) and BEFORE this probe's first write (measure_main.py 09:45:47). A window-1/autopilot writer emitted a masquerade-verdict report without rebuilding claude_handoff_manifest.json. This probe wrote nothing under data_vault/.",
  "vault_manifest_sha_start":open("../vault_sha_start.txt").read().strip()[:16],
  "vault_manifest_sha_end":open("../vault_sha_end.txt").read().strip()[:16],
  "vault_manifest_sha_identical":True,
  "readonly_assertions":{
   "1_all_vault_files_opened_read_only":True,
   "2_only_paths_created_or_modified":[f"{SCR}/work/ tree",
     "research/channel_structure_ch1/CH1_CHANNEL_STRUCTURE_PROBE.v1.json",
     "PHASE2_PROGRESS.md (append)"],
   "3_no_writer_lock_taken":True},
  "readonly_all_green":True,
  "concurrent_writer_disposition":"§8: unmanifested vault change from a concurrent writer with all three read-only assertions green is the writer's work, not this probe's -> NOT a STOP for CH1. Flagged to director as an informational repo-integrity anomaly (manifest needs rebuild by the masquerade-report owner)."},

 "must_not_do_compliance":{"changed_no_weight_threshold_baseline_member_channel":True,
  "admitted_nothing":True,"wrote_nothing_to_vault":True,
  "target_ledger_untouched":True,"operational_status_untouched":True,
  "no_test_adjusted":True,"took_no_writer_lock":True},

 "evidence_files":evidence
}
open("../../CH1_CHANNEL_STRUCTURE_PROBE.v1.json","w").write(json.dumps(R,indent=1,default=str))
print("receipt bytes:",os.path.getsize("../../CH1_CHANNEL_STRUCTURE_PROBE.v1.json"))
print("evidence files:",len(evidence))
PY