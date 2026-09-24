import os, sys, time, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
ENV = os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
KEY = None
for ln in open(ENV):
    if "FRED" in ln.upper() and "=" in ln:
        KEY = ln.split("=",1)[1].strip().strip('"').strip("'")
OUT = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl")
os.makedirs(OUT, exist_ok=True)
CC = dict(AUS="AU", CAN="CA", DEU="DE", ESP="ES", FRA="FR", GBR="GB", ITA="IT",
          JPN="JP", KOR="KR", MEX="MX", NOR="NO", NZL="NZ", SWE="SE", CHE="CH",
          DNK="DK", FIN="FI", AUT="AT", BEL="BE", NLD="NL", PRT="PT", GRC="GR",
          IRL="IE", POL="PL", HUN="HU", CZE="CZ", TUR="TR", ZAF="ZA", CHL="CL",
          ISR="IL", USA="US")
EU = dict(DEU="DE", ESP="ES", FRA="FR", ITA="IT", NLD="NL", BEL="BE", AUT="AT",
          PRT="PT", GRC="EL", IRL="IE", FIN="FI", DNK="DK", SWE="SE", POL="PL",
          HUN="HU", CZE="CZ", NOR="NO", CHE="CH", GBR="UK")
pats = ["LFEMTTTT{}M647S","LREM64TT{}M156S","LMUNRRTT{}M156S","LMUNRRTT{}M156N",
        "ODCNPI03{}M657S","ODCNPI03{}M661S","BSCICP02{}M460S","CSCICP02{}M460S",
        "LOLITOAA{}M661S","SPASTT01{}M657N","PRINTO01{}M661S","PRMNTO01{}M661S",
        "NAEXKP01{}Q652S","NAEXKP01{}Q657S","NGDPRSAXDC{}Q","LRHUTTTT{}M156S",
        "LRUNTTTT{}M156S","IR3TIB01{}M156N","IRSTCI01{}M156N","IRLTLT01{}M156N"]
want = [p.format(cc) for cc in CC.values() for p in pats]
want += ["CLVMNACSCAB1GQ" + v for v in EU.values()]
want += [i + "PROINDMISMEI" for i in CC]
want = sorted(set(want))
todo = [s for s in want if not (os.path.exists(os.path.join(OUT, s + ".csv"))
                                and os.path.getsize(os.path.join(OUT, s + ".csv")) > 100)]
DEADLINE = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 140)
def get(s):
    if time.time() > DEADLINE: return None
    u = ("https://api.stlouisfed.org/fred/series/observations?series_id=" + s +
         "&api_key=" + KEY + "&file_type=json")
    try:
        j = json.load(urllib.request.urlopen(u, timeout=15))
        obs = [(o["date"], o["value"]) for o in j["observations"] if o["value"] != "."]
        if len(obs) < 24: return None
        with open(os.path.join(OUT, s + ".csv"), "w") as f:
            f.write("date,value\n")
            for d, v in obs: f.write(d + "," + v + "\n")
        return s
    except Exception: return None
with ThreadPoolExecutor(max_workers=20) as ex:
    got = [r for r in ex.map(get, todo) if r]
print("todo", len(todo), "fetched", len(got), "remaining",
      len([s for s in want if not os.path.exists(os.path.join(OUT, s + ".csv"))]))
