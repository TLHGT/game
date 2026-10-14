"""Configuración global del prototipo.

Todo valor "de diseño" (velocidades, tamaños, colores de UI) vive aquí para
poder ajustarlo sin tocar la lógica.
"""
import os
import sys

# --- Rutas -----------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Ejecutable de PyInstaller: los datos empaquetados están en _MEIPASS.
    # Las carpetas maps/ y assets/ junto al .exe tienen prioridad, para poder
    # añadir mapas o PNG sin recompilar.
    BASE_DIR = sys._MEIPASS
    _EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _EXE_DIR = BASE_DIR


def _data_dir(name):
    local = os.path.join(_EXE_DIR, name)
    return local if os.path.isdir(local) else os.path.join(BASE_DIR, name)


ASSET_DIR = _data_dir("assets")
MAP_DIR = _data_dir("maps")

# --- Ventana ---------------------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Hospital abandonado - Exploración y combate de cartas"
START_MAP = "hospital_exterior"  # nivel principal: la caverna ante el hospital (el bosque: "forest")
START_SPAWN = "default"

# --- Jugador ---------------------------------------------------------------
PLAYER_SPEED = 210            # píxeles de mundo por segundo
PLAYER_HITBOX = (22, 12)      # solo los "pies" son sólidos, no todo el sprite

# --- Interacción -----------------------------------------------------------
INTERACT_RANGE = 36           # margen alrededor de la hitbox del objeto

# --- Cámara ----------------------------------------------------------------
# Suavizado exponencial: valores altos = cámara más pegada al jugador.
# 0 desactiva el suavizado (cámara rígida).
CAMERA_SMOOTHING = 9.0
CAMERA_LOOK_OFFSET_Y = -20    # centra la cámara en el torso, no en los pies

# --- Mundo -----------------------------------------------------------------
COLLISION_CELL = 40           # tamaño de celda de la rejilla de colisión
FOREST_TREE_SPACING = 50      # separación media de árboles del bosque denso

# --- UI --------------------------------------------------------------------
FONT_NAMES = "segoeui,verdana,arial,dejavusans"
DIALOGUE_CHARS_PER_SEC = 55
NOTIFICATION_DURATION = 2.8
UI_TEXT = (245, 240, 225)
UI_TEXT_DIM = (190, 182, 160)
UI_PANEL = (22, 26, 30)
UI_ACCENT = (232, 196, 110)

# --- Combate (combate/) ----------------------------------------------------
# Mazo del jugador: un mazo de combate/cards/card_database.py (DECKS) o uno
# creado/editado con el editor de mazos (python combate/main.py -> decks.json).
# Se pueden cambiar durante la partida en el menú de pausa (TAB).
# En la exploración solo hay UN mazo (se edita desde la pausa; se guarda en
# decks_hospital.json, aparte de los mazos del duelo PvP) y no admite cartas repetidas.
PLAYER_DECK = "hospital"
HOSPITAL_DECK = ["attack", "guard", "break", "magic", "perfect_guard", "recover", "taunt",
                 "stun_guard", "revenge", "overdrive"]
DECKS_PATH = os.path.join(_EXE_DIR, "decks_hospital.json")
# Cartas disponibles desde el principio. Todas las demás empiezan BLOQUEADAS; algunas
# se consiguen en cofres del hospital (Ice Shard en el piso 1, Fire Bolt en el piso 2).
AVAILABLE_CARDS = ("attack", "guard", "break", "magic", "perfect_guard", "recover", "taunt",
                   "stun_guard", "revenge", "overdrive", "heavy_blow", "venom_strike")
# Puzle de las máquinas de ventajas: None = secuencia aleatoria en cada partida;
# p. ej. (2, 4, 1, 3) la fija (pruebas).
PERK_SEQUENCE = None
PLAYER_CHARACTER = "hero"     # personajes jugables: "hero" o "blaze"
PLAYER_COMBAT_NAME = "TÚ"     # nombre del jugador en la pantalla de combate
ENEMIES_ENABLED = True        # False: los mapas se cargan sin enemigos (pruebas de exploración)
BATTLE_FADE_SPEED = 5.0       # fundido al empezar un combate (por segundo)

# --- Debug -----------------------------------------------------------------
DEBUG_START_ENABLED = False
