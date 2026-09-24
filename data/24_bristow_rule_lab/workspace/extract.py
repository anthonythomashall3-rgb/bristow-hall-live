from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
import sys

def iter_block_items(parent):
    from docx.oxml.ns import qn
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)

doc = Document(sys.argv[1])
out = []
ti = 0
for block in iter_block_items(doc):
    if isinstance(block, Paragraph):
        t = block.text.strip()
        if t:
            out.append(t)
    else:
        ti += 1
        out.append(f"\n=== TABLE {ti} ===")
        for r_i, row in enumerate(block.rows):
            cells = [c.text.strip().replace("\n"," | ") for c in row.cells]
            out.append(f"[R{r_i}] " + " ;; ".join(cells))
        out.append(f"=== END TABLE {ti} ===\n")
print("\n".join(out))
