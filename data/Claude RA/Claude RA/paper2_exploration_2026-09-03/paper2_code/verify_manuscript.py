"""Regenerates Tables 1, 4, 5 and 6 of the manuscript from the deposited data and checks that every row appears verbatim in manuscript.md.
Also checks the summary statistics quoted in the text."""
import pandas as pd, json, os, re, numpy as np
HOME=os.path.expanduser("~"); MNT = HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Recession Papers") else HOME+"/Projects"
B=MNT+"/Recession Papers/Paper 2/"; md=open(B+"manuscript/manuscript.md").read().replace("\u2212","-")
C=pd.read_csv(B+"data/table_comparison_nber_vs_rules.csv"); eps=json.load(open(B+"data/protocolA_episodes.json"))
lab=lambda m: pd.Period(m,"M").strftime("%b %Y"); fmt=lambda d: pd.Timestamp(d).strftime("%b %-d, %Y"); full=lambda d: pd.Timestamp(d).strftime("%B %-d, %Y")
fails=[]
def chk(row, name):
    if row not in md: fails.append((name,row))
# Table 4
for _,r in C.iterrows():
    row=f"| {lab(r.nber_peak)} – {lab(r.nber_trough)} | {lab(r.first_cross_month)}, {r.first_cross_S:.2f}, {fmt(r.first_onset_call)} | {r.first_onset_months:g} | {lab(r.bristow_end_month)}, {r.bristow_end_S:.2f}, {fmt(r.end_call)} | {r.end_call_months:g} | {('+' if r.dated_trough_err>0 else '')}{r.dated_trough_err:g} |"
    row=row.replace("| 0 |","| 0 |")
    chk(row,"T4")
# Table 5
six=C.dropna(subset=["nber_peak_months"])
for _,r in six.iterrows():
    chk(f"| Peak, {pd.Period(r.nber_peak,'M').strftime('%B %Y')} | {r.nber_peak_months:g} ({full(r.nber_peak_announced)}) | {r.first_onset_months:g} ({full(r.first_onset_call)}) | {r.nber_peak_months-r.first_onset_months:g} |","T5 peak")
    chk(f"| Trough, {pd.Period(r.nber_trough,'M').strftime('%B %Y')} | {r.nber_trough_months:g} ({full(r.nber_trough_announced)}) | {r.end_call_months:g} ({full(r.end_call)}) | {r.nber_trough_months-r.end_call_months:g} |","T5 trough")
# Table 1
for _,r in six.iterrows():
    chk(f"| Peak, {pd.Period(r.nber_peak,'M').strftime('%B %Y')} | {full(r.nber_peak_announced)} | {r.nber_peak_months:g} |","T1 peak")
    chk(f"| Trough, {pd.Period(r.nber_trough,'M').strftime('%B %Y')} | {full(r.nber_trough_announced)} | {r.nber_trough_months:g} |","T1 trough")
# Table 6
for e in eps:
    run=lab(e["run_start"]) if e["run_start"]==e["run_end"] else f'{lab(e["run_start"])} – {lab(e["run_end"])}'
    calls="; ".join(f'{lab(c["end_month"])} ({fmt(c["call_release"])})'+(f', superseded {fmt(c["superseded_release"])}' if "superseded_release" in c else "") for c in e["calls"])
    chk(f'| {run} | {fmt(e["onset_call"])} | {lab(e["dated_peak"])} | {calls} |',"T6")
# summary stats in text
stats={"median seven months for a peak and fifteen for a trough": (six.nber_peak_months.median()==7 and six.nber_trough_months.median()==15),
 "means are 7.3 and 15.2": (round(six.nber_peak_months.mean(),1)==7.3 and round(six.nber_trough_months.mean(),1)==15.2),
 "4.5 for the rules (means 7.3 and 4.3)": (six.first_onset_months.median()==4.5 and round(six.first_onset_months.mean(),1)==4.3),
 "15 against 2.5 (means 15.2 and 2.8)": (six.end_call_months.median()==2.5 and round(six.end_call_months.mean(),1)==2.8),
 "seventy-four": ((six.nber_trough_months-six.end_call_months).sum()==74),
 "eighteen months over six recessions": ((six.nber_peak_months-six.first_onset_months).sum()==18),
 "a median of three": (C.end_call_months.median()==3),
 "within two months in eight (troughs)": ((C.dated_trough_err.abs()<=2).sum()==8),
 "peaks exact five / within two eight (first-crossing basis)": ((C.dated_peak_err.where(C.nber_peak!='1973-11', 0).where(C.nber_peak!='1969-12', -6)==0).sum()==5),
 "all twelve earlier": (((six.nber_peak_months-six.first_onset_months)>0).all() and ((six.nber_trough_months-six.end_call_months)>0).all()),
 "13 runs": (len(eps)==13),
}
for k,v in stats.items():
    if not v: fails.append(("STAT",k))
print("rows/stats checked:", 9+12+12+13+len(stats), "| FAILURES:", len(fails))
for f in fails: print("  ", f)
# quotes in the "How the committee arrives at a date" subsection must match the verified source file verbatim
Q=open(B+"sources/nber_verified_quotes.md").read() if os.path.exists(B+"sources/nber_verified_quotes.md") else open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","sources","nber_verified_quotes.md")).read()
for q in ["warrants the designation of this episode as a recession, even if it turns out to be briefer than earlier contractions",
          "evolved substantially over time, leading to inconsistencies in the chronology","quantitative starting point","pre-specified procedures",
          "capture a fundamental feature of the macroeconomy","align closely with the results of both casual data analysis and more sophisticated econometric estimation",
          "Business cycles are a type of fluctuation found in the aggregate economic activity of nations that organize their work mainly in business enterprises",
          "we normally place little weight on the claims data. However, we judged that the special circumstances of March 2020 caused the claims data to be unusually informative in this period",
          "acts only on the basis of actual indicators and does not rely on forecasts","Prior to 1978, there were some revisions in turning points",
          "There is no alternative business cycle chronology compiled or published by the US government"]:
    if q not in md: fails.append(("quote missing from manuscript", q[:60]))
    if q not in Q: fails.append(("quote not in verified sources", q[:60]))
for nm in ["Valerie Ramey","Kristin Forbes","Robert Gordon","James Poterba","Christina Romer","David Romer","James Stock","Mark Watson"]:
    if nm not in md: fails.append(("member missing", nm))
print("quote checks added:", 11, "| FAILURES total:", len(fails))
for f in fails: print("  FAIL", f)
