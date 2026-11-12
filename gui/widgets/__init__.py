# gui.widgets package — widgets de la interfaz de ERIS.
# Durante la transición T4, ui.py sigue siendo el punto de entrada público
# y re-exporta desde aquí para no romper from ui import X.

from gui.widgets.orb import (  # noqa: F401
    _OrbBridge,
    WebGLOrb,
    Particle,
    ParticleOrb,
    _ORB_ACCENTS,
)
from gui.widgets.glass import (  # noqa: F401
    GlassWidget,
    SystemWidget,
    WeatherWidget,
    TodoWidget,
    SpotifyWidget,
    NotesWidget,
)
