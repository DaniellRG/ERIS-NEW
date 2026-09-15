"""
test_params_tool.py — Tool creada por Eris en runtime.

necesita input
Creada: 2026-09-15 10:21
"""
import json


def test_params_tool_tool(parameters=None, player=None):
    params = parameters or {}
    action = str(params.get('action') or 'status').lower().strip()
    if action == 'status':
        return json.dumps({'tool': 'test_params_tool', 'status': 'activa'}, ensure_ascii=False)
    if action == 'sumar3':
        return sumar3(params)

    return json.dumps({'tool': 'test_params_tool', 'action': action, 'status': 'ok'}, ensure_ascii=False)



def sumar3(params: dict):
    """suma a+b+c"""
    return json.dumps({"total": params["a"] + params["b"] + params["c"]}, ensure_ascii=False)
