import os, time, json, urllib.request
ENV = os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
KEY = None
for ln in open(ENV):
    if "FRED" in ln.upper() and "=" in ln:
        KEY = ln.split("=",1)[1].strip().strip('"').strip("'")
assert KEY
OUT = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl")
CC = dict(AUS="AU", CAN="CA", DEU="DE", ESP="ES", FRA="FR", GBR="GB", ITA="IT",
          JPN="JP", KOR="KR", MEX="MX", NOR="NO", NZL="NZ", SWE="SE", CHE="CH",
          DNK="DK", FIN="FI", AUT="AT", BEL="BE", NLD="NL", PRT="PT", GRC="GR",
          IRL="IE", POL="PL", HUN="HU", CZE="CZ", TUR="TR", ZAF="ZA", CHL="CL",
          ISR="IL", USA="US")
EU = dict(DEU="DE", ESP="ES", FRA="FR", ITA="IT", NLD="NL", BEL="BE", AUT="AT",
          PRT="PT", GRC="EL", IRL="IE", FIN="FI", DNK="DK", SWE="SE", POL="PL",
          HUN="HU", CZE="CZ", NOR="NO", CHE="CH", GBR="UK")
want = []
for iso, cc in CC.items():
    want.append("NAEXKP01%sQ652S" % cc)      # real GDP, sa, national currency
    want.append("NAEXKP01%sQ657S" % cc)      # real GDP growth rate q/q
    if iso in EU: want.append("CLVMNACSCAB1GQ%s" % EU[iso])
want += ["GDPC1", "JPNRGDPEXP", "NGDPRSAXDCAUQ", "NGDPRSAXDCCAQ", "NGDPRSAXDCMXQ",
         "NGDPRSAXDCKRQ", "NGDPRSAXDCILQ", "NGDPRSAXDCTRQ", "NGDPRSAXDCZAQ",
         "NGDPRSAXDCCLQ", "NGDPRSAXDCNZQ", "NGDPRSAXDCJPQ", "NGDPRSAXDCGBQ"]
want = sorted(set(want))
ok = err = skip = 0
for s in want:
    p = os.path.join(OUT, s + ".csv")
    if os.path.exists(p) and os.path.getsize(p) > 100: skip += 1; continue
    u = ("https://api.stlouisfed.org/fred/series/observations?series_id=" + s +
         "&api_key=" + KEY + "&file_type=json")
    try:
        j = json.load(urllib.request.urlopen(u, timeout=30))
        obs = [(o["date"], o["value"]) for o in j["observations"] if o["value"] != "."]
        if len(obs) < 20: err += 1; time.sleep(0.3); continue
        with open(p, "w") as f:
            f.write("date,value\n")
            for d, v in obs: f.write(d + "," + v + "\n")
        ok += 1
    except Exception: err += 1
    time.sleep(0.4)
print("gdp fetched", ok, "failed", err, "skipped", skip)
