"""
ActionDetector — Detecta intenciones de acción en mensajes del usuario.

Este módulo analiza el texto del usuario y determina si está pidiendo
una acción concreta que debe ser ejecutada con una tool, o si es una
conversación normal.
"""

import re
from typing import Optional, Dict, Any

# Patrones de acciones concretas
ACTION_PATTERNS = {
    "open_url": {
        "patterns": [
            r"abr[ií]\s+(.+?)\s+(en\s+)?(el\s+)?navegador",
            r"abr[ií]\s+(www\.)?([\w-]+\.(com|org|net|ar|io|dev)[\w/.-]*)",
            r"abr[ií]\s+(youtube|google|gmail|whatsapp|telegram|discord|spotify|netflix)",
            r"naveg[aá]\s+a\s+(.+)",
            r"open\s+(.+?)\s+(in\s+)?(the\s+)?browser",
            r"open\s+(youtube|google|gmail|whatsapp|telegram|discord|spotify|netflix)",
        ],
        "tool": "web_navigation",
        "params": {"action": "navigate", "url": "{match}"},
    },
    "search_web": {
        "patterns": [
            r"busc[aá]\s+(.+?)\s+(en\s+)?(internet|google|la\s+web)",
            r"busc[aá]\s+(informaci[oó]n|info|datos|algo)\s+(sobre|acerca\s+de|de)\s+(.+)",
            r"busc[aá]\s+(.+)",
            r"qu[eé]\s+es\s+(.+)",
            r"qui[eé]n\s+es\s+(.+)",
            r"search\s+(.+?)\s+(on\s+)?(the\s+)?(internet|web|google)",
            r"what\s+is\s+(.+)",
            r"who\s+is\s+(.+)",
        ],
        "tool": "web_search",
        "params": {"action": "search", "query": "{match}"},
    },
    "system_status": {
        "patterns": [
            r"c[oó]mo\s+est[aá]\s+el\s+sistema",
            r"estado\s+del\s+sistema",
            r"dame\s+el\s+estado\s+del\s+sistema",
            r"uso\s+de\s+(cpu|ram|disco)",
            r"system\s+status",
            r"how\s+is\s+the\s+system",
        ],
        "tool": "system_monitor",
        "params": {"action": "report"},
    },
    "list_processes": {
        "patterns": [
            r"list[aá]\s+los\s+procesos",
            r"procesos\s+que\s+m[aá]s\s+(cpu|memoria)\s+consumen",
            r"top\s+procesos",
            r"list\s+processes",
            r"top\s+processes",
        ],
        "tool": "system_monitor",
        "params": {"action": "processes", "count": 10},
    },
    "create_file": {
        "patterns": [
            r"cre[aá]\s+(un\s+)?archivo\s+(llamado\s+)?(.+?)\s+con\s+(el\s+)?texto\s+(.+)",
            r"cre[aá]\s+(un\s+)?archivo\s+(llamado\s+)?([\w/.-]+\.\w+)\s*$",
            r"escrib[ií]\s+(un\s+)?script\s+(python|javascript|html|css)\s+en\s+(.+)",
            r"create\s+(a\s+)?file\s+(called\s+)?(.+?)\s+with\s+(the\s+)?text\s+(.+)",
            r"write\s+(a\s+)?(python|javascript|html|css)\s+script\s+in\s+(.+)",
        ],
        "tool": "file_api",
        "params": {"action": "write", "path": "{path}", "content": "{content}"},
    },
    "read_file": {
        "patterns": [
            r"le[eé]\s+(el\s+)?archivo\s+(.+)",
            r"mostrame\s+el\s+contenido\s+de\s+(.+)",
            r"read\s+(the\s+)?file\s+(.+)",
            r"show\s+me\s+the\s+content\s+of\s+(.+)",
        ],
        "tool": "file_api",
        "params": {"action": "read", "path": "{match}"},
    },
    "list_directory": {
        "patterns": [
            r"list[aá]\s+el\s+contenido\s+de\s+(.+)",
            r"qu[eé]\s+hay\s+en\s+(.+)",
            r"list\s+the\s+content\s+of\s+(.+)",
            r"what('s|\s+is)\s+in\s+(.+)",
        ],
        "tool": "file_api",
        "params": {"action": "list", "path": "{match}"},
    },
    "play_music": {
        "patterns": [
            r"toc[aá]\s+(una\s+)?canci[oó]n",
            r"reproduc[ií]\s+(una\s+)?canci[oó]n",
            r"play\s+(a\s+)?song",
            r"put\s+on\s+(some\s+)?music",
        ],
        "tool": "spotify_control",
        "params": {"action": "play"},
    },
    "send_message": {
        "patterns": [
            r"mand[aá]\s+un\s+mensaje\s+a\s+(.+)",
            r"env[ií]a\s+un\s+mensaje\s+a\s+(.+)",
            r"send\s+a\s+message\s+to\s+(.+)",
            r"text\s+(.+)",
        ],
        "tool": "send_message",
        "params": {"action": "send", "to": "{match}"},
    },
    "take_screenshot": {
        "patterns": [
            r"tom[aá]\s+(una\s+)?captura\s+de\s+pantalla",
            r"screenshot",
            r"captura\s+de\s+pantalla",
        ],
        "tool": "screen_control",
        "params": {"action": "capture"},
    },
    "open_app": {
        "patterns": [
            r"abr[ií]\s+(.+?)\s+(en\s+)?(la\s+)?app",
            r"abr[ií]\s+(.+?)\s+(en\s+)?(el\s+)?(programa|aplicaci[oó]n)",
            r"open\s+(.+?)\s+(in\s+)?(the\s+)?(app|application|program)",
            r"launch\s+(.+)",
        ],
        "tool": "open_app",
        "params": {"app_name": "{match}"},
    },
}


class ActionDetector:
    """Detecta intenciones de acción en mensajes del usuario."""

    def __init__(self):
        self._patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, list]:
        """Compila los patrones regex para cada tipo de acción."""
        compiled = {}
        for action_type, config in ACTION_PATTERNS.items():
            compiled[action_type] = [
                re.compile(p, re.IGNORECASE) for p in config["patterns"]
            ]
        return compiled

    def detect(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detecta si el texto del usuario contiene una intención de acción.

        Returns:
            Dict con 'tool', 'params', 'confidence' si detecta una acción,
            None si no detecta ninguna.
        """
        text_lower = text.lower().strip()

        for action_type, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text_lower)
                if match:
                    config = ACTION_PATTERNS[action_type]
                    params = self._extract_params(config["params"], match, text_lower)
                    return {
                        "tool": config["tool"],
                        "params": params,
                        "confidence": 0.9,
                        "action_type": action_type,
                    }

        return None

    def _extract_params(self, template: Dict[str, str], match: re.Match, text: str) -> Dict[str, Any]:
        """Extrae los parámetros del match y los aplica al template."""
        params = {}
        groups = match.groups()

        for key, value_template in template.items():
            if value_template == "{match}" and groups:
                # Usar el primer grupo no vacío
                for g in groups:
                    if g:
                        params[key] = g.strip()
                        break
            elif value_template == "{path}" and groups:
                # Buscar un path en el texto
                path_match = re.search(r'(/[\w/.-]+|[\w.-]+\.\w+)', text)
                params[key] = path_match.group(1) if path_match else groups[0] if groups else ""
            elif value_template == "{content}" and groups:
                # Buscar contenido después de "con texto" o "with text"
                content_match = re.search(r'(?:con\s+texto|with\s+text)\s+(.+)', text, re.IGNORECASE)
                params[key] = content_match.group(1).strip() if content_match else groups[-1] if groups else ""
            else:
                params[key] = value_template

        return params


# Instancia global
_detector = None

def get_action_detector() -> ActionDetector:
    """Obtiene la instancia global del ActionDetector."""
    global _detector
    if _detector is None:
        _detector = ActionDetector()
    return _detector


if __name__ == "__main__":
    detector = ActionDetector()

    test_cases = [
        "Abrí YouTube en el navegador",
        "Buscá información sobre Python 3.14",
        "Dame el estado del sistema",
        "Listá los procesos que más CPU consumen",
        "Creá un archivo llamado test.txt con el texto hola mundo",
        "Leé el archivo /tmp/test.txt",
        "Tocá una canción",
        "Mandá un mensaje a Juan",
        "Tomá una captura de pantalla",
        "Abrí Firefox",
        "¿Cómo estás?",
        "¿Qué es la inteligencia artificial?",
    ]

    for text in test_cases:
        result = detector.detect(text)
        if result:
            print(f"✓ '{text}' → {result['tool']} {result['params']}")
        else:
            print(f"✗ '{text}' → (no action detected)")
