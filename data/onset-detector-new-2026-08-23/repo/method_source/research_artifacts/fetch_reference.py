#!/usr/bin/env python3
"""fetch_reference.py - Reference Forecasts panel fetch + distill (DISPLAY-only, credited).

Nightly step for refresh.sh (run BEFORE assemble.py):
    python3 fetch_reference.py || echo 'WARN: reference panel refresh failed, keeping cached'

Pulls the four DISPLAY-verdict sources from the 2026-07-18 acquisition report
(research/artifacts/reference_products.md):
  1. Atlanta Fed GDPNow        - FRED fredgraph CSV, no key
  2. Philly Fed ADS index      - direct xlsx, browser UA, stdlib xlsx->CSV
  3. Cleveland Fed infl nowcast- undocumented FusionCharts JSON, Chrome UA, fail-soft
  4. SPF medians (RGDP, UNEMP) - Philly Fed per-variable xlsx (FRED does NOT mirror SPF)
Excluded by verdict: CBO (DataDome bot wall); Fed SEP (optional later card, out of scope).

Fail-soft ladder per source, never fabricates:
  live fetch OK  -> refresh raw/ file -> distill card
  live fetch bad -> distill card from existing raw/ file (last good)
  raw/ also bad  -> carry the card forward from the previous geo/reference.json
  nothing        -> card omitted (front end just renders fewer cards)

Output: geo/reference.json  {"generated": ..., "cards": [...]} - schema per
research/artifacts/reference_panel_spec.md section 2. String fields are
HTML-ready (entity-encoded by this builder); values NEVER enter any model.
No heavy compute: tail-row reads and one division (SPF growth).
"""
import csv, datetime as dt, io, json, os, re, sys, urllib.request, zipfile
import xml.etree.ElementTree as ET

# ---- paths: use the directory of this script if it looks like the repo, else the known root
_here = os.path.dirname(os.path.abspath(__file__))
REPO = _here if os.path.isdir(os.path.join(_here, "geo")) and os.path.isdir(os.path.join(_here, "raw")) \
    else "/Users/anthonyhall/Desktop/RecessionMonitor"
RAW = os.path.join(REPO, "raw")
OUT = os.path.join(REPO, "geo", "reference.json")

CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
MID = "&#183;"     # middle dot
ARR = "&#8594;"    # right arrow

warns = []
def warn(msg):
    warns.append(msg)
    print("WARN:", msg, file=sys.stderr)

def fetch(url, ua=None, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": ua} if ua else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def save_raw(name, data):
    """Atomic write into raw/ (same .new+mv pattern as refresh.sh)."""
    p = os.path.join(RAW, name)
    with open(p + ".new", "wb") as f:
        f.write(data)
    os.replace(p + ".new", p)

def raw_mtime_date(name):
    return dt.date.fromtimestamp(os.path.getmtime(os.path.join(RAW, name))).isoformat()

# ---- stdlib xlsx -> rows (installed openpyxl chokes on these files' doc properties)
def xlsx_rows(data):
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    z = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(ns + "si"):
            shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
    sheet = next(n for n in z.namelist() if re.match(r"xl/worksheets/sheet1?\.xml$", n))
    rows = []
    for row in ET.fromstring(z.read(sheet)).iter(ns + "row"):
        cells = {}
        for c in row.iter(ns + "c"):
            ref = c.get("r", "")
            col = re.match(r"[A-Z]+", ref).group(0)
            idx = 0
            for ch in col:
                idx = idx * 26 + (ord(ch) - 64)
            v = c.find(ns + "v")
            txt = v.text if v is not None else ""
            if c.get("t") == "s" and txt != "":
                txt = shared[int(txt)]
            elif c.get("t") == "inlineStr":
                txt = "".join(t.text or "" for t in c.iter(ns + "t"))
            cells[idx - 1] = txt or ""
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
    return rows

def rows_to_csv(rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue().encode()

def last_data_row(csv_name):
    with open(os.path.join(RAW, csv_name), newline="") as f:
        rows = [r for r in csv.reader(f) if r and r[0].strip()]
    return rows[-1]

def fnum(s):
    return float(str(s).replace(",", ""))  # E-notation strings are float()-parseable

def trim(x, nd):
    """Round to nd decimals, then drop trailing zeros (4.30 -> 4.3, 4.4526 -> 4.45)."""
    s = f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"

# ---------------------------------------------------------------- 1. GDPNow (FRED)
def fetch_gdpnow():
    save_raw("GDPNOW.csv", fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPNOW"))

def card_gdpnow():
    date_s, val_s = last_data_row("GDPNOW.csv")[:2]
    v = fnum(val_s)
    y, m = int(date_s[:4]), int(date_s[5:7])
    q = f"{y}Q{(m - 1) // 3 + 1}"
    return {
        "id": "gdpnow", "label": "GDPNow", "agency": "Atlanta Fed",
        "big": f"{v:+.1f}%",
        "detail": f"{q} {MID} annualized real GDP growth",
        "sub": "The Atlanta Fed&#8217;s running model estimate of current-quarter real GDP growth, updated with each data release.",
        # FRED keeps only the latest estimate per target quarter; as_of = pull date (raw file mtime)
        "as_of": raw_mtime_date("GDPNOW.csv"),
        "stale_after_days": 14,
        "note": "Model runs ~6-8x a month; FRED shows only the latest estimate for the target quarter.",
        "credit": "Federal Reserve Bank of Atlanta, GDPNow, retrieved from FRED",
        "url": "https://fred.stlouisfed.org/series/GDPNOW",
    }

# ---------------------------------------------------------------- 2. ADS (Philly Fed)
def fetch_ads():
    data = fetch("https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/"
                 "ads/ads_index_most_current_vintage.xlsx", ua=CHROME_UA)
    save_raw("ADS_INDEX.csv", rows_to_csv(xlsx_rows(data)))

def card_ads():
    row = last_data_row("ADS_INDEX.csv")
    as_of = row[0].replace(":", "-")           # 2026:07:11 -> 2026-07-11
    v = fnum(row[1])
    return {
        "id": "ads", "label": "ADS Business Conditions", "agency": "Philadelphia Fed",
        "big": f"{v:.2f}",
        "detail": f"daily index {MID} 0 = average conditions",
        "sub": "The Aruoba-Diebold-Scotti index: daily business conditions blended from six indicators; below zero means below-average conditions.",
        "as_of": as_of,
        "stale_after_days": 14,
        # honesty note per the spec: full history re-estimated each vintage
        "note": "The full history is re-estimated with each vintage, so this series is not point-in-time; shown for display only.",
        "credit": "Aruoba-Diebold-Scotti index, FRB Philadelphia",
        "url": "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/ads",
    }

# ------------------------------------------------- 3. Cleveland Fed inflation nowcast
def fetch_cleveland():
    # Undocumented FusionCharts chart feed; Chrome UA required; parse defensively.
    raw = fetch("https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/"
                "nowcast_quarter.json", ua=CHROME_UA)
    charts = json.loads(raw)
    rows = [["quarter", "series", "latest_nowcast", "n_obs", "as_of"]]
    for ch in charts:
        quarter = ch["chart"]["subcaption"]
        as_of = ch["chart"].get("_comment", "")
        for s in ch.get("dataset", []):
            data = [d for d in s.get("data", []) if d.get("value") not in (None, "")]
            if not data:
                continue
            rows.append([quarter, s.get("seriesname", ""), data[-1]["value"], len(data), as_of])
    if len(rows) < 5:
        raise ValueError("Cleveland feed parsed to fewer than 4 series rows; keeping last good")
    save_raw("CLEVELAND_INFLATION_NOWCAST_Q.csv", rows_to_csv(rows))

def card_cleveland():
    with open(os.path.join(RAW, "CLEVELAND_INFLATION_NOWCAST_Q.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    latest_q = rows[-1]["quarter"]                       # file is chronological
    want = ["CPI Inflation", "Core CPI Inflation", "PCE Inflation", "Core PCE Inflation"]
    vals, as_of = {}, ""
    for r in rows:
        if r["quarter"] == latest_q and r["series"] in want:
            vals[r["series"]] = fnum(r["latest_nowcast"])
            as_of = r["as_of"][:10]
    if len(vals) != 4:
        raise ValueError(f"Cleveland latest quarter {latest_q} has {len(vals)}/4 nowcast series")
    q = latest_q.replace(":", "")                        # 2026:Q3 -> 2026Q3
    return {
        "id": "cleveland", "label": "Inflation Nowcast", "agency": "Cleveland Fed",
        "big": f"{trim(vals['PCE Inflation'], 1)}%",
        "detail": (f"{q} {MID} CPI {trim(vals['CPI Inflation'], 1)} {MID} "
                   f"core CPI {trim(vals['Core CPI Inflation'], 1)} {MID} "
                   f"PCE {trim(vals['PCE Inflation'], 1)} {MID} "
                   f"core PCE {trim(vals['Core PCE Inflation'], 1)}"),
        "sub": "The Cleveland Fed&#8217;s daily model nowcast of current-quarter inflation, before the official releases arrive. Headline figure is PCE.",
        "as_of": as_of,
        "stale_after_days": 7,   # spec: 5 business days ~= 7 calendar days
        "note": "Updated each business day from an undocumented chart feed; on outage the last good value stays up with a stale badge.",
        "credit": "Federal Reserve Bank of Cleveland, Inflation Nowcasting",
        "url": "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting",
    }

# ---------------------------------------------------------------- 4. SPF (Philly Fed)
SPF_BASE = ("https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/"
            "survey-of-professional-forecasters/data-files/files/")

def fetch_spf():
    # per-variable files only; the all-variables medianlevel.xlsx URL returns an HTML error page
    for fname, csvname in (("median_rgdp_level.xlsx", "SPF_MEDIAN_RGDP_LEVEL.csv"),
                           ("median_unemp_level.xlsx", "SPF_MEDIAN_UNEMP_LEVEL.csv")):
        save_raw(csvname, rows_to_csv(xlsx_rows(fetch(SPF_BASE + fname, ua=CHROME_UA))))

def card_spf():
    g = last_data_row("SPF_MEDIAN_RGDP_LEVEL.csv")
    u = last_data_row("SPF_MEDIAN_UNEMP_LEVEL.csv")
    year, quarter = int(fnum(g[0])), int(fnum(g[1]))
    if (int(fnum(u[0])), int(fnum(u[1]))) != (year, quarter):
        raise ValueError("SPF RGDP and UNEMP files disagree on latest survey quarter")
    # columns: YEAR, QUARTER, VAR1..VAR6 then VARA..VARD; panel shows the VAR1 -> VAR6 path
    # (the approved spec's verified figures: unemp 4.3 -> 4.45, RGDP 24,174.5 -> 24,765.0)
    g0, g4 = fnum(g[2]), fnum(g[7])
    u0, u4 = fnum(u[2]), fnum(u[7])
    growth = (g4 / g0 - 1.0) * 100.0          # the one derived number, labeled as derived
    return {
        "id": "spf", "label": "SPF Consensus", "agency": "Philadelphia Fed",
        "big": f"{trim(u0, 2)}% {ARR} {trim(u4, 2)}%",
        "detail": (f"unemployment path {MID} real GDP {g0:,.1f} {ARR} {g4:,.1f} "
                   f"({growth:+.1f}% over 4 quarters, derived from median levels)"),
        "sub": "Median forecasts from the Survey of Professional Forecasters: the profession&#8217;s consensus path for the year ahead.",
        # survey is a mid-quarter release: date the vintage at the survey quarter's second month
        "as_of": f"{year}-{quarter * 3 - 1:02d}-01",
        "as_of_label": f"{year}Q{quarter} survey",
        "stale_after_days": 120,   # one missed quarterly survey
        "note": "Quarterly survey, mid-quarter release; the four-quarter GDP growth figure is derived here from the published median levels.",
        "credit": "Survey of Professional Forecasters, FRB Philadelphia",
        "url": "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters",
    }

# ---------------------------------------------------------------- driver
def main():
    prior = {}
    try:
        with open(OUT) as f:
            prior = {c["id"]: c for c in json.load(f).get("cards", [])}
    except (OSError, ValueError, TypeError, KeyError) as e:
        warn(f"prior reference cache unavailable ({e!r}); rebuilding from sources")

    cards = []
    for cid, fetch_fn, card_fn in (("gdpnow", fetch_gdpnow, card_gdpnow),
                                   ("ads", fetch_ads, card_ads),
                                   ("cleveland", fetch_cleveland, card_cleveland),
                                   ("spf", fetch_spf, card_spf)):
        try:
            fetch_fn()
        except Exception as e:
            warn(f"{cid}: live fetch failed ({e!r}); distilling from cached raw/ file")
        try:
            cards.append(card_fn())
        except Exception as e:
            warn(f"{cid}: distill failed ({e!r}); " +
                 ("carrying forward previous card" if cid in prior else "card omitted"))
            if cid in prior:
                cards.append(prior[cid])

    out = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "cards": cards}
    with open(OUT + ".new", "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    os.replace(OUT + ".new", OUT)
    print(f"geo/reference.json: {len(cards)}/4 cards"
          + (f" ({len(warns)} warnings)" if warns else ""))
    for c in cards:
        big = c["big"].replace("&#8594;", "->")
        print(f"  {c['id']:9} {big:18} as of {c.get('as_of_label', c['as_of'])}")

if __name__ == "__main__":
    main()
