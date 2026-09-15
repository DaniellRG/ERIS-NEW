"""Auditoría de veracidad de Eris.

Registra los resultados REALES de cada tool (la evidencia) y, después de cada
turno, cruza la respuesta de Eris contra esa evidencia: si afirmó un éxito que
los registros contradicen (la tool devolvió error/vacío), queda una bandera que
se inyecta en el siguiente turno como [VERIFICACIÓN] para que Eris se corrija
sola. Previene la invención de acciones ("lo envié", "quedó listo", "ya lo hice")
cuando en verdad falló o no devolvió datos.

Uso:
    from core.truth_audit import record_tool, audit_turn, evidence_block
    record_tool("email_manager", "error", "Email no configurado")
    audit_turn("Listo, ya envié el correo")        # deja flag
    evidence_block()                                # para inyectar en el prompt
"""
import threading
import time
from collections import deque

_LOCK = threading.RLock()
_TOOL_LOG: deque = deque(maxlen=40)   # (ts, name, status, snippet)
_FLAGS: deque = deque(maxlen=6)       # (ts, text)

_SUCCESS_SIGNALS = (
    "envié", "envie", "guardé", "guarde", "creé", "cree", "borré", "borre",
    "modifiqué", "modifique", "actualicé", "actualice", "ejecuté", "ejecute",
    "instalé", "instale", "descargué", "descargue", "conecté", "conecte",
    "agregué", "agregue", "corregí", "corregi", "arreglé", "arregle",
    "ya lo hice", "ya lo resolví", "quedó listo", "quedó resuelto",
    "quedo listo", "quedo resuelto", "ya está listo", "ya esta listo",
    "funcionó", "funciono", "lo logré", "listo,", "hecho,",
)
# Señales que NO deberían dispararse por casualidad (evita falsos positivos
# en frases negativas o de despedida).
_NEGATORS = ("no pude", "no pude ", "no puedo", "no se pudo", "falló", "fallo ",
             "no funcionó", "no funciono", "no lo hice", "no lo envié", "no lo envie",
             "no encontré", "no encontre", "no existe", "todavía no", "todavia no",
             "no pude", "intenté", "intente")

# Dominios → palabras de la afirmación que lo implican. Solo se marca una
# afirmación de éxito si habla del MISMO dominio del tool que falló: si Eris
# dice "creé la nota" y lo que falló fue el email, no hay contradicción real.
_DOMAINS = {
    "email_manager": ("email", "mail", "correo", "envié", "envie", "mensaje", "reclamar", "soport", "queja"),
    "sms": ("sms", "mensaje", "texto", "enviar"),
    "web_search": ("busqué", "busque", "resultado", "página", "pagina", "encontré en internet"),
    "smart_browser": ("navegador", "página", "pagina", "descargué", "descargue", "abrí", "abri", "url"),
    "download": ("descargué", "descargue", "descarga", "bajé", "baje"),
    "file_write": ("guardé", "guarde", "creé", "cree", "archivo", "nota", "escribí", "escribi", "escribí el archivo"),
    "file_edit": ("modifiqué", "modifique", "edité", "edite", "cambié", "cambie", "archivo"),
    "code_helper": ("código", "codigo", "script", "función", "funcion que", "corregí", "corregi"),
    "task_manager": ("tarea", "marqué", "marque", "completé", "complete"),
    "chart_generator": ("gráfico", "grafico", "chart", "analicé", "analice"),
    "image_generator": ("imagen", "ilustración", "ilustracion", "foto", "dibujo"),
    "speech": ("dije", "hablé", "hable", "anuncié", "anuncie", "avisé", "avise", "pedí", "pedi por voz"),
    "desktop_notifications": ("notif", "avisé", "avise", "alerta", "aviso"),
    "window_manager": ("ventana", "abrí", "abri", "cerré", "cierre", "enfoqué", "enfoque"),
    "system_volume": ("volumen", "bajé", "baje", "subí", "subi", "silencié", "silencie"),
    "finance_tracker": ("gast", "ingres", "presupuesto", "transaccion", "registré", "registre"),
    "google_calendar": ("agend", "evento", "recordatorio en el calendario", "calendario"),
    "meeting_transcriber": ("transcri", "reunión", "reunion", "minuta"),
    "translator": ("tradu", "castellano", "inglés", "ingles", "al inglés"),
    "terminal_agent": ("terminal", "comando", "corrí", "corri el comando", "script"),
    "pc_control": ("reinic", "apagu", "bloque", "pantalla", "monitor", "wifi", "bluetooth"),
"pdf_editor": ("pdf", "documento", "firmé", "firme"),
    "screen_recorder": ("grab", "video"),
    "music": ("canción", "cancion", "música", "musica", "tema", "playlist", "puse", "sonando", "sonando algo"),
    "spotify": ("canción", "cancion", "música", "musica", "tema", "playlist", "spotify"),
    "radio": ("radio", "emisora", "sintoniz"),
    "smart_home": ("luces", "luz", "termostato", "calefacci", "aire acondicionado", "persiana", "enchufe", "alarma", "casa inteligente"),
    "home_assistant": ("luces", "luz", "termostato", "calefacci", "aire acondicionado", "persiana", "enchufe", "casa inteligente"),
    "screen_vision": ("miré", "mire", "vi", "pantalla", "ví la pantalla", "vi la pantalla", "captura", "pixel", "imagen de pantalla"),
    "screen_reader": ("leí la pantalla", "lei la pantalla", "texto de pantalla", "lectura de pantalla"),
    "memoria": ("memoria", "recordé", "recorde", "me acordé", "me acorde", "aquella vez", "recuerdo"),
    "memory_rag": ("memoria", "recordé", "recorde", "me acordé", "me acorde", "búsqueda en memoria", "busque en memoria"),
    "advanced_rag": ("rag", "memoria", "recuper", "busqué en mis archivos", "busque en mis archivos"),
    "sesiones": ("sesión", "sesion", "resumí la sesión", "resumi la sesion", "epílogo", "epilogo"),
    "cron_scheduler": ("rutina", "agendé", "agende", "programé", "programe", "diario", "semanal", "se repite", "recordatorio automático"),
    "ambiente": ("ambiente", "música de fondo", "musica de fondo", "lofi", "ambient"),
    "calendar_manager": ("evento", "escribí en el calendario", "escribi en el calendario", "reunión", "reunion", "recordatorio"),
    "cerebro": ("recordé", "recorde", "cerebro", "mi estado interno", "autoconsciencia", "estado mental"),
    "emotional_core": ("emocion", "sentimient", "me siento", "cambié mi estado", "cambie mi estado"),
}
_WINDOW = 180.0   # solo fallos recientes (3 min)
_FLAG_TTL = 600.0 # las correcciones envejecen (10 min) y dejan de mostrarse



def record_tool(name: str, status: str, snippet: str = "") -> None:
    """Registra la evidencia de una ejecución de tool (status: ok|error|vacío)."""
    try:
        with _LOCK:
            _TOOL_LOG.append((time.time(), str(name), str(status), str(snippet)[:160]))
    except Exception:
        pass


def _bad_recent(window: float = _WINDOW):
    with _LOCK:
        now = time.time()
        return [(n, s, seg) for (ts, n, s, seg) in _TOOL_LOG
                if now - ts < window and s != "ok"]


def audit_turn(text: str) -> list:
    """Cruza la respuesta final del turno contra la evidencia reciente.

    Devuelve la lista de flags detectados y los deja guardados para que
    `evidence_block()` los inyecte en el próximo turno. Solo marca si la
    afirmación de éxito habla del MISMO dominio que un tool que falló hace
    menos de 3 minutos (sin afirmación → sin marca; sin fallo → sin marca)."""
    flags: list = []
    if not text or not isinstance(text, str):
        return flags
    low = text.lower()
    if any(n in low for n in _NEGATORS):
        return flags
    signals = [s for s in _SUCCESS_SIGNALS if s in low]
    if not signals:
        return flags
    bad = _bad_recent()
    if not bad:
        return flags
    seen: set = set()
    for tname, tstatus, _seg in bad:
        tname_l = tname.lower()
        keywords = _DOMAINS.get(tname_l, (tname_l,))
        if any(k in low for k in keywords):
            if tname_l in seen:
                continue
            seen.add(tname_l)
            flags.append(
                f"Aseguraste un éxito de \"{tname}\" (\"{signals[0]}…\") pero el "
                f"registro REAL de este turno muestra: {tname} → {tstatus}. "
                f"Confésalo abiertamente; no lo des por hecho."
            )
    if flags:
        with _LOCK:
            now = time.time()
            for f in flags:
                _FLAGS.append((now, f))
    return flags


def evidence_block(max_items: int = 7) -> str:
    """Bloque [VERIFICACIÓN] con la evidencia real de las últimas tools + flags.

    Los flags envejecen (10 min): una corrección vieja deja de mostrarse para no
    convertirse en insistencia eterna."""
    try:
        lines = []
        for ts, name, status, snippet in list(_TOOL_LOG)[-max_items:]:
            sym = {"ok": "✔", "error": "✘ ERROR", "vacío": "◦ VACÍO"}.get(status, status)
            lines.append(f"- {name} → {sym} {snippet}")
        now = time.time()
        with _LOCK:
            flags = [f for fts, f in list(_FLAGS)[-3:] if now - fts < _FLAG_TTL]
        if not lines and not flags:
            return ""
        block = ["[VERIFICACIÓN — LO QUE HICISTE (evidencia real)]"]
        for line in lines:
            block.append(line)
        if flags:
            block.append("\n⚠️ Corregite: en tu última respuesta afirmaste algo que los registros contradicen:")
            for f_ in flags:
                block.append(f"- {f_}")
            block.append("¿Fue así? Reconocelo y no lo vuelvas a afirmar sin verificar.")
        return "\n".join(block)
    except Exception:
        return ""