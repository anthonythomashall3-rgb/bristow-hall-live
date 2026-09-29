#!/usr/bin/env python3
"""Conference Board HWI release calendar 1996-2005 (the months with no official print source in this
collection). Rule: 10:00 ET on the last Thursday of the month after the reference month (stated in the
Conference Board HWOL technical note for the successor series), moved to the Wednesday before when that
Thursday is Thanksgiving. The rule is checked against release dates stated in news articles
('said Thursday', 'reported yesterday', ...). Output: hwi_release_calendar_1996_2005.csv"""
import os, datetime as dt, calendar
import pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def last_thursday(y, m):
    d = dt.date(y, m, calendar.monthrange(y, m)[1])
    while d.weekday() != 3:
        d -= dt.timedelta(days=1)
    return d


def thanksgiving(y):
    d = dt.date(y, 11, 1)
    while d.weekday() != 3:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=21)


rows = []
for y in range(1995, 2006):
    for m in range(1, 13):
        ry, rm = (y, m + 1) if m < 12 else (y + 1, 1)
        d = last_thursday(ry, rm)
        adj = ''
        if rm == 11 and d == thanksgiving(ry):
            d -= dt.timedelta(days=1); adj = 'thanksgiving_moved_to_wednesday'
        rows.append(dict(ref_month=f'{y}-{m:02d}', rule_release_date=d.isoformat(), rule_adjustment=adj))
cal = pd.DataFrame(rows)
cal = cal[(cal.ref_month >= '1995-11') & (cal.ref_month <= '2005-06')]
news = pd.read_csv(os.path.join(W, 'work', 'news_cells.csv'))
news = news[(news.role.isin(['current'])) & news.release_date.notna() & (news.outlet != 'IndustryWeek')]
news = news[news.release_basis.str.contains('yesterday|thursday|wednesday|friday|monday|tuesday', regex=True)]
ev = news.groupby('month').agg(stated_release_date=('release_date', 'first'), evidence_url=('url', 'first'),
                               evidence_basis=('release_basis', 'first'))
cal = cal.merge(ev, left_on='ref_month', right_index=True, how='left')
cal['rule_matches_evidence'] = cal.apply(lambda r: (r.stated_release_date == r.rule_release_date) if isinstance(r.stated_release_date, str) else None, axis=1)
cal.to_csv(os.path.join(W, 'hwi_release_calendar_1996_2005.csv'), index=False)
print(cal[cal.stated_release_date.notna()].to_string())
