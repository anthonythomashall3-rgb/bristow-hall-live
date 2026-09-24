import sys
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

def iter_block(doc):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'): yield Paragraph(child, doc)
        elif child.tag == qn('w:tbl'): yield Table(child, doc)

doc = Document(sys.argv[1])
out=[]
for b in iter_block(doc):
    if isinstance(b, Table):
        rows=[]
        for r in b.rows:
            rows.append('| ' + ' | '.join(c.text.strip().replace('\n',' ') for c in r.cells) + ' |')
        if rows:
            hdr=rows[0]; ncol=hdr.count('|')-1
            rows.insert(1,'|'+'---|'*ncol)
        out.append('\n'.join(rows))
    else:
        t=b.text.strip()
        st=(b.style.name or '')
        if not t: continue
        if st.startswith('Heading'):
            lvl=''.join(ch for ch in st if ch.isdigit()) or '1'
            out.append('#'*int(lvl)+' '+t)
        elif st.startswith('Title'):
            out.append('# '+t)
        else:
            out.append(t)
open(sys.argv[2],'w').write('\n\n'.join(out)+'\n')
print('wrote', sys.argv[2], len(out),'blocks')
