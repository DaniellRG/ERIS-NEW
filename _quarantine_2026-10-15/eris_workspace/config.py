"""Eris Workspace — Configuration."""
from pathlib import Path

ERIS_ROOT = Path("D:/Eris_Source")
ERIS_MEMORY = ERIS_ROOT / "memory"
ERIS_CORE = ERIS_ROOT / "core"
ERIS_CONFIG = ERIS_ROOT / "config"
WORKSPACE = ERIS_ROOT / "eris_workspace"

WINDOW_TITLE = "Eris Workspace 3D"
WINDOW_W = 1920
WINDOW_H = 1080

NODE_TYPES = {
    "semantic":    {"color": (0.2, 0.5, 1.0),  "label": "Semantica",   "size": 0.25},
    "episodic":    {"color": (0.2, 0.9, 0.4),  "label": "Episodica",   "size": 0.30},
    "goal":        {"color": (1.0, 0.2, 0.2),  "label": "Goal",        "size": 0.35},
    "emotion":     {"color": (1.0, 0.9, 0.2),  "label": "Emocion",     "size": 0.45},
    "neurosphere": {"color": (0.7, 0.3, 1.0),  "label": "Neurosphere", "size": 0.32},
    "working":     {"color": (1.0, 0.6, 0.1),  "label": "Working",     "size": 0.20},
    "autonomy":    {"color": (0.0, 0.8, 0.8),  "label": "Autonomia",   "size": 0.28},
}

TAB_LIST = ["Memory", "NeuroSpheres", "Goals", "Emotions", "System", "Logs", "Chat"]

LEFT_HEMISPHERE = ["semantic", "episodic", "working", "autonomy"]
RIGHT_HEMISPHERE = ["emotion", "neurosphere", "goal"]

FILE_EXPLORER_DIRS = [
    ("memory", ERIS_MEMORY),
    ("core", ERIS_CORE),
    ("config", ERIS_CONFIG),
]

AUTO_REFRESH_INTERVAL = 30
TERMINAL_MAX_LINES = 60
ROTATION_SPEED = 0.15

GLOW_COLOR = (255, 255, 150)
NODE_GLOW_SIZE = 14

COLORS = {
    "bg":      (15, 15, 25),
    "panel":   (25, 25, 42),
    "menu":    (12, 12, 20),
    "hover":   (45, 45, 70),
    "item":    (32, 32, 52),
    "border":  (55, 55, 85),
    "txt":     (220, 220, 240),
    "dim":     (130, 130, 155),
    "accent":  (100, 180, 255),
    "green":   (100, 220, 140),
    "red":     (255, 100, 100),
    "yellow":  (255, 220, 80),
    "cyan":    (80, 220, 220),
    "purple":  (180, 120, 255),
}
