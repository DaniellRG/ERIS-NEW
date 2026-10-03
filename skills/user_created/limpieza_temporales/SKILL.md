---
name: limpieza_temporales
description: Limpia archivos temporales del sistema (caché, /tmp, prefetch, etc) para liberar espacio en disco
---

# limpieza_temporales

## Skill: Limpieza de Temporales

### Qué hace
Libera espacio en disco eliminando archivos temporales seguros del sistema.

### Pasos
1. **Escaneá** los directorios temporales comunes: `/tmp`, `~/.cache`, `C:\Users\[usuario]\AppData\Local\Temp`, `C:\Windows\Temp`
2. **Calculá** el espacio que se puede liberar en cada uno
3. **Eliminá** los archivos temporales seguros (más de 7 días de antigüedad)
4. **Reportá** cuánto espacio se liberó

### Herramientas útiles
- `terminal_agent` o `shell_executor` para ejecutar comandos de limpieza
- `system_monitor` para ver el estado del disco antes/después

### Cuidado
- NO eliminar archivos del sistema operativo
- NO eliminar caché de aplicaciones que se estén usando
- Solo archivos temporales y de caché seguros
