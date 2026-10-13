"""
eris_cli.py — Interfaz de terminal para Eris (estilo opencode).
Ejecutar: python eris_cli.py  ó  eris (via .bat en PATH)

Modo de texto puro: chat con Gemini + ejecución de tools + historial.
"""
import asyncio
import json
import os
import sys
import signal
import traceback
import threading
import queue as _queue
from contextlib import contextmanager
from pathlib import Path

try:
    import readline
except Exception:
    readline = None

# ── Setup paths ──
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.logging_setup import API_CONFIG_PATH, PROMPT_PATH, setup_logging
setup_logging()

# ── Colores ANSI ──
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    GRAY    = "\033[90m"
    BG_BLUE = "\033[44m"

# ── Sesiones persistidas ──
_SESSIONS_DIR = BASE_DIR / "data" / "cli_sessions"

# ── Autocompletado con readline ──
CLI_CMDS = [
    "/salir", "/exit", "/quit", "/q",
    "/reset", "/help", "/menu", "/ayuda", "/comandos",
    "/clear", "/tools", "/memoria", "/status",
    "/sesion", "/sesion lista", "/sesion nueva", "/sesion borrar",
    "/sesion actual", "/sesion salvar",
]

def _setup_autocomplete():
    if readline is None:
        return
    try:
        # Historial persistente
        hist_dir = BASE_DIR / "data"
        hist_dir.mkdir(parents=True, exist_ok=True)
        hist_file = hist_dir / "cli_history.txt"
        try:
            readline.read_history_file(hist_file)
        except Exception:
            pass
        import atexit
        atexit.register(readline.write_history_file, hist_file)
        readline.set_history_length(1000)
    except Exception:
        pass

    def completer(text, state):
        try:
            buf = readline.get_line_buffer()
            buf_l = buf.lstrip()
            # Autocompletar comandos que empiecen con /
            if buf_l.startswith("/"):
                matches = [c for c in CLI_CMDS if c.startswith(buf_l)]
                if state < len(matches):
                    return matches[state]
                return None
            return None
        except Exception:
            return None

    readline.set_completer(completer)
    try:
        if "libedit" in readline.__doc__ or os.name == "darwin":
            readline.parse_and_bind("bind -e")
            readline.parse_and_bind("bind '\t': complete")
        else:
            readline.parse_and_bind("tab: complete")
    except Exception:
        pass


def _safe_name(name: str) -> str:
    import re
    return re.sub(r"[^\w\-]+", "_", name.strip()).strip("_") or "sesion"


def _session_path(name: str) -> Path:
    return _SESSIONS_DIR / f"{_safe_name(name)}.json"


def _save_session(chat, name: str):
    import json as _json
    try:
        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "name": name,
            "backend": chat.backend_name,
            "history": chat.export_history(),
            "updated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        }
        _session_path(name).write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"{C.RED}Error guardando sesión: {e}{C.RESET}")


def _load_session(chat, name: str) -> bool:
    import json as _json
    p = _session_path(name)
    if not p.exists():
        return False
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
        chat.import_history(data.get("history", []))
        return True
    except Exception as e:
        print(f"{C.RED}Error cargando sesión: {e}{C.RESET}")
        return False


def _list_sessions() -> list:
    if not _SESSIONS_DIR.exists():
        return []
    out = []
    for f in sorted(_SESSIONS_DIR.glob("*.json")):
        try:
            import json as _json
            data = _json.loads(f.read_text(encoding="utf-8"))
            n = len(data.get("history", []))
            out.append((data.get("name", f.stem), n, data.get("updated", "")))
        except Exception:
            out.append((f.stem, 0, ""))
    return out


def _delete_session(name: str) -> bool:
    p = _session_path(name)
    if p.exists():
        try:
            p.unlink()
            return True
        except Exception:
            pass
    return False

# ── ASCII Art Banner ──
BANNER = rf"""
{C.CYAN}{C.BOLD}███████╗██████╗ ██╗███████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔════╝██╔══██╗██║██╔════╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
█████╗  ██████╔╝██║███████╗█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
██╔══╝  ██╔══██╗██║╚════██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
███████╗██║  ██║██║███████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
╚══════╝╚═╝  ╚═╝╚═╝╚══════╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝
{C.RESET}{C.DIM}  Asistente IA — Modo Terminal{C.RESET}
{C.GRAY}  ERIS-AGENT — Escribe tu mensaje, o pulsa '/' para ver menú. '/salir' para cerrar.{C.RESET}
"""
HELP_TEXT = f"""\
{C.CYAN}{C.BOLD}Comandos CLI:{C.RESET}
  {C.GREEN}/salir{C.RESET}      Cerrar Eris CLI
  {C.GREEN}/reset{C.RESET}      Limpiar historial de conversación
  {C.GREEN}/help{C.RESET}       Mostrar esta ayuda
  {C.GREEN}/tools{C.RESET}      Listar tools disponibles
  {C.GREEN}/memoria{C.RESET}    Ver memoria de Eris
  {C.GREEN}/status{C.RESET}     Estado del sistema
  {C.GREEN}/clear{C.RESET}      Limpiar pantalla
  {C.GREEN}/sesion lista{C.RESET}       Ver sesiones guardadas
  {C.GREEN}/sesion nueva NOMBRE{C.RESET} Crear/abrir sesión nueva
  {C.GREEN}/sesion NOMBRE{C.RESET}      Cambiar a esa sesión (la crea si no está)
  {C.GREEN}/sesion borrar NOMBRE{C.RESET} Eliminar una sesión guardada
  {C.GREEN}/sesion actual{C.RESET}      Mostrar sesión actual
  {C.GREEN}/sesion salvar{C.RESET}      Guardar la sesión actual

{C.DIM}Tip: Escribe solo {C.GREEN}/{C.RESET}{C.DIM} para ver menú completo con ejemplos para hablarle a Eris.{C.RESET}
"""

SLASH_MENU = f"""\
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════════════════════╗{C.RESET}
{C.CYAN}{C.BOLD}║                        MENÚ DE COMANDOS ERIS                        ║{C.RESET}
{C.CYAN}{C.BOLD}╚══════════════════════════════════════════════════════════════════════╝{C.RESET}

{C.YELLOW}{C.BOLD}[ COMANDOS DEL CLI ]{C.RESET}
  {C.GREEN}/salir{C.RESET}                Cerrar Eris CLI
  {C.GREEN}/reset{C.RESET}                Limpiar historial
  {C.GREEN}/help{C.RESET}                 Mostrar esta ayuda
  {C.GREEN}/clear{C.RESET}                Limpiar pantalla
  {C.GREEN}/tools{C.RESET}                Listar todas las tools ({C.DIM}@TOOLS@{C.RESET})
  {C.GREEN}/memoria{C.RESET}              Ver memoria de Eris
  {C.GREEN}/status{C.RESET}               Estado del sistema
  {C.GREEN}/sesion lista{C.RESET}         Ver sesiones guardadas
  {C.GREEN}/sesion nueva <nombre>{C.RESET} Crear nueva sesión
  {C.GREEN}/sesion <nombre>{C.RESET}      Cambiar/cargar sesión
  {C.GREEN}/sesion borrar <nombre>{C.RESET} Eliminar sesión
  {C.GREEN}/sesion actual{C.RESET}        Mostrar sesión actual
  {C.GREEN}/sesion salvar{C.RESET}        Guardar sesión actual

{C.YELLOW}{C.BOLD}[ HABLARLE A ERIS (lenguaje natural) ]{C.RESET}
  {C.CYAN}Archivos & Directorios{C.RESET}
    • "lista los archivos de este directorio"
    • "lee main.py"
    • "crea archivo.py con este contenido..."
    • "busca 'HERMES' en todos los .py"
    • "muestra las últimas 20 líneas de eris.log"

  {C.CYAN}Código{C.RESET}
    • "revisa este archivo por errores"
    • "explica qué hace core/gemini_text_chat.py"
    • "corrige imports rotos"
    • "ejecuta test_all.py y dime solo fallos"

  {C.CYAN}Sistema & Terminal{C.RESET}
    • "ejecuta ls -la"
    • "muestra uso de disco"
    • "procesos corriendo"
    • "reinicia servicio..."

  {C.CYAN}Búsqueda & Análisis{C.RESET}
    • "resumir README.md"
    • "¿qué hace esta función?"
    • "encuentra donde se define _main"
    • "compara estos dos archivos"

  {C.CYAN}Organización{C.RESET}
    • "ordena archivos por extensión"
    • "renombra este archivo"
    • "mueve logs a backups/"

{C.DIM}Todo lo que NO empiece con / se envía directamente a Eris.{C.RESET}
{C.DIM}Escríbelo en español, natural. Eris elegirá las tools necesarias.{C.RESET}
"""

# ── UI Stub para ToolDispatcher ──
class CLIStub:
    """Stub mínimo que satisface las interfaces que ToolDispatcher necesita."""
    def __init__(self):
        self.ui = self
        self._state = "IDLE"
        self._session_id = "cli_session"
        self.is_sleeping = False

    # UI interface
    def set_state(self, state: str):
        self._state = state
        if state == "THINKING":
            print(f"  {C.GRAY}[pensando...]{C.RESET}", end="\r", flush=True)

    def write_log(self, msg: str):
        pass  # Silencioso en CLI

    @property
    def muted(self):
        return True  # Sin audio

    @property
    def visual_mode(self):
        return False

    def ask(self, question: str, options=None, timeout=30) -> bool:
        print(f"  {C.YELLOW}{question}{C.RESET}")
        ans = input(f"  {C.CYAN}[s/n]: {C.RESET}").strip().lower()
        return ans in ("s", "si", "sí", "y", "yes")

    # speak stub
    def speak(self, text: str, **kwargs):
        pass

    def speak_error(self, text: str):
        pass


# ── Carga del system prompt ──
def load_full_prompt() -> str:
    """Carga el prompt de Eris y lo adapta para modo texto."""
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        prompt = (
            "Sos Eris, una asistente IA colombiana con personalidad cálida. "
            "Hablás en español natural, cálido, como una persona real. "
            "NUNCA uses 'che' ni modismos argentinos."
        )

    cli_addition = """
## MODO TERMINAL (CLI)
Estás operando en modo terminal de texto (sin interfaz gráfica, sin cámara, sin micrófono).
- Respondé en texto plano.
- No narrés procesos internos.
- Si usás una tool, simplemente mostrá el resultado.
- Sé concisa pero completa.
- Emoji permitting: usá emojis con moderación para dar calidez.
"""
    return prompt + cli_addition


# ── Fase 3.1b: lectura de intención del turno ──
# Razones de INVESTIGAR que significan "no hay señal": no se inyecta nada.
_QUIET_REASONS = (
    "sin señales claras: el modo que no rompe nada",
    "ante la duda, investigar",
)


def _turn_intent(text: str, shared):
    """Devuelve ``(etiqueta, instruccion)`` para el turno.

    Etiqueta = modo accionable ("EDITAR"/"AUTONOMO") o "" (charla o INVESTIGAR
    explícito). Instrucción = bloque a inyectar, o "" si no hay nada que decir.
    Nunca lanza.
    """
    try:
        from core.intent_reader import classify, instruction
        res = classify(text or "", shared)
        mode = res.get("mode", "")
        reason = res.get("reason", "")
        if mode == "INVESTIGAR" and reason in _QUIET_REASONS:
            return "", ""
        tag = mode if mode in ("EDITAR", "AUTONOMO") else ""
        return tag, instruction(mode)
    except Exception:
        return "", ""


@contextmanager
def _intent_system(chat, text: str, shared):
    """Inyecta el modo en el system SOLO durante el turno y lo restaura.

    Yields la etiqueta del modo ("EDITAR"/"AUTONOMO") si se detectó uno accionable,
    o "" si el turno es charla normal. Garantiza la restauración aunque el turno
    se cancele (barge-in) o falle.
    """
    _orig = getattr(chat, "_system", "")
    _orig_compact = getattr(chat, "_system_compact", "")
    tag, instr = _turn_intent(text, shared)
    try:
        if instr:
            if _orig:
                chat._system = _orig + "\n\n" + instr
            if _orig_compact:
                chat._system_compact = _orig_compact + "\n\n" + instr
        yield tag
    finally:
        try:
            chat._system = _orig
            chat._system_compact = _orig_compact
        except Exception:
            pass


# ── Chat principal ──
async def chat_loop():
    """Loop principal de chat por terminal."""
    from core.gemini_text_chat import GeminiTextChat
    from core.tool_dispatcher import ToolDispatcher

    # Cargar tools custom (fábrica) para que estén disponibles en el CLI
    try:
        from core.tool_registry import install_custom_tools
        install_custom_tools(BASE_DIR)
        from core.tool_declarations import load_custom_tools
        load_custom_tools(BASE_DIR)
    except Exception:
        import traceback as _tb
        _tb.print_exc()

    stub = CLIStub()

    print(f"\n{C.DIM}Inicializando Eris...{C.RESET}")

    try:
        dispatcher = ToolDispatcher(stub)
        chat = GeminiTextChat(tool_dispatcher=dispatcher)
    except Exception as e:
        print(f"{C.RED}Error inicializando: {e}{C.RESET}")
        print(f"{C.DIM}{traceback.format_exc()}{C.RESET}")
        return

    # Cargar system prompt completo (el modo compact para Ollama, cuyo contexto
    # local es limitado; Gemini conserva siempre el prompt completo).
    full_prompt = load_full_prompt()
    cli_addition = """
## MODO TERMINAL (CLI)
Estás operando en modo terminal de texto (sin interfaz gráfica, sin cámara, sin micrófono).
- Respondé en texto plano.
- No narrés procesos internos.
- Si usás una tool, simplemente mostrá el resultado.
- Sé concisa pero completa.
- Emoji permitting: usá emojis con moderación para dar calidez.
"""
    if "ollama" in chat.backend_name or "groq" in chat.backend_name:
        try:
            from core.logging_setup import PROMPT_COMPACT_PATH
            compact = PROMPT_COMPACT_PATH.read_text(encoding="utf-8")
            if compact:
                chat._system = compact + cli_addition
            else:
                chat._system = full_prompt
        except Exception:
            chat._system = full_prompt
    else:
        chat._system = full_prompt

    # ── Fase 1.2: contexto compartido. La CLI deja de ser una isla: fija la raíz
    #    del proyecto (cwd) y espeja la conversación para que GUI y subagentes
    #    compartan el mismo contexto. ──
    shared = None
    try:
        from core.shared_context import get_shared_context
        shared = get_shared_context()
        shared.detect_project_root(os.getcwd())
        _shared_block = shared.context_block(include_convo=False, include_summary=False)
        if _shared_block:
            chat._system = (chat._system or "") + "\n\n" + _shared_block
        # ── Fase 2.3: al detectar un proyecto, Eris YA sabe qué hay adentro.
        #    Solo si hay marcador de proyecto (evita recorrer un cwd cualquiera). ──
        try:
            _proj = shared.project_root
            _root = Path(_proj) if _proj else None
            _is_proj = bool(_root and _root.is_dir() and any(
                (_root / m).exists() for m in
                (".git", "pyproject.toml", "setup.py", "package.json", "Cargo.toml", "go.mod")))
            if _is_proj:
                from core.codebase_explorer import codebase_explorer as _cbe
                _map = _cbe({"action": "map", "path": str(_root), "limit": 60})
                if _map and not _map.startswith("Sin "):
                    chat._system = (chat._system or "") + "\n\n[PROYECTO — MAPA]\n" + _map[:4000]
        except Exception:
            pass
    except Exception:
        shared = None

    backend = chat.backend_name
    backend_color = C.GREEN if "ollama" in backend else C.CYAN
    if "groq" in backend:
        backend_color = C.MAGENTA
    print(f"{C.GREEN}Eris lista.{C.RESET} Backend: {backend_color}{backend}{C.RESET}\n")

    # Sesión actual: cargar "default" si existe
    current_session = "default"
    if _load_session(chat, current_session):
        print(f"{C.DIM}Sesión '{current_session}' restaurada ({chat.get_history_len()} mensajes).{C.RESET}\n")

    import sys as _sys
    streamed = {"on": False}

    def _printer(tok: str):
        streamed["on"] = True
        _sys.stdout.write(tok)
        _sys.stdout.flush()

    def _handle_session(cmd_line: str):
        nonlocal current_session
        parts = cmd_line.split()
        sub = parts[1] if len(parts) > 1 else ""
        if sub == "lista":
            sessions = _list_sessions()
            if not sessions:
                print(f"{C.YELLOW}No hay sesiones guardadas.{C.RESET}")
                return
            print(f"\n{C.CYAN}{C.BOLD}Sesiones guardadas:{C.RESET}")
            for name, n, updated in sessions:
                mark = " →" if name == current_session else ""
                print(f"  {C.GREEN}{name}{C.RESET}{mark} ({n} mensajes, {updated})")
            print()
        elif sub == "actual" or sub == "hoy":
            print(f"Sesión actual: {C.GREEN}{current_session}{C.RESET} ({len(chat._history)} mensajes)")
        elif sub == "salvar":
            _save_session(chat, current_session)
            print(f"{C.GREEN}Sesión '{current_session}' guardada.{C.RESET}")
        elif sub == "borrar" and len(parts) >= 3:
            name = " ".join(parts[2:])
            if _delete_session(name):
                print(f"{C.GREEN}Sesión '{name}' eliminada.{C.RESET}")
            else:
                print(f"{C.YELLOW}No existe una sesión llamada '{name}'.{C.RESET}")
        elif sub == "nueva" and len(parts) >= 3:
            name = " ".join(parts[2:])
            _save_session(chat, current_session)
            current_session = name
            chat.reset()
            _load_session(chat, current_session)
            print(f"{C.GREEN}Sesión nueva: {current_session}{C.RESET}")
        elif sub and len(parts) >= 2:
            name = " ".join(parts[1:])
            _save_session(chat, current_session)
            current_session = name
            chat.reset()
            if _load_session(chat, current_session):
                print(f"{C.GREEN}Abriendo sesión '{current_session}' ({chat.get_history_len()} mensajes).{C.RESET}")
            else:
                print(f"{C.GREEN}Nueva sesión: {current_session}{C.RESET}")
        else:
            print(f"{C.YELLOW}Uso: /sesion [lista|nueva NOMBRE|NOMBRE|borrar NOMBRE|actual|salvar]{C.RESET}")

    # Cola y hilo para input tipo "type-ahead" + barge-in
    input_queue = _queue.Queue()
    current_task: asyncio.Task | None = None
    thinking = {"on": False}

    def _input_reader():
        while True:
            try:
                s = input()
                input_queue.put(s)
            except EOFError:
                break
            except RuntimeError:
                break
            except Exception:
                continue

    t_reader = threading.Thread(target=_input_reader, daemon=True)
    t_reader.start()

    async def get_next_input(prompt: str) -> str | None:
        try:
            print(prompt, end="", flush=True)
            while True:
                try:
                    line = await asyncio.to_thread(input_queue.get, True, 0.3)
                    print("\r" + " " * (len(prompt)), end="\r", flush=True)
                    return line
                except Exception:
                    if thinking["on"]:
                        try:
                            print(f"\r{C.DIM}⏳ Eris está pensando... (Ctrl+C para interrumpir){C.RESET}", end="", flush=True)
                        except Exception:
                            pass
                    continue
        except EOFError:
            return None

    while True:
        try:
            # Input con prompt personalizado
            user_line = await get_next_input(f"{C.GREEN}{C.BOLD}Tú >{C.RESET} ")
            if user_line is None:
                break
            user_input = user_line.rstrip("\n\r").strip()

            if not user_input:
                continue

            # ── Comandos CLI ──
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                # Mostrar menú completo si solo escribe "/" o variantes
                cmd_clean = user_input.strip().lower()
                if cmd_clean == "/" or cmd_clean in ("/menu", "/ayuda", "/comandos", "/help"):
                    try:
                        from core.tool_registry import get_all_tool_names
                        _n_tools = len(get_all_tool_names())
                    except Exception:
                        _n_tools = ""
                    print(SLASH_MENU.replace("@TOOLS@", str(_n_tools)))
                    continue

                if cmd in ("/salir", "/exit", "/quit", "/q"):
                    _save_session(chat, current_session)
                    print(f"\n{C.CYAN}Eris: {C.RESET}¡Hasta luego, señor! {C.DIM}(sesión '{current_session}' guardada){C.RESET}\n")
                    break

                elif cmd == "/reset":
                    chat.reset()
                    print(f"{C.YELLOW}Historial limpiado.{C.RESET}")
                    continue



                elif cmd == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    print(BANNER)
                    continue

                elif cmd == "/tools":
                    from core.tool_registry import get_all_tool_names
                    tools = get_all_tool_names()
                    print(f"\n{C.CYAN}{C.BOLD}Tools disponibles: {len(tools)}{C.RESET}")
                    for i, name in enumerate(sorted(tools), 1):
                        print(f"  {C.DIM}{i:3d}.{C.RESET} {name}")
                    print()
                    continue

                elif cmd == "/memoria":
                    try:
                        from memory.memory_manager import load_memory
                        mem = load_memory()
                        print(f"\n{C.CYAN}{C.BOLD}Memoria de Eris:{C.RESET}")
                        for key in list(mem.keys())[:10]:
                            val = mem[key]
                            if isinstance(val, dict):
                                print(f"  {C.GREEN}{key}:{C.RESET} {len(val)} entradas")
                            else:
                                print(f"  {C.GREEN}{key}:{C.RESET} {str(val)[:80]}")
                        print()
                    except Exception as e:
                        print(f"{C.RED}Error leyendo memoria: {e}{C.RESET}")
                    continue

                elif cmd.startswith("/sesion"):
                    _handle_session(cmd)
                    continue

                elif cmd == "/status":
                    print(f"\n{C.CYAN}{C.BOLD}Estado de Eris CLI:{C.RESET}")
                    backend = chat.backend_name
                    print(f"  {C.GREEN}Backend:{C.RESET} {backend}")
                    print(f"  {C.GREEN}Tools:{C.RESET} {len(get_all_tool_names())} disponibles")
                    print(f"  {C.GREEN}Historial:{C.RESET} {len(chat._history)} mensajes")
                    print(f"  {C.GREEN}Sesión:{C.RESET} {current_session}")
                    print(f"  {C.GREEN}Prompt:{C.RESET} {len(full_prompt)} caracteres")
                    print()
                    continue

                else:
                    print(f"{C.YELLOW}Comando no reconocido: {cmd}{C.RESET}")
                    print(f"{C.DIM}Escribe / para ver el menú de comandos.{C.RESET}")
                    continue

            # ── Chat con streaming de tokens ──
            streamed["on"] = False
            thinking["on"] = True
            try:
                if shared is not None and user_input:
                    shared.note(f"Usuario: {user_input}")
            except Exception:
                pass

            async def _run_chat():
                thinking["on"] = True
                try:
                    with _intent_system(chat, user_input, shared) as _mode:
                        _tag = f"{C.YELLOW}[{_mode}]{C.RESET} " if _mode else ""
                        print(f"  {_tag}{C.CYAN}{C.BOLD}Eris >{C.RESET} ", end="", flush=True)
                        if user_input:
                            resp = await asyncio.wait_for(
                                chat.stream_chat(user_input, on_token=_printer),
                                timeout=120.0
                            )
                        else:
                            resp = await asyncio.wait_for(
                                chat.stream_chat("", on_token=_printer),
                                timeout=120.0
                            )
                        return resp
                finally:
                    thinking["on"] = False

            current_task = asyncio.create_task(_run_chat())

            # Supervisar: si llega nuevo input mientras piensa → BARGE-IN
            response_final = ""
            while not current_task.done():
                try:
                    pending = input_queue.get_nowait()
                except _queue.Empty:
                    await asyncio.sleep(0.10)
                    continue
                except Exception:
                    await asyncio.sleep(0.10)
                    continue

                # Nuevo mensaje mientras procesa → cancelar (barge-in)
                try:
                    if streamed["on"]:
                        print("\n" + f"{C.YELLOW}⏸ Interrumpido por tu nuevo mensaje...{C.RESET}")
                    else:
                        print(f"\n{C.YELLOW}⏸ Interrumpido por tu nuevo mensaje...{C.RESET}")
                except Exception:
                    pass
                current_task.cancel()
                try:
                    await asyncio.wait_for(current_task, timeout=5.0)
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                current_task = None
                thinking["on"] = False

                # Procesar el nuevo mensaje inmediatamente (inyectado en contexto)
                user_input2 = pending.rstrip("\n\r").strip()
                if not user_input2:
                    streamed["on"] = False
                    print(f"  {C.CYAN}{C.BOLD}Eris >{C.RESET} ", end="", flush=True)
                    current_task = asyncio.create_task(_run_chat())
                    continue

                # Inyectar mensaje en historial (preserva trabajo en curso)
                try:
                    chat._history.append({"role": "user", "content": user_input2})
                except Exception:
                    pass

                try:
                    print(f"\n{C.YELLOW}✏️  Mensaje inyectado en contexto...{C.RESET}")
                except Exception:
                    pass

                streamed["on"] = False
                thinking["on"] = True
                print(f"  {C.CYAN}{C.BOLD}Eris >{C.RESET} ", end="", flush=True)

                async def _run_chat2():
                    thinking["on"] = True
                    try:
                        with _intent_system(chat, user_input2, shared):
                            resp = await asyncio.wait_for(
                                chat.stream_chat("", on_token=_printer),
                                timeout=120.0
                            )
                            return resp
                    finally:
                        thinking["on"] = False

                current_task = asyncio.create_task(_run_chat2())
                user_input = ""

            # Tarea terminó
            try:
                response_final = await current_task
            except asyncio.CancelledError:
                response_final = ""
                if streamed["on"]:
                    try:
                        print()
                    except Exception:
                        pass
                try:
                    print(f"{C.DIM}(interrumpido){C.RESET}")
                except Exception:
                    pass
            except asyncio.TimeoutError:
                print(f"\n{C.RED}Timeout: Eris tardó más de 120s en responder.{C.RESET}")
                response_final = ""
            except Exception as e:
                print(f"\n{C.RED}Error: {e}{C.RESET}")
                response_final = ""
            finally:
                current_task = None
                thinking["on"] = False

            try:
                if shared is not None and response_final:
                    shared.note(f"Eris: {response_final[:400]}")
            except Exception:
                pass

            if streamed["on"]:
                print()
            else:
                if response_final and not response_final.startswith("\033"):
                    print(f"{response_final}")
                else:
                    pass

            _save_session(chat, current_session)

        except KeyboardInterrupt:
            # Interrumpir respuesta en curso (barge-in manual), NO salir del CLI
            if current_task and not current_task.done():
                try:
                    if streamed["on"]:
                        print(f"\n{C.YELLOW}⏸ Interrumpido (Ctrl+C). Puedes seguir escribiendo...{C.RESET}")
                    else:
                        print(f"\n{C.YELLOW}⏸ Interrumpido (Ctrl+C). Puedes seguir escribiendo...{C.RESET}")
                except Exception:
                    pass
                current_task.cancel()
                try:
                    await asyncio.wait_for(current_task, timeout=3.0)
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                current_task = None
                thinking["on"] = False
                if streamed["on"]:
                    try:
                        print()
                    except Exception:
                        pass
            else:
                print(f"\n{C.DIM}(Ctrl+C — Sin tarea en curso){C.RESET}")
        except Exception as e:
            print(f"\n{C.RED}Error inesperado: {e}{C.RESET}")
            traceback.print_exc()


# ── Punto de entrada ──
def main():
    # Manejar Ctrl+C graciosamente
    signal.signal(signal.SIGINT, lambda *_: None)

    print(BANNER)

    # Configurar autocompletado
    try:
        _setup_autocomplete()
    except Exception:
        pass

    # Verificar API key (Gemini directo, o un proveedor OpenAI-compatible
    # como OpenRouter / Nous Portal vía openrouter_api_key)
    try:
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        api_key = cfg.get("gemini_api_key", "")
        or_key = cfg.get("openrouter_api_key", "")
        if not api_key and not or_key:
            print(f"{C.RED}No hay API key configurada.{C.RESET}")
            print(f"{C.DIM}Configurá tu key en: {API_CONFIG_PATH}{C.RESET}")
            return
        if api_key:
            print(f"{C.DIM}API key Gemini: ...{api_key[-6:]}{C.RESET}")
        else:
            print(f"{C.DIM}Backend OpenAI-compatible: {cfg.get('openrouter_model','?')} "
                  f"@ {cfg.get('openrouter_base_url','?')}{C.RESET}")
    except Exception as e:
        print(f"{C.RED}Error leyendo config: {e}{C.RESET}")
        print(f"{C.DIM}Archivo: {API_CONFIG_PATH}{C.RESET}")
        return

    # Ejecutar loop async
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print(f"\n{C.DIM}Sesión terminada.{C.RESET}")


if __name__ == "__main__":
    main()
