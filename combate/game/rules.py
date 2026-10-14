"""Reglas puras del combate: sin Pygame, sin estado, deterministas.

Tres preguntas separadas, tres funciones:

    resolve_interaction()  ¿QUIÉN GANA?            tipo, efectos "pre", Stability, prioridad
    sequence_continues()   ¿HAY OTRA INTERACCIÓN?  iniciativa
    reaches_mega_combo()   ¿MEGA COMBO?            hits consecutivos

Qué CONSECUENCIAS tiene ganar (daño, hit, Stability, Mana...) lo deciden los
datos de la carta ganadora y las aplica game/combat.py en este orden:
    efectos -> hits -> daño normal -> Stability -> combo
    -> (Mega Combo: daño adicional, combo = 0) -> continuar / terminar según iniciativa

Orden para decidir el ganador:
    1. PASS
    2. efectos que anulan o fuerzan el resultado (CANCEL_CARD, MODIFY_RESULT)
    3. tipo:        GUARD > ATTACK,  ATTACK > BREAK,  BREAK > GUARD
    4. Stability:   mismo tipo con choque (alguna carta con iniciativa) -> STABLE
                    gana a UNSTABLE (salvo IGNORE_STABILITY). GUARD = GUARD: empate.
    5. prioridad de carta
    6. empate
"""
from dataclasses import dataclass, field

from combate.cards.card import has_initiative
from combate.cards.card_effects import applies
from combate.game.config import RULES

WIN, DRAW = "win", "draw"

DAMAGE_INTERACTION = "interaction"   # daño normal de ganar la interacción
DAMAGE_MEGA_COMBO = "mega_combo"     # daño adicional del Mega Combo
DAMAGE_BREAK_ICE = "break_ice"       # acción BREAK ICE del jugador congelado (a su propio cubo)


@dataclass
class DamageEvent:
    kind: str           # DAMAGE_INTERACTION | DAMAGE_MEGA_COMBO | DAMAGE_BREAK_ICE
    source: int         # índice de quien hace el daño
    target: int         # índice de quien lo recibe
    amount: int
    to_cube: bool = False   # lo absorbió el ICE CUBE (FREEZE): el HP del jugador no cambia
    # Origen del daño de interacción (para efectos que reaccionen a daño mágico, de fuego...).
    # Son metadatos: no cuentan al comparar eventos.
    action: str = field(default=None, compare=False)    # tipo de carta: ATTACK, MAGIC, BREAK...
    channel: str = field(default=None, compare=False)   # "physical" | "magic" (None: Mega Combo, BREAK ICE)
    element: str = field(default=None, compare=False)   # FIRE, ICE... o None. NUNCA aplica estados
    # Pasiva del personaje que causa el daño (CombatEngine._apply_passive, una sola vez)
    base_amount: int = field(default=None, compare=False)    # daño antes de la pasiva
    passive_pct: int = field(default=0, compare=False)       # % que añadió la pasiva
    combo_step: int = field(default=None, compare=False)     # nº de HIT consecutivo (Hero)
    passive_applied: bool = field(default=False, compare=False)
    # Pasiva de quien RECIBE el daño (Passive.incoming_damage)
    heal: bool = field(default=False, compare=False)          # cura al objetivo en vez de dañarle
    weak_base: int = field(default=None, compare=False)       # daño antes de la debilidad elemental


@dataclass
class InteractionResult:
    outcome: str                        # WIN | DRAW
    winner: int = None                  # índice 0/1 del ganador
    cards: tuple = (None, None)         # carta de cada jugador (None = PASS)
    lines: list = field(default_factory=list)    # POR QUÉ ganó (para la UI)
    tags: list = field(default_factory=list)     # COUNTER, BREAK, BLOCK, ADVANTAGE...
    decided_by: str = None              # pass | effect | type | stability | priority | draw
    # --- Consecuencias (las rellena CombatEngine) -----------------------------
    damage_events: list = field(default_factory=list)       # DamageEvent, en orden
    hit_generated: int = 0                                  # hits ganados por el ganador
    received_hit: tuple = (False, False)                    # ¿recibió un hit cada jugador?
    combo_after: tuple = (0, 0)                             # combo_hits de cada jugador tras resolver
    stability_changes: dict = field(default_factory=dict)   # {índice: nuevo valor stable}
    mega_combo: int = None                                  # índice de quien activa Mega Combo
    consequences: list = field(default_factory=list)        # QUÉ PASÓ (para la UI)
    continues: bool = None                                  # ¿hay otra interacción? (iniciativa)
    mana_paid: tuple = (0, 0)                               # Mana pagado por cada jugador
    specials: tuple = (None, None)                          # SPECIAL jugada por cada jugador
    special_lines: list = field(default_factory=list)       # qué hicieron (antes del matchup)
    interaction_number: int = 0                             # nº de interacción en el turno
    status_actions: tuple = (None, None)                    # BREAK_ICE / WAIT del jugador congelado
    status_changes: list = field(default_factory=list)      # (índice, texto) de estados en esta interacción
    ultimates: tuple = (None, None)                         # categoría de la definitiva usada por cada jugador
    style_changes: tuple = ()                               # StyleChange de cada jugador (una vez por interacción)

    @property
    def initiative_continues(self):
        return self.continues

    @property
    def loser(self):
        return None if self.winner is None else 1 - self.winner

    @property
    def draw(self):
        return self.outcome == DRAW

    @property
    def winning_card(self):
        return None if self.winner is None else self.cards[self.winner]


def matchup_type(card_type, rules=RULES):
    """Tipo con el que se enfrenta una acción (MAGIC -> ATTACK). El tipo de
    la carta no cambia: solo se traduce para consultar BEATS."""
    return rules.MATCHUP_AS.get(card_type, card_type)


def compare_types(type_a, type_b, beats=None, matchup_as=None):
    """1 si A vence a B, -1 si B vence a A, 0 si empatan."""
    beats = beats or RULES.BEATS
    matchup_as = RULES.MATCHUP_AS if matchup_as is None else matchup_as
    type_a, type_b = matchup_as.get(type_a, type_a), matchup_as.get(type_b, type_b)
    if type_a == type_b:
        return 0
    if beats.get(type_a) == type_b:
        return 1
    if beats.get(type_b) == type_a:
        return -1
    return 0


def label(card):
    """Nombre para explicar: el tipo en las básicas, el nombre en las especiales."""
    if card is None:
        return "PASS"
    return card.card_type if card.category == "basic" else card.name.upper()


def _pre_modifier(card, other):
    """Efecto "pre" de `card` contra `other`: "cancel", "win", "draw" o None."""
    if card is None:
        return None
    for data in card.effects_when("pre"):
        if data["type"] == "CANCEL_CARD":
            return "cancel"
        if data["type"] == "MODIFY_RESULT" and applies(data, other):
            return data.get("result", "win")
    return None


def resolve_interaction(card_a, card_b, stable_a, stable_b, rules=RULES, names=("P1", "P2")):
    """card_a / card_b: Card o None (PASS). stable_x: bool. Solo decide quién gana."""
    cards = (card_a, card_b)

    # --- 1. PASS --------------------------------------------------------------
    if card_a is None and card_b is None:
        return InteractionResult(DRAW, None, cards, ["PASS · PASS", "DRAW"], decided_by="pass")
    if card_a is None or card_b is None:
        player = 0 if card_a is not None else 1
        if not rules.PASS_LOSES_INTERACTION:
            return InteractionResult(DRAW, None, cards, [f"{label(cards[player])} vs PASS", "DRAW"], decided_by="pass")
        return InteractionResult(WIN, player, cards, [f"{label(cards[player])} vs PASS", f"{names[player]} WINS"],
                                 decided_by="pass")

    # --- 2. Efectos que cambian el resultado -------------------------------------
    mods = (_pre_modifier(card_a, card_b), _pre_modifier(card_b, card_a))
    if "cancel" in mods:
        who = cards[mods.index("cancel")]
        return InteractionResult(DRAW, None, cards, [f"{label(who)} ANULA LA INTERACCIÓN", "DRAW"],
                                 decided_by="effect")
    if mods.count("win") == 1:
        winner = mods.index("win")
        w, l = cards[winner], cards[1 - winner]
        return InteractionResult(WIN, winner, cards, [f"{label(w)} > {l.card_type}", f"{names[winner]} WINS"],
                                 [f"{w.name.upper()}"], decided_by="effect")
    if "draw" in mods:
        return InteractionResult(DRAW, None, cards, [f"{label(card_a)} = {label(card_b)} (efecto)", "DRAW"],
                                 decided_by="effect")

    # --- 3. Tipo ----------------------------------------------------------------
    ta, tb = card_a.card_type, card_b.card_type
    cmp = compare_types(ta, tb, rules.BEATS, rules.MATCHUP_AS)
    if cmp != 0:
        winner = 0 if cmp > 0 else 1
        w, l = cards[winner], cards[1 - winner]
        wm, lm = matchup_type(w.card_type, rules), matchup_type(l.card_type, rules)
        tags = []
        if wm == "GUARD" and lm == "ATTACK":
            tags.append("COUNTER" if w.causes_instability else "BLOCK")
        if wm == "BREAK" and lm == "GUARD":
            tags.append("BREAK")
        lines = [f"{label(w)} > {label(l)}" if w.category != "basic" or l.category != "basic"
                 else f"{w.card_type} > {l.card_type}", f"{names[winner]} WINS"]
        return InteractionResult(WIN, winner, cards, lines, tags, decided_by="type")

    lines = [f"{ta} = {tb}"]

    # --- 4. Stability (prioridad negativa, binaria) ------------------------------------
    ignoring = [c for c in cards if c.has_effect("IGNORE_STABILITY", "pre")]
    clash = sequence_continues(card_a, card_b) or not rules.STABILITY_TIEBREAK_NEEDS_INITIATIVE
    if stable_a != stable_b:
        if ignoring:
            lines.append(f"{label(ignoring[0])} ignora la Stability")
        elif not clash:
            lines.append("SIN INICIATIVA: la Stability no desempata")
        else:
            winner = 0 if stable_a else 1
            lines += [f"{names[winner]} STABLE > {names[1 - winner]} UNSTABLE", f"{names[winner]} WINS"]
            return InteractionResult(WIN, winner, cards, lines, ["ADVANTAGE"], decided_by="stability")
    else:
        lines.append("AMBOS STABLE" if stable_a else "AMBOS UNSTABLE")

    # --- 5. Prioridad de carta --------------------------------------------------------
    if card_a.priority != card_b.priority:
        winner = 0 if card_a.priority > card_b.priority else 1
        hi, lo = cards[winner], cards[1 - winner]
        lines += [f"{label(hi)}: PRIORIDAD {hi.priority} > {lo.priority}", f"{names[winner]} WINS"]
        return InteractionResult(WIN, winner, cards, lines, decided_by="priority")

    # --- 6. Empate -------------------------------------------------------------------
    lines.append("DRAW")
    return InteractionResult(DRAW, None, cards, lines, decided_by="draw")


def sequence_continues(card_a, card_b):
    """Regla de iniciativa: hay otra interacción si AL MENOS UNA de las dos
    acciones tenía iniciativa. Solo decide si sigue, no quién gana."""
    return has_initiative(card_a) or has_initiative(card_b)


def reaches_mega_combo(combo_hits, rules=RULES):
    """El Mega Combo se activa al llegar a MAX_COMBO_HITS hits consecutivos."""
    return combo_hits >= rules.MAX_COMBO_HITS
