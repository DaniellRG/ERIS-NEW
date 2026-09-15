"""
test_rota_tool.py — Tool creada por Eris en runtime.

tool que debe ser rechazada
Creada: 2026-09-15 10:20
"""
import json


def test_rota_tool_tool(parameters=None, player=None):
    params = parameters or {}
    action = str(params.get('action') or 'status').lower().strip()
    if action == 'status':
        return json.dumps({'tool': 'test_rota_tool', 'status': 'activa'}, ensure_ascii=False)
    if action == 'boom':
        return boom(params)

    return json.dumps({'tool': 'test_rota_tool', 'action': action, 'status': 'ok'}, ensure_ascii=False)



def boom(params: dict):
    """explota"""
    return 1/0
