import os, time, json, urllib.request, urllib.parse
ENV = os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
KEY = None
for ln in open(ENV):
    if "FRED" in ln.upper() and "=" in ln:
        KEY = ln.split("=",1)[1].strip().strip('"').strip("'")
assert KEY
OUT = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl")
os.makedirs(OUT, exist_ok=True)

CC = dict(AUS="AU", CAN="CA", DEU="DE", ESP="ES", FRA="FR", GBR="GB", ITA="IT",
          JPN="JP", KOR="KR", MEX="MX", NOR="NO", NZL="NZ", SWE="SE", CHE="CH",
          DNK="DK", FIN="FI", AUT="AT", BEL="BE", NLD="NL", PRT="PT", GRC="GR",
          IRL="IE", POL="PL", HUN="HU", CZE="CZ", TUR="TR", ZAF="ZA", CHL="CL",
          ISR="IL", USA="US", BRA="BR", IND="IN", IDN="ID", RUS="RU", CHN="CN",
          SVK="SK", SVN="SI", EST="EE")

want = []
for iso, cc in CC.items():
    for pat in ["LRHUTTTT{}M156S", "LRUNTTTT{}M156S", "IR3TIB01{}M156N",
                "IRSTCI01{}M156N", "IRLTLT01{}M156N", "{}PROINDMISMEI".format(iso),
                "PRINTO01{}M661S", "LMUNRRTT{}M156S", "LREM64TT{}M156S"]:
        s = pat.format(cc) if "{}" in pat else pat
        want.append(s)
want = sorted(set(want))
print("candidates:", len(want))

ok = err = skip = 0
for s in want:
    p = os.path.join(OUT, s + ".csv")
    if os.path.exists(p) and os.path.getsize(p) > 100:
        skip += 1; continue
    u = ("https://api.stlouisfed.org/fred/series/observations?series_id=" + s +
         "&api_key=" + KEY + "&file_type=json")
    try:
        j = json.load(urllib.request.urlopen(u, timeout=30))
        obs = [(o["date"], o["value"]) for o in j["observations"] if o["value"] != "."]
        if len(obs) < 24: err += 1; time.sleep(0.4); continue
        with open(p, "w") as f:
            f.write("date,value\n")
            for d, v in obs: f.write(d + "," + v + "\n")
        ok += 1
    except Exception:
        err += 1
    time.sleep(0.5)
print("fetched", ok, "missing/failed", err, "already had", skip)
