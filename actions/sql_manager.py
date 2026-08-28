"""
actions/sql_manager.py — SQL database manager for ERIS.
Supports SQLite (built-in) and PostgreSQL (psycopg2, optional).
Actions:
  connect    — Connect to a database
  query      — Execute a SELECT query
  execute    — Execute INSERT/UPDATE/DELETE
  tables     — List all tables
  schema     — Show table schema
  export     — Export query results to JSON/CSV
  disconnect — Close connection
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

_connections: dict[str, object] = {}
_cursor: dict[str, object] = {}
_db_type: dict[str, str] = {}


def _get_conn(name: str = "default"):
    return _connections.get(name)


def _get_cur(name: str = "default"):
    return _cursor.get(name)


def _get_type(name: str = "default"):
    return _db_type.get(name, "sqlite")


def sql_manager(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "status")).strip().lower()
    name = str(params.get("name", "default")).strip() or "default"

    if player:
        try:
            player.write_log(f"[SQL] action={action} db={name}")
        except Exception:
            pass

    if action == "connect":
        return _connect(params, name)
    elif action == "query":
        return _query(params, name)
    elif action == "execute":
        return _execute(params, name)
    elif action == "tables":
        return _tables(name)
    elif action == "schema":
        return _schema(params, name)
    elif action == "export":
        return _export(params, name)
    elif action == "disconnect":
        return _disconnect(name)
    elif action == "status":
        return _status(name)
    return "Actions: connect, query, execute, tables, schema, export, disconnect, status"


def _connect(params: dict, name: str) -> str:
    db_type = str(params.get("type", "sqlite")).strip().lower()

    if db_type == "postgresql" or db_type == "postgres":
        if not HAS_PSYCOPG2:
            return "psycopg2 no instalado. Ejecutá: pip install psycopg2-binary"
        host = str(params.get("host", "localhost")).strip()
        port = str(params.get("port", "5432")).strip()
        user = str(params.get("user", "postgres")).strip()
        password = str(params.get("pass", "")).strip()
        database = str(params.get("db", "postgres")).strip()
        try:
            conn = psycopg2.connect(
                host=host, port=port, user=user,
                password=password, dbname=database
            )
            conn.autocommit = True
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            _connections[name] = conn
            _cursor[name] = cur
            _db_type[name] = "postgresql"
            return f"Conectado a PostgreSQL: {host}:{port}/{database} (conexión '{name}')"
        except Exception as e:
            return f"Error conectando a PostgreSQL: {e}"

    else:
        db_path = str(params.get("db_path", params.get("path", ""))).strip()
        if not db_path:
            db_path = str(Path(__file__).resolve().parent.parent / "data" / "eris.db")
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            _connections[name] = conn
            _cursor[name] = cur
            _db_type[name] = "sqlite"
            return f"Conectado a SQLite: {db_path} (conexión '{name}')"
        except Exception as e:
            return f"Error conectando a SQLite: {e}"


def _ensure_connected(name: str) -> str | None:
    if name not in _connections:
        return f"No hay conexión activa '{name}'. Usá connect primero."
    return None


def _query(params: dict, name: str) -> str:
    err = _ensure_connected(name)
    if err:
        return err

    sql = str(params.get("sql", "")).strip()
    if not sql:
        return "Falta el parámetro 'sql' con la consulta SELECT."

    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return "Para consultas SELECT usá 'query'. Para INSERT/UPDATE/DELETE usá 'execute'."

    try:
        cur = _cursor[name]
        dbt = _get_type(name)
        if dbt == "postgresql":
            cur.execute(sql)
            rows = cur.fetchall()
        else:
            cur.execute(sql)
            rows = cur.fetchall()

        if not rows:
            return "Consulta ejecutada. Sin resultados."

        if dbt == "postgresql":
            columns = [desc[0] for desc in cur.description]
            row_dicts = [dict(zip(columns, row)) for row in rows]
        else:
            columns = rows[0].keys() if rows else []
            row_dicts = [dict(zip(columns, row)) for row in rows]

        max_rows = int(params.get("limit", 50))
        truncated = len(row_dicts) > max_rows
        display = row_dicts[:max_rows]

        header = " | ".join(str(c) for c in columns)
        sep = "-" * len(header)
        lines = [header, sep]
        for r in display:
            lines.append(" | ".join(str(r.get(c, "")) for c in columns))

        result = f"Filas: {len(row_dicts)}{'(mostrando ' + str(len(display)) + ')' if truncated else ''}\n\n"
        result += "\n".join(lines)
        return result

    except Exception as e:
        return f"Error en consulta: {e}"


def _execute(params: dict, name: str) -> str:
    err = _ensure_connected(name)
    if err:
        return err

    sql = str(params.get("sql", "")).strip()
    if not sql:
        return "Falta el parámetro 'sql' con la sentencia SQL."

    sql_upper = sql.strip().upper()
    if sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
        return "Para SELECT usá 'query'. 'execute' es para INSERT/UPDATE/DELETE/DDL."

    try:
        cur = _cursor[name]
        cur.execute(sql)
        conn = _connections[name]
        dbt = _get_type(name)
        if dbt == "sqlite":
            affected = cur.rowcount
            conn.commit()
        else:
            conn.commit()
            affected = cur.rowcount

        if affected >= 0:
            return f"Sentencia ejecutada. Filas afectadas: {affected}"
        return "Sentencia ejecutada correctamente."

    except Exception as e:
        try:
            _connections[name].rollback()
        except Exception:
            pass
        return f"Error ejecutando sentencia: {e}"


def _tables(name: str) -> str:
    err = _ensure_connected(name)
    if err:
        return err

    try:
        dbt = _get_type(name)
        cur = _cursor[name]
        if dbt == "postgresql":
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            rows = cur.fetchall()
            tables = [row[0] if isinstance(row, tuple) else row.get("table_name", str(row)) for row in rows]
        else:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            rows = cur.fetchall()
            tables = [row[0] for row in rows]

        if not tables:
            return "No hay tablas en la base de datos."

        lines = [f"Tablas ({len(tables)}):"]
        for t in tables:
            lines.append(f"  - {t}")
        return "\n".join(lines)

    except Exception as e:
        return f"Error listando tablas: {e}"


def _schema(params: dict, name: str) -> str:
    err = _ensure_connected(name)
    if err:
        return err

    table = str(params.get("table", "")).strip()
    if not table:
        return "Falta el parámetro 'table' con el nombre de la tabla."

    try:
        dbt = _get_type(name)
        cur = _cursor[name]
        if dbt == "postgresql":
            cur.execute(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                (table,)
            )
            rows = cur.fetchall()
            if not rows:
                return f"La tabla '{table}' no existe."
            lines = [f"Schema de '{table}':"]
            for row in rows:
                col_name = row[0] if isinstance(row, tuple) else row.get("column_name")
                col_type = row[1] if isinstance(row, tuple) else row.get("data_type")
                nullable = row[2] if isinstance(row, tuple) else row.get("is_nullable")
                default = row[3] if isinstance(row, tuple) else row.get("column_default")
                lines.append(f"  {col_name}: {col_type} {'NULL' if nullable == 'YES' else 'NOT NULL'}{f' DEFAULT {default}' if default else ''}")
            return "\n".join(lines)
        else:
            cur.execute(f"PRAGMA table_info([{table}])")
            rows = cur.fetchall()
            if not rows:
                return f"La tabla '{table}' no existe."
            lines = [f"Schema de '{table}':"]
            for row in rows:
                cid, name_col, col_type, notnull, default_val, pk = row
                pk_str = " [PK]" if pk else ""
                nn_str = " NOT NULL" if notnull else ""
                def_str = f" DEFAULT {default_val}" if default_val else ""
                lines.append(f"  {name_col}: {col_type}{nn_str}{def_str}{pk_str}")
            return "\n".join(lines)

    except Exception as e:
        return f"Error obteniendo schema: {e}"


def _export(params: dict, name: str) -> str:
    err = _ensure_connected(name)
    if err:
        return err

    sql = str(params.get("sql", "")).strip()
    fmt = str(params.get("format", "json")).strip().lower()
    output = str(params.get("output", "")).strip()

    if not sql:
        return "Falta el parámetro 'sql' con la consulta a exportar."

    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return "Solo se pueden exportar consultas SELECT."

    try:
        cur = _cursor[name]
        dbt = _get_type(name)
        cur.execute(sql)
        rows = cur.fetchall()

        if not rows:
            return "Sin resultados para exportar."

        if dbt == "postgresql":
            columns = [desc[0] for desc in cur.description]
            row_dicts = [dict(zip(columns, row)) for row in rows]
        else:
            columns = rows[0].keys() if rows else []
            row_dicts = [dict(zip(columns, row)) for row in rows]

        data_dir = Path(__file__).resolve().parent.parent / "data" / "exports"
        data_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if fmt == "csv":
            if not output:
                output = str(data_dir / f"export_{timestamp}.csv")
            with open(output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows(row_dicts)
            return f"Exportado {len(row_dicts)} filas a CSV: {output}"

        else:
            if not output:
                output = str(data_dir / f"export_{timestamp}.json")
            with open(output, "w", encoding="utf-8") as f:
                json.dump(row_dicts, f, indent=2, ensure_ascii=False, default=str)
            return f"Exportado {len(row_dicts)} filas a JSON: {output}"

    except Exception as e:
        return f"Error exportando: {e}"


def _disconnect(name: str) -> str:
    if name not in _connections:
        return f"No hay conexión activa '{name}'."

    try:
        if name in _cursor:
            _cursor[name].close()
            del _cursor[name]
        _connections[name].close()
        del _connections[name]
        dbt = _db_type.pop(name, "sqlite")
        return f"Conexión '{name}' ({dbt}) cerrada."
    except Exception as e:
        _connections.pop(name, None)
        _cursor.pop(name, None)
        _db_type.pop(name, None)
        return f"Error cerrando conexión (forzado): {e}"


def _status(name: str) -> str:
    active = list(_connections.keys())
    if not active:
        return "No hay conexiones activas."
    lines = [f"Conexiones activas ({len(active)}):"]
    for n in active:
        dbt = _db_type.get(n, "?")
        lines.append(f"  - '{n}' ({dbt})")
    lines.append(f"\npsycopg2 disponible: {'sí' if HAS_PSYCOPG2 else 'no'}")
    return "\n".join(lines)
