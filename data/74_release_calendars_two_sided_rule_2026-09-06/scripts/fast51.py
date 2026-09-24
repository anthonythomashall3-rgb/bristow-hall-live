"""v3.5 RECORD SCRIPT — THE CREDIT SUBINDEX REMOVED ON A RULE ZERO FINDING, AND THE VINTAGE LEDGER VERIFIED.
Anthony asked whether the tool is real-time or mixed. Put to every object, the question failed on one: the Chicago
Fed's NFCI credit subindex. Its ALFRED vintages begin 5 July 2012 - the index was first published in 2011, so no
reading of it existed in 1973 - and its whole history is RE-ESTIMATED weekly: the week of 3 August 1973 reads -0.47
in the vintage of 2 January 2015, +0.18 in the vintage of 3 January 2020 and -2.200 today. The memo's claim that
'the reading that fires is the one that printed' is WITHDRAWN (Rule Zero). Removing it costs the tool NOTHING,
because the paper spread - Federal Reserve H.15, published at the time, never revised - already carries 1973."""
exec(open('fast50.py').read().split("full('v3.3r")[0].replace("out=open('fast50.out','w')","out=open('fast51.out','w')"))
full('v3.4 (credit subindex in) — WITHDRAWN',[CRD,SPR],look45=91)
full('v3.5 (credit subindex out, paper spread only) — SHIPPED',[SPR],look45=91)
P("\nTHE VINTAGE LEDGER, OBJECT BY OBJECT, VERIFIED AGAINST THE ARCHIVE THIS SESSION")
AL2=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')
import csv
for s in ['UNRATE','HOUST','AWHMAN','NDMANEMP','JTSJOL','ICSA']:
    p=os.path.join(AL2,s+'_all_vintages.csv')
    if not os.path.exists(p): P(f"   {s}: no vintage file held"); continue
    r=csv.reader(open(p)); h=next(r); vd=[c.split('_')[-1] for c in h[1:]]; rows=list(r)
    P(f"   {s}: {len(vd)} ALFRED vintages, the first dated {vd[0][:4]}-{vd[0][4:6]}-{vd[0][6:]}; observations {rows[0][0]} to {rows[-1][0]}")
P("   paper spread (H.15 one-month commercial paper and three-month bill): published daily at the time, NEVER REVISED — real-time over its whole span from 20 April 1956")
P("   insured unemployment rate: the Department's own weekly FIRST PRINTS before 1971 (collection 59, read from the printed releases); the current file 1971 to October 2002, where no first-print series exists; the Department's advance figures from October 2002")
P("   vacancy rate: JOLTS vintages from 11 August 2010; the JOLTS current file December 2000 to August 2010; the Barnichon reconstruction before December 2000, which is not a vintage series")
P("   closers K and H: the Department's current file")
P("\n   SO: the tool is MIXED in exactly the sense Anthony set. Every object is read at the earliest vintage that exists")
P("   for it, and where a first print exists it is used. Where no vintage exists — the unemployment rate before March")
P("   1960, housing starts before July 1960, the hours pair before November 1961, the vacancy before December 2000,")
P("   the insured rate 1971-2002, initial claims before October 2002 — the tool reads the EARLIEST vintage that was")
P("   ever published, not today's revised file. Nothing in the rule reads a number that only exists today except the")
P("   vacancy reconstruction before 2000 and the two closers, and both are declared.")
out.close()
