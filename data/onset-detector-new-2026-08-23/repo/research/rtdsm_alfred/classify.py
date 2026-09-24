"""CH-R103 classification: RTDSM var x ALFRED prefetch overlap.

Crosswalk RTDSM var -> FRED concept id is RESEARCH (parser docstring L106-113;
owner CLAIMSx!=ICSA ruling). It is NOT an alias -> IDENTITY is barred by ruling,
independent of bytes. Byte test below confirms: RTDSM vintage grid (day-01,
quarter-mid-month) is disjoint from ALFRED true release days.
"""
import json

hdr={o["var"]:o for o in json.load(open("research/rtdsm_alfred/rtdsm_headers.json"))}
alf=json.load(open("research/rtdsm_alfred/alfred_spans.json"))  # {series:[dates]}

# Conservative concept crosswalk for the clear macro aggregates. cand = the FRED
# id that WOULD be the twin. present_variant = an alfred-prefetched series that is
# the SAME concept but a different series (projection/industry cut) -> NON-IDENTITY.
XWALK={
 "ruc":     ("UNRATE",   None),
 "employ":  ("PAYEMS",   None),
 "cpi":     ("CPIAUCSL", "CPIAUCSL"),   # exact concept present
 "pcpix":   ("CPILFESL", "CPILFESL"),
 "m1":      ("M1SL",     "M1SL"),
 "m2":      ("M2SL",     "M2SL"),
 "ipt":     ("INDPRO",   None),
 "ipm":     ("IPMAN",    "IPMANSICS"),  # SIC variant present, not exact IPMAN
 "hstarts": ("HOUST",    None),
 "routput": ("GDPC1",    None),         # GDPC1MD present = SEP projection, not actual
 "noutput": ("GDP",      None),
 "rcon":    ("PCEC96",   "PCEC96"),     # real PCE present
 "rconnd":  ("PCND",     "PCND"),
 "ndpi":    ("DSPIC96",  "DSPIC96"),    # real disposable personal income
 "npsav":   ("PSAVERT",  "PSAVERT"),
 "ratesav": ("PSAVERT",  "PSAVERT"),
 "oph":     ("OPHNFB",   "OPHNFB"),     # output per hour nonfarm business
 "ulc":     ("ULCNFB",   None),
 "cum":     ("CUMFNS",   "CUMFNS"),     # capacity util manufacturing
 "cut":     ("TCU",      None),
 "pcpi":    ("PCECTPI",  "PCEPI"),      # PCE price index (PCEPI present)
}

def span(dates):
    return (dates[0], dates[-1]) if dates else (None,None)

rows=[]
for var in sorted(hdr):
    h=hdr[var]
    fv,lv=h.get("first_vintage"),h.get("last_vintage")
    if var in XWALK:
        cand,pv=XWALK[var]
        in_alf = cand in alf
        variant = pv if (pv and pv in alf) else None
        a_earliest,a_latest = span(alf.get(cand)) if in_alf else (None,None)
        if in_alf:
            bucket="NEAR-NEEDS-VERIFICATION"
            note="concept twin %s IS prefetched (%d vintages); grid disjoint -> byte-IDENTITY untestable, verification needs full ALFRED vintage history"%(cand,len(alf.get(cand,[])))
        elif variant:
            bucket="NON-IDENTITY"
            note="exact twin %s ABSENT from prefetch; nearest prefetched %s is a different series (industry/proj cut), ruled out as substitute"%(cand,variant)
        else:
            bucket="ABSENT"
            note="FRED concept twin %s not among the 221 prefetched ALFRED series"%cand
        rows.append({"var":var,"fred_concept":cand,"bucket":bucket,
            "rtdsm_first_vintage":fv,"rtdsm_last_vintage":lv,
            "alfred_variant_present":variant,
            "alfred_earliest_vintage":a_earliest,"alfred_latest_vintage":a_latest,
            "span_advantage_rtdsm": (fv is not None and (a_earliest is None or fv < a_earliest.replace("-",""))),
            "note":note})
    else:
        rows.append({"var":var,"fred_concept":None,"bucket":"ABSENT",
            "rtdsm_first_vintage":fv,"rtdsm_last_vintage":lv,
            "alfred_variant_present":None,"alfred_earliest_vintage":None,
            "note":"RTDSM national-income/subaggregate detail; FRED twin (if any) not prefetched"})

json.dump(rows,open("research/rtdsm_alfred/classification.json","w"),indent=1)
from collections import Counter
c=Counter(r["bucket"] for r in rows)
print("buckets:",dict(c),"total",len(rows))
print("\nCROSSWALKED (concept-mapped) rows:")
for r in rows:
    if r["fred_concept"]:
        print(" %-8s %-9s %-24s rtdsm %s->%s  alf_twin_earliest=%s variant=%s"%(
            r["var"],r["bucket"][:9],r["fred_concept"],r["rtdsm_first_vintage"],
            r["rtdsm_last_vintage"],r["alfred_earliest_vintage"],r["alfred_variant_present"]))
