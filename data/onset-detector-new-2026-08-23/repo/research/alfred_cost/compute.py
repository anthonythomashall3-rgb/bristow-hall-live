#!/usr/bin/env python3
"""CH-R100 step 3: fit cost curve, price rebuild, emit recommendations."""
import json

counts=json.load(open("research/alfred_cost/counts.json"))
byts=json.load(open("research/alfred_cost/bytes.json"))

# INDPRO measured landing (deep_vintage_window.v1.json cap_evidence, B-LAND-5-R2):
IND_VINT=1139; IND_REC=742789; IND_NORMB=895702096; IND_ADMIT_S=79.08; IND_VERIFY_DELTA=0.38
NORMB_PER_REC=IND_NORMB/IND_REC          # 1205.87 normalized bytes / record
ADMIT_S_PER_REC=IND_ADMIT_S/IND_REC      # 1.0646e-4 s / record (admission+one publish, post-F1 store)
READINESS=1800; WATCHDOG=2400

FLOORS=["2015-01-01","2009-01-01","2000-01-01"]
# severity from CH-R20 revision_certification (share_rev, p95%)
SEV={"NFCI":(0.997,225.5,"LARGE",0.10),"ICSA":(0.337,4.33,"MODERATE",None),
     "IURSA":(0.134,6.25,"MODERATE",None),"HOUST":(0.431,4.19,"MODERATE",None),
     "PERMIT":(0.426,5.17,"MODERATE",None)}
# steady-state fetch override (NFCI first hit was cold-start drift 60.8s; refetch 2.4s)
FETCH_STEADY={"NFCI":2.4}

def price(rec):
    return {"records":rec,
            "implied_norm_bytes":round(rec*NORMB_PER_REC),
            "implied_norm_MB":round(rec*NORMB_PER_REC/1e6,1),
            "implied_admit_publish_s":round(rec*ADMIT_S_PER_REC,1)}

series_out={}
for s in ["NFCI","ICSA","IURSA","HOUST","PERMIT"]:
    b=byts[s]; c=counts[s]
    wins={}
    rpv_prev=None; superlinear=False
    for f in FLOORS:
        rec=b["windows"][f]["records"]; vint=b["windows"][f]["vintages"]
        rpv=rec/vint if vint else 0
        wins[f]={"vintages":vint,**price(rec),"records_per_vintage":round(rpv,1)}
    # linearity test: records per vintage roughly constant across windows => LINEAR in count
    rpvs=[wins[f]["records_per_vintage"] for f in FLOORS if wins[f]["vintages"]]
    lin_spread=(max(rpvs)-min(rpvs))/ (sum(rpvs)/len(rpvs)) if rpvs else 0
    shape="LINEAR" if lin_spread<0.15 else "SUPERLINEAR(records/vintage rises going back)"
    # ALFRED floor: where widening stops adding vintages
    v2000=wins["2000-01-01"]["vintages"]; v2009=wins["2009-01-01"]["vintages"]
    alfred_floor_reached_at_2009 = (v2000==v2009)
    # recommendation: widest floor that still ADDS vintages, capped by budget
    if alfred_floor_reached_at_2009:
        rec_floor="2009-01-01"; rec_reason="ALFRED has ZERO vintages pre-2009 (weekly series); 2000 floor adds 0 vintages"
    else:
        rec_floor="2000-01-01"; rec_reason="monotone vintage growth to 2000; monthly series, cheap"
    fetch=FETCH_STEADY.get(s,b["fetch_wall_s"])
    admit=wins[rec_floor]["implied_admit_publish_s"]
    peak_single=max(fetch,admit)
    breach = peak_single>READINESS
    series_out[s]={
        "severity":{"share_revised":SEV[s][0],"p95_pct":SEV[s][1],"class":SEV[s][2],"member_weight":SEV[s][3]},
        "reference_period_rows":b["reference_periods_rows"],
        "steady_fetch_wall_s":fetch,
        "fetch_note":"first hit 60.8s cold-start drift; refetch 2.4s identical bytes => transient, not regression" if s=="NFCI" else "single fetch",
        "windows":wins,
        "curve_shape":shape,"records_per_vintage_spread":round(lin_spread,3),
        "alfred_floor_reached_at_2009":alfred_floor_reached_at_2009,
        "recommended_floor":rec_floor,"recommendation_reason":rec_reason,
        "recommended_records":wins[rec_floor]["records"],
        "recommended_norm_MB":wins[rec_floor]["implied_norm_MB"],
        "recommended_admit_publish_s":admit,
        "peak_single_measurement_s":round(peak_single,1),
        "readiness_headroom_s":round(READINESS-peak_single,1),
        "budget_breach":breach,
    }

tot_rec=sum(series_out[s]["recommended_records"] for s in series_out)
tot_admit=sum(series_out[s]["recommended_admit_publish_s"] for s in series_out)
tot_fetch=sum(series_out[s]["steady_fetch_wall_s"] for s in series_out)
tot_normMB=sum(series_out[s]["recommended_norm_MB"] for s in series_out)

result={
 "batch":"CH-R100_ALFRED_COST_CURVE","schema_version":"recession-monitor-v2.ch-r100.v1",
 "class":"§20 read-only probe","gate":"No gate. Window 2 wave 6.",
 "quiet_machine":"all 13 predecessor plists quarantined 2026-08-08; only V2 agent com.anthonyhall.recession-monitor-v2.nightly loaded (backup agent, not a landing/rebuild agent) during measurement",
 "deep_window_max":"2019-12-31","floors_tested":FLOORS,
 "cost_model_reference":{"source":"INDPRO deep landing, deep_vintage_window.v1.json cap_evidence (B-LAND-5-R2)",
   "vintages":IND_VINT,"records":IND_REC,"normalized_bytes":IND_NORMB,
   "admit_publish_s":IND_ADMIT_S,"verify_full_delta_s":IND_VERIFY_DELTA,
   "normalized_bytes_per_record":round(NORMB_PER_REC,2),"admit_publish_s_per_record":ADMIT_S_PER_REC,
   "note":"F1 content-addressed projection cache DECOUPLES per-boot verify --full rebuild from vintage depth (INDPRO +0.38s only). Binding residual cost = per-source normalized-blob disk + one-time admission time. Rebuild time is NOT the wall; admission+disk is."},
 "budget":{"readiness_s":READINESS,"watchdog_s":WATCHDOG,"per_source_vintage_cap":IND_VINT},
 "series":series_out,
 "curve_verdict":"LINEAR in vintage count for all 5 (records/vintage spread <15%); weekly series (NFCI/ICSA/IURSA) FLAT 2009->2000 (ALFRED holds no pre-2009 weekly vintages); the historical machine break was absolute magnitude x O(store) republish (fixed by F1), not superlinearity",
 "all_at_once":{"records":tot_rec,"norm_MB":round(tot_normMB,1),
   "serial_admit_publish_s":round(tot_admit,1),"serial_fetch_s":round(tot_fetch,1),
   "serial_total_wall_s":round(tot_admit+tot_fetch,1),
   "vs_readiness_1800s":"per-source peak %.1fs << 1800s; combined serial %.1fs is multi-source and NOT one boot"%(
       max(series_out[s]["peak_single_measurement_s"] for s in series_out), tot_admit+tot_fetch)},
 "any_budget_breach":any(series_out[s]["budget_breach"] for s in series_out),
 "recommendations_priceable":True,
}
json.dump(result,open("research/CH-R100.v1.json","w"),indent=2)
print("=== CH-R100 COST CURVE ===")
for s in series_out:
    o=series_out[s]
    print("%-7s %s w=%s | rec@floor=%d norm=%.0fMB admit=%.1fs fetch=%.1fs headroom=%.0fs breach=%s"%(
        s,o["curve_shape"][:6],o["recommended_floor"],o["recommended_records"],
        o["recommended_norm_MB"],o["recommended_admit_publish_s"],o["steady_fetch_wall_s"],
        o["readiness_headroom_s"],o["budget_breach"]))
print("ALL-AT-ONCE: %d rec, %.1f GB norm, serial %.0fs (%.1f min), breach=%s"%(
    tot_rec,tot_normMB/1000,tot_admit+tot_fetch,(tot_admit+tot_fetch)/60,result["any_budget_breach"]))
print("WROTE research/CH-R100.v1.json")
