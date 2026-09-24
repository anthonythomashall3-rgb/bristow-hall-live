"""24 September 2026 (Anthony: remove "Against six ex-post measures ... 75 of 78 pairs ..." and make the Notes "as short as the
Sahm Indicator notes section"; approved text, then "go").
The detector page's Notes: two paragraphs (405 words) -> three (126 words; FRED's SAHMREALTIME notes are 108). The record sentence
(R15) and the six-measure damage consensus leave the Notes; the speed panels below still carry the record. bhs_site.py: the
__RECORD_SENTENCE__ token becomes optional (where a template carries it, the sentence is still the state's). q41: the record check
follows the template (1 if the token is there, else 0) and a new check holds the Notes to at most 140 words.
Also: the Excel download's Units cell still read 'damage in points of unemployment' (the one-dimension grade before v3.73); it now
reads what the page reads. Idempotent: a root already patched is left alone.
Usage: python3 patch_notes_short_2026-09-24.py <collection-105 root> [<collection-105 root> ...]"""
import sys, os

NOTES_HEAD = '  <p class="kv"><b>Notes:</b></p>\n'
CITE_HEAD = '  <p class="kv"><b>Citation:</b></p>'
NEW = ('  <p>The Bristow-Hall Rule signals a recession&rsquo;s start when a labor measure (insured unemployment, initial claims or the '
       'Sahm gap, national or state) crosses its threshold and a demand measure (job openings, hours, housing, credit or stocks) '
       'confirms it, or when production and stocks fall, the policy rate rises and unemployment spreads across states. It signals the '
       'end when initial claims fall from their peak and a second measure confirms it.</p>\n'
       '  <p>The index shows how near a call is (1.00 = recession); during a recession it adds a damage grade (0&ndash;10, log scale; '
       '1929&ndash;33 = 10) from unemployment, real GDP and industrial production.</p>\n'
       '  <p>This indicator is based on real-time data: each call uses only data as published that day, with thresholds set only from '
       'recessions already dated.<!-- 24 September 2026 (Anthony: "as short as the Sahm Indicator notes section"): 405 words to 126; '
       'the record sentence (R15, s2/record_sentence.py) and the six-measure damage consensus left the Notes; the speed panels carry '
       'the record --></p>\n')
XO = "['Units','Index, 1.00 = the rule fired; above it, the recession\\'s damage in points of unemployment']"
XN = "['Units','Index, 1.00 = recession, 0\\u201310 damage']"

SO = "assert t.count('__RECORD_SENTENCE__')==1, 'template must contain exactly one __RECORD_SENTENCE__ token'"
SN = ("# 24 September 2026 (Anthony: the Notes as short as the Sahm indicator's): the record sentence left the Notes, so the token is\n"
      "# optional; where a template carries it, the sentence is still the state's (R15)\n"
      "assert t.count('__RECORD_SENTENCE__')<=1, 'template must contain at most one __RECORD_SENTENCE__ token'")

QO = "chk('record: the front page sentence is computed from the state',_fp.count(_rs.sentence(S)),1)"
QN = ("# 24 September 2026 (Anthony: the Notes as short as the Sahm indicator's): the record sentence left the Notes. The check follows\n"
      "# the template: where it carries the token the page carries the state's sentence once; where it does not, nowhere.\n"
      "_tpl=open(os.path.join(COL,'site','template.html'),encoding='utf-8').read()\n"
      "chk('record: the front page sentence is computed from the state',_fp.count(_rs.sentence(S)),1 if '__RECORD_SENTENCE__' in _tpl else 0)\n"
      "import html as _html\n"
      "_nt=_re.search(r'<p class=\"kv\"><b>Notes:</b></p>(.*?)<p class=\"kv\"><b>Citation:</b></p>',_fp,_re.S)\n"
      "_nw=len(_html.unescape(_re.sub(r'<!--.*?-->|<[^>]+>',' ',_nt.group(1),flags=_re.S)).split()) if _nt else 0\n"
      "chk('notes: the Notes are a short summary (Anthony, 24 September 2026: as short as the Sahm indicator notes)',_nw,'at most 140 words',ok=(0<_nw<=140))")


def patch(path, old, new, done_mark):
    t = open(path, encoding='utf-8').read()
    if done_mark in t:
        return 'already'
    assert t.count(old) == 1, '%s: expected exactly one match' % path
    open(path, 'w', encoding='utf-8').write(t.replace(old, new))
    return 'patched'


def patch_template(path):
    t = open(path, encoding='utf-8').read()
    if 'as short as the Sahm Indicator notes section' in t:
        return 'already'
    a = t.index(NOTES_HEAD) + len(NOTES_HEAD); b = t.index(CITE_HEAD)
    old = t[a:b]
    assert old.count('<p>') == 2 and 'six ex-post' in old and '__RECORD_SENTENCE__' in old, 'Notes not in the expected v3.74 form'
    t = t[:a] + NEW + t[b:]
    assert t.count(XO) == 1, 'Excel Units cell not in the expected form'
    t = t.replace(XO, XN)
    open(path, 'w', encoding='utf-8').write(t)
    return 'patched'


if __name__ == '__main__':
    for root in sys.argv[1:]:
        print(root)
        print('  template.html', patch_template(os.path.join(root, 'site', 'template.html')))
        print('  bhs_site.py', patch(os.path.join(root, 'workspace', 'bhs_site.py'), SO, SN, 'at most one __RECORD_SENTENCE__'))
        print('  q41', patch(os.path.join(root, 'workspace', 's2', 'q41_data_check.py'), QO, QN, "'notes: the Notes are a short summary"))
