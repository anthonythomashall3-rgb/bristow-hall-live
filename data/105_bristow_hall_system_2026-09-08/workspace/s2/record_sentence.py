"""The front page's record sentence, computed from the state (v3.74, Step 6 R15, 23 September 2026, collection 347).

Until v3.73 the sentence "On the NBER's twelve recessions and Paper 1's 2024, it calls all thirteen ... with no false alarm"
was fixed text in site/template.html; a fourteenth episode would have published with it stale, because the deploy gate never
holds back a call. Now bhs_site.py writes the sentence from the state at every build and q41 checks the page carries it.
The counts: the chronology's recessions (state['announcements']: peak, trough, the rule's open and close), how many the rule
called inside [-92, +31] days of the end of the peak month, how many it closed inside [-31, +31] days of the end of the
trough month, and any episode of the rule that no chronology dates (an open the announcements do not carry) - which is a
call standing on its own, named as such, never called a false alarm by the page until a dater speaks."""
import datetime as _dt

_WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
          'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty']
def words(n): return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)
def _mend(ym):
    y, m = int(ym[:4]), int(ym[5:7]); nxt = _dt.date(y + (m == 12), 1 if m == 12 else m + 1, 1); return nxt - _dt.timedelta(days=1)
def _d(s): return _dt.date.fromisoformat(str(s)[:10])

def counts(state):
    A = state.get('announcements') or []; E = state.get('episodes') or []
    n = len(A); nber = sum(1 for a in A if 'not dated by the NBER' not in str(a.get('source', ''))); other = n - nber
    calls_in = sum(1 for a in A if a.get('rule_open') and -92 <= (_d(a['rule_open']) - _mend(a['peak'])).days <= 31)
    closed = [a for a in A if a.get('rule_close')]
    closes_in = sum(1 for a in closed if -31 <= (_d(a['rule_close']) - _mend(a['trough'])).days <= 31)
    opens = {str(a.get('rule_open'))[:10] for a in A if a.get('rule_open')}
    undated = [e for e in E if str(e.get('open_pub'))[:10] not in opens]
    return dict(n=n, nber=nber, other=other, calls_in=calls_in, closed=len(closed), closes_in=closes_in, undated=[str(e.get('open_pub'))[:10] for e in undated])

def sentence(state):
    c = counts(state); n = c['n']
    who = "the NBER&rsquo;s %s recessions%s" % (words(c['nber']), (" and Paper 1&rsquo;s 2024" if c['other'] == 1 else (" and %s dated by another source" % words(c['other']) if c['other'] else "")))
    calls = "all %s" % words(n) if c['calls_in'] == n else "%s of %s" % (words(c['calls_in']), words(n))
    if c['closed'] == n: ends = "all %s" % words(n) if c['closes_in'] == n else "%s of %s" % (words(c['closes_in']), words(n))
    else: ends = ("all %s that have ended" % words(c['closed']) if c['closes_in'] == c['closed'] else "%s of the %s that have ended" % (words(c['closes_in']), words(c['closed'])))
    s = ("On %s, it calls %s within three months before to one month after the end of the peak month and ends %s within a month either side of the end of the trough month"
         % (who, calls, ends))
    if c['undated']:
        s += (", with no false alarm on those; it has also opened %s episode%s that no chronology has yet dated (from %s) &mdash; a call standing on its own until a dater speaks."
              % (words(len(c['undated'])), '' if len(c['undated']) == 1 else 's', ', '.join(c['undated'])))
    else: s += ", with no false alarm."
    return s

if __name__ == '__main__':
    import json, sys
    st = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'out/bhs_state.json')); print(counts(st)); print(sentence(st))
