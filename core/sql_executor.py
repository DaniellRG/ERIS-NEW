"""SQL query builder + executor for Eris."""
import json
import sqlite3
from pathlib import Path

def sql_executor_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready", "engines": ["sqlite"]})
    elif action == "query":
        db_path = params.get("db", "")
        query = params.get("query", "")
        if not query:
            return json.dumps({"error": "Query required"})
        if not db_path:
            return json.dumps({"error": "Database path required"})
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query)
            if query.strip().upper().startswith("SELECT"):
                rows = [dict(r) for r in cur.fetchall()[:100]]
                return json.dumps({"rows": rows, "count": len(rows), "columns": list(rows[0].keys()) if rows else []})
            else:
                conn.commit()
                return json.dumps({"affected": cur.rowcount, "status": "executed"})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
        finally:
            conn.close()
    elif action == "tables":
        db_path = params.get("db", "")
        if not db_path:
            return json.dumps({"error": "Database path required"})
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            schema = {}
            for t in tables:
                cur.execute("PRAGMA table_info({})".format(t))
                schema[t] = [{"name": r[1], "type": r[2], "pk": bool(r[5])} for r in cur.fetchall()]
            conn.close()
            return json.dumps({"tables": tables, "schema": schema})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
    elif action == "build_insert":
        table = params.get("table", "")
        data = params.get("data", {})
        if not table or not data:
            return json.dumps({"error": "Table and data required"})
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = "INSERT INTO {} ({}) VALUES ({})".format(table, cols, placeholders)
        return json.dumps({"sql": sql, "values": list(data.values())})
    elif action == "build_select":
        table = params.get("table", "")
        where = params.get("where", "")
        columns = params.get("columns", "*")
        if not table:
            return json.dumps({"error": "Table required"})
        sql = "SELECT {} FROM {}".format(columns, table)
        if where:
            sql += " WHERE {}".format(where)
        return json.dumps({"sql": sql})
    return json.dumps({"error": "Unknown action"})
