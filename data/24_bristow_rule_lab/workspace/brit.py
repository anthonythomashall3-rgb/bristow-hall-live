import re, sys
BRIT = r'\b(labour|labours|labouring|behaviour\w*|favour\w*|colour\w*|neighbour\w*|centre[sd]?|metre[sd]?|programme[sd]?|organis\w+|recognis\w+|emphasis(?:e|ed|es|ing)\b|analys(?:e|ed|es|ing)\b|summaris\w+|normalis\w+|utilis\w+|realis(?:e|ed|es|ing)\b|characteris\w+|generalis\w+|specialis\w+|minimis\w+|maximis\w+|stabilis\w+|categoris\w+|criticis\w+|prioritis\w+|defence|offence|licence[sd]?|practise[sd]?|travell\w+|modell\w+|labelled|labelling|cancelled|cancelling|fuelled|signalled|signalling|marvell\w+|towards|amongst|whilst|learnt|spelt|dreamt|grey|sceptic\w*|artefact\w*|ageing|judgement[s]?|enrol\b|enrolment|instalment|fulfil\b|fulfilment|storey[s]?|tyre[s]?|kerb|plough|draught|aluminium|manoeuvr\w+|paediatr\w+|foetal|oestrogen|haemo\w+|anaemi\w+|oesophag\w+)\b'
def spans_in_quotes(t):
    out=[]
    for m in re.finditer(r'[“"]([^“”"]{2,900})[””"]', t): out.append((m.start(1), m.end(1)))
    for m in re.finditer(r'[‘]([^’]{2,900})[’]', t): out.append((m.start(1), m.end(1)))
    return out
def scan(t, label):
    qs=spans_in_quotes(t)
    def inq(i): return any(a<=i<b for a,b in qs)
    hits=[(m.start(), m.group(0), inq(m.start())) for m in re.finditer(BRIT, t, re.I)]
    outside=[h for h in hits if not h[2]]
    inside=[h for h in hits if h[2]]
    print(f'== {label}: {len(hits)} British-spelling hits | outside quotes {len(outside)} | inside quotes {len(inside)}')
    from collections import Counter
    print('   outside:', Counter(w.lower() for _,w,_ in outside).most_common())
    print('   inside :', Counter(w.lower() for _,w,_ in inside).most_common())
    return outside, inside, t
