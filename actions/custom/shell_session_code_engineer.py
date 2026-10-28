"""
shell_session_code_engineer.py — Tool creada por Eris en runtime.

Auto-fábrica ERIS: ejecuta la secuencia repetida shell_session|code_engineer (x7) y reporta el resultado de cada paso.
Creada: 2026-10-20 17:31
"""
import json


def shell_session_code_engineer_tool(parameters=None, player=None):
    params = parameters or {}
    action = str(params.get('action') or 'status').lower().strip()
    if action == 'status':
        return json.dumps({'tool': 'shell_session_code_engineer', 'status': 'activa'}, ensure_ascii=False)
    if action == 'run':
        return run_shell_session_code_engineer(params)

    return json.dumps({'tool': 'shell_session_code_engineer', 'action': action, 'status': 'ok'}, ensure_ascii=False)



def run_shell_session_code_engineer(params: dict):
    """Ejecuta la secuencia completa"""
    try:
        import json as _j
    except Exception:
        _j = None
    from core.tool_registry import get_tool as _gt
    pasos = ["shell_session", "code_engineer"]
    reporte = []
    for i, nombre_tool in enumerate(pasos, 1):
        try:
            fn = _gt(nombre_tool)
            r = fn({}, player) if fn else 'tool no disponible'
            if isinstance(r, (dict, list)) and _j:
                try:
                    r = _j.dumps(r, default=str)[:200]
                except Exception:
                    r = str(r)[:200]
            reporte.append({'paso': i, 'tool': nombre_tool, 'estado': 'ok', 'info': str(r)[:200]})
        except Exception as e:
            reporte.append({'paso': i, 'tool': nombre_tool, 'estado': 'error', 'info': str(e)[:150]})
    return {'proceso': 'secuencia auto', 'patron': 'shell_session|code_engineer', 'pasos': reporte}
