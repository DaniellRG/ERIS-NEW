# Contributing a ERIS

Guía para tocar el código de ERIS sin romper lo que ya funciona. Reglas duras
primero, convenciones después.

## Reglas duras (violarlas = quebrar Eris)

1. **Tool sync es sagrada.** Si agregás o sacás una tool tenés que editar
   `core/tool_registry.py` **y** `core/tool_declarations.py`, y verificar:
   ```python
   from core.tool_registry import _TOOLS
   from core.tool_declarations import TOOL_DECLARATIONS
   assert len(_TOOLS) == len(TOOL_DECLARATIONS) == 448  # mismo largo
   names = [t["name"] for t in TOOL_DECLARATIONS]
   assert len(names) == len(set(names))                 # 0 duplicados
   ```
   Reiniciá Eris después. `core/action_imports.py` importa un módulo por tool:
   si el módulo no importa limpio, se rompe TODO el árbol.

2. **Deps opcionales = guard TODO.** Cuando importás algo opcional (openpyxl,
   PyQt6, google-genai, chromadb…) vía `try/except ImportError`, **ninguna
   referencia a nivel de módulo** puede usar esos nombres fuera del guard:
   ni constantes de estilo, ni `class X(QBase)`, ni args default. Si lo hacés
   el módulo explota con `NameError`/`TypeError` al importar en una máquina
   sin esa dep y tira abajo `core/action_imports.py` entero. Ejemplos reales
   ya corregidos: `actions/spreadsheet_generator.py`,
   `actions/accessibility_overlay.py`.

3. **Nunca hardcodees rutas Windows.** No `D:\Eris_*`, `C:\Users\...`, ni
   `ctypes.windll` suelto. Usá `BASE = Path(__file__).resolve().parent.parent`,
   env vars (`ERIS_WORKSPACE`, `ERIS_OBSIDIAN_VAULT`) con fallback, y guardá
   `ctypes` con `if os.name == "nt":`. Para el vault: `from
   core.logging_setup import get_obsidian_vault`.

4. **Gate de tests.** Después de cualquier cambio estructural corré
   `python test_all.py`. En Windows tiene que dar **56 PASS, 0 FAIL**.
   El `BASE` de `test_all.py` es portable — no lo vuelvas a hardcodear.

5. **`config/api_keys.json`: UTF-8 sin BOM.** BOM → crash al cargar. Escribilo
   con `Path.write_text(json, encoding="utf-8")` o PowerShell con
   `[System.IO.File]::WriteAllText($p, $json, (New-Object System.Text.UTF8Encoding($false)))`.

## Convenciones

- **Una tool por archivo** en `actions/`, expuesta como `run()`. `296`
  módulos hoy.
- **JSON-encoded en STRING, no ARRAY**: Gemini rechaza `array` en los
  parámetros de las declaraciones (ver `actions/office_tools.py`).
- **Ollama manda `arguments` como `dict`**: chequeá `isinstance(raw_args,
  dict)` antes de `json.loads`.
- **Excepciones tipadas**: no `except:` desnudo (queda el analizador de
  `self_evolution` y el de `cybersecurity` como único caso justificado).
- **Comentarios en español**, concisos. Sin emojis salvo que el código ya los
  use en strings de usuario.
- Mantené `AGENTS.md` al día: agregá constraints no obvios al descubrirlos
  (te ahorran el bug la próxima vez).
- Servicio `vault/` vivo (raw → wiki → outputs) es parte del sistema; no
  borres su estructura al refactorizar.

## Build y ejecución

- Windows: `.\.venv\Scripts\pythonw.exe main.py`
- Linux: `./run_linux.sh`
- CLI: `eris`
- Tests: `python test_all.py`