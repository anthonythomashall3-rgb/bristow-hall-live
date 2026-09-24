"""CH-R69 classification: judge the 184 candidates into inline scientific
constants vs excluded-on-inspection. Emits research/inline_parameter_census_v1.{csv,json}.

EXCLUSION RULE (mechanical stage, applied first in _ch_r69_scan split):
  E1 array-index / slice bound          E2 identity/init/step {0,1,-1} not in a Compare
  E3 epsilon/regularizer |v|<=1e-4
EXCLUSION RULE (inspection stage, applied here) — a candidate is NOT a scientific
constant if it is:
  I1 date/calendar arithmetic (12 months/yr, %12, 365/365.25/366 day-count, mid-month day)
  I2 unit/format conversion (*100 pct, /30.44 or /30 days-per-month, 1<<20 byte chunk, 4*1024*1024)
  I3 display rounding precision (round(x, k))
  I4 pure math identity in a stat formula (**.5 sqrt, **2 variance, n(n+1)/2 rank sum, //2 split)
  I5 min-class / degenerate-guard count (len(unique)<2, ndim!=2)
  I6 HTTP status / IO literal (404, indent=2)
Everything surviving both stages is an inline SCIENTIFIC constant. Every one is
undeclared by construction (the registry + guard see MODULE-LEVEL names only), so
M(undeclared)=N. `dup_declared` marks the value that also exists as a module const
elsewhere (the number is documented, just not at this inline site).
`ncopy` = how many build modules re-declare this same inline constant.
"""
import json, csv
from pathlib import Path

# (basename, line, value) -> dict(name, controls, prov, conf, ruled, dup_declared, ncopy, influence)
# influence: HIGH/MED/LOW  ruled: S1/S6/S7/'' (owner already ruled)
SCI = {
 # ---- alfred_replay.py ----
 ("alfred_replay.py",116,365):dict(name="yoy_horizon_days",controls="year-over-year growth lookback horizon (days)",prov="chosen",conf=0.8,ruled="",dup="",ncopy=4,infl="HIGH"),
 ("alfred_replay.py",117,20):dict(name="yoy_match_tol_days",controls="±tolerance matching the prior-year observation (days)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=3,infl="MED"),
 ("alfred_replay.py",131,370):dict(name="drawdown_window_days",controls="trailing-max window for drawdown (days)",prov="chosen",conf=0.85,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("alfred_replay.py",132,370):dict(name="rise_floor_window_days",controls="rise-from-floor lookback window (days) — DEFAULT for all channels",prov="chosen",conf=0.9,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("alfred_replay.py",146,4.0):dict(name="compress_knee",controls="soft-compression knee C: values above C are damped",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("alfred_replay.py",147,0.25):dict(name="compress_exponent",controls="soft-compression tail exponent ((v-C)**0.25)",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("alfred_replay.py",153,120):dict(name="unratev_window_days",controls="UNRATEv rise-floor window (days) — the ~3-4mo labor trigger",prov="chosen",conf=0.9,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("alfred_replay.py",165,24):dict(name="min_base_obs",controls="minimum baseline length before standardizing a member",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="LOW"),
 ("alfred_replay.py",189,21):dict(name="burden_roll_obs",controls="rolling-window length for burden accumulation (obs)",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="MED"),
 ("alfred_replay.py",194,365):dict(name="energy_roll_days",controls="1-yr rolling window for energy accumulation (days)",prov="chosen",conf=0.65,ruled="",dup="",ncopy=1,infl="MED"),
 # ---- census_build.py ----
 ("census_build.py",35,4.0):dict(name="compress_knee",controls="soft-compression knee C",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("census_build.py",36,0.25):dict(name="compress_exponent",controls="soft-compression tail exponent",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("census_build.py",74,5):dict(name="n_damage_categories",controls="number of damage categories (1+len(CAT_FLOORS))",prov="derived",conf=0.7,ruled="",dup="CAT_FLOORS",ncopy=1,infl="MED"),
 ("census_build.py",122,2):dict(name="damage_rise_exponent",controls="rise exponent in geometric damage Dg=(rise^2*burden)^(1/3)",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("census_build.py",122,3):dict(name="damage_geom_root",controls="cube-root aggregation exponent for damage Dg",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("census_build.py",124,366):dict(name="lead_assoc_window_days",controls="max lead from peak to recession start to associate an event (days)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("census_build.py",125,730):dict(name="echo_after_window_days",controls="post-recession echo suppression window (days)",prov="chosen",conf=0.75,ruled="",dup="TAIL_PAD",ncopy=1,infl="MED"),
 ("census_build.py",135,400):dict(name="pre_peak_lookback_days",controls="pre-peak segment-stats lookback (days)",prov="chosen",conf=0.65,ruled="",dup="",ncopy=1,infl="MED"),
 # ---- energy_build.py ----
 ("energy_build.py",52,4.0):dict(name="compress_knee",controls="soft-compression knee C",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("energy_build.py",53,0.25):dict(name="compress_exponent",controls="soft-compression tail exponent",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 # ---- forecaster/backtest.py ----
 ("backtest.py",35,21):dict(name="cv_embargo",controls="purge/embargo gap between train and test (units of index)",prov="chosen",conf=0.75,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",49,4):dict(name="inner_cv_folds",controls="expanding inner CV fold count",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",79,2.0):dict(name="synth_pos_weight",controls="synthetic walk-forward positive-class weight",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",117,0.1):dict(name="l2_grid_lo",controls="L2 hyperparameter grid low",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",117,10.0):dict(name="l2_grid_hi",controls="L2 hyperparameter grid high",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",118,2.0):dict(name="posw_grid_mid",controls="positive-weight grid mid",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",118,5.0):dict(name="posw_grid_hi",controls="positive-weight grid high",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",153,0.25):dict(name="naive_prevalence_wt",controls="naive fallback predictor: prevalence blend weight",prov="chosen",conf=0.75,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",153,0.75):dict(name="naive_lastlabel_wt",controls="naive fallback predictor: last-label blend weight",prov="chosen",conf=0.75,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",167,24):dict(name="min_inner_train",controls="floor on inner-CV training length (months)",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="LOW"),
 ("backtest.py",167,0.55):dict(name="inner_train_frac",controls="inner-CV minimum-train fraction of series",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",186,0.1):dict(name="thr_grid",controls="decision-threshold grid (0.1..0.5) for family selection",prov="chosen",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",190,40):dict(name="min_fit_obs",controls="minimum rows to fit a family bundle",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="LOW"),
 ("backtest.py",206,20):dict(name="min_inner_obs",controls="minimum inner-prediction rows to calibrate",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="LOW"),
 ("backtest.py",266,15):dict(name="min_training_years",controls="minimum training span before an outer fold scores (years)",prov="chosen",conf=0.75,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",267,3):dict(name="min_training_episodes",controls="minimum recession episodes in training",prov="chosen",conf=0.75,ruled="",dup="",ncopy=1,infl="MED"),
 ("backtest.py",268,3):dict(name="refit_months",controls="outer walk-forward refit cadence (months)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 # ---- forecaster/features.py ----
 ("features.py",58,21):dict(name="release_day_of_month",controls="assumed monthly issue day for feature timing",prov="chosen",conf=0.65,ruled="",dup="",ncopy=1,infl="LOW"),
 ("features.py",139,45):dict(name="stale_tol_icsa",controls="max staleness for ICSA before a feature is dropped (days)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("features.py",139,62):dict(name="stale_tol_other",controls="max staleness for non-ICSA series (days)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 # ---- forecaster/models.py ----
 ("models.py",51,80):dict(name="logistic_iterations",controls="Newton/IRLS iteration count for logistic fit",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("models.py",67,0.5):dict(name="label_binarize_thr",controls="target>0.5 → positive-class sample weighting cut",prov="chosen",conf=0.55,ruled="",dup="",ncopy=1,infl="LOW"),
 ("models.py",107,0.1):dict(name="fit_default_l2",controls="default L2 penalty in fit()",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 # ---- forecaster_site.py ----
 ("forecaster_site.py",174,11):dict(name="e12_sum_window",controls="12-month trailing-sum window (i-11:i+1) for E12 series",prov="chosen",conf=0.75,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",186,3):dict(name="floor_rising_lookback_m",controls="months back used to test the floor is rising",prov="chosen",conf=0.7,ruled="",dup="",ncopy=2,infl="MED"),
 ("forecaster_site.py",445,0.2278):dict(name="pub_ece",controls="HARDCODED published calibration ECE (publication_aware)",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",445,0.61):dict(name="pub_mce",controls="HARDCODED published MCE",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",446,0.383):dict(name="pub_mean_p",controls="HARDCODED published mean probability",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",446,0.155):dict(name="pub_base_rate",controls="HARDCODED published base rate",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",447,0.1192):dict(name="rt_ece",controls="HARDCODED realtime_strict ECE",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",453,0.8856):dict(name="rt_displayed_auc",controls="HARDCODED realtime displayed AUC",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",453,0.9075):dict(name="rt_leg_auc",controls="HARDCODED realtime legacy AUC",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",454,3.103):dict(name="rt_fa_per_decade",controls="HARDCODED realtime false-alarm clusters/decade",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",455,2.328):dict(name="rt_leg_fa_per_decade",controls="HARDCODED realtime legacy FA clusters/decade",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",456,0.9523):dict(name="pub_displayed_auc",controls="HARDCODED publication_aware displayed AUC",prov="calibrated",conf=0.9,ruled="",dup="REGISTERED",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",456,0.9544):dict(name="pub_leg_auc",controls="HARDCODED publication_aware legacy AUC (=REGISTERED.auc)",prov="calibrated",conf=0.95,ruled="",dup="REGISTERED",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",457,2.586):dict(name="pub_fa_per_decade",controls="HARDCODED publication FA clusters/decade",prov="calibrated",conf=0.9,ruled="",dup="",ncopy=1,infl="HIGH"),
 ("forecaster_site.py",470,0.915):dict(name="ci_pub_lo",controls="HARDCODED AUC CI low (publication_aware)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",470,0.984):dict(name="ci_pub_hi",controls="HARDCODED AUC CI high (publication_aware)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",471,0.822):dict(name="ci_rt_lo",controls="HARDCODED AUC CI low (realtime_strict)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",471,0.967):dict(name="ci_rt_hi",controls="HARDCODED AUC CI high (realtime_strict)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",472,0.762):dict(name="ci_nber_lo",controls="HARDCODED AUC CI low (nber_target)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",472,0.976):dict(name="ci_nber_hi",controls="HARDCODED AUC CI high (nber_target)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",473,0.0196):dict(name="brier_skill",controls="HARDCODED brier skill score (displayed, publication_aware)",prov="calibrated",conf=0.85,ruled="",dup="",ncopy=1,infl="MED"),
 ("forecaster_site.py",506,5):dict(name="ensemble_size_check",controls="expected ensemble member count (==5, ties to MEMBERS)",prov="derived",conf=0.7,ruled="",dup="MEMBERS",ncopy=1,infl="LOW"),
 ("forecaster_site.py",516,500):dict(name="min_history_len",controls="minimum output history length before publishing",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="LOW"),
 # ---- index_v1.py ----
 ("index_v1.py",60,365):dict(name="yoy_horizon_days",controls="YoY growth lookback horizon (days)",prov="chosen",conf=0.8,ruled="",dup="",ncopy=4,infl="HIGH"),
 ("index_v1.py",62,20):dict(name="yoy_match_tol_days",controls="±tolerance matching prior-year obs (days)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=3,infl="MED"),
 ("index_v1.py",85,370):dict(name="drawdown_window_days",controls="trailing-max drawdown window (days)",prov="chosen",conf=0.85,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("index_v1.py",88,370):dict(name="rise_floor_window_days",controls="rise-from-floor default window (days)",prov="chosen",conf=0.9,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 # ---- nowcast_live.py ----
 ("nowcast_live.py",68,365):dict(name="yoy_horizon_days",controls="YoY growth lookback horizon (days)",prov="chosen",conf=0.8,ruled="",dup="",ncopy=4,infl="HIGH"),
 ("nowcast_live.py",70,20):dict(name="yoy_match_tol_days",controls="±tolerance matching prior-year obs (days)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=3,infl="MED"),
 ("nowcast_live.py",88,370):dict(name="drawdown_window_days",controls="trailing-max drawdown window (days)",prov="chosen",conf=0.85,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("nowcast_live.py",91,370):dict(name="rise_floor_window_days",controls="rise-from-floor default window (days)",prov="chosen",conf=0.9,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("nowcast_live.py",98,2):dict(name="sahm_ma_window",controls="SAHM 3-month moving-average span (range i-2..i)",prov="chosen",conf=0.7,ruled="",dup="",ncopy=1,infl="MED"),
 ("nowcast_live.py",100,370):dict(name="sahm_rise_window",controls="SAHM rise-floor window (days)",prov="chosen",conf=0.85,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("nowcast_live.py",106,20):dict(name="asof_match_tol_days",controls="±tolerance for as-of value lookup (days)",prov="chosen",conf=0.6,ruled="",dup="",ncopy=1,infl="LOW"),
 ("nowcast_live.py",172,15):dict(name="nasdaq_target_day",controls="mid-month target day for NASDAQ drawdown read",prov="chosen",conf=0.55,ruled="",dup="",ncopy=1,infl="LOW"),
 ("nowcast_live.py",212,120):dict(name="unratev_window_days",controls="UNRATEv rise-floor window (days)",prov="chosen",conf=0.9,ruled="S6",dup="",ncopy=6,infl="HIGH"),
 ("nowcast_live.py",221,5):dict(name="min_spread_days",controls="min observations for BAA-AAA spread z",prov="chosen",conf=0.55,ruled="",dup="",ncopy=1,infl="LOW"),
 # ---- watch_build.py ----
 ("watch_build.py",79,4.0):dict(name="compress_knee",controls="soft-compression knee C",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("watch_build.py",80,0.25):dict(name="compress_exponent",controls="soft-compression tail exponent",prov="chosen",conf=0.85,ruled="",dup="",ncopy=6,infl="HIGH"),
 ("watch_build.py",144,30):dict(name="gate30_days",controls="30-day pace-gate horizon",prov="chosen",conf=0.7,ruled="",dup="G30",ncopy=1,infl="MED"),
 ("watch_build.py",145,60):dict(name="gate60_days",controls="60-day pace-gate horizon",prov="chosen",conf=0.7,ruled="",dup="G60",ncopy=1,infl="MED"),
 ("watch_build.py",146,90):dict(name="gate90_days",controls="90-day pace-gate horizon",prov="chosen",conf=0.7,ruled="",dup="G90",ncopy=1,infl="MED"),
 ("watch_build.py",213,31):dict(name="run_merge_gap_monthly",controls="max gap to merge adjacent runs, monthly (days)",prov="chosen",conf=0.65,ruled="",dup="",ncopy=1,infl="MED"),
 ("watch_build.py",213,46):dict(name="run_merge_gap_daily",controls="max gap to merge adjacent runs, daily (days)",prov="chosen",conf=0.65,ruled="",dup="",ncopy=1,infl="MED"),
 ("watch_build.py",362,548):dict(name="yc_inversion_lookback_days",controls="yield-curve inversion lookback (~18mo, days)",prov="chosen",conf=0.8,ruled="",dup="",ncopy=1,infl="MED"),
}

cand = json.load(open("research/_ch_r69_cand.json"))
census=[]; excl_inspect=[]
for r in cand:
    key=(r["file"].split("/")[-1], r["line"], r["value"])
    if key in SCI:
        m=SCI[key]
        census.append({**r,**m})
    else:
        excl_inspect.append(r)

# emit
cols=["file","line","func","value","name","controls","prov","conf","ruled","dup","ncopy","infl","src"]
with open("research/inline_parameter_census_v1.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader()
    for r in sorted(census,key=lambda r:({"HIGH":0,"MED":1,"LOW":2}[r["infl"]],r["file"],r["line"])):
        w.writerow(r)

N=len(census); M=sum(1 for r in census if True)  # all inline are guard-invisible
ruled=[r for r in census if r["ruled"]]
by_infl={k:sum(1 for r in census if r["infl"]==k) for k in ("HIGH","MED","LOW")}
summary={
  "batch":"CH-R69_INLINE_PARAMETER_CENSUS",
  "science_files_scanned":11,
  "raw_numeric_literals":595,
  "excluded_mechanical":411,
  "candidates":184,
  "excluded_on_inspection":len(excl_inspect),
  "N_inline_scientific_constants":N,
  "M_undeclared_by_guard":M,
  "note_M_equals_N":"every inline literal is invisible to bh/params.py, which scans module-level names only; M=N by construction",
  "by_influence":by_infl,
  "owner_ruled_sites":len(ruled),
  "distinct_dup_declared":sorted({r["dup"] for r in census if r["dup"]}),
  "ncopy_max":max(r["ncopy"] for r in census),
  "hardcoded_published_metrics":sum(1 for r in census if "HARDCODED" in r["controls"]),
  "exclusion_rule":"E1 index/slice; E2 identity {0,1,-1} not-in-Compare; E3 |v|<=1e-4 epsilon; I1 date/calendar; I2 unit/format; I3 round precision; I4 stat-formula math identity; I5 degenerate-class guard; I6 HTTP/IO literal",
  "census":sorted(census,key=lambda r:({"HIGH":0,"MED":1,"LOW":2}[r["infl"]],r["file"],r["line"])),
  "excluded_on_inspection_rows":excl_inspect,
}
json.dump(summary,open("research/inline_parameter_census_v1.json","w"),indent=1)
print(f"N inline scientific constants = {N}, of which M undeclared = {M}")
print("by influence:",by_infl)
print("owner-ruled sites:",len(ruled),"| hardcoded published metrics:",summary["hardcoded_published_metrics"])
print("excluded on inspection:",len(excl_inspect),"| dup-declared values:",summary["distinct_dup_declared"])
print("max inline copies of one constant:",summary["ncopy_max"])
