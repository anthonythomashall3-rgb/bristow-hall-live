"""B-LAND-4 §2.1 — measure RTDSM xlsx layout before parsing at scale.
Writes findings to research/AL4_layout.txt. Read-only on prefetch cache."""
import sys, io, zipfile
from pathlib import Path
import openpyxl


def load_ws(path):
    """Load first worksheet, stripping docProps/core.xml (Phil-Fed xlsx carry a
    date-only <modified> that openpyxl 3.1.5 on py3.8 refuses)."""
    src = zipfile.ZipFile(path)
    buf = io.BytesIO()
    dst = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    for item in src.infolist():
        if item.filename == "docProps/core.xml":
            continue
        dst.writestr(item, src.read(item.filename))
    dst.close()
    src.close()
    buf.seek(0)
    return openpyxl.load_workbook(buf, read_only=True, data_only=True)

ROOT = Path("research/prefetch/rtdsm")
targets = [
    ("routput", "ROUTPUTQvQd.xlsx"),   # quarterly-vintage, quarterly-obs
    ("ruc", "rucQvMd.xlsx"),           # quarterly-vintage, monthly-obs (member: UNRATE)
    ("employ", "employMvMd.xlsx"),     # monthly-vintage, monthly-obs (member: PAYEMS)
]
out = []
for var, fname in targets:
    p = ROOT / var / fname
    out.append("=" * 70)
    out.append(f"VAR={var} FILE={fname} bytes={p.stat().st_size}")
    wb = load_ws(p)
    out.append(f"sheets={wb.sheetnames}")
    ws = wb[wb.sheetnames[0]]
    out.append(f"dims={ws.max_row}rows x {ws.max_column}cols")
    rows = list(ws.iter_rows(min_row=1, max_row=6, values_only=True))
    for i, r in enumerate(rows):
        # show first 6 and last 3 cells of each of the first rows
        head = list(r[:6])
        tail = list(r[-3:])
        out.append(f"  row{i+1}: head={head} ... tail={tail}")
    # last data row first cells
    last = list(ws.iter_rows(min_row=ws.max_row, max_row=ws.max_row, values_only=True))[0]
    out.append(f"  LASTrow head={list(last[:4])} tail={list(last[-3:])}")
    # header row (row 1) full col names -> count vintage columns
    hdr = rows[0]
    out.append(f"  header col0={hdr[0]!r} col1={hdr[1]!r} col2={hdr[2]!r} last2={list(hdr[-2:])}")
    wb.close()
Path("research/AL4_layout.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
