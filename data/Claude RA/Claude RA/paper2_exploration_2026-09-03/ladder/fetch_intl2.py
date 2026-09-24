import os, time, json, urllib.request
ENV = os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
KEY = None
for ln in open(ENV):
    if "FRED" in ln.upper() and "=" in ln:
        KEY = ln.split("=",1)[1].strip().strip('"').strip("'")
OUT = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl")
CC = dict(AUS="AU", CAN="CA", DEU="DE", ESP="ES", FRA="FR", GBR="GB", ITA="IT",
          JPN="JP", KOR="KR", MEX="MX", NOR="NO", NZL="NZ", SWE="SE", CHE="CH",
          DNK="DK", FIN="FI", AUT="AT", BEL="BE", NLD="NL", PRT="PT", GRC="GR",
          IRL="IE", POL="PL", HUN="HU", CZE="CZ", TUR="TR", ZAF="ZA", CHL="CL",
          ISR="IL", USA="US")
pats = ["LFEMTTTT{}M647S", "LFEMTTTT{}M647N", "LREM64TT{}M156S",
        "LMUNRRTT{}M156S", "LMUNRRTT{}M156N", "LMUNRLTT{}M647S",
        "ODCNPI03{}M657S", "ODCNPI03{}M661S", "LORSGPOR{}M156S",
        "SLRTTO01{}M657S", "SLRTCR03{}M657S", "BSCICP02{}M460S",
        "CSCICP02{}M460S", "LOLITOAA{}M661S", "SPASTT01{}M657N"]
want = sorted(set(p.format(cc) for cc in CC.values() for p in pats))
ok = err = skip = 0
for s in want:
    p = os.path.join(OUT, s + ".csv")
    if os.path.exists(p) and os.path.getsize(p) > 100: skip += 1; continue
    u = ("https://api.stlouisfed.org/fred/series/observations?series_id=" + s +
         "&api_key=" + KEY + "&file_type=json")
    try:
        j = json.load(urllib.request.urlopen(u, timeout=25))
        obs = [(o["date"], o["value"]) for o in j["observations"] if o["value"] != "."]
        if len(obs) < 24: err += 1; time.sleep(0.25); continue
        with open(p, "w") as f:
            f.write("date,value\n")
            for d, v in obs: f.write(d + "," + v + "\n")
        ok += 1
    except Exception: err += 1
    time.sleep(0.3)
print("fetched", ok, "failed", err, "skipped", skip)
