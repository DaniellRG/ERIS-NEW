import json
from pathlib import Path


def get_time_context() -> str:
    """Local system time - always correct."""
    import datetime
    now = datetime.datetime.now()
    time_str = now.strftime("%A, %d %B %Y - %I:%M:%S %p")
    hour = now.hour
    time_of_day = "de la madrugada" if hour < 6 else "de la manana" if hour < 12 else "de la tarde" if hour < 18 else "de la noche"
    return (
        f"[CURRENT DATE & TIME - Colombia]\n"
        f"Right now it is: {time_str}\n"
        f"Time of day: {time_of_day}\n"
        f"Use this information to answer time-related questions accurately in Spanish.\n\n"
    )


def load_tz(config_path):
    """Load timezone from api_keys.json config.

    Returns the loaded timezone object (or the system local timezone as fallback).
    """
    from zoneinfo import ZoneInfo as _ZoneInfo
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        tz_name = cfg.get("timezone", "")
        if tz_name:
            try:
                tz = _ZoneInfo(tz_name)
                print(f"[TZ] Timezone loaded: {tz_name}")
                return tz
            except Exception as e:
                print(f"[TZ] Failed to load '{tz_name}': {e}")
                import zoneinfo as _zi
                available = _zi.available_timezones()
                tz_lower = tz_name.lower()
                for known in available:
                    if known.lower() == tz_lower:
                        tz = _ZoneInfo(known)
                        print(f"[TZ] Matched '{tz_name}' → '{known}'")
                        return tz
                else:
                    parts = tz_name.replace("\\", "/").split("/")
                    short = parts[-1].lower() if parts else ""
                    for known in available:
                        if known.lower().endswith("/" + short):
                            tz = _ZoneInfo(known)
                            print(f"[TZ] Partial match '{tz_name}' → '{known}'")
                            return tz
                    else:
                        from datetime import datetime as _dt
                        tz = _dt.now().astimezone().tzinfo
                        print(f"[TZ] Falling back to system timezone: {tz}")
                        return tz
    except Exception as e:
        print(f"[TZ] Error reading config: {e}")
