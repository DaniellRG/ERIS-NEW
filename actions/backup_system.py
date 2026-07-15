"""Sistema de backup - guarda DB, Obsidian, config en ZIP."""
import zipfile, os, time
from pathlib import Path

def _backup_folder(zipf, folder: Path, arcname: str):
    if not folder.exists(): return
    for root, dirs, files in os.walk(folder):
        for f in files:
            fp = Path(root) / f
            rel = str(fp.relative_to(folder))
            zipf.write(fp, f"{arcname}/{rel}")

def backup_system(parameters: dict = None, player=None) -> str:
    """Crea backup completo en ZIP."""
    action = (parameters or {}).get("action", "create")
    
    if action == "create":
        home = Path.home()
        backup_dir = home / "Documents" / "ERIS_Data" / "Backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        ts = time.strftime("%Y%m%d_%H%M%S")
        zip_path = backup_dir / f"ERIS_backup_{ts}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            # DB
            db_path = home / "Documents" / "ERIS_Data" / "eris_brain.db"
            if db_path.exists():
                z.write(db_path, "DB/eris_brain.db")
            
            # Obsidian vault
            vault = Path(r"D:\Eris_NEW\BaseDatosObsidian\BaseObsiEris")
            if vault.exists():
                _backup_folder(z, vault, "Obsidian")
            
            # Config
            config = Path(r"D:\Eris_NEW\config")
            if config.exists():
                _backup_folder(z, config, "Config")
            
            # Memory
            memory = Path(r"D:\Eris_Source\memory")
            if memory.exists():
                _backup_folder(z, memory, "Memory")
        
        size_mb = zip_path.stat().st_size / 1024 / 1024
        return f"Backup creado: {zip_path.name} ({size_mb:.1f}MB)"
    
    elif action == "list":
        backup_dir = Path.home() / "Documents" / "ERIS_Data" / "Backups"
        if not backup_dir.exists():
            return "No hay backups."
        files = sorted(backup_dir.glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return "No hay backups."
        lines = [f"Backups ({len(files)}):"]
        for f in files[:10]:
            size = f.stat().st_size / 1024 / 1024
            ts = time.strftime("%d/%m %H:%M", time.localtime(f.stat().st_mtime))
            lines.append(f"  {f.name} ({size:.1f}MB) - {ts}")
        return "\n".join(lines)
    
    return "Acciones: create, list"
