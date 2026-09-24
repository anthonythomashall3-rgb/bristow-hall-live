import json, datetime as dt
raw=json.load(open("research/ext1948/raw_floors.json"))
def d(s): return dt.date.fromisoformat(s)
# member -> (channel, weight, underlying series list, transform-lag-days)
# lag: yoy=365 (needs prior-year obs); rise_floor/drawdown/direct=0 (produce from obs1)
CH={"labor":0.30,"realactivity":0.25,"creditequity":0.20,"finconditions":0.10,"housingincome":0.15}
MEM={
 "ICSA":("labor",["ICSA"],365),      # yoy
 "IURSA":("labor",["IURSA"],0),       # rise_floor
 "SAHM":("labor",["SAHMREALTIME"],0), # direct
 "UNRATEv":("labor",["UNRATE"],0),    # rise_floor 120d
 "INDPRO":("realactivity",["INDPRO"],365),
 "CMRMT":("realactivity",["CMRMTSPL"],365),
 "TCU":("realactivity",["TCU"],365),
 "PHILLY":("realactivity",["GACDFSA066MSFRBPHI"],0),
 "NASDAQ":("creditequity",["NASDAQCOM"],0),   # drawdown
 "BAAAAA":("creditequity",["BAA","AAA"],0),    # direct diff
 "BAA10Y":("creditequity",["BAA10Y"],0),
 "VIX":("creditequity",["VIXCLS"],0),
 "NFCI":("finconditions",["NFCI"],0),
 "PERMIT":("housingincome",["PERMIT"],365),
 "HOUST":("housingincome",["HOUST"],365),
 "UMCSENT":("housingincome",["UMCSENT"],0),    # drawdown
 "W875":("housingincome",["W875RX1"],365),
}
def series_floor(s): return d(raw[s]["main"]["min"])
def eff_start(m):
    ch,ser,lag=MEM[m]
    f=max(series_floor(s) for s in ser)  # BAAAAA needs BOTH -> later floor
    return f+dt.timedelta(days=lag), f
anchors=[dt.date(1948,1,1),dt.date(1950,1,1),dt.date(1953,1,1),dt.date(1957,1,1),dt.date(1976,6,1)]
members={}
for m in MEM:
    es,rf=eff_start(m)
    members[m]={"channel":MEM[m][0],"underlying":MEM[m][1],"raw_floor":rf.isoformat(),
                "effective_start":es.isoformat()}
# channel coverage at each anchor
cov={}
for a in anchors:
    chan_present={c:[] for c in CH}
    for m in MEM:
        es=d(members[m]["effective_start"])
        if es<=a: chan_present[members[m]["channel"]].append(m)
    nonempty=[c for c in CH if chan_present[c]]
    share=round(sum(CH[c] for c in nonempty),10)
    cov[a.isoformat()]={
        "channels_nonempty":sorted(nonempty),
        "nonempty_channel_count":len(nonempty),
        "available_channel_weight_raw":share,
        "renormalized_available_weight":round(share/1.0,10),
        "members_available":sorted(m for m in MEM if d(members[m]["effective_start"])<=a),
        "members_per_channel":{c:sorted(chan_present[c]) for c in CH},
    }
# buckets by earliest anchor a member becomes available
def bucket(m):
    es=d(members[m]["effective_start"])
    if es<=dt.date(1948,1,1): return "AVAILABLE_1948"
    if es<=dt.date(1957,1,1): return "PARTIAL_1948_1957"
    if es<=dt.date(1976,6,1): return "PARTIAL_1957_1976"
    return "ABSENT_pre1976"
for m in MEM: members[m]["bucket"]=bucket(m)
out={"members":members,"channel_weights":CH,"anchor_coverage":cov,
     "bytes_source":"data_archive/current_revised_and_spatial/<SID>.csv (model current_revised input)"}
json.dump(out,open("research/ext1948/analysis.json","w"),indent=1)
# print summary
print("MEMBER              CH            RAWFLOOR    EFFSTART    BUCKET")
for m in MEM:
    x=members[m]; print(f"{m:12s} {x['channel']:13s} {x['raw_floor']:11s} {x['effective_start']:11s} {x['bucket']}")
print("\nANCHOR      nCh  share  channels_nonempty")
for a in anchors:
    c=cov[a.isoformat()]; print(f"{a.isoformat()}  {c['nonempty_channel_count']}   {c['available_channel_weight_raw']:.2f}  {c['channels_nonempty']}")
