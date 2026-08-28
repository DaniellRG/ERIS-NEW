"""Database schema visualizer for Eris."""
import json
import sqlite3
from pathlib import Path

def db_schema_visualizer_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"formats": ["text", "mermaid", "json"]})
    elif action == "visualize":
        db_path = params.get("db", "")
        fmt = params.get("format", "text")
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
                schema[t] = [{"name": r[1], "type": r[2], "pk": bool(r[5]), "notnull": bool(r[3])} for r in cur.fetchall()]
                cur.execute("PRAGMA foreign_key_list({})".format(t))
                fks = [{"from": r[3], "table": r[2], "to": r[4]} for r in cur.fetchall()]
                schema[t + "_fks"] = fks
            conn.close()
            if fmt == "mermaid":
                md = "erDiagram\n"
                for t in tables:
                    md += "    {} {{\n".format(t)
                    for col in schema.get(t, []):
                        md += "        {} {}{}\n".format(col["type"], col["name"], " PK" if col["pk"] else "")
                    md += "    }\n"
                return json.dumps({"mermaid": md, "tables": len(tables)})
            elif fmt == "json":
                return json.dumps({"schema": {t: schema.get(t, []) for t in tables}, "tables": len(tables)})
            else:
                lines = []
                for t in tables:
                    lines.append("TABLE: {}".format(t))
                    for col in schema.get(t, []):
                        pk = " [PK]" if col["pk"] else ""
                        nn = " NOT NULL" if col["notnull"] else ""
                        lines.append("  {} {}{}{}".format(col["name"], col["type"], pk, nn))
                    lines.append("")
                return json.dumps({"text": "\n".join(lines), "tables": len(tables)})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
    return json.dumps({"error": "Unknown action"})
