#!/usr/bin/env python3
"""Build Paper 2 as a .docx in the layout of Paper 1 (Hall & Bristow 2026). Adapted from Paper 1's build_manuscript.py.

v5.0 measured spec (from the PDF character stream):
  page 612x792 pt (US Letter), margins 72 pt all round
  title      15 pt TNR bold, centered
  authors    12 pt TNR, centered, superscript footnote marker
  affil.     11 pt TNR italic, centered
  wp line    11 pt TNR italic, centered
  'Abstract' 11 pt TNR bold, centered
  abstract   11 pt TNR justified, 36 pt indent each side, 12.5 pt exact leading
  body       12 pt TNR justified, 18 pt first-line indent, 17 pt exact leading, 8 pt after
  headings   12 pt TNR bold, left, no indent
  tables     10 pt TNR, bold header row, grid borders
  captions   10 pt ('Table 1.'/'Figure 1.' bold, figure caption body italic)
  notes      10 pt ('Notes:' bold)
  references 11 pt, 18 pt hanging indent, 13 pt exact leading
  page no.   10 pt centered in footer
"""
import re, sys, os, zipfile, shutil
import os
FIGDIR = os.environ.get('FIGDIR') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'figures')

from docx import Document
from docx.shared import Pt, Inches, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TNR = 'Times New Roman'

# ---------------------------------------------------------------- low-level

def set_exact_leading(par, pts):
    pPr = par._p.get_or_add_pPr()
    sp = pPr.find(qn('w:spacing'))
    if sp is None:
        sp = OxmlElement('w:spacing'); pPr.append(sp)
    sp.set(qn('w:line'), str(int(round(pts * 20))))
    sp.set(qn('w:lineRule'), 'exact')

def kill_widow_control(par):
    pPr = par._p.get_or_add_pPr()
    w = OxmlElement('w:widowControl'); w.set(qn('w:val'), '1'); pPr.append(w)

def run(par, text, size=11, bold=False, italic=False, sup=False):
    r = par.add_run(smart_quotes(text))
    r.font.name = TNR
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    rPr = r._element.get_or_add_rPr()
    rf = rPr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rPr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), TNR)
    if sup:
        va = OxmlElement('w:vertAlign'); va.set(qn('w:val'), 'superscript'); rPr.append(va)
    return r

def para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_indent=None, left=None,
         right=None, before=0, after=8, leading=14.0, hanging=None, keep_next=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if first_indent is not None: pf.first_line_indent = Pt(first_indent)
    if hanging is not None:      pf.first_line_indent = Pt(-hanging)
    if left is not None:         pf.left_indent = Pt(left)
    if right is not None:        pf.right_indent = Pt(right)
    set_exact_leading(p, leading)
    kill_widow_control(p)
    if keep_next: pf.keep_with_next = True
    return p

# --------------------------------------------------------- inline markdown


def smart_quotes(t):
    """Straight quotes to typographic quotes, matching the v5.0 typesetting."""
    out=[]; in_d=False
    prev=''
    for ch in t:
        if ch == '"':
            out.append('\u201c' if (not prev or prev in ' ([{\u2014\u2013-\n\t') else '\u201d')
        elif ch == "'":
            out.append('\u2018' if (not prev or prev in ' ([{\u2014\u2013-\n\t') else '\u2019')
        else:
            out.append(ch)
        prev = ch
    return ''.join(out)

INLINE = re.compile(r'(\*\*.+?\*\*|\*[^*]+?\*)')

def emit_inline(p, text, size=11, base_italic=False):
    """Render **bold** and *italic* spans; drop code backticks."""
    text = text.replace('`', '')
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            run(p, tok[2:-2], size=size, bold=True, italic=base_italic)
        elif tok.startswith('*') and tok.endswith('*') and len(tok) > 2:
            run(p, tok[1:-1], size=size, italic=True)
        else:
            run(p, tok, size=size, italic=base_italic)

# --------------------------------------------------------------- footnote

FN_STYLES = '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:basedOn w:val="DefaultParagraphFont"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:vertAlign w:val="superscript"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>'

FOOTNOTES_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>
<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
<w:footnote w:id="1"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>
<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:footnoteRef/></w:r>
<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve"> FOOTNOTE_TEXT</w:t></w:r>
</w:p></w:footnote>
</w:footnotes>'''

def add_footnote_marker(par):
    """Insert a real footnote reference (id 1) at the end of `par`."""
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    for a in ('w:ascii', 'w:hAnsi', 'w:cs'): rf.set(qn(a), TNR)
    rPr.append(rf)
    # Render the marker at exactly 8.0 pt (v5.0's measured size). The
    # FootnoteReference character style carries vertAlign=superscript, which
    # LibreOffice renders at 0.58 x the run size and so cannot land on 8.0 at
    # half-point granularity; overriding to baseline and raising with w:position
    # gives the size exactly and keeps the superscript position.
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '28'); rPr.append(sz)
    szcs = OxmlElement('w:szCs'); szcs.set(qn('w:val'), '28'); rPr.append(szcs)
    r.append(rPr)
    ref = OxmlElement('w:footnoteReference'); ref.set(qn('w:id'), '1')
    r.append(ref)
    par._p.append(r)

def inject_footnotes(path, text):
    """Post-process the saved .docx to add word/footnotes.xml and wire it up."""
    tmp = path + '.tmp'
    zin = zipfile.ZipFile(path, 'r')
    names = zin.namelist()
    zout = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == 'word/styles.xml':
            s = data.decode('utf8')
            if 'FootnoteReference' not in s:
                s = s.replace('</w:styles>', FN_STYLES + '</w:styles>')
            data = s.encode('utf8')
        elif item.filename == '[Content_Types].xml':
            s = data.decode('utf8')
            if 'footnotes+xml' not in s:
                s = s.replace('</Types>',
                    '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/></Types>')
            data = s.encode('utf8')
        elif item.filename == 'word/_rels/document.xml.rels':
            s = data.decode('utf8')
            if 'footnotes.xml' not in s:
                s = s.replace('</Relationships>',
                    '<Relationship Id="rIdFootnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/></Relationships>')
            data = s.encode('utf8')
        zout.writestr(item, data)
    if 'word/footnotes.xml' not in names:
        text = smart_quotes(text)
        esc = (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        zout.writestr('word/footnotes.xml', FOOTNOTES_XML.replace('FOOTNOTE_TEXT', esc))
    zin.close(); zout.close()
    shutil.move(tmp, path)

# ------------------------------------------------------------------ tables

def shade_none(cell):
    pass

def set_cell_margins(table, top=40, bottom=40, left=80, right=80):
    tblPr = table._tbl.tblPr
    mar = OxmlElement('w:tblCellMar')
    for tag, val in (('top', top), ('left', left), ('bottom', bottom), ('right', right)):
        e = OxmlElement('w:' + tag)
        e.set(qn('w:w'), str(val)); e.set(qn('w:type'), 'dxa')
        mar.append(e)
    tblPr.append(mar)

def grid_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement('w:' + edge)
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '6')
        e.set(qn('w:space'), '0'); e.set(qn('w:color'), '000000')
        borders.append(e)
    tblPr.append(borders)

def add_table(doc, rows, widths_in):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    grid_borders(t); set_cell_margins(t)
    for _r in t.rows:
        _trPr = _r._tr.get_or_add_trPr()
        for _tag in ('w:cantSplit',):
            for _e in _trPr.findall(qn(_tag)): _trPr.remove(_e)
    for ri, r in enumerate(rows):
        for ci, cellText in enumerate(r):
            cell = t.cell(ri, ci)
            cell.width = Inches(widths_in[ci])
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.alignment = (WD_ALIGN_PARAGRAPH.CENTER if ri == 0
                                            else WD_ALIGN_PARAGRAPH.LEFT)
            set_exact_leading(p, 11.5)
            if ri == 0:
                run(p, cellText, size=10, bold=True)
            else:
                emit_inline(p, cellText, size=10)
    for row in t.rows:
        for ci, cell in enumerate(row.cells):
            cell.width = Inches(widths_in[ci])
    return t

# ------------------------------------------------------------------ footer

def add_page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    for instr in ('begin', 'PAGE', 'end'):
        r = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        rf = OxmlElement('w:rFonts')
        for a in ('w:ascii', 'w:hAnsi', 'w:cs'): rf.set(qn(a), TNR)
        rPr.append(rf)
        sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '20'); rPr.append(sz)
        r.append(rPr)
        if instr == 'begin':
            f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'begin'); r.append(f)
        elif instr == 'end':
            f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'end'); r.append(f)
        else:
            t = OxmlElement('w:instrText'); t.set(qn('xml:space'), 'preserve')
            t.text = ' PAGE '; r.append(t)
        p._p.append(r)

# -------------------------------------------------------------- the builder

FOOTNOTE_TEXT = None   # no title-page footnote; set a string to restore one

def build(md_path, out_path):
    src = open(md_path, encoding='utf8').read().split('\n')

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin = sec.bottom_margin = Inches(0.9)
    sec.left_margin = sec.right_margin = Inches(1)
    sec.footer_distance = Inches(0.55)
    st = doc.styles['Normal']
    st.font.name = TNR; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), TNR)
    add_page_number_footer(sec)

    REFS_MODE[0] = False
    i, n = 0, len(src)
    in_abstract = False
    title_done = False
    first_para_flag = False

    def peek(k=0):
        return src[i + k] if i + k < n else ''

    while i < n:
        line = src[i].rstrip()

        # ---- skip blanks and horizontal rules -------------------------
        if not line.strip() or line.strip() == '---':
            i += 1; continue

        # ---- title block ----------------------------------------------
        if line.startswith('# ') and not title_done:
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=6, leading=18)
            run(p, line[2:].strip(), size=15, bold=True)
            title_done = True
            i += 1; continue

        if line.strip().strip('*').startswith('Anthony Hall'):
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=1, leading=13)
            run(p, 'Anthony Hall and Duke K. Bristow', size=11)
            if FOOTNOTE_TEXT:
                add_footnote_marker(p)
                # The footnote marker is part of the centered line, so centering the
                # paragraph centers name+marker and pushes the names left by half the
                # marker's width. A left indent equal to that width restores exact
                # centering of the names, leaving the marker to hang to their right.
                p.paragraph_format.left_indent = Pt(4)
            i += 1; continue

        if line.startswith('*Marshall School'):
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=1, leading=13)
            run(p, line.strip('*'), size=11, italic=True)
            i += 1; continue

        if line.startswith('*FBE Working Paper'):
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=14, leading=13)
            run(p, line.strip('*'), size=11, italic=True)
            i += 1; continue

        # ---- Abstract --------------------------------------------------
        if line.strip() == '## Abstract':
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=5, leading=13)
            run(p, 'Abstract', size=11, bold=True)
            in_abstract = True
            i += 1; continue

        # ---- section headings ------------------------------------------
        if line.startswith('## '):
            in_abstract = False
            txt = line[3:].strip()
            REFS_MODE[0] = txt.lower().startswith('references')
            p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, before=20, after=4,
                     leading=14, keep_next=True)
            run(p, txt, size=12, bold=True)
            first_para_flag = True
            i += 1; continue

        # ---- '### Subhead' becomes a run-in lead on the next paragraph --
        if line.startswith('### '):
            lead = line[4:].strip().rstrip('.')
            i += 1
            while i < n and not src[i].strip():
                i += 1
            body = src[i].rstrip() if i < n else ''
            p = para(doc, first_indent=18)
            emit_inline(p, lead + '. ' + body, size=12)
            i += 1; continue

        # ---- figure image ----------------------------------------------
        m = re.match(r'!\[\]\((fig\d\.png)\)\{width=([\d.]+)in\}', line.strip())
        if m:
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.space_before = Pt(12); pf.space_after = Pt(6)
            pf.first_line_indent = Pt(0)
            pf.left_indent = Pt(-9); pf.right_indent = Pt(0)
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.keep_with_next = True
            r = p.add_run()
            FIGMAP={'fig1.png':'figure_speed.png','fig2.png':'figure3_box_comparison.png','fig3.png':'figure2_rule_lags.png'}
            r.add_picture(os.path.join(FIGDIR, FIGMAP.get(m.group(1), m.group(1))), width=Inches(float(m.group(2))))
            i += 1; continue

        # ---- figure caption --------------------------------------------
        if line.startswith('**Figure '):
            m2 = re.match(r'\*\*(Figure \d+\.)\*\*\s*\*(.+)\*\s*$', line.strip())
            p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, after=12, leading=12)
            p.paragraph_format.first_line_indent = Pt(0)
            if m2:
                run(p, m2.group(1) + ' ', size=10, bold=True)
                run(p, m2.group(2), size=10, italic=True)
            else:
                emit_inline(p, line, size=10)
            i += 1; continue

        # ---- table caption ----------------------------------------------
        if re.match(r'\*\*Table \d+\..*\*\*$', line.strip()):
            p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, before=10, after=4, leading=13,
                     keep_next=True)
            p.paragraph_format.first_line_indent = Pt(0)
            run(p, line.strip().strip('*'), size=10, bold=True)
            i += 1; continue

        # ---- pipe table ---------------------------------------------------
        if line.startswith('|'):
            rows = []
            while i < n and src[i].strip().startswith('|'):
                cells = [c.strip() for c in src[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            ncol = len(rows[0])
            if ncol == 4:
                widths = [1.35, 2.35, 1.05, 1.75]
            elif ncol == 3:
                widths = [1.55, 2.45, 2.5]
            elif ncol == 2:
                widths = [2.6, 3.9]
            elif ncol == 5 and rows[0][0].startswith('Run'):
                widths = [1.3, 0.95, 0.8, 2.25, 1.2]
            elif ncol == 5:
                widths = [1.1, 1.7, 1.7, 1.1, 0.9]
            elif ncol == 6:
                widths = [1.25, 1.45, 0.7, 1.45, 0.7, 0.95]
            else:
                widths = [6.5 / ncol] * ncol
            add_table(doc, rows, widths)
            para(doc, after=0, leading=6)
            continue

        # ---- table notes ---------------------------------------------------
        if line.startswith('*Notes:*') or line.startswith('*Sources:*'):
            m3 = re.match(r'\*(Notes:|Sources:)\*\s*(.+)$', line.strip())
            p = para(doc, after=12, leading=11.5)
            p.paragraph_format.first_line_indent = Pt(0)
            run(p, m3.group(1) + ' ', size=10, bold=True)
            emit_inline(p, m3.group(2), size=10)
            i += 1; continue

        # ---- references (hanging indent) -------------------------------------
        if REFS_MODE[0]:
            p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, hanging=18, left=18,
                     after=2, leading=12.5)
            emit_inline(p, line.strip(), size=11)
            i += 1; continue

        # ---- bullet item -------------------------------------------------------
        if line.strip().startswith('- '):
            p = para(doc, left=36, hanging=18, after=4)
            emit_inline(p, line.strip()[2:], size=11)
            i += 1; continue

        # ---- ordinary body paragraph -----------------------------------------
        p = para(doc, first_indent=18)
        emit_inline(p, line.strip(), size=11 if in_abstract else 12)
        if in_abstract:
            pf = p.paragraph_format
            pf.left_indent = Pt(36); pf.right_indent = Pt(36)
            pf.first_line_indent = Pt(0)
            pf.space_after = Pt(12)
            set_exact_leading(p, 12.5)
        i += 1

    doc.save(out_path)
    if FOOTNOTE_TEXT:
        inject_footnotes(out_path, FOOTNOTE_TEXT)
    return out_path


REFS_MODE = [False]

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
    print('built', sys.argv[2])
