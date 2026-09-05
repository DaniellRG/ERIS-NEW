"""Game Launcher - encuentra juegos en todos los discos."""
import os, subprocess, json, time
from pathlib import Path

def _get_all_drives():
    """Get all available drive letters."""
    drives = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        if Path(f"{letter}:\\").exists():
            drives.append(f"{letter}:\\")
    return drives

def _find_exe_in_folder(folder: str, max_depth=3):
    """Find all executables in a folder (limited depth)."""
    results = []
    try:
        for root, dirs, files in os.walk(folder):
            depth = root.replace(folder, "").count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('Windows','$Recycle.Bin','System Volume Information','node_modules')]
            for f in files:
                if f.endswith('.exe') and 'unins' not in f.lower() and 'crash' not in f.lower() and 'vcredist' not in f.lower():
                    results.append(str(Path(root) / f))
    except OSError: pass
    return results

def game_launcher(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    game_name = (parameters.get("game") or parameters.get("name", "")).lower()
    
    if action == "scan_all":
        """Scan ALL drives for games."""
        if player: player.write_log("Escaneando todos los discos en busca de juegos...")
        games = []
        
        # Known game folders
        known_paths = [
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"D:\SteamLibrary\steamapps\common",
            r"E:\SteamLibrary\steamapps\common",
            r"C:\Program Files (x86)\Epic Games",
            r"C:\Program Files\Epic Games",
            r"C:\Program Files (x86)\GOG Galaxy\Games",
            r"C:\Program Files\GOG Galaxy\Games",
        ]
        
        # Also scan common game folders on all drives
        for drive in _get_all_drives():
            for folder in ["Games", "Juegos", "Jogos", "SteamLibrary", "GOG Games"]:
                p = Path(drive) / folder
                if p.exists():
                    known_paths.append(str(p))
        
        # Scan Program Files on all drives
        for drive in _get_all_drives():
            for pf in ["Program Files", "Program Files (x86)"]:
                p = Path(drive) / pf
                if p.exists():
                    for sub in p.iterdir():
                        if sub.is_dir() and sub.name not in ('Common Files','WindowsApps','Internet Explorer','Windows Defender','Microsoft','dotnet'):
                            if any(_find_exe_in_folder(str(sub), 1)):
                                games.append({"name": sub.name, "path": str(sub), "source": f"{pf}"})
        
        # Scan known paths
        for path in known_paths:
            p = Path(path)
            if not p.exists(): continue
            if player: player.write_log(f"  Escaneando: {p.name}...")
            for folder in p.iterdir():
                if folder.is_dir():
                    exes = _find_exe_in_folder(str(folder), 2)
                    if exes:
                        games.append({"name": folder.name, "path": exes[0], "source": str(p.parent.name) if p.parent else str(p.name)})
        
        # Deduplicate
        seen = set()
        unique = []
        for g in games:
            key = g["name"].lower()
            if key not in seen:
                seen.add(key)
                unique.append(g)
        
        if not unique:
            return "No se encontraron juegos."
        
        lines = [f"Juegos encontrados ({len(unique)}):"]
        for g in sorted(unique, key=lambda x: x["name"].lower())[:50]:
            lines.append(f"  - {g['name']} [{g['source']}] -> {g['path']}")
        return "\n".join(lines)
    
    elif action == "list":
        # Quick scan
        games = []
        known_paths = [
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"C:\Program Files\Steam\steamapps\common",
        ]
        for drive in _get_all_drives():
            for lib in ["SteamLibrary", "Games", "Juegos"]:
                p = Path(drive) / lib
                if p.exists():
                    for sub in p.iterdir():
                        if sub.is_dir():
                            exes = _find_exe_in_folder(str(sub), 1)
                            if exes:
                                games.append({"name": sub.name, "path": exes[0], "source": "Disco"})
        
        for path in known_paths:
            p = Path(path)
            if p.exists():
                for folder in p.iterdir():
                    if folder.is_dir():
                        exes = _find_exe_in_folder(str(folder), 1)
                        if exes:
                            games.append({"name": folder.name, "path": exes[0], "source": "Steam"})
        
        seen = set()
        unique = []
        for g in games:
            k = g["name"].lower()
            if k not in seen:
                seen.add(k)
                unique.append(g)
        
        if not unique:
            return "No se encontraron juegos. Usa 'scan_all' para escaneo profundo."
        
        lines = [f"Juegos ({len(unique)}):"]
        for g in sorted(unique, key=lambda x: x["name"].lower())[:30]:
            lines.append(f"  - {g['name']} [{g['source']}]")
        return "\n".join(lines)
    
    elif action == "launch":
        if not game_name:
            return "Dime que juego ejecutar (game)."
        
        # Search everywhere
        search_paths = []
        for drive in _get_all_drives():
            for folder in ["Games", "Juegos", "SteamLibrary", "Program Files", "Program Files (x86)"]:
                search_paths.append(str(Path(drive) / folder))
        for lib in [r"C:\Program Files (x86)\Steam\steamapps\common", r"D:\SteamLibrary\steamapps\common"]:
            search_paths.append(lib)
        
        for sp in search_paths:
            p = Path(sp)
            if not p.exists(): continue
            for folder in p.iterdir():
                if game_name in folder.name.lower().replace(" ","").replace("_",""):
                    exes = _find_exe_in_folder(str(folder), 2)
                    if exes:
                        try:
                            os.startfile(exes[0])
                            return f"Ejecutando: {folder.name}"
                        except Exception as e:
                            return f"Error: {e}"
        
        return f"Juego '{game_name}' no encontrado. Usa 'scan_all' primero."
    
    elif action == "open_steam":
        for p in [r"C:\Program Files (x86)\Steam\steam.exe", r"C:\Program Files\Steam\steam.exe"]:
            if Path(p).exists():
                os.startfile(p)
                return "Abriendo Steam."
        return "Steam no encontrado."
    
    elif action == "open_epic":
        for base in [r"C:\Program Files (x86)\Epic Games", r"C:\Program Files\Epic Games"]:
            exe = Path(base) / "Launcher" / "Portal" / "Binaries" / "Win64" / "EpicGamesLauncher.exe"
            if exe.exists():
                os.startfile(str(exe))
                return "Abriendo Epic Games."
        return "Epic Games no encontrado."

    return "Acciones: list, scan_all, launch, open_steam, open_epic"
