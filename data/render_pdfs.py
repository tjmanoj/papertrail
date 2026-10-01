#!/usr/bin/env python3
"""Render regulatory documents as PDFs via soffice.

Reads regulatory_document.csv and regulatory_document_clause.csv,
builds a simple HTML file per document, then converts to PDF with
soffice --headless.
"""
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PDF_DIR = OUT / "pdf"


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Load documents
    docs = {}
    with open(OUT / "regulatory_document.csv", newline="") as f:
        for row in csv.DictReader(f):
            docs[row["document_id"]] = row

    # Load clauses grouped by document
    clauses_by_doc = {}
    with open(OUT / "regulatory_document_clause.csv", newline="") as f:
        for row in csv.DictReader(f):
            clauses_by_doc.setdefault(row["document_id"], []).append(row)

    with tempfile.TemporaryDirectory() as tmpdir:
        html_files = []
        for doc_id, doc in sorted(docs.items()):
            clauses = clauses_by_doc.get(doc_id, [])
            clauses.sort(key=lambda c: [int(x) for x in c["clause_number"].split(".")])

            html = _build_html(doc, clauses)
            html_path = os.path.join(tmpdir, f"{doc_id}.html")
            with open(html_path, "w") as hf:
                hf.write(html)
            html_files.append(html_path)

        # Convert all at once
        cmd = [
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(PDF_DIR),
        ] + html_files
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"soffice failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    # Verify
    print(f"\nGenerated PDFs in {PDF_DIR}:")
    for doc_id in sorted(docs):
        pdf_path = PDF_DIR / f"{doc_id}.pdf"
        if pdf_path.exists():
            size = pdf_path.stat().st_size
            # Check it starts with %PDF
            with open(pdf_path, "rb") as pf:
                header = pf.read(5)
            valid = header == b"%PDF-"
            print(f"  {pdf_path.name:40s}  {size:>8,} bytes  {'VALID' if valid else 'INVALID'}")
        else:
            print(f"  {pdf_path.name:40s}  MISSING")

    print(f"\nTotal: {len(docs)} documents")


def _build_html(doc, clauses):
    title = _esc(doc["title"])
    version = _esc(doc["version"])
    eff_date = _esc(doc["effective_date"])
    jurisdiction = _esc(doc["jurisdiction"])
    watermark = _esc(doc["synthetic_watermark"])
    doc_type = _esc(doc["document_type"])

    clause_html = []
    for c in clauses:
        clause_html.append(
            f'<div class="clause">'
            f'<h2>&sect;{_esc(c["clause_number"])} {_esc(c["clause_title"])}</h2>'
            f'<p>{_esc(c["clause_text"])}</p>'
            f'</div>'
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: A4;
    margin: 2.5cm 2cm;
    @bottom-center {{
        content: "{watermark}";
        font-size: 8pt;
        color: #999;
    }}
}}
body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #222;
    max-width: 18cm;
    margin: 0 auto;
}}
.header {{
    border-bottom: 2px solid #333;
    padding-bottom: 12pt;
    margin-bottom: 18pt;
}}
.header h1 {{
    font-size: 16pt;
    margin: 0 0 6pt 0;
}}
.meta {{
    font-size: 9pt;
    color: #666;
}}
.clause {{
    margin-bottom: 14pt;
    page-break-inside: avoid;
}}
.clause h2 {{
    font-size: 12pt;
    margin: 12pt 0 4pt 0;
    color: #333;
}}
.clause p {{
    margin: 0;
    text-align: justify;
}}
.watermark {{
    position: fixed;
    bottom: 10px;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 8pt;
    color: #bbb;
}}
.footer-watermark {{
    text-align: center;
    font-size: 8pt;
    color: #bbb;
    margin-top: 30pt;
    padding-top: 10pt;
    border-top: 1px solid #ddd;
}}
</style>
</head>
<body>
<div class="watermark">{watermark}</div>
<div class="header">
    <h1>{title}</h1>
    <div class="meta">
        Document Type: {doc_type} &nbsp;|&nbsp;
        Version: {version} &nbsp;|&nbsp;
        Effective: {eff_date} &nbsp;|&nbsp;
        Jurisdiction: {jurisdiction}
    </div>
</div>
{''.join(clause_html)}
<div class="footer-watermark">{watermark}</div>
</body>
</html>"""


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    main()
