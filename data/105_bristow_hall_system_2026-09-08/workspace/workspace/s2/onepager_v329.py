# -*- coding: utf-8 -*-
"""The executive one-pager, set in Paper 1's own format.

Typography copied from `Recession Signals Without Recession (100 Word Abstract) copy (2).docx`: one-inch margins;
Times New Roman; a centred title at 15pt bold, the author line at 14pt, the affiliation and the dateline italic at
11pt; a centred bold "Abstract" over a justified block indented half an inch on both sides; body justified at 11pt
with a quarter-inch first line; bold numbered section headings. The only departure is the leading, tightened from
17pt to 14pt so the summary holds one page, which is what a one-pager is.

Every figure is taken from RECORD-w55 and site/bhs_state.json and was recomputed before writing
(s2/q41_data_check.py, and the arithmetic printed in the session of 11 September 2026).
"""
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
RP=os.path.expanduser('~/Projects/Recession Papers')
LEAD=Pt(14)
d=Document()
s=d.sections[0]
s.page_width=Inches(8.5); s.page_height=Inches(11)
for m in ('top_margin','bottom_margin','left_margin','right_margin'): setattr(s,m,Inches(1))
n=d.styles['Normal']; n.font.name='Times New Roman'; n.font.size=Pt(11)
def P(text,size=11,bold=False,italic=False,align='both',after=8,before=0,lead=LEAD,
      left=0,right=0,first=0):
    p=d.add_paragraph(); r=p.add_run(text)
    r.bold=bold; r.italic=italic; r.font.size=Pt(size); r.font.name='Times New Roman'
    p.alignment={'both':WD_ALIGN_PARAGRAPH.JUSTIFY,'center':WD_ALIGN_PARAGRAPH.CENTER,
                 'left':WD_ALIGN_PARAGRAPH.LEFT}[align]
    f=p.paragraph_format
    f.space_after=Pt(after); f.space_before=Pt(before)
    f.line_spacing_rule=WD_LINE_SPACING.EXACTLY; f.line_spacing=lead
    if left: f.left_indent=Inches(left)
    if right: f.right_indent=Inches(right)
    if first: f.first_line_indent=Inches(first)
    return p

P('The Bristow-Hall Rule and a New Methodology for Dating Recessions',size=15,bold=True,align='center',after=6,lead=Pt(18))
P('Anthony Hall',size=14,align='center',after=1,lead=Pt(15))
P('Marshall School of Business, University of Southern California',italic=True,align='center',after=1,lead=Pt(13))
P('Executive Summary, September 11, 2026',italic=True,align='center',after=10,lead=Pt(13))

P('Abstract',bold=True,align='center',after=5,lead=Pt(13))
P('The Bristow-Hall Rule dates both ends of a United States recession from labor-market data as they stood on each '
  'release day. Objects that propose a turn are paired with objects that confirm it, and every threshold was chosen '
  'forward — each January from 1962 to 2026, from the recessions the National Bureau had announced by then — so no '
  'line has ever seen the case it is scored on. Since 1962 the rule has opened nine of nine recessions with no '
  'false alarm, a median of seven days before the peak month ended, and closed all nine. It runs live at '
  'bhrrealtime.pages.dev.',
  left=0.5,right=0.5,after=11,lead=Pt(12.5))

P('1. The problem with a committee',bold=True,align='left',before=2,after=4,lead=Pt(13))
P('The National Bureau dates recessions by committee, in retrospect, on revised data, under criteria it calls '
  '“somewhat interchangeable.” Over the eight recessions dated since 1969 its announcements came a median of 9.3 '
  'months after the peak month began and 15.6 months after the trough month began, so the date is unavailable '
  'through the entire first year, when every decision that matters is made. What is missing is a rule that dates '
  'both ends, reads the data as the public saw them, and is fixed before the case arrives.',first=0.25,after=4)

P('2. The rule',bold=True,align='left',before=3,after=3,lead=Pt(13))
P('The rule is built on the premise that demand turns before supply gives way. Five labor-supply objects can propose '
  'a peak — the insured unemployment rate, the survey-week rate, initial claims above their own base, the share of '
  'states with the insured rate rising, and the Sahm gap with vacancies already falling. A proposal stands only if a '
  'demand-side object confirms it within six months back and four forward: vacancies, factory hours with nondurable '
  'employment, housing starts or permits with the unemployment rate, or the commercial paper spread. A sudden stop '
  'is read the week it happens, from claims or from search behavior with the S&P 500 twenty percent below its '
  'twenty-day high. A turn is dated the month the rule fires and is never revised.',
  first=0.25,after=4)

P('3. The record, and what a rule would do that a committee cannot',bold=True,align='left',before=3,after=3,lead=Pt(13))
P('Read forward from January 1962, the rule opened every recession in the sample and called none outside one: '
  '6 October 1969, 17 September 1973, 29 November 1979, 26 February 1981, 26 July 1990, 29 March 2001, '
  '24 December 2007, 12 March 2020 and 3 May 2024. Seven of the nine came before the peak month had ended; the '
  'median call is seven days before it, and it closed all nine a median of seven days after the trough month ended. '
  'Against the eight recessions the committee has dated, measured in months after the end of the peak month, the '
  'rule stands at −1.1, the real-time Sahm rule at +3.6 and the committee’s own announcement at +8.3; at the other '
  'end the rule stands at 0.0 against the committee’s +14.7. Frozen at today’s lines over 1948–2026 it calls all '
  'thirteen recessions and nothing else.',first=0.25,after=4)
P('A date produced by a stated rule from published data is read by everyone on the same morning, fixed the day it is '
  'made, and falsifiable the day a false alarm or a missed recession occurs. It can be written into law, as Extended '
  'Benefits are already keyed to the insured unemployment rate: the rule spoke fifty-one days before the Economic '
  'Stimulus Act of 2008 was signed and fifteen days before the CARES Act. This paper proposes that the rule’s '
  'chronology become the operative dating of United States recessions, the committee’s dates remaining the '
  'historical record against which it is scored.',first=0.25,after=0)

out=os.path.join(RP,'The Bristow-Hall Rule and a New Methodology for Dating Recessions (1 page, v3.29, 2026-09-11).docx')
d.save(out); print(out)
