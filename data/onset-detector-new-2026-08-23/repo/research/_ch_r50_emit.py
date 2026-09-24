import csv,json,os
D="research/prefetch/nber_macrohistory"
rows={r["id"]:r for r in csv.DictReader(open("research/nber_catalog_scan.csv"))}
allr=list(rows.values())
def od_line(path,lineno):
    ls=open(path,encoding="latin-1").read().splitlines()
    return ls[lineno] if lineno<len(ls) else ""
# ---- 7 shortlist final selection ----
seven=[
 ("commercial_paper_rate_1857","m13002","target 1857; NYC commercial paper rate, longest span"),
 ("pig_iron_1877","m01130a","target 1877 exact; US pig iron production, gross tons"),
 ("steel_ingot_1899","m01135a","target 1899 exact; steel ingot production, long tons"),
 ("weekly_carloadings_1918","m03030","NO true weekly/1918 file in cache; m03030=FRB total carloadings index 1919-1953 is best coverage; earliest carloadings=m03006b(1909, per-working-day)"),
 ("call_money","m13001","call money rate mixed collateral, NYC, 1857-1970, longest"),
 ("retail_trade_index_1914","m06001a","target 1914 exact but only 72 obs(1914-1919); m06001b continues 1919-1927"),
 ("department_store_sales","m06002b","index of dept store sales 1919-1963; near-dup of m06002ab(identical span/obs)"),
]
located=[]
for concept,fid,note in seven:
    r=rows[fid]; dp=f"{D}/data/{r['chapter']}/{fid}.dat"
    located.append({"concept":concept,"id":fid,"chapter":r["chapter"],"title":r["title"],
        "freq":r["freq"],"units":r["units"],"sa":r["sa"],"date_range":f"{r['ymin']}-{r['ymax']}",
        "obs_count":int(r["nobs"]),"missing_count":int(r["nmiss"]),"docvar":r["docvar"],
        "filename":f"data/{r['chapter']}/{fid}.dat","doc":f"docs/{r['chapter']}/{fid}.txt","note":note})
# ---- worked byte examples ----
def bytes_of(path,idx):
    raw=open(path,encoding="latin-1").read().splitlines()[idx]
    return {"repr":repr(raw),"len":len(raw),"split_tokens":raw.split()}
examples={
 "monthly_full_layout":{"file":"data/01/m01001.dat","line0":bytes_of(f"{D}/data/01/m01001.dat",0),
    "line_missing_blank_tail":bytes_of(f"{D}/data/01/m01001.dat",825)},
 "annual_layout":{"file":"data/03/m03003h.dat","line0":bytes_of(f"{D}/data/03/m03003h.dat",0)},
 "dot_missing":{"file":"data/14/m14056.dat","line0":bytes_of(f"{D}/data/14/m14056.dat",0),
    "line_value":bytes_of(f"{D}/data/14/m14056.dat",[i for i,l in enumerate(open(f'{D}/data/14/m14056.dat',encoding='latin-1').read().splitlines()) if '.' in l.split()[-1] and l.split()[-1]!='.'][0] if True else 0)},
}
layout={
 "schema":"nber_layout_v1",
 "corpus":{"root":"research/prefetch/nber_macrohistory","n_series":len(allr),
   "data":"data/<chapterNN>/<id>.dat","doc":"docs/<chapterNN>/<id>.txt",
   "encoding":"latin-1","line_ending":"LF (\\n)","chapters":sorted(set(r["chapter"] for r in allr))},
 "data_layout":{
   "parse_recommendation":"whitespace-split each line into tokens; do NOT rely on fixed columns for value (value width varies 15.7 vs 15.7000).",
   "fixed_columns_observed":{"year":"cols 0-3","period":"cols 4-9 right-justified (month 1-12)","sep":"col 10 space","value":"col 11.. left-justified, line right-padded to fixed width"},
   "line_length":{"monthly":42,"annual":39,"note":"padding differs; content is whitespace-delimited"},
   "monthly_tokens":["YYYY","period(1-12)","value"],
   "annual_tokens":["YYYY","value"],
   "value_format":"plain decimal, variable precision within a file (e.g. 15.7 then 15.7000); TRAILING-DOT integers occur (e.g. 103. = 103.0) so numeric test must accept a trailing dot; a lone '.' is MISSING not a value; some negative; no thousands separators",
   "mixed_period_row":"some files (e.g. m03030) carry an annual-summary row with BLANK period (2 tokens: year+value) interleaved among monthly 3-token rows; token-count alone does not classify a file as annual",
   "missing_value":{"primary":". (single dot) — 1416 files","secondary":"blank value field — 2 files (m01001,m01123 trailing)","declared_sentinel":"MD=1E-37 in doc header, NEVER appears literally in data"}},
 "doc_layout":{
   "common":"quoted lines each begin with \"c ; fields: NBER SERIES, AREA COVERED, UNITS, ANNUAL/QUARTERLY/MONTHLY COVERAGE, SEASONAL ADJUSTMENT, SOURCE, NOTES",
   "variants":{
     "full":{"count":2187,"markers":"codebook line1 (VAR/REF/LOC/WIDTH/DK/COL/EXP DEC), a TITLE line, a ----- divider; colon fields double-spaced","title_source":"line above the ----- divider"},
     "compact":{"count":42,"markers":"NO codebook line1, NO title line, NO ----- divider; starts at 'NBER SERIES:'; colon fields single-spaced","title_source":"NOT in doc — must come from listings/chNN.html or filename; these are the title-less rows","chapters":"mostly 14, some 08, one 11"}},
   "codebook_line_warning":"LOC/WIDTH/COL/EXP DEC in the full-variant header describe the ORIGINAL 80-col NBER punch-card master (COL 35-43 etc.), NOT the extracted .dat. Do NOT use them to slice the .dat. EXP DEC is implied-decimal of the master, not the extract (extract carries an explicit decimal point)."},
 "anomalies":{
   "corrupt_payload":{"files":["m01100a (line 200, 55B binary)","m01121 (line 340, 44B binary)"],"action":"NUM-match fails on garbage token -> emit as missing + flag; do not abort file"},
   "empty_stub":{"files":["m08217"],"content":"single line 'data not available'","action":"skip file, 0 obs"},
   "annual_single":{"files":["m03003h"],"note":"only annual-format file in corpus (2-token lines, no period col)"}},
 "frequency_distribution":{"M":sum(1 for r in allr if r["freq"]=="M"),"A":sum(1 for r in allr if r["freq"]=="A"),"EMPTY":sum(1 for r in allr if r["freq"]=="EMPTY")},
 "worked_examples":examples,
 "located_seven":located,
}
json.dump(layout,open("research/nber_layout_v1.json","w"),indent=1)
# ---- remainder ranking ----
short_ids={fid for _,fid,_ in seven}
FREQW={"M":1.0,"A":0.4,"EMPTY":0.0}
rem=[]
for r in allr:
    if r["id"] in short_ids: continue
    fw=FREQW.get(r["freq"],0)
    parse_penalty=1.0 if (int(r["corrupt"]) or r["docvar"]=="compact") else 0.0  # extra cost
    ep=int(r["episodes"]); nobs=int(r["nobs"])
    score=round(ep*fw*(1.0/(1.0+parse_penalty)),3)
    rem.append({"id":r["id"],"chapter":r["chapter"],"title":r["title"],"freq":r["freq"],
        "ymin":r["ymin"],"ymax":r["ymax"],"nobs":nobs,"episodes":ep,"docvar":r["docvar"],
        "corrupt":r["corrupt"],"parse_cost":"high" if parse_penalty else "low","score":score})
rem.sort(key=lambda x:(-x["score"],-x["episodes"],-x["nobs"]))
with open("research/nber_remainder_ranking_v1.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rem[0].keys())); w.writeheader(); w.writerows(rem)
print("layout json + ranking csv written. remainder rows:",len(rem))
print("top5:",[(r["id"],r["score"],r["episodes"],r["title"][:30]) for r in rem[:5]])
print("located7 obs:",[(l["id"],l["obs_count"],l["date_range"]) for l in located])
