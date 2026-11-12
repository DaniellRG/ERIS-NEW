## INSTALAR / DESCARGAR PROGRAMAS — PROCEDIMIENTO (Linux → terminal, Windows → winget)

En Linux instalás directo por terminal bash. En Windows usá `program_manager` (winget) con este flujo:

1. Windows: BUSCAR `program_manager(action="search", name="<programa>")` → obtené el ID EXACTO de winget.
2. CONFIRMAR: mostrá el paquete y pedí confirmación antes de instalar/desinstalar.
3. INSTALAR (o DESCARGAR): `program_manager(action="install", name="<nombre>", confirm=True, silent=True)`.
4. VERIFICAR: confirmá versión y ruta instalada.
5. REPORTAR: resumí al usuario el resultado.

Linux (este equipo): corré `sudo pacman -S <pkg>` o `sudo apt install <pkg>` vía `terminal_agent action=run` (elevated=true antepone sudo). Para Python: `pip install`. Para node: `npm install -g`. Indexá con `pacman -Ss <pkg>` / `apt search <pkg>` o instalalo directo.
Reglas: pedí confirmación antes de instalar/desinstalar, y si falla leé la salida y proponé alternativa.

