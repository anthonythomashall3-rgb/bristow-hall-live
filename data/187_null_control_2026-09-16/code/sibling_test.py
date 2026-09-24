#!/usr/bin/env python3
"""The sibling test: does the whole family behave like the channel that survived, or only that one line?

WHY IT IS NECESSARY, WITH THE CASE THAT PROVED IT. `D3WACL` -- coin holdings at the Federal Reserve
Bank of Philadelphia -- produced 548 admissible configurations against a mean of 0.1 across forty fake
chronologies, a ratio of about eleven thousand to one and the most statistically significant channel in
the collection. It is obviously not a national recession mechanism. Every statistical control passed it.

The test that catches it costs a minute: run the ELEVEN OTHER Federal Reserve districts. If Reserve
Bank coin holdings were a channel, all twelve would behave alike. Seven of the twelve produce nothing
at all, and District 3 produces five hundred and forty-eight. The channel is District 3's own noise.

So: for any surviving channel that belongs to a family of near-identical series -- the twelve districts,
the Treasury inflation-indexed notes, the H.8 bank balance-sheet breakdowns -- run the whole family. A
mechanism shows up across the family. An artefact shows up once.
"""
import os, sys, json, warnings, collections, multiprocessing as mp, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import late_screen as L
L.FOLDERS = [os.environ.get('US_DATA', '/mnt/user-data/outputs/us')]
L.FP2 = os.environ.get('US_FP', '/mnt/user-data/outputs/fp2'); L.VDIR = L.FP2

FAMILIES = {
 'fed_district_coin': ['D%dWACL' % i for i in range(1, 13)],
 'tips_notes': [s[:-4] for s in sorted(os.listdir(L.FOLDERS[0])) if s.startswith('WTP') and s.endswith('.csv')],
 'h8_cash_assets': [s[:-4] for s in sorted(os.listdir(L.FOLDERS[0])) if s.startswith('CAS') and s.endswith('.csv')],
 'h8_borrowings_from_others': [s[:-4] for s in sorted(os.listdir(L.FOLDERS[0])) if s.startswith('BFO') and s.endswith('.csv')],
}

if __name__ == '__main__':
    want = sys.argv[1:] or list(FAMILIES)
    for fam in want:
        members = FAMILIES[fam]
        rows = []
        with mp.Pool(max(1, os.cpu_count() or 2), initializer=L.init) as pool:
            for res in pool.imap(L.one, members): rows += res
        c = collections.Counter(); pk = collections.defaultdict(set)
        for r in rows:
            c[r['proposer']] += 1
            for p in json.loads(r['tight']): pk[r['proposer']].add(p)
        clear = sum(1 for s in members if c.get(s, 0) > 0)
        print('\n=== %s: %d of %d members clear the bar ===' % (fam, clear, len(members)), flush=True)
        for s in members:
            if c.get(s, 0):
                print('  %-18s %6d configs  %s' % (s, c[s], ','.join(sorted(pk[s]))))
        zero = [s for s in members if not c.get(s, 0)]
        if zero: print('  producing nothing: %s' % ', '.join(zero))
        pd.DataFrame([dict(family=fam, member=s, n_cfg=c.get(s, 0), peaks=','.join(sorted(pk.get(s, []))))
                      for s in members]).to_csv('/mnt/user-data/outputs/late_out2/sibling_%s.csv' % fam, index=False)
