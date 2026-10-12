# -*- coding: utf-8 -*-
"""
core/hermes_tools.py — Herramientas Hermes (reales).
────────────────────────────────────────────────────
Fase 0.5 / B9: `core/gemini_text_chat._GEMINI_PRIORITY_TOOLS` listaba 12 tools
`hermes_*` que NO existían (`core/action_imports.py` las importaba y quedaban
en `None`). Prometerle a Gemini una herramienta que no existe es peor que no
prometerla: el modelo la "usa", falla, y Eris lo narra como si hubiera pasado.

Acá se construyen de verdad las 7 que importan, con dependencias ligeras y
degradación elegante (si falta una lib, se dice — no se miente):

    hermes_web_search       búsqueda web (delega en actions.web_search)
    hermes_web_scraper      baja una URL y devuelve el texto limpio
    hermes_page_summarizer  resume una URL o un texto pegado
    hermes_data_analyzer    estructura/estadísticas de JSON o CSV
    hermes_csv_processor    lee y procesa CSV (head/columnas/describe/filtro)
    hermes_code_review      revisión estática (py_compile + ruff + heurísticas)
    hermes_security_audit   auditoría de seguridad básica (bandit + heurísticas)

Regla de oro de este módulo: NINGUNA función lanza. Siempre devuelven un
string (éxito o el motivo real del fallo), porque son la cara visible de la
cadena de herramientas de Gemini.

Sincronización sagrada (AGENTS.md): estas tools están en
`core/tool_registry.py` Y en `core/tool_declarations.py`, `len == len`, 0 dupes.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path

__all__ = [
    "hermes_web_search",
    "hermes_web_scraper",
    "hermes_page_summarizer",
    "hermes_data_analyzer",
    "hermes_csv_processor",
    "hermes_code_review",
    "hermes_security_audit",
]

_UA = "curl/8.0"  # wttr.in y varios sitios bloquean user-agents de navegador genéricos


# ── helpers ──────────────────────────────────────────────────────────────────

def _err(msg: str) -> str:
    return f"⚠️ {msg}"


def _read_source(params: dict) -> tuple[str, str]:
    """Devuelve (texto, etiqueta). Acepta 'text', 'code' o un 'path' de archivo."""
    for key in ("text", "code", "content", "data"):
        val = params.get(key)
        if isinstance(val, str) and val.strip():
            return val, f"<{key}>"
    path = str(params.get("path") or params.get("file") or "").strip()
    if path:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"no existe: {path}")
        if p.is_dir():
            raise IsADirectoryError(f"es un directorio: {path}")
        return p.read_text(encoding="utf-8", errors="replace"), str(p)
    raise ValueError("Falta 'text', 'code' o 'path'.")


def _fetch(url: str, timeout: int = 20) -> str:
    import requests  # dep opcional; el caller captura ImportError
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    return r.text


def _html_to_text(html: str) -> tuple[str, str]:
    """Devuelve (titulo, texto_limpio)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    for tag in soup(["script", "style", "noscript", "header", "footer",
                     "nav", "aside", "form", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text


def _extractive_summary(text: str, max_sentences: int = 6) -> str:
    """Resumen extractivo simple (frecuencia de palabras), sin LLM: nunca falla."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
    if not sentences:
        return text.strip()[:600]
    words: dict[str, int] = {}
    for w in re.findall(r"\w{4,}", text.lower()):
        words[w] = words.get(w, 0) + 1
    scored = []
    for i, s in enumerate(sentences):
        score = sum(words.get(w, 0) for w in re.findall(r"\w{4,}", s.lower()))
        scored.append((score / (len(s.split()) + 1), i, s))
    top = sorted(scored, reverse=True)[:max_sentences]
    top.sort(key=lambda x: x[1])  # orden original
    return " ".join(s for _, _, s in top)


# ── 1. hermes_web_search ─────────────────────────────────────────────────────

def hermes_web_search(parameters: dict = None, player=None) -> str:
    """Búsqueda web real. params: query (req), action=search|news|images, max_results."""
    params = parameters or {}
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return _err("Necesito 'query'. Ej: {'query': 'noticias IA 2026'}")
    action = str(params.get("action") or "search").lower()
    max_results = int(params.get("max_results") or 8)
    try:
        from actions.web_search import web_search as _ws
        return _ws({"query": query, "action": action, "max_results": max_results})
    except Exception as e:
        return _err(f"búsqueda web no disponible: {e}")


# ── 2. hermes_web_scraper ────────────────────────────────────────────────────

def hermes_web_scraper(parameters: dict = None, player=None) -> str:
    """Baja una URL y devuelve su texto limpio. params: url (req), max_chars, links(bool)."""
    params = parameters or {}
    url = str(params.get("url") or "").strip()
    if not url:
        return _err("Necesito 'url'. Ej: {'url': 'https://example.com'}")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    max_chars = int(params.get("max_chars") or 8000)
    try:
        html = _fetch(url)
    except ImportError as e:
        return _err(f"falta requests: {e}")
    except Exception as e:
        return _err(f"no pude descargar {url}: {e}")
    try:
        title, text = _html_to_text(html)
    except ImportError as e:
        return _err(f"falta beautifulsoup4: {e}")
    except Exception as e:
        return _err(f"no pude limpiar el HTML de {url}: {e}")
    header = f"# {title or url}\n{url}\n"
    if params.get("links"):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            hrefs = []
            for a in soup.find_all("a", href=True):
                h = a["href"]
                if h.startswith("http"):
                    hrefs.append(h)
            seen = list(dict.fromkeys(hrefs))[:30]
            header += "\nENLACES:\n" + "\n".join(f"- {h}" for h in seen) + "\n"
        except Exception:
            pass
    body = text if len(text) <= max_chars else text[:max_chars] + "\n…[texto recortado]"
    return f"{header}\n{body}"


# ── 3. hermes_page_summarizer ────────────────────────────────────────────────

def hermes_page_summarizer(parameters: dict = None, player=None) -> str:
    """Resume una URL o un texto. params: url | text, max_sentences, use_llm(bool)."""
    params = parameters or {}
    url = str(params.get("url") or "").strip()
    text = str(params.get("text") or "").strip()
    if not text and url:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            html = _fetch(url)
            _t, text = _html_to_text(html)
        except Exception as e:
            return _err(f"no pude leer {url}: {e}")
    if not text:
        return _err("Necesito 'url' o 'text' para resumir.")
    max_sentences = int(params.get("max_sentences") or 6)
    # Con LLM si se pide explícitamente; si no, extractivo (nunca falla).
    if params.get("use_llm"):
        try:
            from core.model_router import quick_chat
            prompt = ("Resumí en español, en pocas frases claras y fieles al "
                      "texto (sin inventar), lo esencial de esto:\n\n" + text[:6000])
            out = quick_chat(prompt, task="summary")
            if out and str(out).strip():
                return "RESUMEN (IA):\n" + str(out).strip()
        except Exception:
            pass  # cae al extractivo
    return "RESUMEN (extractivo):\n" + _extractive_summary(text, max_sentences)


# ── 4. hermes_data_analyzer ──────────────────────────────────────────────────

def _numeric_stats(values: list) -> str:
    nums = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not nums:
        return "sin numéricos"
    import statistics
    out = [f"n={len(nums)}", f"min={min(nums):g}", f"max={max(nums):g}",
           f"media={statistics.mean(nums):.3g}"]
    if len(nums) > 1:
        out.append(f"mediana={statistics.median(nums):.3g}")
    return ", ".join(out)


def hermes_data_analyzer(parameters: dict = None, player=None) -> str:
    """Analiza JSON o CSV. params: data|path. Devuelve estructura y estadísticas."""
    params = parameters or {}
    try:
        raw, label = _read_source(params)
    except Exception as e:
        return _err(str(e))

    # JSON inline o archivo .json
    parsed = None
    if isinstance(params.get("data"), (dict, list)):
        parsed = params["data"]
    else:
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
    if parsed is not None:
        lines = [f"DATOS JSON ({label}):"]
        if isinstance(parsed, list):
            lines.append(f"• lista con {len(parsed)} elementos")
            if parsed and isinstance(parsed[0], dict):
                keys = sorted({k for item in parsed if isinstance(item, dict) for k in item})
                lines.append(f"• claves por elemento: {', '.join(keys[:20])}")
                for k in keys[:8]:
                    vals = [item.get(k) for item in parsed if isinstance(item, dict)]
                    lines.append(f"  - {k}: {_numeric_stats(vals)}")
        elif isinstance(parsed, dict):
            lines.append(f"• objeto con {len(parsed)} claves: {', '.join(list(parsed)[:20])}")
            for k, v in list(parsed.items())[:12]:
                kind = type(v).__name__
                extra = f" ({len(v)} elems)" if isinstance(v, (list, dict)) else ""
                lines.append(f"  - {k}: {kind}{extra}")
        else:
            lines.append(f"• valor: {parsed!r}")
        return "\n".join(lines)

    # CSV
    if "," in raw.split("\n", 1)[0] or str(params.get("path", "")).lower().endswith(".csv"):
        reader = list(csv.DictReader(io.StringIO(raw)))
        if reader:
            cols = list(reader[0].keys())
            lines = [f"DATOS CSV ({label}): {len(reader)} filas, {len(cols)} columnas",
                     f"• columnas: {', '.join(cols[:25])}"]
            for c in cols[:8]:
                vals = []
                for row in reader:
                    v = row.get(c, "")
                    try:
                        vals.append(float(v))
                    except Exception:
                        pass
                if vals:
                    lines.append(f"  - {c}: {_numeric_stats(vals)}")
            return "\n".join(lines)

    return (f"No pude interpretar como JSON ni CSV ({len(raw)} chars). "
            f"Primeros 300:\n{raw[:300]}")


# ── 5. hermes_csv_processor ──────────────────────────────────────────────────

def hermes_csv_processor(parameters: dict = None, player=None) -> str:
    """Procesa un CSV. params: path (req), action=read|head|columns|describe|filter,
    n(rows), filter_col + filter_val."""
    params = parameters or {}
    path = str(params.get("path") or params.get("file") or "").strip()
    if not path:
        return _err("Necesito 'path' de un CSV.")
    p = Path(path).expanduser()
    if not p.exists():
        return _err(f"no existe: {path}")
    action = str(params.get("action") or "read").lower()
    try:
        with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            cols = reader.fieldnames or []
            rows = list(reader)
    except Exception as e:
        return _err(f"no pude leer el CSV: {e}")

    if action in ("columns", "columnas"):
        return f"Columnas ({len(cols)}): {', '.join(cols)}"
    if action in ("describe", "resumen"):
        lines = [f"{p.name}: {len(rows)} filas, {len(cols)} columnas"]
        for c in cols:
            vals = []
            for row in rows:
                try:
                    vals.append(float(row.get(c, "")))
                except Exception:
                    pass
            if vals:
                lines.append(f"  - {c}: {_numeric_stats(vals)}")
        return "\n".join(lines)
    if action in ("filter", "filtrar"):
        fc = str(params.get("filter_col") or "").strip()
        fv = str(params.get("filter_val") or "").strip()
        if not fc:
            return _err("Para filtrar necesito 'filter_col' (y opcional 'filter_val').")
        hits = [r for r in rows if fv.lower() in str(r.get(fc, "")).lower()]
        n = int(params.get("n") or 20)
        out = [f"{len(hits)} coincidencias en '{fc}'~'{fv}':"]
        for r in hits[:n]:
            out.append("  " + ", ".join(f"{k}={v}" for k, v in list(r.items())[:8]))
        return "\n".join(out)

    action = "head" if action in ("head", "primeras") else "read"
    n = int(params.get("n") or (10 if action == "head" else 50))
    out = [f"{p.name}: {len(rows)} filas, {len(cols)} columnas",
           " | ".join(cols)]
    for r in rows[:n]:
        out.append(" | ".join(str(r.get(c, "")) for c in cols))
    if len(rows) > n:
        out.append(f"…[{len(rows) - n} filas más]")
    return "\n".join(out)


# ── 6. hermes_code_review ────────────────────────────────────────────────────

def hermes_code_review(parameters: dict = None, player=None) -> str:
    """Revisión estática. params: path|code, filename(opcional para py_compile)."""
    params = parameters or {}
    try:
        src, label = _read_source(params)
    except Exception as e:
        return _err(str(e))

    findings: list[str] = []
    lines = src.splitlines()
    # Heurísticas siempre-disponibles
    if len(lines) > 800:
        findings.append(f"archivo largo: {len(lines)} líneas")
    for i, ln in enumerate(lines, 1):
        if len(ln) > 120:
            findings.append(f"L{i}: línea muy larga ({len(ln)} chars)")
        if re.search(r"\bexcept\s*:", ln):
            findings.append(f"L{i}: 'except:' desnudo (traga todo)")
        if re.search(r"\b(eval|exec)\s*\(", ln):
            findings.append(f"L{i}: usa {re.search(r'(eval|exec)', ln).group(1)}()")
        if "TODO" in ln or "FIXME" in ln:
            findings.append(f"L{i}: {ln.strip()[:60]}")
    # py_compile si parece Python
    if label.endswith(".py") or "def " in src or "import " in src:
        try:
            import py_compile
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                             encoding="utf-8") as tf:
                tf.write(src)
                tmp = tf.name
            try:
                py_compile.compile(tmp, doraise=True)
            except py_compile.PyCompileError as e:
                findings.append(f"SINTAXIS: {e}")
            finally:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
        except Exception:
            pass
    # ruff si está
    try:
        import shutil
        import subprocess
        from core.platform_compat import run_flags
        if shutil.which("ruff"):
            r = subprocess.run(["ruff", "check", "--output-format", "concise", "-"],
                               input=src, capture_output=True, text=True, timeout=30,
                               creationflags=run_flags())
            if r.stdout.strip():
                findings.append("RUFF:\n" + r.stdout.strip()[:1500])
    except Exception:
        pass

    if not findings:
        return f"REVISIÓN ({label}): sin observaciones. {len(lines)} líneas."
    return f"REVISIÓN ({label}) — {len(findings)} observación(es):\n" + "\n".join(
        f"- {f}" for f in findings[:40])


# ── 7. hermes_security_audit ─────────────────────────────────────────────────

_SEC_PATTERNS = (
    (r"\beval\s*\(", "eval() — ejecución dinámica"),
    (r"\bexec\s*\(", "exec() — ejecución dinámica"),
    (r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True", "subprocess con shell=True"),
    (r"\bos\.system\s*\(", "os.system()"),
    (r"pickle\.loads?\s*\(", "pickle.load — deserialización insegura"),
    (r"yaml\.load\s*\((?![^)]*Safe)", "yaml.load sin SafeLoader"),
    (r"verify\s*=\s*False", "TLS verify=False"),
    (r"(?i)(password|passwd|secret|api[_-]?key|token)\s*=\s*['\"][^'\"]{6,}['\"]",
     "posible secreto hardcodeado"),
    (r"0\.0\.0\.0", "bind a 0.0.0.0 (expuesto)"),
)


def hermes_security_audit(parameters: dict = None, player=None) -> str:
    """Auditoría de seguridad básica. params: path (archivo o directorio), code."""
    params = parameters or {}
    targets: list[Path] = []
    path = str(params.get("path") or "").strip()
    if path:
        p = Path(path).expanduser()
        if p.is_dir():
            targets = [f for f in p.rglob("*.py") if f.is_file()][:200]
        elif p.exists():
            targets = [p]
        else:
            return _err(f"no existe: {path}")
    else:
        # auditar un snippet de código pegado
        src = str(params.get("code") or params.get("text") or "")
        if not src:
            return _err("Necesito 'path' (archivo/dir) o 'code' (snippet).")
        hits = []
        for pat, desc in _SEC_PATTERNS:
            if re.search(pat, src):
                hits.append(desc)
        return ("AUDITORÍA (snippet): " +
                ("sin hallazgos." if not hits else "; ".join(hits)))

    findings: list[str] = []
    for f in targets:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat, desc in _SEC_PATTERNS:
            for m in re.finditer(pat, text):
                ln = text[:m.start()].count("\n") + 1
                findings.append(f"{f.name}:L{ln}: {desc}")
    # bandit si está
    if targets and len(targets) > 1:
        try:
            import shutil
            import subprocess
            from core.platform_compat import run_flags
            if shutil.which("bandit"):
                r = subprocess.run(
                    ["bandit", "-q", "-f", "txt", *[str(t) for t in targets[:50]]],
                    capture_output=True, text=True, timeout=60, creationflags=run_flags())
                if "Issue:" in r.stdout:
                    findings.append("BANDIT:\n" + r.stdout.strip()[:2000])
        except Exception:
            pass

    if not findings:
        return f"AUDITORÍA: {len(targets)} archivo(s), sin hallazgos evidentes."
    return (f"AUDITORÍA — {len(findings)} hallazgo(s) en {len(targets)} archivo(s):\n"
            + "\n".join(f"- {f}" for f in findings[:60]))
