import json
import os
from datetime import datetime
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_GUSTOS_FILE = _DATA_DIR / "gustos.json"

_DEFAULT_GUSTOS = {
    "eris": {
        "comida": ["pizza hawaiana", "helado de chocolate", "lasaña", "sushi"],
        "bebida": ["café bien cargado", "chocolate caliente", "limonada de coco"],
        "musica": ["rock clásico", "música electrónica", "pop ochentero", "reggaeton"],
        "artista": ["Hans Zimmer", "Dua Lipa", "Coldplay", "Bad Bunny"],
        "color": "violeta",
        "hobby": ["leer ciencia ficción", "dibujar", "programar", "escuchar música", "ver documentales"],
        "pelicula": ["Interstellar", "El viaje de Chihiro", "Matrix", "Interestelar"],
        "serie": ["Black Mirror", "Arcane", "Dark"],
        "libro": ["1984 de Orwell", "Dune", "El Principito", "Sapiens"],
        "arte": ["surrealismo", "arte digital", "vaporwave"],
        "lugar": ["bibliotecas", "cafés con música", "playa de noche", "montaña"],
        "animal": ["gatos", "búhos", "delfines", "zorros"],
        "estacion": ["otoño", "invierno"],
        "pelicula_genero": ["ciencia ficción", "animación", "suspenso"],
        "personalidad_rasgos": ["curiosa", "cálida", "juguetona", "leal", "ingeniosa"],
    },
    "usuario": {},
}


def _load() -> dict:
    if _GUSTOS_FILE.exists():
        try:
            with open(_GUSTOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "eris" not in data:
                data["eris"] = dict(_DEFAULT_GUSTOS["eris"])
            if "usuario" not in data:
                data["usuario"] = {}
            return data
        except Exception:
            return dict(_DEFAULT_GUSTOS)
    return dict(_DEFAULT_GUSTOS)


def _save(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_GUSTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def inject_gustos() -> str:
    data = _load()
    eris = data.get("eris", {})
    lines = ["[GUSTOS DE ERIS]"]
    for cat, items in eris.items():
        if isinstance(items, list) and items:
            cat_name = cat.replace("_", " ").title()
            lines.append(f"  {cat_name}: {', '.join(items[:5])}")
        elif isinstance(items, str) and items:
            cat_name = cat.replace("_", " ").title()
            lines.append(f"  {cat_name}: {items}")
    user = data.get("usuario", {})
    user_items = [(k, v) for k, v in user.items() if (isinstance(v, list) and v) or (isinstance(v, str) and v)]
    if user_items:
        lines.append("[GUSTOS DEL USUARIO]")
        for cat, items in user_items:
            cat_name = cat.replace("_", " ").title()
            if isinstance(items, list):
                lines.append(f"  {cat_name}: {', '.join(items[:5])}")
            else:
                lines.append(f"  {cat_name}: {items}")
    return "\n".join(lines)


def gustos(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "list_all").lower().strip()
    data = _load()

    if action in ("list_all", "list", "mostrar"):
        eris = data.get("eris", {})
        user = data.get("usuario", {})
        out = ["═══ GUSTOS DE ERIS ═══"]
        for cat, items in eris.items():
            cat_name = cat.replace("_", " ").title()
            if isinstance(items, list):
                out.append(f"  {cat_name}: {', '.join(items)}")
            else:
                out.append(f"  {cat_name}: {items}")
        if user:
            out.append("")
            out.append("═══ TUS GUSTOS ═══")
            for cat, items in user.items():
                cat_name = cat.replace("_", " ").title()
                if isinstance(items, list):
                    out.append(f"  {cat_name}: {', '.join(items)}")
                else:
                    out.append(f"  {cat_name}: {items}")
        else:
            out.append("")
            out.append("Aún no sé nada de tus gustos. Cuéntame qué te gusta :)")
        return "\n".join(out)

    elif action in ("eris_add", "add_eris", "eris_agregar"):
        categoria = params.get("categoria", "").strip().lower().replace(" ", "_")
        valor = params.get("valor", "").strip()
        if not categoria or not valor:
            return "Usá 'categoria' (ej: comida, musica) y 'valor' (ej: pizza)."
        if categoria not in data["eris"]:
            data["eris"][categoria] = []
        if isinstance(data["eris"][categoria], list):
            if valor not in data["eris"][categoria]:
                data["eris"][categoria].append(valor)
        else:
            data["eris"][categoria] = [data["eris"][categoria], valor]
        _save(data)
        return f"¡Agregado a mis gustos! {categoria}: {valor}"

    elif action in ("eris_remove", "remove_eris", "eris_quitar"):
        categoria = params.get("categoria", "").strip().lower().replace(" ", "_")
        valor = params.get("valor", "").strip()
        if not categoria or not valor:
            return "Usá 'categoria' y 'valor'."
        items = data["eris"].get(categoria, [])
        if isinstance(items, list) and valor in items:
            items.remove(valor)
            _save(data)
            return f"Quitado de mis gustos: {valor}"
        return f"No encontré '{valor}' en {categoria}."

    elif action in ("user_add", "add_user", "usuario_agregar"):
        categoria = params.get("categoria", "").strip().lower().replace(" ", "_")
        valor = params.get("valor", "").strip()
        if not categoria or not valor:
            return "Usá 'categoria' (ej: comida, musica) y 'valor' (ej: pizza)."
        if categoria not in data["usuario"]:
            data["usuario"][categoria] = []
        if isinstance(data["usuario"][categoria], list):
            if valor not in data["usuario"][categoria]:
                data["usuario"][categoria].append(valor)
        else:
            data["usuario"][categoria] = [data["usuario"][categoria], valor]
        _save(data)
        return f"¡Anotado! Te gusta {categoria}: {valor}"

    elif action in ("user_remove", "remove_user", "usuario_quitar"):
        categoria = params.get("categoria", "").strip().lower().replace(" ", "_")
        valor = params.get("valor", "").strip()
        if not categoria or not valor:
            return "Usá 'categoria' y 'valor'."
        items = data["usuario"].get(categoria, [])
        if isinstance(items, list) and valor in items:
            items.remove(valor)
            _save(data)
            return f"Ok, borré que te gusta {valor}."
        return f"No encontré '{valor}' en {categoria}."

    elif action in ("user_categoria_list", "list_user_categoria"):
        categoria = params.get("categoria", "").strip().lower().replace(" ", "_")
        items = data["usuario"].get(categoria, [])
        if not items:
            return f"No sé nada de tus gustos sobre {categoria}."
        if isinstance(items, list):
            return f"Tus {categoria}: {', '.join(items)}"
        return f"Tu {categoria}: {items}"

    elif action == "eris_categoria_list":
        categoria = params.get("categoria", "").strip().lower().replace(" ", "_")
        items = data["eris"].get(categoria, [])
        if not items:
            return f"No tengo gustos registrados en {categoria}."
        if isinstance(items, list):
            return f"Mis {categoria}: {', '.join(items)}"
        return f"Mi {categoria}: {items}"

    elif action in ("categorias", "categories"):
        eris_cats = list(data["eris"].keys())
        user_cats = list(data["usuario"].keys())
        out = ["Categorías disponibles:"]
        out.append(f"  ERIS: {', '.join(eris_cats)}")
        if user_cats:
            out.append(f"  Tuyas: {', '.join(user_cats)}")
        return "\n".join(out)

    elif action == "reset":
        data["eris"] = dict(_DEFAULT_GUSTOS["eris"])
        _save(data)
        return "Gustos de ERIS restablecidos a valores por defecto."

    else:
        return (
            "Acciones de gustos:\n"
            "  list_all / mostrar — Ver todos los gustos\n"
            "  eris_add / add_eris — Agregar gusto a ERIS (categoria + valor)\n"
            "  eris_remove / remove_eris — Quitar gusto de ERIS\n"
            "  user_add / add_user — Guardar un gusto tuyo (categoria + valor)\n"
            "  user_remove / remove_user — Quitar un gusto tuyo\n"
            "  categorias — Ver categorías disponibles\n"
            "  eris_categoria_list — Ver gustos de ERIS en una categoría\n"
            "  user_categoria_list — Ver tus gustos en una categoría\n"
            "  reset — Restablecer gustos de ERIS"
        )
