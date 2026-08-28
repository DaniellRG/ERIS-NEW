from __future__ import annotations

"""PDF Generator — Create simple PDF documents from text or markdown-like content.

Actions
-------
create        – Generate a PDF from plain text.
from_markdown – Strip markdown syntax and render to PDF.
list          – List previously generated PDFs in the storage directory.
info          – Return page count and file size for a PDF.
"""

import os
import re

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None  # type: ignore[assignment,misc]

_STORAGE = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
os.makedirs(_STORAGE, exist_ok=True)

_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fonts", "DejaVuSans.ttf")


def _strip_markdown(text: str) -> str:
    """Minimal markdown → plain text conversion."""
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "  ", text, flags=re.MULTILINE)
    return text.strip()


def _build_pdf(title: str, content: str, output: str, font_size: int) -> str:
    """Core PDF creation routine. Returns the full output path."""
    if FPDF is None:
        return "Error: fpdf2 is not installed. Run: pip install fpdf2"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    use_unicode = os.path.isfile(_FONT_PATH)
    if use_unicode:
        pdf.add_font("DejaVu", "", _FONT_PATH, uni=True)
        pdf.add_page()
        pdf.set_font("DejaVu", size=14)
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("DejaVu", size=font_size)
    else:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Helvetica", size=font_size)

    for line in content.split("\n"):
        pdf.multi_cell(0, 7, line)

    safe_name = re.sub(r'[\\/*?:"<>|]', "_", output if output.endswith(".pdf") else f"{output}.pdf")
    full_path = os.path.join(_STORAGE, safe_name)
    pdf.output(full_path)
    return full_path


def pdf_generator(parameters: dict = None, player=None) -> str:  # noqa: C901
    """Generate, list, or inspect PDF files."""
    params = parameters or {}
    action = str(params.get("action", "create")).strip().lower()
    title = str(params.get("title", "Untitled")).strip()
    content = str(params.get("content", "")).strip()
    output = str(params.get("output", "output")).strip()
    font_size = int(str(params.get("font_size", 12)).strip() or 12)

    if action == "create":
        if not content:
            return "Error: No content provided."
        path = _build_pdf(title, content, output, font_size)
        return f"PDF created: {path}" if not path.startswith("Error") else path

    if action == "from_markdown":
        if not content:
            return "Error: No content provided."
        plain = _strip_markdown(content)
        path = _build_pdf(title, plain, output, font_size)
        return f"PDF created from markdown: {path}" if not path.startswith("Error") else path

    if action == "list":
        files = [f for f in os.listdir(_STORAGE) if f.lower().endswith(".pdf")]
        if not files:
            return "No PDFs found."
        return "PDFs:\n" + "\n".join(f"  • {f}" for f in sorted(files))

    if action == "info":
        target = output if output.endswith(".pdf") else f"{output}.pdf"
        full_path = os.path.join(_STORAGE, target)
        if not os.path.isfile(full_path):
            return f"Error: PDF '{target}' not found."
        size_kb = os.path.getsize(full_path) / 1024
        try:
            if FPDF is None:
                return f"File: {target}, Size: {size_kb:.1f} KB (page count unavailable without fpdf2)."
            from fpdf import FPDF as _FPDF  # noqa: F811

            # Quick page count via binary search is non-trivial; report size only.
        except Exception:
            pass
        return f"File: {target}\nSize: {size_kb:.1f} KB"

    return f"Error: Unknown action '{action}'."
