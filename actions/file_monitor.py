"""Monitor de archivos - detecta cambios en tiempo real."""
import os, time, json
from pathlib import Path
from collections import defaultdict

_STATE_FILE = Path(__file__).resolve().parent.parent / "memory" / "file_snapshot.json"

def file_monitor(parameters: dict, player=None) -> str:
    """Monitorea archivos: cambios recientes, snapshot, comparacion."""
    action = parameters.get("action", "recent")
    folder = parameters.get("folder", "")
    limit = int(parameters.get("limit", 20))
    
    target = Path(folder) if folder else Path.home()
    if not target.exists():
        return f"Carpeta no encontrada: {folder}"
    
    if action == "recent":
        # Find recently modified files
        files = []
        try:
            for root, dirs, filenames in os.walk(str(target)):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'AppData', 'Windows', '$Recycle.Bin')]
                for name in filenames[:50]:
                    fp = Path(root) / name
                    try:
                        st = fp.stat()
                        files.append({"path": str(fp), "size": st.st_size, "modified": st.st_mtime})
                    except OSError: pass
                if len(files) > 200: break
        except OSError: pass
        
        files.sort(key=lambda x: x["modified"], reverse=True)
        lines = [f"Archivos recientes en {target}:"]
        for f in files[:limit]:
            ts = time.strftime("%d/%m %H:%M", time.localtime(f["modified"]))
            size_kb = f["size"] / 1024
            lines.append(f"  {ts} | {size_kb:.0f}KB | {f['path']}")
        return "\n".join(lines) if len(lines) > 1 else "No se encontraron archivos recientes."
    
    elif action == "snapshot":
        # Take snapshot of current files
        files = {}
        try:
            for root, dirs, filenames in os.walk(str(target)):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules','__pycache__','AppData','Windows')]
                for name in filenames[:30]:
                    fp = Path(root) / name
                    try:
                        files[str(fp)] = fp.stat().st_mtime
                    except OSError: pass
                if len(files) > 500: break
        except OSError: pass
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps({"folder": str(target), "files": files, "time": time.time()}, indent=2))
        return f"Snapshot guardado: {len(files)} archivos en {target}"
    
    elif action == "changes":
        # Compare with last snapshot
        if not _STATE_FILE.exists():
            return "No hay snapshot. Usa action='snapshot' primero."
        try:
            prev = json.loads(_STATE_FILE.read_text())
            prev_files = prev.get("files", {})
            prev_time = prev.get("time", 0)
        except (json.JSONDecodeError, OSError):
            return "Error leyendo snapshot."
        
        new = []
        deleted = []
        modified = []
        try:
            for root, dirs, filenames in os.walk(str(target)):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules','__pycache__','AppData','Windows')]
                for name in filenames[:30]:
                    fp = str(Path(root) / name)
                    if fp not in prev_files:
                        new.append(fp)
                    elif os.path.getmtime(fp) > prev_files[fp] + 1:
                        modified.append(fp)
                if len(new) + len(modified) > 500: break
        except OSError: pass
        
        for fp in prev_files:
            if not os.path.exists(fp):
                deleted.append(fp)
        
        lines = [f"Cambios desde {time.strftime('%d/%m %H:%M', time.localtime(prev_time))}:"]
        if new:
            lines.append(f"\nNUEVOS ({len(new)}):")
            for f in new[:10]: lines.append(f"  + {f}")
        if modified:
            lines.append(f"\nMODIFICADOS ({len(modified)}):")
            for f in modified[:10]: lines.append(f"  * {f}")
        if deleted:
            lines.append(f"\nELIMINADOS ({len(deleted)}):")
            for f in deleted[:10]: lines.append(f"  - {f}")
        if not new and not modified and not deleted:
            lines.append("  Sin cambios detectados.")
        return "\n".join(lines)
    
    elif action == "search":
        query = parameters.get("query", "")
        if not query: return "Especifica 'query' para buscar."
        results = []
        try:
            for root, dirs, filenames in os.walk(str(target)):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules','__pycache__','AppData','Windows')]
                for name in filenames:
                    if query.lower() in name.lower():
                        results.append(str(Path(root) / name))
                if len(results) > 100: break
        except OSError: pass
        if not results:
            return f"No se encontro '{query}' en {target}"
        return f"Resultados para '{query}' ({len(results)}):\n" + "\n".join(results[:20])
    
    return f"Accion '{action}' no reconocida. Usa: recent, snapshot, changes, search"
