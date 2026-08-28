"""ERIS Watchdog — auto-restarts Eris on crash."""
import subprocess, time, os, signal
from pathlib import Path
from datetime import datetime

WORKDIR = Path(r"D:\Eris_Source")
PYTHON = WORKDIR / ".venv" / "Scripts" / "python.exe"
SCRIPT = WORKDIR / "run.py"
LOG = WORKDIR / "data" / "watchdog.log"
CREATE_NO_WINDOW = 0x08000000
MAX_RESTARTS = 10
RESTART_WINDOW = 3600  # 1 hour

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    log("Watchdog started")
    restart_times = []
    running = True
    
    def shutdown(sig, frame):
        nonlocal running
        log("Watchdog shutting down")
        running = False
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    while running:
        # Clean old restart times
        now = time.time()
        restart_times = [t for t in restart_times if now - t < RESTART_WINDOW]
        
        if len(restart_times) >= MAX_RESTARTS:
            log(f"CRITICAL: {MAX_RESTARTS} restarts in 1 hour. Stopping watchdog.")
            break
        
        log(f"Starting Eris... (restart #{len(restart_times) + 1})")
        try:
            proc = subprocess.Popen(
                [str(PYTHON), str(SCRIPT)],
                cwd=str(WORKDIR),
                creationflags=CREATE_NO_WINDOW,
            )
            proc.wait()
            exit_code = proc.returncode
            log(f"Eris exited with code {exit_code}")
        except Exception as e:
            log(f"Error launching Eris: {e}")
            exit_code = -1
        
        if not running:
            break
        
        restart_times.append(time.time())
        log(f"Restarting in 5s...")
        time.sleep(5)
    
    log("Watchdog stopped")

if __name__ == "__main__":
    main()
