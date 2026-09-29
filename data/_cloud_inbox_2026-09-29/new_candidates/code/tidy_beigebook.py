#!/usr/bin/env python3
"""Tidy Beige Book national summaries (raw/beigebook/national_summaries.jsonl) into
tidy/beigebook/editions.csv (+ one .txt per edition). Counts are of a word list DECLARED HERE IN ADVANCE
and never tuned against recessions; they are plain counts, not a fitted index.
"""
import os, re, json, datetime
import pandas as pd

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
R = os.path.join(W, 'raw', 'beigebook', 'national_summaries.jsonl')
O = os.path.join(W, 'tidy', 'beigebook'); TX = os.path.join(O, 'text'); os.makedirs(TX, exist_ok=True)
NEG = ['recession', 'recessionary', 'decline', 'declined', 'declines', 'declining', 'weak', 'weaker',
       'weakened', 'weakening', 'weakness', 'slow', 'slowed', 'slower', 'slowing', 'slowdown', 'soft',
       'softened', 'softening', 'softness', 'layoff', 'layoffs', 'contraction', 'deteriorated',
       'deteriorating', 'deterioration', 'decrease', 'decreased', 'decreases', 'down']
POS = ['strong', 'stronger', 'strength', 'strengthened', 'increase', 'increased', 'increases',
       'increasing', 'expand', 'expanded', 'expanding', 'expansion', 'growth', 'grew', 'improve', 'improved',
       'improving', 'improvement', 'robust', 'gain', 'gains', 'up']
rows = []
for ln in open(R):
    r = json.loads(ln)
    if not r.get('edition'): continue
    t = r['text']
    m = re.search(r'Beige Book\s+(\w+ \d{1,2}, \d{4})', t)
    body = t[m.end():] if m else t
    body = re.split(r'\s(Previous Report|Next Report|Back to Beige Book|Related Links)\b', body)[0].strip()
    pub = datetime.datetime.strptime(r['pub_date'], '%B %d, %Y').date() if r.get('pub_date') else None
    words = re.findall(r"[a-z]+", body.lower())
    rec = dict(slug=r['slug'], edition_month=r['slug'][:7], pub_date=pub, url=r['url'], n_words=len(words),
               n_neg_listed=sum(w in NEG for w in words), n_pos_listed=sum(w in POS for w in words),
               n_recession=words.count('recession') + words.count('recessionary'))
    rows.append(rec)
    open(os.path.join(TX, r['slug'] + '.txt'), 'w').write(body)
d = pd.DataFrame(rows).sort_values('slug')
d.to_csv(os.path.join(O, 'editions.csv'), index=False)
print(len(d), d['pub_date'].min(), d['pub_date'].max())
