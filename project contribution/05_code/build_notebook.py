"""Turn nutrition_label.py into a self-contained Colab notebook.

Usage (from this folder):  python build_notebook.py
Output: ../04_notebook_video_nutrition_label.ipynb

Why: nutrition_label.py is the single source of truth (cells are marked with "# %%"). The notebook is
generated from it, so the two can never drift apart. The HTML template is pasted into the notebook, so
Colab users need to upload only one file.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "nutrition_label.py").read_text(encoding="utf-8")
template = (HERE / "label_template.html").read_text(encoding="utf-8")
assert "'''" not in template

src = src.replace(
    'TEMPLATE_PATH = find_file("label_template.html") or "label_template.html"\n'
    'template = open(TEMPLATE_PATH, encoding="utf-8").read()\n',
    "template = TEMPLATE   # defined in the last cell of Step 8's setup (pasted HTML)\n")
assert "template = TEMPLATE" in src

cells = []
for chunk in src.split("# %%")[1:]:
    if chunk.startswith(" [markdown]"):
        body = chunk[len(" [markdown]"):].strip("\n")
        text = "\n".join(line[2:] if line.startswith("# ") else line.lstrip("#") for line in body.splitlines())
        cells.append(("markdown", text))
    else:
        cells.append(("code", chunk.strip("\n")))

# Colab install line first; template cell just before the build cell.
cells.insert(2, ("code", "!pip -q install pandas numpy matplotlib google-genai"))
cells.insert(len(cells) - 1, ("code", "# The prototype's HTML template (you don't need to read or change this).\nTEMPLATE = r'''" + template + "'''\nprint(len(TEMPLATE), 'characters of HTML template loaded')"))

nb = {"nbformat": 4, "nbformat_minor": 5,
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "cells": []}
for i, (kind, text) in enumerate(cells):
    cell = {"cell_type": kind, "id": f"c{i:02d}", "metadata": {}, "source": text.splitlines(keepends=True)}
    if kind == "code":
        cell.update(outputs=[], execution_count=None)
    nb["cells"].append(cell)

out = HERE.parent / "04_notebook_video_nutrition_label.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("Wrote", out, "with", len(cells), "cells")
