"""
lab_pulse.py — Tool creada por Eris en runtime.

Pulso del Pentest Lab: estado del aprendizaje, escalada global e inventario de tools en un vistazo.
Creada: 2026-09-11 23:02
"""
import json


def lab_pulse_tool(parameters=None, player=None):
    params = parameters or {}
    action = str(params.get('action') or 'status').lower().strip()
    if action == 'status':
        return json.dumps({'tool': 'lab_pulse', 'status': 'activa'}, ensure_ascii=False)
    if action == 'aprendizaje':
        return aprendizaje(params)

    if action == 'escalada':
        return escalada(params)

    if action == 'inventario':
        return inventario(params)

    return json.dumps({'tool': 'lab_pulse', 'action': action, 'status': 'ok'}, ensure_ascii=False)



def aprendizaje(params: dict):
    """Estado del aprendizaje del lab (hallazgos, errores, caminos, niveles)."""
    import sys as _s
    _s.path.insert(0, 'core')
    from pentest_learning import _load
    st = _load()
    return f"hallazgos={len(st.get('hallazgos', []))} errores={len(st.get('errores', []))} caminos={len(st.get('caminos', []))} niveles={sorted(st.get('niveles', {}).keys())}"


def escalada(params: dict):
    """Dominios activos de la escalada global."""
    import sys as _s
    _s.path.insert(0, 'core')
    from escalada import _load as _el
    st = _el()
    activos = [d for d,v in st.get('dominios', {}).items() if v.get('nivel', 0) > 0]
    return f"{len(activos)}/{len(st.get('dominios', {}))} dominios activos: {', '.join(sorted(activos)) if activos else 'ninguno'}"


def inventario(params: dict):
    """Cantidad de tools registradas y declaradas."""
    import sys as _s
    _s.path.insert(0, 'core')
    from tool_registry import _TOOLS
    from tool_declarations import TOOL_DECLARATIONS
    return f"registry={len(_TOOLS)} declarations={len(TOOL_DECLARATIONS)}"
