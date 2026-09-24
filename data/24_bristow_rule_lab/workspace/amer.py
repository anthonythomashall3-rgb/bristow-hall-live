import re
MAP = [
 (r'\blabour\b','labor'), (r'\bLabour\b','Labor'),
 (r'\blabour-','labor-'), (r'\bLabour-','Labor-'),
 (r'\bjudgement\b','judgment'), (r'\bJudgement\b','Judgment'),
 (r'\bjudgements\b','judgments'),
 (r'\bsignalled\b','signaled'), (r'\bsignalling\b','signaling'),
 (r'\banalysing\b','analyzing'), (r'\bAnalysing\b','Analyzing'),
 (r'\banalysed\b','analyzed'), (r'\banalyse\b','analyze'), (r'\banalyses\b','analyzes'),
 (r'\bgeneralises\b','generalizes'), (r'\bgeneralise\b','generalize'), (r'\bgeneralised\b','generalized'),
 (r'\borganised\b','organized'), (r'\borganise\b','organize'), (r'\borganises\b','organizes'), (r'\borganising\b','organizing'),
 (r'\brecognised\b','recognized'), (r'\brecognise\b','recognize'), (r'\brecognises\b','recognized'),
 (r'\bemphasised\b','emphasized'), (r'\bemphasise\b','emphasize'), (r'\bemphasises\b','emphasizes'),
 (r'\bsummarised\b','summarized'), (r'\bsummarise\b','summarize'), (r'\bsummarises\b','summarizes'),
 (r'\bnormalised\b','normalized'), (r'\bnormalise\b','normalize'),
 (r'\bcharacterised\b','characterized'), (r'\bcharacterise\b','characterize'),
 (r'\bcategorised\b','categorized'), (r'\bcriticised\b','criticized'), (r'\bcriticises\b','criticizes'),
 (r'\bprioritised\b','prioritized'), (r'\bspecialised\b','specialized'),
 (r'\bminimised\b','minimized'), (r'\bmaximised\b','maximized'), (r'\bstabilised\b','stabilized'),
 (r'\brealised\b','realized'), (r'\butilised\b','utilized'),
 (r'\bbehaviour\b','behavior'), (r'\bbehavioural\b','behavioral'), (r'\bBehaviour\b','Behavior'),
 (r'\bfavour\b','favor'), (r'\bfavours\b','favors'), (r'\bfavoured\b','favored'), (r'\bfavourable\b','favorable'),
 (r'\bcentre\b','center'), (r'\bcentres\b','centers'), (r'\bcentred\b','centered'),
 (r'\bprogramme\b','program'), (r'\bprogrammes\b','programs'),
 (r'\bdefence\b','defense'), (r'\boffence\b','offense'),
 (r'\bmodelled\b','modeled'), (r'\bmodelling\b','modeling'),
 (r'\blabelled\b','labeled'), (r'\blabelling\b','labeling'),
 (r'\bcancelled\b','canceled'), (r'\bcancelling\b','canceling'),
 (r'\bfuelled\b','fueled'), (r'\btravelled\b','traveled'), (r'\btravelling\b','traveling'),
 (r'\btowards\b','toward'), (r'\bamongst\b','among'), (r'\bwhilst\b','while'),
 (r'\blearnt\b','learned'), (r'\bspelt\b','spelled'), (r'\bdreamt\b','dreamed'),
 (r'\bgrey\b','gray'), (r'\bGrey\b','Gray'),
 (r'\bsceptical\b','skeptical'), (r'\bscepticism\b','skepticism'), (r'\bsceptic\b','skeptic'),
 (r'\bartefact\b','artifact'), (r'\bartefacts\b','artifacts'),
 (r'\bageing\b','aging'),
]
def quote_spans(t):
    sp=[]
    for m in re.finditer(r'[“"]([^“”"]{2,1200})[”"]', t): sp.append((m.start(1), m.end(1)))
    for m in re.finditer(r'‘([^’]{2,1200})’', t): sp.append((m.start(1), m.end(1)))
    return sp
def americanize(t, protect_urls=True):
    sp=quote_spans(t)
    if protect_urls:
        for m in re.finditer(r'https?://\S+', t): sp.append((m.start(), m.end()))
    def prot(i): return any(a<=i<b for a,b in sp)
    n=0
    for pat,rep in MAP:
        out=[]; last=0
        for m in re.finditer(pat, t):
            if prot(m.start()): continue
            out.append((m.start(), m.end(), rep))
        for s,e,r in reversed(out):
            t = t[:s] + r + t[e:]; n+=1
        sp=quote_spans(t)
        if protect_urls:
            for m in re.finditer(r'https?://\S+', t): sp.append((m.start(), m.end()))
    return t, n
