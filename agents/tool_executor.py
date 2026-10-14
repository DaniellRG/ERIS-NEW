"""
ToolExecutor — Sub-agente especializado en ejecutar tools de Eris.

Este agente tiene acceso a TODAS las tools de Eris y puede ejecutarlas
cuando Eris se lo pida. Es el puente entre la conversación y la ejecución
real de acciones.

Uso:
    from agents.tool_executor import ToolExecutor
    executor = ToolExecutor()
    result = executor.execute("web_search", {"query": "Python 3.14"})
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

# Añadir el root del proyecto al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.tool_dispatcher import ToolDispatcher
from core.tool_registry import get_tool


class ToolExecutor:
    """Sub-agente que ejecuta tools de Eris con control total."""

    def __init__(self):
        self._dispatcher = self._build_dispatcher()
        self._tool_cache = {}

    def _build_dispatcher(self) -> ToolDispatcher:
        """Construye un dispatcher con un mock de UI."""
        class MockUI:
            def __init__(self):
                self.ui = self
                self._state = "IDLE"
                self._session_id = "tool_executor"
                self.is_sleeping = False

            def set_state(self, s):
                pass

            def write_log(self, m):
                pass

            @property
            def muted(self):
                return True

            @property
            def visual_mode(self):
                return False

            def ask(self, q, options=None, timeout=30):
                # F5b: fail-closed. Antes devolvía True y auto-aprobaba CUALQUIER
                # confirmación (bypass real del permission gate en esta ruta).
                return False

            def speak(self, t, **k):
                pass

            def speak_error(self, t):
                pass

        return ToolDispatcher(MockUI())

    def list_tools(self) -> List[str]:
        """Lista todas las tools disponibles."""
        from core.tool_registry import _TOOLS
        return sorted(_TOOLS.keys())

    def get_tool_info(self, name: str) -> Optional[Dict]:
        """Obtiene información de una tool específica."""
        tool = get_tool(name)
        if tool is None:
            return None
        import inspect
        sig = inspect.signature(tool)
        return {
            "name": name,
            "signature": str(sig),
            "doc": (tool.__doc__ or "").strip()[:200],
        }

    def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Ejecuta una tool con los parámetros dados, PASANDO por las guardas.

        F5b (2026-10-13): esta ruta tenía un MockUI cuyo ask() devolvía True, así
        que toda confirmación se auto-aprobaba y el permission gate quedaba
        sorteado (bypass real de las aprobaciones, usado por ActionDetector en
        main.py). Ahora se consultan las MISMAS guardas que el chat:
          1) Custodio (`guard_check`): bloqueos duros por patrón/parámetro.
          2) Árbitro único (`permission_gate`): mismo criterio de riesgo. Esta
             ruta no tiene canal interactivo confiable, así que si algo pide
             confirmación se DENIEGA (fail-closed) en vez de auto-aprobarse.
        """
        tool = get_tool(tool_name)
        if tool is None:
            return f"Error: tool '{tool_name}' no encontrada"

        # 1) Custodio de acciones (bloqueos duros por patrón/parámetro).
        try:
            from core.tool_dispatch_api import guard_check
            verdict = guard_check(tool_name, params)
            if not verdict.allowed:
                return f"⛔ Bloqueado por el Custodio: {verdict.message or verdict.reason}"
        except Exception as e:
            return (f"No pude evaluar la seguridad de '{tool_name}' "
                    f"({type(e).__name__}); se deniega por precaución.")

        # 2) Permission gate: MISMO criterio de riesgo que el chat principal.
        #    Esta ruta no tiene canal interactivo confiable → fail-closed.
        try:
            from core.permission_gate import get_permission_gate
            needs, risk, desc = get_permission_gate().assess_risk(tool_name, params)
            if needs:
                return (f"⛔ '{tool_name}' requiere confirmación "
                        f"([RIESGO {risk.upper()}] {desc}). Pedila desde el chat "
                        f"principal, donde Eris puede preguntarte.")
        except Exception:
            return f"⛔ No pude evaluar el permiso de '{tool_name}'; se deniega por precaución."

        try:
            kwargs = self._dispatcher._build_kwargs(tool, params)
            result = tool(**kwargs)
            if asyncio.iscoroutine(result):
                result = self._run_coroutine(result)
            return str(result)
        except Exception as e:
            return f"Error ejecutando {tool_name}: {type(e).__name__}: {str(e)[:200]}"

    @staticmethod
    def _run_coroutine(coro):
        """Resuelve una corrutina aunque ya haya un event loop corriendo.

        `asyncio.run()` explota con 'asyncio.run() cannot be called from a
        running event loop' cuando el executor corre dentro de la GUI (que ya
        tiene su loop). En ese caso la corrutina se resuelve en un hilo propio.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No hay loop corriendo en este hilo → camino normal.
            return asyncio.run(coro)

        # Hay un loop corriendo: resolver en un hilo aparte con su propio loop.
        import threading
        box: Dict[str, Any] = {}

        def _worker():
            try:
                box["result"] = asyncio.run(coro)
            except Exception as e:  # propagar el error al hilo que llamó
                box["error"] = e

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=120)
        if "error" in box:
            raise box["error"]
        if t.is_alive():
            raise TimeoutError(f"la corrutina de {getattr(coro, '__qualname__', 'tool')} superó 120s")
        return box.get("result", "")

    def execute_batch(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """Ejecuta un batch de tasks."""
        results = []
        for task in tasks:
            name = task.get("name", "")
            params = task.get("params", {})
            result = self.execute(name, params)
            results.append(result)
        return results

    def can_execute(self, tool_name: str) -> bool:
        """Verifica si una tool existe y puede ser ejecutada."""
        return get_tool(tool_name) is not None


# Instancia global para uso en toda la aplicación
_executor = None

def get_tool_executor() -> ToolExecutor:
    """Obtiene la instancia global del ToolExecutor."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor


if __name__ == "__main__":
    # Test básico
    executor = ToolExecutor()
    print(f"Tools disponibles: {len(executor.list_tools())}")
    print(f"system_monitor existe: {executor.can_execute('system_monitor')}")
    print(f"web_search existe: {executor.can_execute('web_search')}")
    print(f"file_api existe: {executor.can_execute('file_api')}")
