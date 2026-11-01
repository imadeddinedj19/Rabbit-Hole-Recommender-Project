"""Convert ../03_report_part4.md into ../03_report_part4.docx (Word), for teammates who don't use Markdown.

Usage (from this folder): python build_docx.py
Handles what the report uses: headings, paragraphs with **bold**, bullet and numbered lists, quotes,
tables and images.
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
md = (ROOT / "03_report_part4.md").read_text(encoding="utf-8").splitlines()

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.2)


def add_runs(par, text):
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        part = part.replace("`", "")
        if not part:
            continue
        chunks = re.split(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", part)   # *italic*
        for j, c in enumerate(chunks):
            r = par.add_run(c)
            r.bold = i % 2 == 1
            r.italic = j % 2 == 1


i = 0
while i < len(md):
    line = md[i]
    if line.startswith("#"):
        level = len(line) - len(line.lstrip("#"))
        doc.add_heading(line.lstrip("# ").strip(), level=min(level - 1, 3) if level > 1 else 0)
    elif line.startswith("!["):
        path = re.search(r"\((.+?)\)", line).group(1)
        doc.add_picture(str(ROOT / path), width=Cm(15))
    elif line.startswith("|"):
        rows = []
        while i < len(md) and md[i].startswith("|"):
            cells = [c.strip() for c in md[i].strip().strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                rows.append(cells)
            i += 1
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Light Grid Accent 2"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for r, cells in enumerate(rows):
            for c, text in enumerate(cells):
                cell = t.cell(r, c)
                cell.text = ""
                add_runs(cell.paragraphs[0], text)
                for run in cell.paragraphs[0].runs:
                    run.font.size = Pt(9.5)
                    run.bold = run.bold or r == 0
        doc.add_paragraph()
        continue
    elif line.startswith("> "):
        p = doc.add_paragraph(style="Intense Quote")
        add_runs(p, line[2:].strip('"'))
    elif line.startswith("- "):
        add_runs(doc.add_paragraph(style="List Bullet"), line[2:])
    elif re.match(r"\d+\. ", line):
        add_runs(doc.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", line))
    elif line.strip():
        add_runs(doc.add_paragraph(), line)
    i += 1

for p in doc.paragraphs:
    if p.style.name.startswith("Heading") or p.style.name == "Title":
        for r in p.runs:
            r.font.color.rgb = RGBColor(0x11, 0x11, 0x11)

out = ROOT / "03_report_part4.docx"
doc.save(out)
print("Wrote", out)
