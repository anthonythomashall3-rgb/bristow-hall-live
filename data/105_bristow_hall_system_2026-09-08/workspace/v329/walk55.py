"""WALK 55 - WALK 54 WITH THE SEARCH WEEK ON THREE LABOUR TERMS (10 September 2026, evening). The sudden stop's search
week (v3.27) read one term, "unemployment"; on 11 March 2020, as a user would have seen it, that term stood 25 per cent
over its base while "layoffs" stood 57 and "laid off" 55 (collection 108, google_trends/asof_terms, scripts/asof_reading.py),
and the market gate first held at the close of 12 March (26.7 under the 20-day high). From here the search week reads
"unemployment", "layoffs" and "laid off", each over its own base with the sudden stop's own numbers (35 over the base; the
S&P 500 20 under its 20-day high at the close of the day the datum is known), and fires on the earliest. On the stitched
histories 2004-2026 each added term fires, with the gate, on 7 October 2008 and 12 March 2020 and nowhere else (alone,
50 and 25 times outside a recession: the gate is load-bearing, as it is for "unemployment"). The terms were chosen after
the case, which the addendum states. Everything else is walk54's. Run:  python3 walk55.py 1962 2026 w55"""
import sys,pickle,os
SEARCH_TERMS=['unemp','layoffs','laidoff']; os.environ['BHS_SEARCH_TERMS']=','.join(SEARCH_TERMS)
_MARK="# ---- the walk "+"itself"
exec(open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out","walk55_%s.out"))
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
