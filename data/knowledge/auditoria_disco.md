# Auditoría de disco y ruido de carpetas (2026-10-15)

Informe completo: `Logs/Auditoria-ruido-2026-10-15.md` en el vault de Obsidian.

## Qué es "ruido" en esta PC (con OK del dueño se limpia)

1. **Papelera llena — 6.3 GB**: `~/.local/share/Trash/files` con
   `MiniOS10 Pro v26.0 x64 - dprojects.rar` (5.9 GB), un deb de Cisco Packet Tracer,
   un flac y un jpeg.
2. **ISOs/instaladores en Downloads — ~10.5 GB**: `MiniOS10 Pro v26.0 x64.iso` (5.9 GB),
   `ShowOS Pro v2.0.iso` (4.2 GB), `MonoFramework-MDK-6.12.0.206.macos10.xamarin.universal.pkg`
   (353 MB, es para macOS, inútil en Linux), y wallpapers/html sueltos.
3. **Cachés regenerables — ~26 GB**: `.cache/yay` 6.1 GB (rider 4.4 G, packettracer 1.2 G),
   `.nuget` + `.local/share/NuGet` 9.8 GB, `.cache/JetBrains/Rider2026.2` 4.2 GB,
   `.npm` 1.1 GB, `.cache/mozilla`+`chromium`+`pkg` ~1.6 GB, `.cache/aether`+`puccinialin`
   1.5 GB, `.cache/uv`+`mise`+`pip` 1.5 GB. Limpiar con `yay -Sc`,
   `dotnet nuget locals all --clear`, `npm cache clean --force`.
4. **OpenDevelop — 8.6 GB**: clone ajeno de `github.com/lextudio/OpenDevelop`
   (fork de SharpDevelop) con `AddIns` 3.3 GB, `src` 2.3 GB, `externals` 1.1 GB,
   `bin` 395 MB de artefactos de build. Adentro está `apinuevo/` que SÍ es del dueño
   (WebAPI .NET de 12 KB) y hay que rescatar antes.
5. **Restos de instalación**: `~/Work/` (`.mise.toml` + `tries/` vacío),
   `~/install.sh` (bootstrap de Hermes agent) y `~/.hermes` (46 MB).

## Qué NO tocar
- `~/Eris_NEW` (vault Obsidian), `~/ERIS-NEW` (repo de Eris), `~/Documents`
  (APIC#, BaseDatosIIMySQL, JAVA, ERIS_Data), `~/PracticaPOO`, `~/RiderProjects`,
  `~/Downloads/mi_primer_api`, `~/Music`, `~/Pictures`, `~/Wallpapers`,
  `~/VirtualBox VMs` (18 GB, lab pentest) y `.local/share/Steam` (63 GB de juegos).
- `~/pt` es el perfil de **Cisco Packet Tracer** (instalado el 12/10), no basura.

## Proyectos reales detectados (mapa de la casa)
`ERIS-NEW`, `PracticaPOO`, `OpenDevelop/apinuevo`, `RiderProjects/{ConsoleApp1,ConsoleApp2,
ConsoleApp3,MiPrimeraAPI,WebApplication1,WebApplication2,ClassLibrary1,APIParciarl2,
Parcial2API2}`, `eris_workspace`, `Downloads/mi_primer_api`.

Total recuperable con OK: **~51 GB**. No incluye juegos ni la VM.
