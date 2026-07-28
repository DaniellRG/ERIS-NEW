"""
core/resilient.py — Task persistence & auto-recovery system.
Ensures ERIS always finishes her work, even through disconnections and errors.
- Pending tools are saved to disk before execution
- Results are persisted if send fails
- On reconnect, pending/failed tasks are resumed
- Voice pipeline auto-restarts on failure
"""
import json
import time
import threading
import traceback
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PENDING_FILE = DATA_DIR / "pending_tasks.json"
_COMPLETED_FILE = DATA_DIR / "completed_tasks.json"
_RETRY_FILE = DATA_DIR / "retry_queue.json"

_lock = threading.Lock()
MAX_RETRY = 3
MAX_COMPLETED_LOG = 200
TASK_TTL = 3600  # 1 hour max age for pending tasks


class TaskManager:
    """Manages persistent task queue — survives crashes and disconnections."""

    def __init__(self):
        self._ensure_dir()

    def _ensure_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Pending tasks (in-flight, waiting for delivery) ──

    def register_task(self, task_id: str, name: str, args: dict, context: str = ""):
        """Register a tool call BEFORE execution so it survives crashes."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            pending[task_id] = {
                "id": task_id,
                "tool": name,
                "args": args,
                "context": context,
                "status": "pending",
                "created": datetime.now().isoformat(),
                "retries": 0,
            }
            self._save(_PENDING_FILE, pending)
            print(f"[RESILIENT] 📝 Task registered: {name} ({task_id})")

    def task_started(self, task_id: str):
        """Mark task as actively executing."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            if task_id in pending:
                pending[task_id]["status"] = "running"
                pending[task_id]["started"] = datetime.now().isoformat()
                self._save(_PENDING_FILE, pending)

    def task_completed(self, task_id: str, result: str):
        """Task finished successfully — remove from pending, log to completed."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            task = pending.pop(task_id, None)
            self._save(_PENDING_FILE, pending)

            if task:
                completed = self._load(_COMPLETED_FILE)
                completed[task_id] = {
                    "id": task_id,
                    "tool": task.get("tool", "?"),
                    "result_preview": str(result)[:200],
                    "completed": datetime.now().isoformat(),
                    "retries": task.get("retries", 0),
                }
                # Cap completed log
                if len(completed) > MAX_COMPLETED_LOG:
                    oldest = sorted(completed, key=lambda k: completed[k].get("completed", ""))[:50]
                    for k in oldest:
                        del completed[k]
                self._save(_COMPLETED_FILE, completed)
                print(f"[RESILIENT] ✅ Task completed: {task.get('tool', '?')} ({task_id})")

    def task_failed(self, task_id: str, error: str):
        """Task failed — move to retry queue if retries remaining."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            task = pending.pop(task_id, None)
            self._save(_PENDING_FILE, pending)

            if task:
                retries = task.get("retries", 0)
                if retries < MAX_RETRY:
                    retry_q = self._load(_RETRY_FILE)
                    task["retries"] = retries + 1
                    task["last_error"] = str(error)[:200]
                    task["status"] = "retry"
                    task["failed_at"] = datetime.now().isoformat()
                    retry_q[task_id] = task
                    self._save(_RETRY_FILE, retry_q)
                    print(f"[RESILIENT] 🔄 Task queued for retry ({retries+1}/{MAX_RETRY}): {task.get('tool', '?')} ({task_id})")
                else:
                    print(f"[RESILIENT] ❌ Task permanently failed after {MAX_RETRY} retries: {task.get('tool', '?')} ({task_id})")
                    # Log to completed as failed
                    completed = self._load(_COMPLETED_FILE)
                    completed[task_id] = {
                        "id": task_id,
                        "tool": task.get("tool", "?"),
                        "result_preview": f"FAILED: {str(error)[:200]}",
                        "completed": datetime.now().isoformat(),
                        "retries": retries,
                        "permanent_failure": True,
                    }
                    self._save(_COMPLETED_FILE, completed)

    def save_result_for_delivery(self, task_id: str, result: str):
        """Save a result that couldn't be delivered (send_tool_response failed)."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            if task_id in pending:
                pending[task_id]["status"] = "awaiting_delivery"
                pending[task_id]["result"] = str(result)[:5000]
                pending[task_id]["delivered_at"] = datetime.now().isoformat()
                self._save(_PENDING_FILE, pending)
                print(f"[RESILIENT] 💾 Result saved for later delivery: {task_id}")

    # ── Recovery ──

    def get_pending_tasks(self) -> list:
        """Get all tasks awaiting delivery or retry."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            retry_q = self._load(_RETRY_FILE)
            tasks = []
            now = time.time()
            # Pending tasks with saved results (need delivery)
            for tid, t in pending.items():
                if t.get("status") == "awaiting_delivery" and t.get("result"):
                    created = t.get("created", "")
                    try:
                        ts = datetime.fromisoformat(created).timestamp()
                        if now - ts < TASK_TTL:
                            tasks.append(t)
                    except Exception:
                        tasks.append(t)
            # Retry queue
            for tid, t in retry_q.items():
                created = t.get("created", "")
                try:
                    ts = datetime.fromisoformat(created).timestamp()
                    if now - ts < TASK_TTL:
                        tasks.append(t)
                except Exception:
                    tasks.append(t)
            return tasks

    def get_tasks_needing_retry(self) -> list:
        """Get tasks that failed and need re-execution."""
        with _lock:
            retry_q = self._load(_RETRY_FILE)
            tasks = list(retry_q.values())
            self._save(_RETRY_FILE, {})  # Clear retry queue (we're processing them)
            return tasks

    def cleanup_stale(self):
        """Remove tasks older than TTL."""
        with _lock:
            now = time.time()
            for fp in [_PENDING_FILE, _RETRY_FILE]:
                data = self._load(fp)
                stale = []
                for tid, t in data.items():
                    created = t.get("created", "")
                    try:
                        ts = datetime.fromisoformat(created).timestamp()
                        if now - ts > TASK_TTL:
                            stale.append(tid)
                    except Exception:
                        pass
                for tid in stale:
                    del data[tid]
                if stale:
                    self._save(fp, data)
                    print(f"[RESILIENT] 🧹 Cleaned {len(stale)} stale tasks from {fp.name}")

    def get_stats(self) -> dict:
        """Get task queue stats."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            retry_q = self._load(_RETRY_FILE)
            completed = self._load(_COMPLETED_FILE)
            return {
                "pending": len(pending),
                "awaiting_delivery": sum(1 for t in pending.values() if t.get("status") == "awaiting_delivery"),
                "retry": len(retry_q),
                "completed_today": sum(
                    1 for t in completed.values()
                    if t.get("completed", "").startswith(datetime.now().strftime("%Y-%m-%d"))
                ),
                "total_completed": len(completed),
            }

    def get_delivery_tasks(self) -> list:
        """Get tasks whose results need to be sent back to Gemini."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            tasks = []
            for tid, t in list(pending.items()):
                if t.get("status") == "awaiting_delivery" and t.get("result"):
                    tasks.append(t)
            return tasks

    def clear_delivered(self, task_id: str):
        """Clear a task after successful delivery."""
        with _lock:
            pending = self._load(_PENDING_FILE)
            task = pending.pop(task_id, None)
            self._save(_PENDING_FILE, pending)
            if task:
                completed = self._load(_COMPLETED_FILE)
                completed[task_id] = {
                    "id": task_id,
                    "tool": task.get("tool", "?"),
                    "result_preview": str(task.get("result", ""))[:200],
                    "completed": datetime.now().isoformat(),
                    "retries": task.get("retries", 0),
                    "delivered": True,
                }
                self._save(_COMPLETED_FILE, completed)

    # ── Helpers ──

    def _load(self, fp: Path) -> dict:
        if fp.exists():
            try:
                return json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self, fp: Path, data: dict):
        try:
            fp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception as e:
            print(f"[RESILIENT] Error saving {fp.name}: {e}")


# ── Global instance ──
_manager = None

def get_manager() -> TaskManager:
    global _manager
    if _manager is None:
        _manager = TaskManager()
    return _manager


# ── Voice pipeline auto-recovery ──
class VoiceRecovery:
    """Auto-restarts the voice pipeline if it crashes."""

    def __init__(self):
        self._pipeline = None
        self._max_restarts = 5
        self._restart_count = 0
        self._last_restart = 0
        self._lock = threading.Lock()

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def check_and_restart(self):
        """Check if voice pipeline is alive, restart if not."""
        if not self._pipeline:
            return False

        with self._lock:
            # Reset counter if enough time passed since last restart
            now = time.time()
            if now - self._last_restart > 300:
                self._restart_count = 0

            if self._restart_count >= self._max_restarts:
                print("[RESILIENT] ⚠️ Voice pipeline restart limit reached")
                return False

            try:
                is_running = getattr(self._pipeline, '_running', False)
                if not is_running:
                    print("[RESILIENT] 🔄 Restarting voice pipeline...")
                    self._pipeline.start()
                    self._restart_count += 1
                    self._last_restart = time.time()
                    print(f"[RESILIENT] ✅ Voice pipeline restarted ({self._restart_count}/{self._max_restarts})")
                    return True
            except Exception as e:
                print(f"[RESILIENT] ❌ Voice restart failed: {e}")
                self._restart_count += 1
                return False
        return True


def get_voice_recovery() -> VoiceRecovery:
    return VoiceRecovery()


# ── Task ID generator ──
def generate_task_id(name: str, args: dict) -> str:
    """Generate a unique task ID from tool name and args."""
    import hashlib
    raw = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
    return f"{name}_{hashlib.md5(raw.encode()).hexdigest()[:12]}_{int(time.time())}"
