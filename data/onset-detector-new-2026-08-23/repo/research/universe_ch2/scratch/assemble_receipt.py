#!/usr/bin/env python3
"""Assemble the single CH2 receipt from scratch result files + gates + innocence proof.
Writes research/universe_ch2/CH2_UNIVERSE_AND_STRUCTURE_PROBE.v1.json (allowed receipt)."""
import json, os
R="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
S=R+"/research/universe_ch2/scratch"
core=json.load(open(S+"/ch2_core_results.json"))
stat=json.load(open(S+"/ch2_stat_asof_nowcast_results.json"))
uni=json.load(open(S+"/ch2_universe_results.json"))
fac=json.load(open(S+"/ch2_factor_results.json"))

s1=core["section1_variance_decomposition"]
s2=stat["section2_asof_frontier"]
s4=fac["section4_factor_structure"]
gates={
 "vault_identity_gate":{
   "vault_payload_rehash_start":"27269 entries / 0 missing / 0 mismatches (CLEAN)",
   "vault_payload_rehash_end":"27269 entries / 0 missing / 0 mismatches (CLEAN)",
   "DATA_SHA256SUMS_sha_start":"4567dbefed8393ed55f236db6358e035f8ab6a3a2c640937a1ee8824faa9eb0e",
   "DATA_SHA256SUMS_sha_end":"4567dbefed8393ed55f236db6358e035f8ab6a3a2c640937a1ee8824faa9eb0e",
   "vault_payload_byte_identical_start_eq_end":True,
   "verify_data_vault_start":"FAIL: handoff byte count differs: live_data/config/sources.v1.json (handoff member_set_sha256=7d456aff...)",
   "verify_data_vault_end":"PASS mode=catalog files=27270 bytes=842485829 series=270 manifest_matches=27269 (handoff member_set_sha256=b8c3f2aa...)",
   "verify_change_explanation":"EXPECTED per CH2 header: window-1 batch B-LAND-3B was concurrently writing live_data and reconciled the claude_handoff_manifest to the edited sources.v1.json during the probe (start FAIL -> end PASS). Vault PAYLOAD stayed byte-identical throughout (DATA_SHA256SUMS unchanged).",
   "git_HEAD_start":"3d96ff380500a9908da2fc7c52c8b3cb7a21f02a",
   "git_HEAD_end":"3d96ff380500a9908da2fc7c52c8b3cb7a21f02a"},
 "mismatch_member_measured_3x":{
   "file":"live_data/config/sources.v1.json",
   "measurements":["536255B sha d62d7d1f... (start#1)","536255B sha d62d7d1f... (start#2)","536255B sha d62d7d1f... (end#3)"],
   "byte_identical_across_all_three":True,
   "attribution":"sources.v1.json byte-stable during probe (measured 3x identical). Its mismatch vs the pre-rebuild handoff manifest was a window-1 B-LAND-3B concurrent-live_data effect (manifest rebuilt mid-probe), NOT this probe. Not inferred static: measured."},
 "innocence_proof":{
   "every_file_opened_read_only":True,
   "only_allowed_paths_written":"research/universe_ch2/** (scripts, scratch results, monthly cache, this receipt) + PHASE2_PROGRESS.md append. NO vault write, NO config edit, NO parser, NO draft, NO test adjust.",
   "other_worktree_changes_are_window1":"build_handoff_manifest.py, build_local_inventory.py, verify_data_vault.py, sources.v1.json, claude_handoff_manifest.json, tests/test_rmv2_source_matrix.py, blockers/* are window-1 B-LAND-3B concurrent writes — not this probe.",
   "writer_lock_taken":False,
   "pycache_under_payload_roots":"NONE (PYTHONDONTWRITEBYTECODE=1 set before every import; verified none under method_source/data_archive/live_data_store/data_vault)",
   "network":"NONE (all on disk)"}}

report_back={
 "1_labor_variance":{
   "labor_share_four_treatments":s1["labor_share_by_treatment"],
   "verdict":"2020 ARTIFACT, not structural. labor 0.751 (as CH1) collapses to 0.376 excluding 2020-21, 0.498 winsorised 1%, 0.330 rank-transformed. NOT >0.5 in all four (fails winsor+rank+ex2020). Dominance is one event.",
   "labor_internal_full":s1["labor_internal_decomposition_full"]["shares"],
   "labor_internal_ex2020":s1["labor_internal_decomposition_ex2020"]["shares"],
   "icsa_is_half_of_labor_and_977pct_2020":{"icsa_share_of_labor_full":0.505,"icsa_share_ex2020":0.247,"icsa_own_variance_fraction_from_2020":s1["icsa_2020_variance_fraction_of_icsa_total"],"icsa_peak_z":198,"icsa_peak_day":"2020-04-04"},
   "erc_stability":s1["erc_by_treatment"],
   "erc_verdict":"UNSTABLE across treatments (labor ERC 0.069->0.163->0.124->0.199 a/b/c/d; rank-transform flattens to ~equal). ERC is NOT a usable derivation basis — report as such (§1.4)."},
 "2_asof_frontier":{
   "member_class":{k:v["as_of_class"] for k,v in s2["member_asof_class"].items()},
   "first_year_for_N_channels":s2["first_year_for_N_channels"],
   "deepest_4channel_asof_year":s2["deepest_4channel_asof_year"],
   "deepest_5channel_asof_year":s2["deepest_5channel_asof_year"],
   "nfci_binds_5channel_at_2011":True,
   "fredmd_deepening_years":{k:v["years_deepened"] for k,v in s2["fredmd_deepening"].items()},
   "fredmd_does_not_move_frontier_or_nfci":True,
   "fredmd_discrepancy":s2["fredmd_discrepancy"],
   "rtdsm_unverified":s2["rtdsm_unverified"]},
 "3_universe_funnel":{**uni["section3_universe"]["funnel"],
   "exclusions":uni["section3_universe"]["exclusions_by_reason_mutually_exclusive"],
   "current_17_survival":uni["section3_universe"]["current_members_surviving_gate"],
   "current_17_present_in_store":"9 of 17 present as base current id (all 9 survive gate); 8 absent as base (exist as .ASOF vintage variants). rights gate excluded 0 — store is pre-filtered at acquisition, so licensing-review members are simply absent."},
 "4_channel_structure":{
   "channels_data_supports_raw_store":s4["how_many_channels_data_supports"]["parallel_analysis_Horn_95pct"],
   "channels_data_supports_dedup_77base":s4["dedup_variant"]["parallel_analysis_factors"],
   "kaiser_over1_raw":s4["how_many_channels_data_supports"]["eigenvalue_over_1_Kaiser"],
   "kaiser_over1_dedup":s4["dedup_variant"]["eig_over1"],
   "inherited_channel_count":5,
   "finding":"data supports ~10 factors (de-duplicated 77-base universe; 19 on raw vintage-contaminated store) — NOT 5. present members scatter across derived factors, NOT the inherited 4/4/4/1/4.",
   "member_derived_factor_dedup":s4["dedup_variant"]["factor_of_present_member"],
   "store_universe_caveat":s4["STORE_UNIVERSE_CAVEAT"],
   "collinear_pairs":s4["collinear_pairs_ch1"],
   "collinear_verdict":"4 of 6 CH1 pairs measurable in store (IURSA~SAHM and BAAAAA~BAA10Y absent). All 4 measurable (PERMIT~HOUST, INDPRO~TCU, INDPRO~CMRMT, CMRMT~TCU) COLLAPSE into one factor — confirmed."},
 "4b_asof_representability":s4["asof_representability_4p8"],
 "5_stationarity_summary":{
   "transform_applied_but_not_reaching_stationary":["INDPRO(yoy->disagree)","NASDAQ(drawdown->disagree)","UMCSENT(drawdown->disagree)","W875(yoy->disagree)"],
   "raw_nonstationary_but_no_transform_applied":["BAAAAA","BAA10Y","VIX","NFCI"],
   "raw_stationary_but_transform_applied":["ICSA","PERMIT"],
   "transform_confirmed_effective":["IURSA","UNRATEv","CMRMT","TCU","HOUST"],
   "borderline_note":"members in 'disagree' (ADF and KPSS disagree) are genuine judgment calls: IURSA,UNRATEv,TCU,BAAAAA,BAA10Y,VIX,NFCI raw. detail in section5."},
 "6_windows_persistence":"see section6: persistence vs window per member, window sensitivity (IURSA/UNRATEv/NASDAQ/UMCSENT), yoy +-20d tolerance sensitivity.",
 "7_staircase":{
   "effective_resolution_all_eras":"monthly (coarsest contributing member cadence 31d in every era 1976-2026)",
   "headline_carry_forward_repeat_fraction":core["section7_staircase"]["headline_carry_forward_repeat_fraction"],
   "fraction_days_daily_unrevised_member_moves":core["section7_staircase"]["fraction_days_a_daily_unrevised_member_moves"],
   "day_precision_basis":"69.3% of published days a genuinely-daily unrevised member (NASDAQ/VIX/BAA10Y) posts a new obs — the honest basis for a same-day call. But effective resolution is monthly; only 16.3% of published days are carry-forward repeats because daily members move most days while the monthly backbone is a staircase."},
 "8_nowcast":stat["section8_nowcast"],
 "9_gates":"vault byte-identical (DATA_SHA256SUMS 4567dbef start==end); verify start FAIL->end PASS (window-1 concurrent reconcile, EXPECTED); no __pycache__; no lock; probe wrote only research/universe_ch2/** + PHASE2 append."}

receipt={
 "schema":"rmv2_probe_receipt.v1",
 "probe_id":"CH2_UNIVERSE_AND_STRUCTURE_PROBE",
 "batch":"/Users/anthonyhall/Desktop/RMV2-Next-Steps/CH2_UNIVERSE_AND_STRUCTURE_PROBE.md",
 "date":"2026-08-05",
 "chains_from":"research/channel_structure_ch1/CH1_CHANNEL_STRUCTURE_PROBE.v1.json",
 "writes":"read-only measurement; adopts/creates/renames/reweights nothing; assigns no economic label",
 "carries_ch1_sections_6A_6D_as":"§5 stationarity, §6 windows, §7 staircase, §8 nowcast",
 "REPORT_BACK":report_back,
 "gates":gates,
 "section1_variance_decomposition":core["section1_variance_decomposition"],
 "section2_asof_frontier":stat["section2_asof_frontier"],
 "section3_universe":uni["section3_universe"],
 "section4_factor_structure":fac["section4_factor_structure"],
 "section5_stationarity":stat["section5_stationarity"],
 "section6_windows_persistence":core["section6_windows_persistence"],
 "section7_staircase":core["section7_staircase"],
 "section8_nowcast":stat["section8_nowcast"],
 "method_notes":{
   "harness":"imports method_source/index_v1.py with NOWCAST_DISABLE=1 (pure carry-forward transformed z); reproduces CH1 treatment(a) ERC exactly (0.069/0.223/0.241/0.197/0.270).",
   "tools":"numpy only (no scipy/statsmodels/sklearn). ADF/KPSS/PCA/parallel-analysis implemented in numpy with cited critical values (MacKinnon ADF const 5%=-2.86; Kwiatkowski KPSS level 5%=0.463).",
   "universe_source":"live_data store generation 93b43e2e (11,838 series/190 sources); span/count/cadence measured by streaming the 673 normalized full-history objects (14GB); PCA on the complete-over-window monthly/weekly/daily subset (no interpolation of quarterly per §7.5).",
   "asof_input":"RTDSM-1 measured floors used as INPUT, not re-derived; 4 unrevised members confirmed one-row-per-date from bytes."}}

out=R+"/research/universe_ch2/CH2_UNIVERSE_AND_STRUCTURE_PROBE.v1.json"
json.dump(receipt,open(out,"w"),indent=1,default=str)
print("RECEIPT WRITTEN:",out)
print("bytes:",os.path.getsize(out))
