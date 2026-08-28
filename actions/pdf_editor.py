"""Editor de PDF: leer, fusionar, dividir, rellenar formularios, firmas."""
import os
import tempfile
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter


def _normalize_params(parameters: dict | None) -> dict:
    """Alias de parámetros para alinear la declaración con la implementación."""
    params = dict(parameters or {})
    if "path" not in params and params.get("file_path"):
        params["path"] = params["file_path"]
    if "output" not in params and params.get("output_path"):
        params["output"] = params["output_path"]
    if "fields" not in params and params.get("form_data"):
        params["fields"] = params["form_data"]
    return params


def pdf_editor(parameters: dict = None, player=None) -> str:
    """Dispatcher: enruta por action a la función correcta (read/merge/split/fill/info)."""
    params = _normalize_params(parameters)
    action = str(params.get("action", "read")).lower().strip()
    if action in ("read", "leer"):
        return read_pdf(params, player)
    if action in ("merge", "unir", "fusion"):
        return merge_pdfs(params, player)
    if action in ("split", "dividir"):
        return split_pdf(params, player)
    if action in ("fill_form", "fill", "llenar"):
        return fill_form(params, player)
    if action in ("info", "metadata"):
        return pdf_info(params, player)
    if action in ("extract_images",):
        return extract_images(params, player)
    return f"Accion '{action}' desconocida. Usa: read, merge, split, fill_form, extract_images, info."


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


def extract_images(parameters: dict = None, player=None) -> str:
    """Extrae las imagenes de un PDF a una carpeta (PNG/JPG segun su formato)."""
    params = parameters or {}
    path = _get_pdf_path(params.get("path", ""))
    if not os.path.isfile(path):
        return f"Archivo no encontrado: {path}"

    out_dir = params.get("output", "")
    if not out_dir:
        base = os.path.splitext(path)[0]
        out_dir = f"{base}_imagenes"
    os.makedirs(out_dir, exist_ok=True)

    try:
        reader = PdfReader(path)
        extracted = 0
        for pno, page in enumerate(reader.pages):
            if "/Resources" not in page or "/XObject" not in page["/Resources"]:
                continue
            for obj in page["/Resources"]["/XObject"].values():
                try:
                    obj = obj.get_object()
                    if obj.get("/Subtype") != "/Image":
                        continue
                    width = obj.get("/Width", 0)
                    height = obj.get("/Height", 0)
                    filt = obj.get("/Filter", "")
                    raw = obj.get_data()
                    if filt == "/DCTDecode":
                        ext = ".jpg"
                        mode = "RGB"
                    elif filt == "/JPXDecode":
                        ext = ".jp2"
                        mode = "RGB"
                    elif filt == "/FlateDecode":
                        ext = ".png"
                        mode = "RGBA" if obj.get("/ColorSpace") == "/DeviceCMYK" else "RGB"
                    else:
                        ext = ".png"
                        mode = "RGB"
                    fname = os.path.join(out_dir, f"pagina{pno+1}_img{extracted+1}{ext}")
                    with open(fname, "wb") as f:
                        f.write(raw)
                    extracted += 1
                except Exception:
                    continue
        if extracted == 0:
            return f"No se encontraron imagenes en {os.path.basename(path)}"
        return f"Extraidas {extracted} imagenes a: {out_dir}"
    except Exception as e:
        return f"Error extrayendo imagenes: {e}"


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
