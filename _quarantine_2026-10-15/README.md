# Cuarentena — 2026-10-15

Archivos **huérfanos / residuos** retirados del árbol activo durante la auditoría
de Eris. **No se borró nada**: están acá por si se los necesita. Para restaurar
cualquiera, moverlo de vuelta a su ruta original (la estructura se conserva).

## Por qué se retiró cada cosa

| Archivo | Motivo (verificado el 2026-10-15) |
|---|---|
| `actions/res_manager.py` | Duplicado muerto de `actions/res_monitor.py` (la tool real). 0 referencias. |
| `actions/training_full.py` | Duplicado muerto de `actions/full_training.py` (la registrada). 0 referencias. |
| `actions/orb_overlay.py` | Port/overlay nunca cableado. 0 referencias. |
| `actions/_chrome_launch.py` | Helper muerto. 0 referencias. |
| `core/test_win_audio.py` | Test de audio de Windows, fuera del suite. 0 referencias. |
| `watchdog.py` (raíz) | No se importa y hardcodea `D:\Eris_Source`. |
| `eris_workspace/` | Proyecto abandonado: importa `core.data_loader`/`core.state`/`core.graph_engine` (no existen). 0 referencias. |
| `ERIS.exe`, `nul`, `watchdog_start.vbs.disabled` | Residuos de Windows en la raíz. |

## Cómo se verificó que no se usan

```bash
grep -rnE "import[[:space:]]+(res_manager|training_full|orb_overlay|_chrome_launch|test_win_audio|watchdog)" --include=*.py .
```
→ 0 resultados. Ninguno figura en `core/tool_registry.py`, `core/tool_declarations.py`
ni `actions/custom_tools.json`.

**Post-retiro:** `test_all.py` sigue en **177 PASS / 0 FAIL / 3 WARN** y el sync de
tools en **514/514** (estos archivos no eran tools).
