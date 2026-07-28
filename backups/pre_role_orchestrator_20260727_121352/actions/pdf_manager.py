"""PDF manager module for PDF operations."""

import os
import io
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime


def _get_pypdf():
    try:
        from PyPDF2 import PdfReader, PdfWriter
        return "pypdf2"
    except ImportError:
        pass
    try:
        import pikepdf
        return "pikepdf"
    except ImportError:
        pass
    return None


def _get_reportlab():
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        return True
    except ImportError:
        return False


def _read_pdf_pypdf2(file_path: str) -> str:
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    text_parts = []
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        text_parts.append(f"--- Page {i + 1} ---\n{t}")
    return "\n\n".join(text_parts)


def _read_pdf_pikepdf(file_path: str) -> str:
    import pikepdf
    pdf = pikepdf.open(file_path)
    text_parts = []
    for i, page in enumerate(pdf.pages):
        t = ""
        if "/Contents" in page:
            contents = page["/Contents"]
            if isinstance(contents, pikepdf.Array):
                for stream in contents:
                    t += pikepdf.Stream(pdf, stream).read_bytes().decode("latin-1", errors="replace")
            elif isinstance(contents, pikepdf.Stream):
                t = contents.read_bytes().decode("latin-1", errors="replace")
        text_parts.append(f"--- Page {i + 1} ---\n{t}")
    pdf.close()
    return "\n\n".join(text_parts)


def _info_pypdf2(file_path: str) -> dict:
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    meta = reader.metadata or {}
    return {
        "pages": len(reader.pages),
        "title": str(meta.get("/Title", "")),
        "author": str(meta.get("/Author", "")),
        "subject": str(meta.get("/Subject", "")),
        "creator": str(meta.get("/Creator", "")),
        "producer": str(meta.get("/Producer", "")),
        "encrypted": reader.is_encrypted,
    }


def _info_pikepdf(file_path: str) -> dict:
    import pikepdf
    pdf = pikepdf.open(file_path)
    meta = pdf.docinfo or {}
    return {
        "pages": len(pdf.pages),
        "title": str(meta.get("/Title", "")),
        "author": str(meta.get("/Author", "")),
        "subject": str(meta.get("/Subject", "")),
        "creator": str(meta.get("/Creator", "")),
        "producer": str(meta.get("/Producer", "")),
        "encrypted": pdf.is_encrypted,
    }


def pdf_manager(parameters: dict, player=None) -> str:
    action = parameters.get("action", "read")
    file_path = parameters.get("file", "")
    lib = _get_pypdf()

    if action == "read":
        if not file_path:
            return "Error: 'file' parameter required."
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if lib == "pypdf2":
            text = _read_pdf_pypdf2(file_path)
        elif lib == "pikepdf":
            text = _read_pdf_pikepdf(file_path)
        else:
            return "Error: No PDF library available. Install PyPDF2 or pikepdf."

        return f"PDF Text ({os.path.basename(file_path)}):\n{'=' * 60}\n{text}"

    elif action == "info":
        if not file_path:
            return "Error: 'file' parameter required."
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if lib == "pypdf2":
            info = _info_pypdf2(file_path)
        elif lib == "pikepdf":
            info = _info_pikepdf(file_path)
        else:
            return "Error: No PDF library available."

        lines = [f"PDF Info: {os.path.basename(file_path)}", "=" * 40]
        for k, v in info.items():
            lines.append(f"  {k}: {v if v else '(empty)'}")
        lines.append(f"  file_size: {os.path.getsize(file_path):,} bytes")
        return "\n".join(lines)

    elif action == "merge":
        files = parameters.get("files", [])
        output = parameters.get("output", "")

        if not files:
            return "Error: 'files' parameter required (list of PDF paths)."
        if not output:
            return "Error: 'output' parameter required."

        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            return f"Error: Files not found: {', '.join(missing)}"

        if lib == "pypdf2":
            from PyPDF2 import PdfWriter, PdfReader
            writer = PdfWriter()
            total_pages = 0
            for fp in files:
                reader = PdfReader(fp)
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1
            output = os.path.expanduser(output)
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            with open(output, "wb") as f:
                writer.write(f)
            return f"Merged {len(files)} PDFs ({total_pages} pages) -> {output}"

        elif lib == "pikepdf":
            import pikepdf
            merged = pikepdf.Pdf.new()
            total_pages = 0
            for fp in files:
                src = pikepdf.open(fp)
                merged.pages.extend(src.pages)
                total_pages += len(src.pages)
                src.close()
            output = os.path.expanduser(output)
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            merged.save(output)
            merged.close()
            return f"Merged {len(files)} PDFs ({total_pages} pages) -> {output}"

        return "Error: No PDF library available."

    elif action == "split":
        if not file_path:
            return "Error: 'file' parameter required."
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        output_dir = parameters.get("output_dir", "")
        if not output_dir:
            return "Error: 'output_dir' parameter required."

        output_dir = os.path.expanduser(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(file_path).stem

        if lib == "pypdf2":
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                writer = PdfWriter()
                writer.add_page(page)
                out_path = os.path.join(output_dir, f"{base_name}_page_{i + 1}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)
            return f"Split {len(reader.pages)} pages to {output_dir}/"

        elif lib == "pikepdf":
            import pikepdf
            pdf = pikepdf.open(file_path)
            for i, page in enumerate(pdf.pages):
                new_pdf = pikepdf.Pdf.new()
                new_pdf.pages.append(page)
                out_path = os.path.join(output_dir, f"{base_name}_page_{i + 1}.pdf")
                new_pdf.save(out_path)
                new_pdf.close()
            count = len(pdf.pages)
            pdf.close()
            return f"Split {count} pages to {output_dir}/"

        return "Error: No PDF library available."

    elif action == "create":
        text = parameters.get("text", "")
        output = parameters.get("output", "")

        if not text:
            return "Error: 'text' parameter required."
        if not output:
            return "Error: 'output' parameter required."

        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        if _get_reportlab():
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(output, pagesize=letter)
            width, height = letter
            y = height - 50
            lines = text.split("\n")

            for line in lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, line[:100])
                y -= 14

            c.save()
            return f"Created PDF with {len(lines)} lines -> {output}"

        else:
            try:
                import fpdf
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                for line in text.split("\n"):
                    pdf.cell(0, 7, line[:120], new_x="LMARGIN", new_y="NEXT")
                pdf.output(output)
                return f"Created PDF -> {output}"
            except ImportError:
                pass

        return "Error: No PDF creation library available. Install reportlab or fpdf2."

    elif action == "encrypt":
        if not file_path:
            return "Error: 'file' parameter required."
        password = parameters.get("password", "")
        output = parameters.get("output", "")
        if not password:
            return "Error: 'password' parameter required."
        if not output:
            return "Error: 'output' parameter required."

        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        if lib == "pypdf2":
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(file_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            with open(output, "wb") as f:
                writer.write(f)
            return f"Encrypted PDF -> {output}"

        return "Error: PDF encryption requires PyPDF2."

    elif action == "watermark":
        if not file_path:
            return "Error: 'file' parameter required."
        watermark_text = parameters.get("text", "WATERMARK")
        output = parameters.get("output", "")
        if not output:
            return "Error: 'output' parameter required."

        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        if lib == "pypdf2" and _get_reportlab():
            from PyPDF2 import PdfReader, PdfWriter
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas as rl_canvas
            import io

            reader = PdfReader(file_path)
            writer = PdfWriter()

            for page in reader.pages:
                packet = io.BytesIO()
                w, h = float(page.mediabox.width), float(page.mediabox.height)
                c = rl_canvas.Canvas(packet, pagesize=(w, h))
                c.setFont("Helvetica-Bold", 60)
                c.setFillAlpha(0.15)
                c.saveState()
                c.translate(w / 2, h / 2)
                c.rotate(45)
                c.drawCentredString(0, 0, watermark_text)
                c.restoreState()
                c.save()
                packet.seek(0)
                wm_reader = PdfReader(packet)
                page.merge_page(wm_reader.pages[0])
                writer.add_page(page)

            with open(output, "wb") as f:
                writer.write(f)
            return f"Watermarked PDF with '{watermark_text}' -> {output}"

        return "Error: Watermarking requires PyPDF2 and reportlab."

    elif action == "compress":
        if not file_path:
            return "Error: 'file' parameter required."
        output = parameters.get("output", "")
        if not output:
            return "Error: 'output' parameter required."

        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        orig_size = os.path.getsize(file_path)

        if lib == "pikepdf":
            import pikepdf
            pdf = pikepdf.open(file_path)
            pdf.save(output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
            pdf.close()
            new_size = os.path.getsize(output)
            ratio = (1 - new_size / orig_size) * 100 if orig_size else 0
            return f"Compressed: {orig_size:,} -> {new_size:,} bytes ({ratio:.1f}% reduction) -> {output}"

        elif lib == "pypdf2":
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(file_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(output, "wb") as f:
                writer.write(f)
            new_size = os.path.getsize(output)
            ratio = (1 - new_size / orig_size) * 100 if orig_size else 0
            return f"Compressed: {orig_size:,} -> {new_size:,} bytes ({ratio:.1f}% reduction) -> {output}"

        return "Error: No PDF library available."

    else:
        return (
            f"Error: Unknown action '{action}'. Available:\n"
            "  read, info, merge, split, create, encrypt, watermark, compress"
        )
