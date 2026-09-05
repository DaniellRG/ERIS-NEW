import sqlite3
import json
import time
import os
import functools
import threading
from pathlib import Path
from datetime import datetime

DB_DIR = Path(os.environ.get("ERIS_DATA", Path.home() / "Documents" / "ERIS_Data"))
DB_PATH = DB_DIR / "eris_brain.db"

# ── Conexion compartida + lock: evita abrir/cerrar SQLite por cada query ──
_DB_LOCK = threading.RLock()          # RLock permite decoradores anidados
_DB_CONN: "sqlite3.Connection | None" = None


class _DBConnection:
    """Proxy sobre la conexion singleton que ignora close() para que el codigo
    existente (`conn.close()` tras cada operacion) siga funcionando intacto."""

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        return None

    def commit(self):
        return self._conn.commit()


def _connect():
    global _DB_CONN
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if _DB_CONN is None:
        _DB_CONN = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _DB_CONN.execute("PRAGMA journal_mode=WAL")
        _DB_CONN.execute("PRAGMA busy_timeout=5000")
        _DB_CONN.execute("PRAGMA synchronous=NORMAL")
        _DB_CONN.execute("PRAGMA foreign_keys=ON")
    return _DBConnection(_DB_CONN)


def _db(func):
    """Serializa cada funcion de DB con el lock compartido (thread-safe)."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _DB_LOCK:
            return func(*args, **kwargs)
    return wrapper

@_db
def _init_db():
    conn = _connect()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            category TEXT DEFAULT 'general',
            importance REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            access_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system','tool')),
            content TEXT NOT NULL,
            tool_name TEXT,
            tool_result TEXT,
            tokens INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS tool_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            parameters TEXT,
            result_status TEXT CHECK(result_status IN ('success','error','timeout')),
            result_summary TEXT,
            duration_ms REAL,
            session_id TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            fact TEXT NOT NULL,
            source TEXT,
            confidence REAL DEFAULT 0.5,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            verified BOOLEAN DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','in_progress','done','cancelled')),
            priority TEXT DEFAULT 'medium' CHECK(priority IN ('low','medium','high','critical')),
            due_date TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT,
            error_type TEXT,
            message TEXT,
            traceback TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key);
        CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);
        CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
        CREATE INDEX IF NOT EXISTS idx_tool_log_name ON tool_log(tool_name);
        CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp);
    """)
    conn.commit()
    conn.close()

_init_db()

# ── FTS5: busquedas de texto sin FULL TABLE SCAN ──────────────────────────
@_db
def _ensure_fts():
    """Crea tablas FTS5 con triggers para indexar texto (buscar en vez de LIKE)."""
    conn = _connect()
    conn.rollback()  # descarta transacciones pendientes antes de DDL de triggers
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
            content, content='conversations', content_rowid='id');
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            fact, topic, content='knowledge', content_rowid='id');
        CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
            event, content='episodic', content_rowid='id');

        DROP TRIGGER IF EXISTS conversations_ai;
        CREATE TRIGGER conversations_ai AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(rowid, content) VALUES (new.id, new.content);
        END;
        DROP TRIGGER IF EXISTS conversations_ad;
        CREATE TRIGGER conversations_ad AFTER DELETE ON conversations BEGIN
            INSERT INTO conversations_fts(conversations_fts, rowid, content) VALUES ('delete', old.id, old.content);
        END;
        DROP TRIGGER IF EXISTS conversations_au;
        CREATE TRIGGER conversations_au AFTER UPDATE ON conversations BEGIN
            INSERT INTO conversations_fts(conversations_fts, rowid, content) VALUES ('delete', old.id, old.content);
            INSERT INTO conversations_fts(rowid, content) VALUES (new.id, new.content);
        END;

        DROP TRIGGER IF EXISTS knowledge_ai;
        CREATE TRIGGER knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, fact, topic) VALUES (new.id, new.fact, new.topic);
        END;
        DROP TRIGGER IF EXISTS knowledge_ad;
        CREATE TRIGGER knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, fact, topic) VALUES ('delete', old.id, old.fact, old.topic);
        END;
        DROP TRIGGER IF EXISTS knowledge_au;
        CREATE TRIGGER knowledge_au AFTER UPDATE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, fact, topic) VALUES ('delete', old.id, old.fact, old.topic);
            INSERT INTO knowledge_fts(rowid, fact, topic) VALUES (new.id, new.fact, new.topic);
        END;

        DROP TRIGGER IF EXISTS episodic_ai;
        CREATE TRIGGER episodic_ai AFTER INSERT ON episodic BEGIN
            INSERT INTO episodic_fts(rowid, event) VALUES (new.id, new.event);
        END;
        DROP TRIGGER IF EXISTS episodic_ad;
        CREATE TRIGGER episodic_ad AFTER DELETE ON episodic BEGIN
            INSERT INTO episodic_fts(episodic_fts, rowid, event) VALUES ('delete', old.id, old.event);
        END;
        DROP TRIGGER IF EXISTS episodic_au;
        CREATE TRIGGER episodic_au AFTER UPDATE ON episodic BEGIN
            INSERT INTO episodic_fts(episodic_fts, rowid, event) VALUES ('delete', old.id, old.event);
            INSERT INTO episodic_fts(rowid, event) VALUES (new.id, new.event);
        END;

        INSERT INTO conversations_fts(conversations_fts) VALUES ('rebuild');
        INSERT INTO knowledge_fts(knowledge_fts) VALUES ('rebuild');
        INSERT INTO episodic_fts(episodic_fts) VALUES ('rebuild');
    """)
    conn.commit()


def _fts_query(query: str) -> str:
    """Convierte una query libre a una MATCH-syntax segura (cada token como frase)."""
    tokens = [t for t in str(query).replace('"', " ").split() if t]
    if not tokens:
        return ""
    return " AND ".join(f'"{t}"' for t in tokens)


def _fts_search(conn, fts_table, order_col, like_col, select_sql, query, limit, *params):
    """Busca con FTS5; si la synthaxis de MATCH falla, cae a LIKE%%-scan."""
    q = _fts_query(query)
    if q:
        try:
            return conn.execute(
                select_sql + f" WHERE {fts_table} MATCH ? ORDER BY {order_col} DESC LIMIT ?",
                (q, limit, *params)
            ).fetchall()
        except sqlite3.OperationalError:
            pass
    return conn.execute(
        select_sql + f" WHERE {like_col} LIKE ? ORDER BY {order_col} DESC LIMIT ?",
        (f"%{query}%", limit, *params)
    ).fetchall()

# ─── MEMORY ───
@_db
def memory_set(key: str, value: str, category: str = "general", importance: float = 0.5):
    conn = _connect()
    conn.execute("""INSERT INTO memory (key, value, category, importance, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category,
        importance=excluded.importance, updated_at=datetime('now')""",
        (key, value, category, importance))
    conn.commit(); conn.close()

@_db
def memory_get(key: str) -> str | None:
    conn = _connect()
    row = conn.execute("UPDATE memory SET access_count=access_count+1 WHERE key=? RETURNING value", (key,)).fetchone()
    conn.commit(); conn.close()
    return row[0] if row else None

@_db
def memory_all(limit: int = 50) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT key, value, category, importance, access_count, updated_at FROM memory ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [{"key": r[0], "value": r[1], "category": r[2], "importance": r[3], "access_count": r[4], "updated_at": r[5]} for r in rows]

@_db
def memory_delete(key: str):
    conn = _connect(); conn.execute("DELETE FROM memory WHERE key=?", (key,)); conn.commit(); conn.close()

# ─── CONVERSATIONS ───
@_db
def convo_log(session_id: str, role: str, content: str, tool_name: str = None, tool_result: str = None, tokens: int = 0):
    conn = _connect()
    conn.execute("INSERT INTO conversations (session_id, role, content, tool_name, tool_result, tokens) VALUES (?,?,?,?,?,?)",
        (session_id, role, content, tool_name, tool_result, tokens))
    conn.commit(); conn.close()

@_db
def convo_search(query: str, limit: int = 10) -> list[dict]:
    """Buscar en el historial de conversaciones (FTS5, fallback LIKE)."""
    conn = _connect()
    select_sql = ("SELECT c.role, c.content, c.timestamp FROM conversations_fts "
                  "JOIN conversations c ON c.id = conversations_fts.rowid")
    rows = _fts_search(conn, "conversations_fts",
                       "c.id", "c.content",
                       select_sql, query, limit)
    conn.close()
    return [{"role": r[0], "content": r[1][:300], "time": r[2]} for r in rows]

@_db
def convo_recent(limit: int = 10) -> list[dict]:
    """Ultimas conversaciones."""
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1][:200], "time": r[2]} for r in rows]

# ─── TOOL LOG ───
@_db
def tool_log(tool_name: str, parameters: dict = None, success: bool = True, summary: str = "", duration_ms: float = 0, session_id: str = None):
    conn = _connect()
    conn.execute("INSERT INTO tool_log (tool_name, parameters, result_status, result_summary, duration_ms, session_id) VALUES (?,?,?,?,?,?)",
        (tool_name, json.dumps(parameters) if parameters else None, 'success' if success else 'error', summary, duration_ms, session_id))
    conn.commit(); conn.close()

@_db
def tool_stats(limit: int = 20) -> list[dict]:
    conn = _connect()
    rows = conn.execute("""SELECT tool_name, COUNT(*) as total, SUM(CASE WHEN result_status='success' THEN 1 ELSE 0 END) as ok,
        AVG(duration_ms) as avg_ms, MAX(timestamp) as last_used FROM tool_log GROUP BY tool_name ORDER BY total DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [{"tool": r[0], "total": r[1], "success": r[2], "avg_ms": round(r[3] or 0, 1), "last": r[4]} for r in rows]

# ─── KNOWLEDGE ───
@_db
def know_add(topic: str, fact: str, source: str = "eris", confidence: float = 0.5, tags: str = None):
    conn = _connect()
    conn.execute("INSERT INTO knowledge (topic, fact, source, confidence, tags) VALUES (?,?,?,?,?)", (topic, fact, source, confidence, tags))
    conn.commit(); conn.close()

@_db
def know_search(query: str, limit: int = 10) -> list[dict]:
    conn = _connect()
    select_sql = ("SELECT k.topic, k.fact, k.source, k.confidence FROM knowledge_fts "
                  "JOIN knowledge k ON k.id = knowledge_fts.rowid")
    rows = _fts_search(conn, "knowledge_fts",
                       "k.confidence", "k.fact",
                       select_sql, query, limit)
    conn.close()
    return [{"topic": r[0], "fact": r[1], "source": r[2], "confidence": r[3]} for r in rows]

@_db
def know_by_topic(topic: str, limit: int = 20) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT fact, source, confidence FROM knowledge WHERE topic=? ORDER BY confidence DESC LIMIT ?", (topic, limit)).fetchall()
    conn.close()
    return [{"fact": r[0], "source": r[1], "confidence": r[2]} for r in rows]

# ─── TASKS ───
@_db
def task_add(title: str, description: str = "", priority: str = "medium", due_date: str = None):
    conn = _connect()
    conn.execute("INSERT INTO tasks (title, description, priority, due_date) VALUES (?,?,?,?)", (title, description, priority, due_date))
    conn.commit(); conn.close()

@_db
def task_list(status: str = None, limit: int = 20) -> list[dict]:
    conn = _connect()
    sql = "SELECT id, title, status, priority, due_date, created_at FROM tasks"
    params = []
    if status: sql += " WHERE status=?"; params.append(status)
    sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "status": r[2], "priority": r[3], "due": r[4], "created": r[5]} for r in rows]

@_db
def task_update(task_id: int, status: str = None, priority: str = None):
    conn = _connect()
    if status: conn.execute("UPDATE tasks SET status=?, completed_at=CASE WHEN ?='done' THEN datetime('now') ELSE completed_at END WHERE id=?", (status, status, task_id))
    if priority: conn.execute("UPDATE tasks SET priority=? WHERE id=?", (priority, task_id))
    conn.commit(); conn.close()

@_db
def task_delete(task_id: int):
    conn = _connect(); conn.execute("DELETE FROM tasks WHERE id=?", (task_id,)); conn.commit(); conn.close()

# ─── USER PROFILE ───
@_db
def profile_set(key: str, value: str):
    conn = _connect()
    conn.execute("INSERT INTO user_profile (key, value, updated_at) VALUES (?,?,datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')", (key, value))
    conn.commit(); conn.close()

@_db
def profile_get(key: str) -> str | None:
    conn = _connect(); row = conn.execute("SELECT value FROM user_profile WHERE key=?", (key,)).fetchone(); conn.close()
    return row[0] if row else None

# ─── ERRORS ───
@_db
def error_log(module: str, error_type: str, message: str, traceback: str = ""):
    conn = _connect()
    conn.execute("INSERT INTO errors (module, error_type, message, traceback) VALUES (?,?,?,?)", (module, error_type, str(message)[:500], traceback[:2000]))
    conn.commit(); conn.close()

# ─── STATS ───
@_db
def db_stats() -> dict:
    conn = _connect()
    tables = ["memory", "conversations", "tool_log", "knowledge", "tasks", "errors", "episodic"]
    stats = {}
    for t in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        stats[t] = row[0]
    stats["db_path"] = str(DB_PATH)
    stats["db_size_mb"] = round(os.path.getsize(DB_PATH) / 1024 / 1024, 2) if DB_PATH.exists() else 0
    conn.close()
    return stats


# ─── SAVE EVERYWHERE ──────────────────────────────────────────────

def save_everywhere(parameters: dict = None, player=None) -> str:
    """
    Guarda informacion en TODOS los sistemas simultaneamente:
    - Base de datos SQLite (memory + knowledge)
    - Obsidian vault (nota interconectada)
    """
    params = parameters or {}
    topic = params.get("topic", params.get("key", ""))
    content = params.get("content", params.get("value", ""))
    category = params.get("category", "general")
    importance = float(params.get("importance", 0.7))
    tags = params.get("tags", "")
    
    if not topic or not content:
        return "Error: Necesito 'topic' y 'content' para guardar en todos lados."
    
    results = []
    
    # 1. SQLite memory
    try:
        memory_set(topic, content, category, importance)
        results.append("DB memory: OK")
    except Exception as e:
        results.append(f"DB memory: {e}")
    
    # 2. SQLite knowledge
    try:
        know_add(topic, content, "eris_learning", importance, tags)
        results.append("DB knowledge: OK")
    except Exception as e:
        results.append(f"DB knowledge: {e}")
    
    # 3. Obsidian note
    try:
        from actions.obsidian_brain import obsidian_note
        obsidian_note({
            "action": "write",
            "title": topic.replace("_", " ").title(),
            "content": f"# {topic}\n\n{content}\n\n*Guardado automaticamente por ERIS*",
            "tags": tags if tags else category,
            "folder": "Memoria" if category in ("identity", "preference") else "Conceptos"
        }, player)
        results.append("Obsidian: OK")
    except Exception as e:
        results.append(f"Obsidian: {e}")
    
    return f"Guardado en 3 sistemas: {' | '.join(results)}"


# ─── EPISODIC MEMORY ────────────────────────────────────────────

@_db
def _ensure_episodic():
    """Create episodic table if not exists."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            context TEXT,
            importance REAL DEFAULT 0.5,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic(timestamp)")
    conn.commit()
    conn.close()

_ensure_episodic()
_ensure_fts()

@_db
def episodic_add(event: str, category: str = "general", context: str = "", importance: float = 0.5) -> int:
    """Registra un evento en la memoria episodica."""
    conn = _connect()
    c = conn.execute(
        "INSERT INTO episodic (event, category, context, importance) VALUES (?,?,?,?) RETURNING id",
        (event, category, str(context) if context else "", importance)
    )
    eid = c.fetchone()[0]
    conn.commit(); conn.close()
    return eid

@_db
def episodic_recent(limit: int = 20) -> list[dict]:
    """Ultimos eventos registrados."""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, event, category, importance, timestamp FROM episodic ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "event": r[1][:150], "category": r[2], "importance": r[3], "time": r[4]} for r in rows]

@_db
def episodic_search(query: str, limit: int = 20) -> list[dict]:
    """Buscar en memoria episodica (FTS5, fallback LIKE)."""
    conn = _connect()
    select_sql = ("SELECT e.id, e.event, e.category, e.importance, e.timestamp FROM episodic_fts "
                  "JOIN episodic e ON e.id = episodic_fts.rowid")
    rows = _fts_search(conn, "episodic_fts",
                       "e.importance", "e.event",
                       select_sql, query, limit)
    conn.close()
    return [{"id": r[0], "event": r[1][:200], "category": r[2], "importance": r[3], "time": r[4]} for r in rows]

@_db
def episodic_count() -> int:
    conn = _connect()
    r = conn.execute("SELECT COUNT(*) FROM episodic").fetchone()
    conn.close()
    return r[0] if r else 0
