"""
test_smoke_tool.py — Tool creada por Eris en runtime.

Tool de prueba para validar el ciclo de la fabrica.
Creada: 2026-09-15 10:20
"""
import json


def test_smoke_tool_tool(parameters=None, player=None):
    params = parameters or {}
    action = str(params.get('action') or 'status').lower().strip()
    if action == 'status':
        return json.dumps({'tool': 'test_smoke_tool', 'status': 'activa'}, ensure_ascii=False)
    if action == 'calcular':
        return calcular(params)

    return json.dumps({'tool': 'test_smoke_tool', 'action': action, 'status': 'ok'}, ensure_ascii=False)



def calcular(params: dict):
    """suma dos numeros"""
    a = params.get("a", 0)
    b = params.get("b", 0)
    return json.dumps({"suma": a + b}, ensure_ascii=False)
