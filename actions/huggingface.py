"""Tool de HuggingFace para ERIS: busca, explora y descarga datasets.

Uso via la API publica de Hugging Face (https://huggingface.co/api, sin token).
Solo explora contenido publico. No descarga modelos (son demasiado grandes para
ejecutarlos localmente); se centra en datasets de conocimiento.

Acciones:
  - search_models / models  <query> [limit]  - busca modelos publicos
  - search_datasets / datasets  <query> [limit]  - busca datasets publicos
  - top  [limit]  - datasets mas populares de la semana
  - info  <model_id | dataset_id>  - metadata de un recurso
  - list_files  <dataset_id>  - lista los archivos de un dataset
  - download  <dataset_id> <file> [dest]  - descarga un archivo del dataset a
    la carpeta de conocimiento (D:/Eris_Source/knowledge) para ingestar con
    knowledge_ingestor / document_rag.
"""

import os
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

_API = "https://huggingface.co/api"
_HEADERS = {"User-Agent": "ErisAI/2.7 (knowledge ingestion)"}
_TIMEOUT = 20
_KNOWLEDGE_DIR = Path("D:/Eris_Source/knowledge")
_MAX_DOWNLOAD = 50 * 1024 * 1024  # 50 MB cap por archivo


def _get(url, params=None, timeout=_TIMEOUT):
    if not HAS_REQUESTS:
        return None, "requests no instalado"
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json(), None
        return None, f"HTTP {r.status_code} de {url}"
    except Exception as e:
        return None, f"error de red: {e}"


def _fmt(res):
    """Devuelve resumen legible de un modelo o dataset."""
    kind = "modelo" if "modelId" in res else "dataset"
    id_ = res.get("modelId") or res.get("id") or res.get("name", "?")
    dl = res.get("downloads", 0)
    likes = res.get("likes", 0)
    tags = res.get("tags", [])[:8]
    extra = []
    if kind == "dataset":
        extra = res.get("siblings", [])
        extra = [s.get("rfilename", "") for s in extra][:10]
    lines = [f"  {id_}"]
    if res.get("author"):
        lines[0] += f"  (por {res['author']})"
    lines.append(f"     descargas: {dl:,} | likes: {likes}")
    if tags:
        lines.append(f"     tags: {', '.join(tags)}")
    if extra:
        lines.append(f"     archivos: {', '.join(extra)}")
    return "\n".join(lines)


def huggingface(parameters: dict, player=None) -> str:
    """Dispatcher principal del tool de HuggingFace."""
    action = str(parameters.get("action") or parameters.get("accion") or "search_datasets").lower()
    query = str(parameters.get("query") or parameters.get("search") or parameters.get("q") or "")
    limit = int(parameters.get("limit") or 5)
    limit = max(1, min(limit, 20))

    if not HAS_REQUESTS:
        return "Error: 'requests' no esta instalado."

    if action in ("search_models", "models", "modelos"):
        data, err = _get(f"{_API}/models", params={"search": query, "limit": limit})
        if data is None:
            return f"Error buscando modelos: {err}"
        if not data:
            return f"No se encontraron modelos para '{query}'."
        out = [f"=== MODELOS EN HUGGINGFACE (busqueda: {query or 'popular'}) ==="]
        for m in data[:limit]:
            out.append(_fmt(m))
        return "\n".join(out)

    if action in ("search_datasets", "datasets", "dataset"):
        data, err = _get(f"{_API}/datasets", params={"search": query, "limit": limit})
        if data is None:
            return f"Error buscando datasets: {err}"
        if not data:
            return f"No se encontraron datasets para '{query}'."
        out = [f"=== DATASETS EN HUGGINGFACE (busqueda: {query or 'populares'}) ==="]
        for d in data[:limit]:
            out.append(_fmt(d))
        return "\n".join(out)

    if action in ("top", "populares", "trending"):
        data, err = _get(f"{_API}/datasets", params={"sort": "downloads", "direction": -1, "limit": limit})
        if data is None:
            return f"Error consultando top datasets: {err}"
        out = [f"=== TOP DATASETS DESCARGADOS EN HUGGINGFACE ==="]
        for d in data[:limit]:
            out.append(_fmt(d))
        return "\n".join(out)

    if action in ("info", "info_model", "info_dataset"):
        rid = str(parameters.get("id") or parameters.get("model_id") or parameters.get("dataset_id") or parameters.get("resource") or "")
        if not rid:
            return "Error: indica 'id' (ej. datasets/oscar, modelos/gpt2)."
        data, err = _get(f"{_API}/{rid.lstrip('/')}")
        if data is None:
            return f"Error obteniendo info de {rid}: {err}"
        return "=== INFO " + rid + " ===\n" + _fmt(data)

    if action in ("list_files", "archivos", "files"):
        rid = str(parameters.get("id") or parameters.get("dataset_id") or "")
        if not rid:
            return "Error: indica 'id' del dataset (ej. datasets/oscar)."
        if not rid.startswith("datasets/"):
            rid = "datasets/" + rid
        data, err = _get(f"{_API}/{rid}")
        if data is None:
            return f"Error obteniendo archivos: {err}"
        sib = [s.get("rfilename", "") for s in data.get("siblings", [])]
        if not sib:
            return f"El dataset {rid} no tiene archivos listados."
        return f"=== ARCHIVOS DE {rid} ({len(sib)}) ===\n" + "\n".join("  " + s for s in sib[:50])

    if action in ("download", "bajar", "descargar"):
        rid = str(parameters.get("dataset_id") or parameters.get("id") or parameters.get("dataset") or "")
        fname = str(parameters.get("file") or parameters.get("filename") or "")
        if not rid or not fname:
            return "Error: indica 'dataset_id' y 'file' (usa list_files para ver los archivos)."
        if not rid.startswith("datasets/"):
            rid = "datasets/" + rid
        dest = str(parameters.get("dest") or _KNOWLEDGE_DIR)
        dest_dir = Path(dest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/{rid}/resolve/main/{fname}"
        try:
            with requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, stream=True) as r:
                if r.status_code != 200:
                    return f"Error descargando {fname}: HTTP {r.status_code} (¿existe el archivo?)"
                ctype = r.headers.get("Content-Type", "")
                clen = r.headers.get("Content-Length")
                if clen and int(clen) > _MAX_DOWNLOAD:
                    return f"Rechazado: {fname} pesa {int(clen) / 1024 / 1024:.1f} MB (maximo 50 MB)."
                safe = os.path.basename(fname)
                out_path = dest_dir / safe
                size = 0
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(64 * 1024):
                        f.write(chunk)
                        size += len(chunk)
                        if size > _MAX_DOWNLOAD:
                            f.close()
                            out_path.unlink(missing_ok=True)
                            return "Rechazado: archivo mayor a 50 MB, descarga cancelada."
            return (
                f"Descargado: {safe} ({size:,} bytes) en {out_path}\n"
                f"Tipo: {ctype or '?'}\n"
                "Para alimentar a ERIS: 'ingesta el directorio knowledge' "
                "(knowledge_ingestor ingest_dir)."
            )
        except Exception as e:
            return f"Error descargando {fname}: {e}"

    return ("HuggingFace (exploracion de datasets/modelos publicos). Acciones:\n"
            "  models <query> [limit]  - busca modelos\n"
            "  datasets <query> [limit]  - busca datasets\n"
            "  top [limit]  - datasets mas descargados\n"
            "  info id=<model_id|dataset_id>  - metadata de un recurso\n"
            "  list_files id=<dataset_id>  - lista archivos de un dataset\n"
            "  download dataset_id=<id> file=<nombre> [dest]  - descarga a "
            "D:/Eris_Source/knowledge")
