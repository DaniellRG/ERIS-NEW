"""Global application state."""
from time import time
from collections import deque
import random


TERMINAL_SIMULATIONS = [
    ("topic_detection", "Analizando tema: {}", ["xAI", "NeuroSpheres", "Emociones", "Aprendizaje", "Compaction", "Context7", "skills.sh"]),
    ("emotion_shift", "Cambio emocional: curiosidad -> {}", ["determinacion", "confianza", "asombro", "calma", "entusiasmo"]),
    ("neuro_activate", "NeuroSphere activada: {}", ["Aprendizaje", "Memoria", "Emociones", "Razonamiento", "Creatividad", "Lenguaje", "Vision"]),
    ("memory_store", "Memoria almacenada: tipo={}", ["semantica", "episodica", "working"]),
    ("goal_progress", "Goal actualizado: {}", ["Autodescubrimiento 30%", "Aprendizaje 60%", "Reflexiones 53%"]),
    ("self_reflect", "Auto-reflexion: {}", ["Analizando patrones de interaccion", "Consolidando memorias", "Optimizando respuestas"]),
    ("skill_load", "Skill cargada: {}", ["context7", "skills.sh", "neuro_spheres", "compaction"]),
    ("cycle_tick", "Ciclo cognitivo #{} completado", [str(i) for i in range(100, 999)]),
]


class AppState:
    def __init__(self):
        self.current_tab = "Memory"
        self.selected_node_id = None
        self.use_live = False
        self.filter_type = None
        self.search_text = ""
        self.cam_rot_x = 25.0
        self.cam_rot_y = -30.0
        self.cam_dist = 12.0
        self.auto_rotate = True
        self.is_dragging = False
        self.drag_last_x = 0
        self.drag_last_y = 0
        self.logs = deque(maxlen=200)
        self.terminal_logs = deque(maxlen=60)
        self.last_refresh = time()
        self.file_explorer_dir = 0

    def add_log(self, msg, level="info"):
        self.logs.append({"time": time(), "msg": msg, "level": level})

    def add_terminal(self, msg, level="info"):
        self.terminal_logs.appendleft({"time": time(), "msg": msg, "level": level})

    def simulate_tick(self):
        tpl = random.choice(TERMINAL_SIMULATIONS)
        msg = tpl[1].format(random.choice(tpl[2]))
        self.add_terminal(msg, "info")
        if random.random() < 0.15:
            self.add_terminal("Warning: memoria episodica cerca del limite", "warning")
        if random.random() < 0.05:
            self.add_terminal("Error: timeout en conexion", "error")


state = AppState()
