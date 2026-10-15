"""Reglas ajustables del combate. Ningún otro archivo debe tener estos números.

Cambiar una regla = cambiar un valor aquí (o crear otra instancia de
RulesConfig para probar variantes en los tests).

Lo que hace cada CARTA (iniciativa, si genera hit, si desestabiliza...) NO
está aquí: está en los datos de cada carta (cards/card_database.py).
"""
from dataclasses import dataclass, field


def default_beats():
    # clave VENCE a valor:  GUARD > ATTACK,  ATTACK > BREAK,  BREAK > GUARD
    return {"ATTACK": "BREAK", "BREAK": "GUARD", "GUARD": "ATTACK"}


def default_style_ranks():
    # (código, nombre, puntos mínimos), de menor a mayor
    return [("D", "Desafiante", 0), ("C", "Competente", 9), ("B", "Experto", 21), ("A", "Élite", 45),
            ("S", "Supremo", 300)]


def default_style_penalties():
    # rango ANTERIOR a la resolución -> (empate, derrota)
    return {"D": (3, 6), "C": (8, 16), "B": (15, 30), "A": (30, 60), "S": (50, 100)}


def default_ultimate_cards():
    # Definitiva provisional: la carta normal de cada categoría (sin bonificaciones).
    # SPECIAL acompaña a la acción principal, como cualquier SPECIAL.
    return {"ATTACK": "attack", "GUARD": "guard", "BREAK": "break", "MAGIC": "magic", "SPECIAL": "recover"}


def default_matchup_as():
    # Tipos que se ENFRENTAN como otro tipo del triángulo. MAGIC usa las mismas
    # relaciones que ATTACK (GUARD > MAGIC, MAGIC > BREAK) y MAGIC contra ATTACK
    # es un choque entre ofensivas equivalentes: lo desempatan la Stability y la
    # prioridad, sin ventaja automática. Las excepciones van en cada carta
    # (efectos "pre" como MODIFY_RESULT), no aquí.
    return {"MAGIC": "ATTACK"}


@dataclass
class RulesConfig:
    # --- Mazo y mano ------------------------------------------------------
    DECK_SIZE: int = 10
    MAX_HAND_SIZE: int = 5
    MAX_REDRAWS: int = 2

    # --- Mana ---------------------------------------------------------------
    MAX_MANA: int = 5
    MIN_MAX_MANA: int = 1               # tope mínimo si un efecto reduce el Mana máximo
    STARTING_MANA: int = 3
    MANA_REGEN: int = 1
    REGEN_ON_FIRST_TURN: bool = False   # el turno 1 se juega con STARTING_MANA
    # Coste de JUGAR una carta (cualquier tipo). PASS nunca cuesta nada.
    FREE_INTERACTIONS_PER_TURN: int = 1  # la 1ª interacción de cada turno es gratis
    PLAY_MANA_COST: int = 1              # a partir de la 2ª: jugar carta = 1 Mana
    # SPECIAL: se juega JUNTO a la acción principal (máx. 1 por interacción) y
    # cuesta siempre esto, sea la interacción que sea. Se suma al coste principal.
    SPECIAL_MANA_COST: int = 1

    # --- Daño y combo ---------------------------------------------------------
    MAX_HP: int = 100
    # El daño normal de cada carta está en su campo `damage` (cards/card_database.py).
    MAX_COMBO_HITS: int = 3             # hits CONSECUTIVOS para activar el Mega Combo
    MEGA_COMBO_DAMAGE: int = 20         # daño ADICIONAL del Mega Combo (evento aparte)

    # --- Tipos y Stability --------------------------------------------------------
    BEATS: dict = field(default_factory=default_beats)
    MATCHUP_AS: dict = field(default_factory=default_matchup_as)
    # La Stability desempata (STABLE > UNSTABLE) solo si hay CHOQUE: al menos una
    # de las dos cartas tiene iniciativa. GUARD = GUARD es empate aunque uno esté
    # UNSTABLE (dos defensas no se enfrentan).
    STABILITY_TIEBREAK_NEEDS_INITIATIVE: bool = True

    # --- PASS ---------------------------------------------------------------
    # PASS es literalmente pasar: no haces nada y la carta del rival se resuelve entera.
    # Carta contra PASS: el que juega gana la interacción...
    PASS_LOSES_INTERACTION: bool = True
    # ...el que pasa pierde la Stability si la carta desestabiliza (no se ha defendido)...
    PASS_PROTECTS_STABILITY: bool = False
    # ...y recibe el daño normal de la carta (y su hit).
    PASS_BLOCKS_DAMAGE: bool = False

    # --- Status Effects (game/status.py) -----------------------------------------
    # Nunca se aplican por azar ni por elemento: solo con APPLY_STATUS.
    BURN_DAMAGE: int = 5                # al empezar cada turno
    BURN_TURNS: int = 3
    POISON_DAMAGE: int = 3              # al empezar cada interacción
    POISON_TURNS: int = 3               # la duración se descuenta al empezar cada turno
    PARALYZE_INTERACTIONS: int = 1      # PASS obligatorio en la siguiente interacción
    SLEEP_INTERACTIONS: int = 3         # interacciones POSTERIORES a la que lo aplica
    ICE_CUBE_HP: int = 30               # FREEZE termina al romperse el cubo
    BREAK_ICE_DAMAGE: int = 15          # acción BREAK ICE del jugador congelado

    # --- Estilo (game/style.py) ------------------------------------------------------
    # Victorias consecutivas en interacciones: 1ª +3, 2ª +6 ... 5ª y siguientes +48
    STYLE_WIN_REWARDS: tuple = (3, 6, 12, 24, 48)
    STYLE_RANKS: list = field(default_factory=default_style_ranks)
    STYLE_PENALTIES: dict = field(default_factory=default_style_penalties)
    ULTIMATE_RANK: str = "S"            # rango que desbloquea la definitiva (1 uso por partida)
    ULTIMATE_CARDS: dict = field(default_factory=default_ultimate_cards)


RULES = RulesConfig()

# Mazos con los que arranca `python main.py` (ver cards/card_database.py: DECKS).
DEFAULT_DECKS = ("duelo", "duelo")

CARD_TYPES = ("ATTACK", "MAGIC", "GUARD", "BREAK")   # acciones principales (matchup)
SPECIAL = "SPECIAL"                             # categoría aparte: no entra en el matchup

# Canal de daño: independiente del tipo de acción y del elemento (cards/card.py)
CHANNEL_PHYSICAL = "physical"
CHANNEL_MAGIC = "magic"
