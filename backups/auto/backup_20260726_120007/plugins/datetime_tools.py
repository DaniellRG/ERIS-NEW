"""
plugins/datetime_tools.py — Date/time info plugin for ERIS.
More practical sample showing real utility.
"""
import time
from datetime import datetime, timezone
from core.plugin_manager import Plugin


class DateTimePlugin(Plugin):
    name = "datetime_tools"
    version = "1.0.0"
    description = "Provides current date, time, timezone info, and time conversion."

    def execute(self, action: str, params: dict) -> str:
        if action == "now":
            tz_str = params.get("timezone", "local")
            fmt = params.get("format", "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            return f"Fecha/hora actual: {now.strftime(fmt)}"
        elif action == "utc":
            now = datetime.now(timezone.utc)
            return f"UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        elif action == "unix":
            return f"Unix timestamp: {int(time())}"
        return f"Actions: now, utc, unix"
