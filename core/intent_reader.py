# -*- coding: utf-8 -*-
"""core/intent_reader.py — LECTURA DE INTENCIÓN (Fase 3.1).

Antes de tocar nada, Eris decide QUÉ se le está pidiendo. No por el verbo solo,
sino combinando **texto + `SharedContext`**: lo mismo dicho en un chat vacío es
una cosa, y con un editor abierto y un archivo activo es otra.

Tres modos:

- ``INVESTIGAR`` — "investiga", "qué está pasando". Lee, ejecuta, diagnostica.
  **No toca archivos.** Propone el parche, no lo aplica.
- ``EDITAR`` — "está en la línea N", "cambiá esto". Edita directo, con backup.
- ``AUTONOMO`` — "arreglalo", "hacelo funcionar". Leer → hipótesis → probar →
  verificar → reintentar (con tope), con backup.

Ejemplo rector (del diseño): *"Hay un error que no logro solucionar"* con VS Code
abierto es ``AUTONOMO``; la misma frase en un chat vacío es ``INVESTIGAR``. El
contexto, no el verbo, decide.

Sin dependencias pesadas. Nunca lanza: ante cualquier duda, ``INVESTIGAR`` (el
modo que no rompe nada).
"""

from __future__ import annotations

import unicodedata
from typing import Optional

INVESTIGAR = "INVESTIGAR"
EDITAR = "EDITAR"
AUTONOMO = "AUTONOMO"

_EDITORS = {
    "code", "codium", "vscode", "vscodium", "code-oss", "zed", "cursor",
    "nvim", "neovim", "vim", "pycharm", "idea", "webstorm", "clion", "rider",
    "goland", "subl", "sublime", "sublime_text", "emacs", "helix", "hx",
    "gnome-text-editor", "kate", "gedit", "mousepad", "pluma",
    "android-studio", "androidstudio",
}

# Cues fuertes de autonomía: "arreglalo" no necesita contexto.
_STRONG_AUTO = (
    "arreglalo", "arreglalo ya", "hacelo funcionar", "hace que funcione",
    "que funcione", "solucionalo", "solucionamelo", "soluciona el", "resolvelo",
    "dejalo andando", "dejalo funcionando", "encargate", "ocupate",
    "hacelo andar", "ponelo a andar", "que ande", "termina el trabajo",
    "terminalo", "reparalo",
)
# Cues débiles: solo son autonomía si HAY contexto de edición (spec example).
_WEAK_AUTO = (
    "error", "falla", "fallas", "no funciona", "no logro", "no puedo",
    "se rompe", "se rompio", "roto", "bug", "crashea", "crash",
    "no anda", "no arranca", "esta fallando",
)
_EDITAR = (
    "linea", "cambia ", "cambia la", "edita ", "edit ", "renombra",
    "reemplaza", "inserta ", "borra ", "borra la", "modifica ", "corregi",
    "corregir la", "arregla la", "arregla esa", "en la linea", "linea ",
    "agrega la linea", "quita la linea",
)
_INVESTIGAR = (
    "investiga", "que esta pasando", "por que", "diagnost", "analiz", "analis",
    "revisa", "mira ", "explica", "sin tocar", "no toques", "solo lee",
    "solo lectura", "lee y", "informe", "estado de", "mostrame", "mostra ",
    "que paso", "explicame", "describi", "describime",
)


def _strip_accents(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm(text: str) -> str:
    return _strip_accents(text).lower()


def _hits(text: str, cues) -> int:
    return sum(1 for c in cues if c in text)


def _snapshot(shared) -> dict:
    """Vista mínima de SharedContext (o dict), sin reventar."""
    try:
        if shared is None:
            from core.shared_context import get_shared_context
            shared = get_shared_context()
        if hasattr(shared, "as_dict"):
            return shared.as_dict()
        if isinstance(shared, dict):
            return shared
    except Exception:
        pass
    return {}


def _in_editor(snap: dict) -> bool:
    fg = _norm(str(snap.get("foreground_app") or ""))
    if fg and any(e in fg for e in _EDITORS):
        return True
    return bool(snap.get("active_file"))


def _is_coding_context(snap: dict) -> bool:
    if _in_editor(snap):
        return True
    fg = _norm(str(snap.get("foreground_app") or ""))
    return any(t in fg for t in ("kitty", "foot", "ghostty", "terminal", "bash", "zsh"))


def classify(text: str, shared=None) -> dict:
    """Clasifica el pedido en INVESTIGAR / EDITAR / AUTONOMO.

    Devuelve ``{"mode", "reason", "in_editor", "read_only"}``. Nunca lanza.
    """
    try:
        t = _norm(text)
        snap = _snapshot(shared)
        read_only = bool(snap.get("read_only"))
        in_editor = _in_editor(snap)
        coding = _is_coding_context(snap)

        strong = _hits(t, _STRONG_AUTO)
        weak = _hits(t, _WEAK_AUTO)
        edit = _hits(t, _EDITAR)
        inv = _hits(t, _INVESTIGAR)

        # Solo lectura manda: jamás edita ni actúa sola.
        if read_only:
            return _result(INVESTIGAR, "contexto de solo lectura", in_editor, read_only)

        # 1) Pedido explícito de investigar.
        if inv and not edit and not strong:
            return _result(INVESTIGAR, "pedido explícito de investigar", in_editor, read_only)

        # 2) Autonomía fuerte: no necesita contexto.
        if strong:
            return _result(AUTONOMO, "pedido directo de arreglar/hacer funcionar",
                           in_editor, read_only)

        # 3) Edición puntual.
        if edit and not inv:
            return _result(EDITAR, "referencia a línea/edición concreta",
                           in_editor, read_only)

        # 4) Autonomía débil SOLO con contexto de edición/código (spec example).
        if weak and coding:
            return _result(AUTONOMO, "hay un problema y estás en contexto de código",
                           in_editor, read_only)

        # 5) Problema sin contexto => investigar.
        if weak:
            return _result(INVESTIGAR, "hay un problema y no hay contexto de edición",
                           in_editor, read_only)

        # 6) Empate / ambiguo: si pide editar y hay editor, editar; si no, investigar.
        if edit and in_editor:
            return _result(EDITAR, "edición en un editor abierto", in_editor, read_only)

        return _result(INVESTIGAR, "sin señales claras: el modo que no rompe nada",
                       in_editor, read_only)
    except Exception:
        return _result(INVESTIGAR, "ante la duda, investigar", False, False)


def _result(mode: str, reason: str, in_editor: bool, read_only: bool) -> dict:
    return {"mode": mode, "reason": reason,
            "in_editor": bool(in_editor), "read_only": bool(read_only)}


_INSTRUCTIONS = {
    INVESTIGAR: ("Modo INVESTIGAR: leé, ejecutá y diagnosticá; NO edites archivos. "
                 "Proponé el parche concreto (archivo + líneas) sin aplicarlo."),
    EDITAR: ("Modo EDITAR: aplicá el cambio mínimo pedido, con backup previo. "
             "Después decí exactamente qué líneas cambiaste."),
    AUTONOMO: ("Modo AUTONOMO: leé → hipótesis → probá → verificá → reintentá "
               "(con tope). Backup antes de escribir. No digas 'listo' sin verificar."),
}


def instruction(mode: str) -> str:
    """Bloque de instrucción para inyectar en el prompt según el modo."""
    return _INSTRUCTIONS.get(mode, _INSTRUCTIONS[INVESTIGAR])
