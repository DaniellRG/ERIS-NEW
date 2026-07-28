# -*- coding: utf-8 -*-
"""
file_processor.py — Process files: describe, summarize, convert, trim, info.
Handles images, PDFs, text, code, audio, video, archives.
"""
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime


def file_processor(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "info").lower().strip()
    file_path = params.get("file_path", "").strip()
    instruction = params.get("instruction", "")
    fmt = params.get("format", "")
    width = params.get("width")
    height = params.get("height")
    scale = params.get("scale")
    quality = int(params.get("quality", 80))
    start = params.get("start", "")
    end = params.get("end", "")
    timestamp = params.get("timestamp", "")
    column = params.get("column", "")
    value = params.get("value", "")
    condition = params.get("condition", "contains")
    ascending = params.get("ascending", True)
    save = params.get("save", True)
    destination = params.get("destination", "")

    if not file_path:
        return "Error: Se requiere 'file_path'."

    if not os.path.exists(file_path):
        return f"Error: '{file_path}' no existe."

    ext = os.path.splitext(file_path)[1].lower()
    size = os.path.getsize(file_path)

    if action == "info":
        return _file_info(file_path, ext, size)
    elif action == "describe":
        return _describe_file(file_path, ext)
    elif action == "word_count":
        return _word_count(file_path, ext)
    elif action == "summarize":
        return _summarize_file(file_path, ext)
    elif action == "to_bullet":
        return _to_bullets(file_path, ext)
    elif action == "extract_text":
        return _extract_text(file_path, ext)
    elif action == "convert":
        return _convert_file(file_path, ext, fmt, destination)
    elif action == "trim":
        return _trim_file(file_path, ext, start, end)
    elif action == "analyze":
        return _analyze_file(file_path, ext)
    elif action == "validate":
        return _validate_file(file_path, ext)
    elif action == "format":
        return _format_file(file_path, ext)
    elif action == "fix":
        return _fix_file(file_path, ext)
    elif action == "compress":
        return _compress_file(file_path, ext, quality)
    elif action == "info":
        return _file_info(file_path, ext, size)
    else:
        return f"Acción '{action}' no reconocida. Usa: info, describe, summarize, word_count, extract_text, convert, trim, analyze, validate, format, fix, compress"


def _file_info(file_path: str, ext: str, size: int) -> str:
    stat = os.stat(file_path)
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

    size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

    type_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".html": "HTML", ".css": "CSS", ".java": "Java",
        ".txt": "Texto", ".md": "Markdown", ".csv": "CSV",
        ".json": "JSON", ".xml": "XML", ".yaml": "YAML",
        ".pdf": "PDF", ".docx": "Word", ".xlsx": "Excel",
        ".pptx": "PowerPoint", ".zip": "ZIP", ".rar": "RAR",
        ".jpg": "Imagen", ".jpeg": "Imagen", ".png": "Imagen",
        ".gif": "Imagen", ".mp3": "Audio", ".wav": "Audio",
        ".mp4": "Video", ".avi": "Video", ".mkv": "Video",
    }
    file_type = type_map.get(ext, ext.replace(".", "").upper() or "Desconocido")

    lines = [
        f"Archivo: {os.path.basename(file_path)}",
        f"Tipo: {file_type}",
        f"Tamaño: {size_str}",
        f"Modificado: {modified}",
        f"Creado: {created}",
        f"Extensión: {ext or 'N/A'}",
    ]
    return "\n".join(lines)


def _describe_file(file_path: str, ext: str) -> str:
    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs", ".sh", ".sql", ".json", ".xml", ".yaml", ".yml", ".csv"}
    if ext in text_exts:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(10000)
            lines = content.split("\n")
            return f"Archivo de texto ({len(lines)} líneas, {len(content)} caracteres):\n{content[:2000]}"
        except Exception as e:
            return f"Error leyendo: {e}"
    elif ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        return f"Imagen {ext.upper()}: {os.path.basename(file_path)}"
    elif ext == ".pdf":
        return f"PDF: {os.path.basename(file_path)}"
    else:
        return f"Archivo {ext or 'desconocido'}: {os.path.basename(file_path)}"


def _word_count(file_path: str, ext: str) -> str:
    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs", ".sh", ".sql", ".json", ".xml", ".yaml", ".yml", ".csv"}
    if ext not in text_exts:
        return f"Conteo de palabras no disponible para {ext}."
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        words = len(content.split())
        chars = len(content)
        lines = content.count("\n") + 1
        return f"Palabras: {words} | Caracteres: {chars} | Líneas: {lines}"
    except Exception as e:
        return f"Error: {e}"


def _summarize_file(file_path: str, ext: str) -> str:
    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs"}
    if ext not in text_exts:
        return f"Resumen no disponible para {ext}."
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(20000)
        lines = content.split("\n")
        non_empty = [l.strip() for l in lines if l.strip()]
        first_5 = non_empty[:5]
        return f"Resumen ({len(lines)} líneas, {len(non_empty)} no vacías):\n" + "\n".join(f"  {l}" for l in first_5)
    except Exception as e:
        return f"Error: {e}"


def _to_bullets(file_path: str, ext: str) -> str:
    text_exts = {".txt", ".md", ".py", ".js", ".ts"}
    if ext not in text_exts:
        return f"Conversión a bullets no disponible para {ext}."
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(10000)
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        bullets = "\n".join(f"- {l}" for l in lines[:50])
        return f" bullets ({len(lines)} líneas):\n{bullets}"
    except Exception as e:
        return f"Error: {e}"


def _extract_text(file_path: str, ext: str) -> str:
    if ext == ".pdf":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file_path)
            text = ""
            for page in reader.pages[:10]:
                text += page.extract_text() or ""
            return text[:5000] or "No se pudo extraer texto del PDF."
        except ImportError:
            return "PyPDF2 no instalado. pip install PyPDF2"
        except Exception as e:
            return f"Error extrayendo PDF: {e}"
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs[:100])
            return text[:5000] or "Documento vacío."
        except ImportError:
            return "python-docx no instalado. pip install python-docx"
        except Exception as e:
            return f"Error extrayendo DOCX: {e}"
    elif ext in {".txt", ".md", ".py", ".js", ".ts", ".html", ".css"}:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(5000)
    return f"Extracción de texto no soportada para {ext}."


def _convert_file(file_path: str, ext: str, fmt: str, destination: str) -> str:
    if not fmt:
        return "Error: Se requiere 'format' para conversión."
    if ext == ".pdf" and fmt == "txt":
        return _extract_text(file_path, ext)
    if ext == ".md" and fmt == "html":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md = f.read()
            html = f"<html><body><pre>{md}</pre></body></html>"
            out = destination or file_path.replace(".md", ".html")
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            return f"Convertido: {out}"
        except Exception as e:
            return f"Error: {e}"
    return f"Conversión de {ext} a {fmt} no implementada aún."


def _trim_file(file_path: str, ext: str, start: str, end: str) -> str:
    text_exts = {".txt", ".md", ".py", ".js", ".ts"}
    if ext not in text_exts:
        return f"Trim no disponible para {ext}."
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        s = _parse_time(start, len(lines)) if start else 0
        e = _parse_time(end, len(lines)) if end else len(lines)
        trimmed = "".join(lines[s:e])
        out = file_path.replace(ext, f"_trimmed{ext}")
        with open(out, "w", encoding="utf-8") as f:
            f.write(trimmed)
        return f"Trim guardado: {out} (líneas {s}-{e})"
    except Exception as e:
        return f"Error: {e}"


def _parse_time(val: str, total: int) -> int:
    try:
        return int(val)
    except ValueError:
        return 0


def _analyze_file(file_path: str, ext: str) -> str:
    text_exts = {".py", ".js", ".ts", ".java", ".go", ".rs"}
    if ext in text_exts:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.split("\n")
        funcs = sum(1 for l in lines if "def " in l or "function " in l)
        classes = sum(1 for l in lines if "class " in l)
        comments = sum(1 for l in lines if l.strip().startswith("#") or l.strip().startswith("//"))
        return f"Líneas: {len(lines)} | Funciones: {funcs} | Clases: {classes} | Comentarios: {comments}"
    return f"Análisis no disponible para {ext}."


def _validate_file(file_path: str, ext: str) -> str:
    if ext == ".json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            return "JSON válido."
        except json.JSONDecodeError as e:
            return f"JSON inválido: {e}"
    elif ext in {".py", ".pyw"}:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                compile(f.read(), file_path, "exec")
            return "Python válido (syntax OK)."
        except SyntaxError as e:
            return f"Error de sintaxis: {e}"
    return f"Validación no disponible para {ext}."


def _format_file(file_path: str, ext: str) -> str:
    if ext == ".json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(formatted)
            return f"JSON formateado: {file_path}"
        except Exception as e:
            return f"Error: {e}"
    return f"Formato no disponible para {ext}."


def _fix_file(file_path: str, ext: str) -> str:
    if ext in {".txt", ".md", ".py", ".js"}:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            fixed = content.replace("\r\n", "\n").replace("\r", "\n")
            if fixed != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                return f"Archivo arreglado (line endings): {file_path}"
            return "El archivo ya está bien."
        except Exception as e:
            return f"Error: {e}"
    return f"Fix no disponible para {ext}."


def _compress_file(file_path: str, ext: str, quality: int) -> str:
    if ext in {".jpg", ".jpeg", ".png"}:
        try:
            from PIL import Image
            img = Image.open(file_path)
            out = file_path.replace(ext, f"_compressed{ext}")
            if ext in {".jpg", ".jpeg"}:
                img.save(out, quality=quality, optimize=True)
            else:
                img.save(out, optimize=True)
            orig = os.path.getsize(file_path)
            comp = os.path.getsize(out)
            reduction = (1 - comp / orig) * 100 if orig > 0 else 0
            return f"Comprimido: {out} ({reduction:.0f}% reducción)"
        except ImportError:
            return "Pillow no instalado. pip install Pillow"
        except Exception as e:
            return f"Error: {e}"
    return f"Compresión no disponible para {ext}."
