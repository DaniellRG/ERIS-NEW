"""Editor de PDF: leer, fusionar, dividir, rellenar formularios, firmas."""
import os
import tempfile
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter


def _get_pdf_path(path: str) -> str:
    if os.path.isfile(path):
        return path
    home = Path.home() / "Documents"
    for f in home.rglob(path):
        return str(f)
    return path


def read_pdf(parameters: dict = None, player=None) -> str:
    """Extrae texto de un PDF."""
    params = parameters or {}
    path = _get_pdf_path(params.get("path", ""))
    if not os.path.isfile(path):
        return f"Archivo no encontrado: {path}"

    try:
        reader = PdfReader(path)
        pages = int(params.get("pages", "0"))
        text_parts = []
        for i, page in enumerate(reader.pages):
            if pages > 0 and i >= pages:
                break
            text = page.extract_text() or ""
            if text.strip():
                text_parts.append(f"--- Pagina {i+1} ---\n{text.strip()}")
        if not text_parts:
            return "No se pudo extraer texto del PDF (probablemente son imagenes escaneadas)."
        return "\n\n".join(text_parts)
    except Exception as e:
        return f"Error al leer PDF: {e}"


def merge_pdfs(parameters: dict = None, player=None) -> str:
    """Fusiona varios PDFs en uno."""
    params = parameters or {}
    files = params.get("files", "")
    output = params.get("output", "fusionado.pdf")

    if not files:
        return "Uso: files=doc1.pdf,doc2.pdf output=fusionado.pdf"

    file_list = [f.strip() for f in files.split(",")]
    resolved = []
    for f in file_list:
        p = _get_pdf_path(f)
        if os.path.isfile(p):
            resolved.append(p)
        else:
            return f"Archivo no encontrado: {f}"

    try:
        writer = PdfWriter()
        for f in resolved:
            reader = PdfReader(f)
            for page in reader.pages:
                writer.add_page(page)

        out_path = os.path.join(os.path.dirname(resolved[0]) if len(resolved) == 1 else str(Path.home() / "Documents"), output)
        with open(out_path, "wb") as f:
            writer.write(f)
        return f"PDFs fusionados: {out_path} ({len(writer.pages)} paginas)"
    except Exception as e:
        return f"Error al fusionar: {e}"


def split_pdf(parameters: dict = None, player=None) -> str:
    """Divide un PDF por paginas o rangos."""
    params = parameters or {}
    path = _get_pdf_path(params.get("path", ""))
    if not os.path.isfile(path):
        return f"Archivo no encontrado: {path}"

    try:
        reader = PdfReader(path)
        pages_param = params.get("pages", "")
        output = params.get("output", "")

        if pages_param:
            ranges = []
            for part in pages_param.split(","):
                part = part.strip()
                if "-" in part:
                    a, b = part.split("-")
                    ranges.extend(range(int(a) - 1, int(b)))
                else:
                    ranges.append(int(part) - 1)
        else:
            ranges = list(range(len(reader.pages)))

        if not output:
            base = os.path.splitext(path)[0]
            output = f"{base}_separado.pdf"

        writer = PdfWriter()
        for i in ranges:
            if 0 <= i < len(reader.pages):
                writer.add_page(reader.pages[i])

        with open(output, "wb") as f:
            writer.write(f)
        return f"PDF dividido: {output} ({len(writer.pages)} paginas)"
    except Exception as e:
        return f"Error al dividir: {e}"


def pdf_info(parameters: dict = None, player=None) -> str:
    """Muestra metadatos del PDF."""
    params = parameters or {}
    path = _get_pdf_path(params.get("path", ""))
    if not os.path.isfile(path):
        return f"Archivo no encontrado: {path}"

    try:
        reader = PdfReader(path)
        meta = reader.metadata or {}
        lines = [
            f"Archivo: {os.path.basename(path)}",
            f"Paginas: {len(reader.pages)}",
            f"Titulo: {meta.get('/Title', 'N/A')}",
            f"Autor: {meta.get('/Author', 'N/A')}",
            f"Asunto: {meta.get('/Subject', 'N/A')}",
            f"Productor: {meta.get('/Producer', 'N/A')}",
        ]
        if reader.pdf_header:
            lines.append(f"Version PDF: {reader.pdf_header}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def fill_form(parameters: dict = None, player=None) -> str:
    """Rellena campos de un formulario PDF."""
    params = parameters or {}
    path = _get_pdf_path(params.get("path", ""))
    if not os.path.isfile(path):
        return f"Archivo no encontrado: {path}"

    fields_param = params.get("fields", "")
    if not fields_param:
        return "Uso: fields='campo1=valor1, campo2=valor2'"

    field_dict = {}
    for pair in fields_param.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            field_dict[k.strip()] = v.strip()

    try:
        reader = PdfReader(path)
        writer = PdfWriter()

        for page in reader.pages:
            if "/Annots" in page:
                for ann in page["/Annots"]:
                    obj = ann.get_object()
                    if obj.get("/FT") == "/Tx" and field_dict:
                        fn = obj.get("/T", "")
                        if fn in field_dict:
                            obj.update({"/V": field_dict[fn], "/Ff": 0})
            writer.add_page(page)

        base = os.path.splitext(path)[0]
        out_path = f"{base}_rellenado.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        return f"Formulario rellenado: {out_path}"
    except Exception as e:
        return f"Error al rellenar formulario: {e}"


def add_signature(parameters: dict = None, player=None) -> str:
    """Anade una firma/imagen a una pagina del PDF."""
    params = parameters or {}
    pdf_path = _get_pdf_path(params.get("path", ""))
    sig_path = params.get("signature", "")

    if not os.path.isfile(pdf_path):
        return f"PDF no encontrado: {pdf_path}"
    if not os.path.isfile(sig_path):
        return f"Imagen de firma no encontrada: {sig_path}"

    page_num = int(params.get("page", "1")) - 1
    x = int(params.get("x", "100"))
    y = int(params.get("y", "100"))
    width = int(params.get("width", "150"))

    try:
        from PyPDF2.generic import AnnotationBuilder
        from PIL import Image
        import io

        with Image.open(sig_path) as img:
            h = int(img.height * (width / img.width))
            sig_bytes = io.BytesIO()
            img_resized = img.resize((width, h))
            img_resized.save(sig_bytes, format="PNG")
            sig_bytes.seek(0)

        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            if i == page_num:
                annotation = AnnotationBuilder.image(
                    rect=(x, y, x + width, y + h),
                    stream=sig_bytes.read(),
                )
                page.add_annotation(annotation)
            writer.add_page(page)

        base = os.path.splitext(pdf_path)[0]
        out_path = f"{base}_firmado.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        return f"Firma anadida: {out_path}"
    except Exception as e:
        return f"Error al anadir firma: {e}"
