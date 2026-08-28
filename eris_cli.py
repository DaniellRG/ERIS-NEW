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
from pathlib import Path

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
{C.CYAN}{C.BOLD}
  ███████╗██████╗ ██╗   ██╗
  ██╔════╝██╔══██╗╚██╗ ██╔╝
  █████╗  ██████╔╝ ╚████╔╝
  ██╔══╝  ██╔══██╗  ╚██╔╝
  ███████╗██║  ██║   ██║
  ╚══════╝╚═╝  ╚═╝   ╚═╝
{C.RESET}{C.DIM}  Asistente IA — Modo Terminal{C.RESET}
{C.GRAY}  Escribe tu mensaje y presiona Enter. '/salir' para cerrar.{C.RESET}
"""

HELP_TEXT = f"""
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


# ── Chat principal ──
async def chat_loop():
    """Loop principal de chat por terminal."""
    from core.gemini_text_chat import GeminiTextChat
    from core.tool_dispatcher import ToolDispatcher

    stub = CLIStub()

    print(f"\n{C.DIM}Inicializando Eris...{C.RESET}")

    try:
        dispatcher = ToolDispatcher(stub)
        chat = GeminiTextChat(tool_dispatcher=dispatcher)
    except Exception as e:
        print(f"{C.RED}Error inicializando: {e}{C.RESET}")
        print(f"{C.DIM}{traceback.format_exc()}{C.RESET}")
        return

    # Cargar system prompt completo
    full_prompt = load_full_prompt()
    chat._system = full_prompt

    backend = chat.backend_name
    backend_color = C.GREEN if "ollama" in backend else C.CYAN
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

    while True:
        try:
            # Input con prompt personalizado
            try:
                user_input = input(f"{C.GREEN}{C.BOLD}Tú >{C.RESET} ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            # ── Comandos CLI ──
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                if cmd in ("/salir", "/exit", "/quit", "/q"):
                    _save_session(chat, current_session)
                    print(f"\n{C.CYAN}Eris: {C.RESET}¡Hasta luego, señor! {C.DIM}(sesión '{current_session}' guardada){C.RESET}\n")
                    break

                elif cmd == "/reset":
                    chat.reset()
                    print(f"{C.YELLOW}Historial limpiado.{C.RESET}")
                    continue

                elif cmd == "/help":
                    print(HELP_TEXT)
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
                    print(f"{C.DIM}Escribe /help para ver comandos disponibles.{C.RESET}")
                    continue

            # ── Chat con streaming de tokens ──
            streamed["on"] = False
            print(f"  {C.CYAN}{C.BOLD}Eris >{C.RESET} ", end="", flush=True)

            try:
                response = await asyncio.wait_for(
                    chat.stream_chat(user_input, on_token=_printer),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                print(f"\n{C.RED}Timeout: Eris tardó más de 120s en responder.{C.RESET}")
                response = ""
            except Exception as e:
                print(f"\n{C.RED}Error: {e}{C.RESET}")
                response = ""

            if streamed["on"]:
                print()
            else:
                if response and not response.startswith("\033"):
                    print(f"{response}")
                else:
                    print()

            _save_session(chat, current_session)

        except KeyboardInterrupt:
            print(f"\n\n{C.YELLOW}Ctrl+C detectado. Escribe '/salir' para cerrar.{C.RESET}\n")
        except Exception as e:
            print(f"\n{C.RED}Error inesperado: {e}{C.RESET}")
            traceback.print_exc()


# ── Punto de entrada ──
def main():
    # Manejar Ctrl+C graciosamente
    signal.signal(signal.SIGINT, lambda *_: None)

    print(BANNER)

    # Verificar API key
    try:
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        api_key = cfg.get("gemini_api_key", "")
        if not api_key:
            print(f"{C.RED}No hay API key configurada.{C.RESET}")
            print(f"{C.DIM}Configurá tu key en: {API_CONFIG_PATH}{C.RESET}")
            return
        print(f"{C.DIM}API key: ...{api_key[-6:]}{C.RESET}")
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
