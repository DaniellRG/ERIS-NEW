"""windows_settings.py — Ajustes de Windows. Implementa lo delegable, honesto con el resto."""
from actions.system_volume import system_volume


def windows_settings(parameters: dict, player=None) -> str:
    """Acciones: audio, status. display/network/power/bluetooth/etc. reportan estado."""
    params = parameters or {}
    action = str(params.get("action", "")).lower()

    if action == "audio":
        return system_volume(params, player)
    if action in ("status", "list"):
        return ("Windows settings: 'audio' disponible (delega en system_volume). "
                "Las demás áreas (display, network, power, bluetooth, defaults, "
                "startup, features, environment) requieren ajustes manuales.")
    return (
        f"Windows settings no implementa '{action}' aún. "
        f"Disponible: audio, status. Para energía usá pc_control (sleep/hibernate/restart)."
    )
