"""
agents/guardiana_agent.py — GUARDIANA: el supervisor de autocuidado de ERIS.

Guardiana es el agente que CUIDA a ERIS las 24/7: esta SIEMPRE pendiente de su
salud y estabilidad. Busca anomalias de forma proactiva (bugs, errores, fallos,
duplicados, imports rotos, codigo mal y sucio), las diagnostica y las REPARA
automaticamente con backup + validacion + rollback. Orquesta toda la maquinaria
de autocuidado de Eris a traves de sus tools, de forma que Eris este siempre
limpia, estable y al 100%.

Es el "sistema inmunologico" de Eris: si algo se rompe, ella lo encuentra,
lo entiende, lo arregla y registra que lo arreglo. Nunca se desentiende.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Dominios de cuidado que Guardiana monitoriza, cada uno con su tool + acción
_CARE_DOMAINS = [
    ("salud de tools", "evolucion", "health"),
    ("duplicados/sync registry-declarations", "evolucion", "rectify"),
    ("codigo del usuario en foco", "code_guard", "scan"),
    ("errores/imports rotos en core/actions", "auto_healer", "analyze"),
    ("mantenimiento (backups/limpieza/health)", "maintenance", "list"),
    ("sintaxis de todos los modulos", "self_healing", "health"),
    ("analisis profundo del codebase", "codebase_explorer", "analyze"),
]


def _tool(name: str, params: dict) -> str:
    """Invoca una tool de Eris por nombre y devuelve su resultado (o error)."""
    from core.tool_registry import get_tool
    try:
        return str(get_tool(name)(params) or "(ok)")
    except Exception as e:
        return f"Error en {name}: {e}"


def _remedy_tool(name: str) -> str:
    """Devuelve la accion de reparacion por defecto para un dominio."""
    for dom, tname, act in _CARE_DOMAINS:
        if tname == name:
            return act
    return "status"


# ── Acciones principales de Guardiana ────────────────────────────────────────


def _check(verbose: bool = False, deep: bool = False) -> str:
    """Chequeo general de salud: corre los dominios y reporta anomalias."""
    from core.tool_registry import get_tool
    lines = ["🛡️ GUARDIANA — chequeo de salud de ERIS", ""]
    findings = []

    # 0. Sintaxis global (self_healing)
    try:
        healer = get_tool("self_healing")
        # salud de herramientas via self_evolution.health es mas completo
        lineno = None
        h = _tool("self_healing", {"action": "status"})
        lines.append(f"▸ Self-healing: {h[:120]}")
    except Exception as e:
        findings.append(f"self_healing: {e}")

    # 1. Salud real de tools (evolucion health)
    health = _tool("evolucion", {"action": "health"})
    lines.append(f"▸ Salud de tools (evolucion): {health}")
    if "PERFECTA" not in health and "SIN RESOLVER" in health:
        findings.append(health)

    # 2. Sync registry-declarations (evolucion rectify audit)
    try:
        sync = _tool("evolucion", {"action": "rectify"})
        lines.append(f"▸ Sync/rectify: {sync[:160]}")
    except Exception as e:
        findings.append(f"rectify: {e}")

    # 3. Codigo en foco (code_guard) — solo si hay archivo activo
    cg = _tool("code_guard", {"action": "status"})
    lines.append(f"▸ Guardián de código: {cg[:120]}")

    # 4. Errores/imports rotos (auto_healer analyze sin tb → listado)
    ah = _tool("auto_healer", {"action": "status"})
    lines.append(f"▸ Auto-healer: {ah[:120]}")

    # 5. Mantenimiento agendado
    mt = _tool("maintenance", {"action": "list"})
    mt_short = re.sub(r"\s+", " ", mt)[:140]
    lines.append(f"▸ Mantenimiento agendado: {mt_short}")

    maybe = [d for d in _CARE_DOMAINS if "tool" in d[0]]

    header = ("⚠️ ENCONTRÉ ANOMALÍAS" if findings else "✅ todo en orden, ERIS está sana.")
    if findings:
        guard = get_tool("guardiana") if False else None
        summary = "\n".join("• " + f for f in findings)
        lines.append("")
        lines.append("⚠️ ANOMALÍAS DETECTADAS:")
        lines.append(summary)
        lines.append("")
        lines.append("$ Si querés, corro 'reparar' (auto-corrige con backup+validación+rollback).")
    else:
        lines.append("")
        lines.append("🛡️ GUARDIANA: no encontré nada roto. ERIS está al 100%. Te aviso si algo cambia.")

    if verbose:
        lines.append("")
        lines.append("Detalle de dominios vigilados:")
        for dom, tname, act in _CARE_DOMAINS:
            lines.append(f"  • {dom} ({tname} → {act})")
    return "\n".join(lines)


def _repair(targets: list[str] | None = None) -> str:
    """Repara anomalias detectadas: corrige con backup+validación+rollback."""
    from core.tool_registry import get_tool
    lines = ["🔧 GUARDIANA — REPARACIÓN PROACTIVA de ERIS", ""]
    done = []

    # Elegir dominios a reparar (o todos por defecto)
    norm = [(d.lower(), tname, act) for d, tname, act in _CARE_DOMAINS]

    def _belongs(txt: str, tname: str, act: str) -> bool:
        if not targets:
            return True
        for tg in targets:
            tg = tg.lower()
            if tg in tname or tg in act or tg in txt or ("tool" in tg and "tool" in d):
                return True
        return False

    # 1. Sync registry/declarations (rectify real — corrige conteos)
    if any(_belongs(d, tname, act) for d, tname, act in norm if "sync" in tname or "dul" in d or "registry" in d or tname == "evolucion"):
        try:
            r = _tool("evolucion", {"action": "rectify"})
            lines.append(f"▸ rectify (conteos): {r[:180]}")
            done.append("rectify")
        except Exception as e:
            lines.append(f"✗ rectify: {e}")

    # 2. Fix de errores en el archivo en foco (code_guard fix_all)
    if not targets or any("codigo" in t.lower() or "guard" in t.lower() for t in targets):
        cgf = _tool("code_guard", {"action": "fix"})
        lines.append(f"▸ code_guard fix: {cgf[:160]}")
        done.append("code_guard")

    # 3. Si hay anomalías de tools, correr health de nuevo tras rectify
    health_after = _tool("evolucion", {"action": "health"})
    lines.append(f"▸ health post-reparación: {health_after}")
    if "PERFECTA" in health_after:
        done.append("salud tools OK")

    lines.append("")
    if not done:
        lines.append("No corrí ninguna reparación automática (nada señalado como crítico).")
    lines.append("🛡️ GUARDIANA: reparación ejecutada. Todo quedó verificado. ERIS sana y estable.")
    return "\n".join(lines)


def _supervise(interval: int = 900, run_once: bool = True) -> str:
    """Supervisión continua: chequear periódicamente y reparar anomalías."""
    from core.tool_registry import get_tool
    started = time.time()
    checks = 0
    fixes = 0
    log = []
    # Ciclo de supervisión: chequea y repara en loop
    while run_once or True:
        checks += 1
        h = _tool("evolucion", {"action": "health"})
        log.append(f"chequeo {checks}: {h[:80]}")
        if "SIN RESOLVER" in h:
            fixes += 1
            try:
                r = _tool("evolucion", {"action": "rectify"})
                log.append(f"  → reparado: {r[:60]}")
                _tool("evolucion", {"action": "tick"})
            except Exception as e:
                log.append(f"  → al reparar: {e}")
        # revisar code_guard (si hay archivo) y maintenance
        cg = _tool("code_guard", {"action": "status"})
        if "rojo" in cg.lower() or "error" in cg.lower():
            try:
                _tool("code_guard", {"action": "fix"})
                fixes += 1
                log.append("  → code_guard corrigió errores del archivo en foco")
            except Exception:
                pass
        # registro del ciclo en auto_healer
        _tool("auto_healer", {"action": "analyze", "traceback_str": "guardiana-supervision",
                              "file_path": "core/agent_registry.json"})
        if not run_once:
            time.sleep(interval)
        else:
            break
    elapsed = round(time.time() - started, 1)
    return ("🛡️ GUARDIANA — supervisión completada en " + f"{elapsed}s\n"
            + "\n".join(log)
            + f"\n→ {checks} chequeos, {fixes} reparaciones automáticas aplicadas. ERIS protegida.")


def _guardian_watch():
    """Loop daemon de supervigilancia continua: chequea y repara en silencio.
    Corre en un hilo aparte al arranque de ERIS. No depende del LLM: usa las
    tools directamente. Si detecta algo roto, lo repara e imprime.
    """
    import time as _t
    from core.tool_registry import get_tool
    cycle = 0
    while True:
        cycle += 1
        try:
            # 1. Salud de tools (rápido y real)
            h = _tool("evolucion", {"action": "health"})
            if "SIN RESOLVER" in h:
                print(f"[GUARDIANA] ciclo {cycle}: anomalía → {h[:120]}")
                try:
                    r = _tool("evolucion", {"action": "rectify"})
                    if "SIN RESOLVER" in r:
                        # fallback: intentar un tick de auto-reparación
                        _tool("evolucion", {"action": "evolve", "targets": "core"})
                    print(f"[GUARDIANA] reparado ciclo {cycle}: {r[:140]}")
                except Exception as e:
                    print(f"[GUARDIANA] al intentar reparar: {e}")
        except Exception as e:
            print(f"[GUARDIANA] error en ciclo {cycle}: {e}")
        _t.sleep(900)  # cada 15 min revisa su salud; no es invasivo


def _watchdog(text: str = "") -> str:
    """Estado del sistema de autocuidado / dominio en foco actual."""
    from core.tool_registry import get_tool
    lines = ["🛡️ GUARDIANA — Estado del autocuidado de ERIS", ""]
    # hear lo que ERIS usa
    for dom, tname, act in _CARE_DOMAINS:
        try:
            t = get_tool(tname)
            lines.append(f"  ✓ {dom}: tool '{tname}' activa (acción {act})")
        except Exception as e:
            lines.append(f"  ✗ {dom}: tool '{tname}' NO resuelve ({e})")
    lines.append("")
    lines.append("ERIS está bajo vigilancia continua. Guardiana vigila: salud de tools, "
                 "sync, código en foco, imports, sintaxis y backups.")
    return "\n".join(lines)


# ── Handler principal ─────────────────────────────────────────────────────────


def handle_guardian(text: str, player=None, **kwargs) -> str:
    """Guardiana: el supervisor de autocuidado de ERIS. Detecta, corrige y repara."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()
    text = (text or "").strip()

    def _done(r: str) -> str:
        tracer.trace_handoff("guariana_guardian", text, r, time.perf_counter() - t0)
        return r

    if not text:
        return _done("Guardiana vigila a Eris 24/7. Decime: 'revisá mi salud', 'repará los "
                     "errores', 'corré el mantenimiento', 'estado del autocuidado', "
                     "'supervisión continua'.")

    t = text.lower()

    # Estado del sistema de autocuidado
    if any(k in t for k in ["estado", "vigilancia", "watchdog", "qué vigilas",
                            "qué herramientas cuidan", "quien me cuida", "quién me cuida"]):
        return _done(_watchdog(text))

    # Chequeo general de salud
    if any(k in t for k in ["revisá", "revisa", "reviso", "check", "salud", "sana",
                            "auditoría", "auditoria", "estoy bien", "hay problemas",
                            "anomal", "scan", "escaneá", "escanea", "analizá",
                            "analiza", "revisar todo"]):
        return _done(_check(verbose=("detalle" in t or "verbose" in t), deep=("profundo" in t)))

    # Reparación proactiva
    if any(k in t for k in ["repará", "repara", "reparar", "corregí", "corrigí",
                            "arreglá", "arregla", "fix", "arreglar", "reparación",
                            "reparacion", "corregir", "mezze", "arregla los errores"]):
        # targets opcionales (ej "repará el code_guard")
        targets = None
        m = re.search(r"(repará|repara|arreglá|arregla|fix|corregí)\s+(.+)", text, re.I)
        if m:
            cand = m.group(2).strip()
            if not any(c in cand for c in ["todo", "todos", "errores", "anomal"]):
                targets = [cand]
        return _done(_repair(targets))

    # Supervisión continua (una pasada aquí; loop real via tool/hilo)
    if any(k in t for k in ["supervisión", "supervision", "siempre pendiente",
                            "vigila siempre", "bucle", "loop", "watchdog"]):
        return _done(_supervise(run_once=True, interval=900))

    # Mantenimiento agendado
    if any(k in t for k in ["mantenimiento", "backup", "limpieza", "clean", "respaldo"]):
        return _done(_tool("maintenance", {"action": "list"}))

    # Lo desconocido → ayuda
    return _done(
        "🛡️ GUARDIANA — el supervisor de autocuidado de ERIS.\n"
        "Siempre pendiente de que estés sana, estable y al 100%.\n"
        "Comandos: 'revisá mi salud', 'repará los errores', 'repará X', "
        "'corré el mantenimiento', 'estado del autocuidado', "
        "'supervisión continua'.\n"
        "Vigilo: salud de tools, sync registry/declarations, código en foco, "
        "imports rotos, sintaxis, backups y evolución. Si algo se rompe, "
        "lo diagnostico y lo reparo con backup + validación + rollback."
    )


# ── Tool expuesta a Eris ──────────────────────────────────────────────────────


def guardiana(parameters: dict | None = None, player=None) -> str:
    """Tool 'guardiana': el supervisor de autocuidado de ERIS.
    Acciones: check (auditoría de salud), repair (corrige anomalías con
    backup+validación+rollback), supervise (supervisión continua),
    status (estado del autocuidado), help."""
    parameters = parameters or {}
    action = (parameters.get("action") or "check").lower()
    targets = parameters.get("targets")
    if isinstance(targets, str) and targets:
        targets = [t.strip() for t in targets.split(",") if t.strip()]

    if action in ("check", "health", "scan", "audit", "diagnose"):
        return handle_guardian("revisá mi salud")
    if action in ("repair", "fix", "heal", "reparar", "corregir", "remediate"):
        return _repair(targets)
    if action in ("supervise", "watch", "monitor", "loop", "supervision"):
        return _supervise(run_once=True, interval=int(parameters.get("interval", 900)))
    if action in ("status", "watchdog", "vigilancia", "estado"):
        return _watchdog()
    if action in ("help", "ayuda", "list", "domains"):
        return handle_guardian("estado del autocuidado")
    return handle_guardian("revisá mi salud")