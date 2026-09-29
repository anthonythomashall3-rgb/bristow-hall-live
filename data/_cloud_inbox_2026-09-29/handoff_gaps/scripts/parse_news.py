"""Deterministic extraction of national weekly UI figures from wire-story text.
extract(text, pub_date) -> list of candidate dicts:
  series: claims | rate | level ; week_ended (ISO) ; value (float/int) ; value_string (exact matched text) ;
  role: 'latest' (the week the story reports as the new figure) or 'prior' (previous week's figure quoted in the same story);
  week_how: 'in-sentence' (week named in the same sentence) or 'adjacent:<n>' (named in sentence n positions away) ;
  sentence: the source sentence.
Year of a 'Mon. D' week is resolved as the latest such date on or before the publication date (within 70 days);
the story's own dateline/publication date is therefore the year proof."""
import re, datetime as dt

MON = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10,
       'nov': 11, 'dec': 12, 'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6, 'july': 7, 'august': 8,
       'september': 9, 'october': 10, 'november': 11, 'december': 12}
MD = r'(Jan(?:uary|\.)?|Feb(?:ruary|\.)?|March|Mar\.|April|Apr\.|May|June|July|Aug(?:ust|\.)?|Sept(?:ember|\.)?|Sep\.|Oct(?:ober|\.)?|Nov(?:ember|\.)?|Dec(?:ember|\.)?)\s+(\d{1,2})'
WEEK = re.compile(r'week (?:ending|ended|that ended|of)\s+(?:Saturday,?\s+)?' + MD, re.I)
NUM7 = r'(\d{1,2},\s?\d{3},\s?\d{3})'
NUM6 = r'(\d{3},\s?\d{3})'


def resolve(mon, day, pub):
    m = MON[mon.lower().rstrip('.')]
    d = int(day)
    for y in (pub.year, pub.year - 1):
        try:
            c = dt.date(y, m, d)
        except ValueError:
            continue
        if c <= pub and (pub - c).days <= 70:
            return c
    return None


def sentences(text):
    text = re.sub(r'\s+', ' ', text)
    # protect abbreviations like "Dec. 5" and "U.S."
    t = re.sub(r'\b(Jan|Feb|Mar|Apr|Aug|Sept|Sep|Oct|Nov|Dec|U\.S|Mass|Calif|No|Inc|Corp|Mr|Mrs|Dr|St)\.', lambda m: m.group(1) + '<DOT>', text)
    t = re.sub(r'(\d)\. (\d)', r'\1<DOTSP>\2', t)  # "2. 6 percent" OCR/typesetting split
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z\'"(])', t)
    return [p.replace('<DOT>', '.').replace('<DOTSP>', '. ') for p in parts]


def num(s):
    return int(re.sub(r'[,\s]', '', s))


def extract(text, pub):
    out = []
    S = sentences(text)
    weeks = []
    for s in S:
        w = [resolve(m.group(1), m.group(2), pub) for m in WEEK.finditer(s)]
        weeks.append([x for x in w if x])

    def near_week(i):
        if weeks[i]:
            return weeks[i][0], 'in-sentence'
        for k in (1, -1, 2, -2):
            j = i + k
            if 0 <= j < len(S) and weeks[j]:
                return weeks[j][0], f'adjacent:{k}'
        return None, ''

    for i, s in enumerate(S):
        low = s.lower()
        # insured unemployment rate
        if 'insured unemployment rate' in low and 'unadjusted' not in low and 'not seasonally' not in low:
            m = re.search(r'insured unemployment rate[^.]*?(\d{1,2}(?:\.|\. )\d) percent', s, re.I)
            if m:
                w, how = near_week(i)
                out.append(dict(series='rate', week_ended=w, value=float(m.group(1).replace(' ', '')), value_string=m.group(0),
                                role='latest', week_how=how, sentence=s))
                m2 = re.search(r'from (?:a revised |an unrevised |the previous week\'s |the prior week\'s )?(\d{1,2}(?:\.|\. )\d) percent', s[m.end() - 12:], re.I)
                if m2 and w:
                    out.append(dict(series='rate', week_ended=w - dt.timedelta(7), value=float(m2.group(1).replace(' ', '')),
                                    value_string=m2.group(0), role='prior', week_how=how + '(-7d)', sentence=s))
        # insured unemployment level (people claiming / receiving / collecting benefits, state programs)
        m = re.search(NUM7 + r'\s+(?:people|persons|jobless|workers|Americans|out-of-work)[^.]{0,80}?(?:claiming|collecting|collected|receiving|received|filed for|drawing|were getting)', s, re.I) \
            or re.search(r'(?:insured unemployment|number of people (?:claiming|collecting|receiving)[^.]{0,60}?)[^.]{0,60}?(?:was|totaled|to|at|of)\s+' + NUM7, s, re.I) \
            or re.search(r'(?:A total of|total of)\s+' + NUM7, s, re.I)
        if m and 'initial' not in low[:max(0, m.start() - 0)][-40:]:
            w, how = near_week(i)
            out.append(dict(series='level', week_ended=w, value=num(m.group(1)), value_string=m.group(0), role='latest',
                            week_how=how, sentence=s))
            m2 = re.search(r"(?:from|prior week's|previous week's|preceding week's)\s+(?:a revised |the prior week's |the previous week's )?" + NUM7, s[m.end():], re.I)
            if m2 and w:
                out.append(dict(series='level', week_ended=w - dt.timedelta(7), value=num(m2.group(1)), value_string=m2.group(0),
                                role='prior', week_how=how + '(-7d)', sentence=s))
        # seasonally adjusted initial claims
        if re.search(r'claims|filing|filed|applications', low) and 'seasonally adjusted' in low and 'emergency' not in low:
            m = re.search(r'seasonally adjusted (?:total of |level of |figure of )?' + NUM6 + r'(?!,\d)', s, re.I)
            if m and not re.search(r'insured|claiming|receiving|collecting', low):
                w, how = near_week(i)
                m2 = re.search(r'from (?:a |the )?(?:revised |previous week\'s revised |prior week\'s revised |upwardly revised |downwardly revised )?' + NUM6, s[m.end():], re.I)
                wm = [x for x in WEEK.finditer(s)]
                if m2 and wm and how == 'in-sentence' and wm[0].start() > m.end() + m2.end():
                    # the only week named in the sentence follows the prior-week figure: it names the prior week
                    w = w + dt.timedelta(7); how = 'in-sentence(prior-week named; latest=+7d)'
                out.append(dict(series='claims', week_ended=w, value=num(m.group(1)), value_string=m.group(0), role='latest',
                                week_how=how, sentence=s))
                m2 = m2 or re.search(r'from (?:a |the )?(?:revised |previous week\'s revised |prior week\'s revised )?' + NUM6, s[:m.start()], re.I)
                if m2 and w:
                    out.append(dict(series='claims', week_ended=w - dt.timedelta(7), value=num(m2.group(1)), value_string=m2.group(0),
                                    role='prior', week_how=how + '(-7d)', sentence=s))
    for o in out:
        o['week_ended'] = o['week_ended'].isoformat() if o['week_ended'] else ''
    return out
