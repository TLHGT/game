"""Todas las cartas y mazos del juego, como datos.

TYPE_DEFAULTS es solo una comodidad para no repetir valores en cada carta:
cualquier carta puede sobrescribirlos (p. ej. un ATTACK sin iniciativa). El
motor lee los campos de la carta, nunca su tipo.

Formato de un efecto:
    {"type": "ADD_HIT", "when": "win", "amount": 1, "vs": "GUARD"}

    when: "special" al revelar, ANTES del matchup (cartas SPECIAL)
          "cost"  modifica el coste de jugarla (MODIFY_PLAY_COST)
          "pre"   al comparar (MODIFY_RESULT, CANCEL_CARD, IGNORE_STABILITY)
          "play"  siempre que se juega, gane o pierda
          "win"   si la carta gana la interacción
          "lose"  si la carta pierde la interacción
    vs:   (opcional) solo si la carta rival es de ese tipo

Estados alterados: {"type": "APPLY_STATUS", "status": "BURN", ...} con
condiciones opcionales if_outcome / if_main_type / if_hit (cards/card_effects.py).
"""
import copy

from combate.cards.card import CATEGORY_BASIC, CATEGORY_SPECIAL, Card
from combate.game.config import CHANNEL_MAGIC, CHANNEL_PHYSICAL

# Sin daño por defecto en los tipos ofensivos: cada carta declara el suyo (card() lo exige).
DAMAGE_TYPES = ("ATTACK", "MAGIC", "BREAK")

TYPE_DEFAULTS = {
    "ATTACK": dict(has_initiative=True, generates_hit=True, causes_instability=True,
                   damage_channel=CHANNEL_PHYSICAL),
    # MAGIC: ofensiva a distancia. Mismos valores que ATTACK; cambia el canal de daño.
    "MAGIC": dict(has_initiative=True, generates_hit=True, causes_instability=True,
                  damage_channel=CHANNEL_MAGIC),
    "BREAK": dict(has_initiative=True, generates_hit=True, causes_instability=True,
                  damage_channel=CHANNEL_PHYSICAL),
    "GUARD": dict(has_initiative=False, damage=0, generates_hit=False, causes_instability=False),
    # SPECIAL: nunca iniciativa, daño ni hit. Su efecto va en `effects` con when="special".
    "SPECIAL": dict(has_initiative=False, damage=0, generates_hit=False, causes_instability=False),
}


def card(**data):
    """Combina los valores por defecto del tipo con los de la carta. Una carta
    ATTACK / MAGIC / BREAK debe declarar su `damage` (puede ser 0 a propósito)."""
    if data["card_type"] in DAMAGE_TYPES and "damage" not in data:
        raise ValueError(f"La carta '{data['id']}' ({data['card_type']}) debe declarar su daño: damage=...")
    return {**TYPE_DEFAULTS[data["card_type"]], **data}


CARD_DATA = [
    # --- Básicas -----------------------------------------------------------------
    card(id="attack", name="Attack", short="ATK", card_type="ATTACK", category=CATEGORY_BASIC,
         damage=10,
         description="Vence a BREAK. Hit, desestabiliza, iniciativa."),
    card(id="guard", name="Guard", short="GRD", card_type="GUARD", category=CATEGORY_BASIC,
         description="Vence a ATTACK. No hace hit ni desestabiliza."),
    card(id="break", name="Break", short="BRK", card_type="BREAK", category=CATEGORY_BASIC,
         damage=10,
         description="Vence a GUARD. Hit, desestabiliza, iniciativa."),
    card(id="magic", name="Magic", short="MAG", card_type="MAGIC", category=CATEGORY_BASIC,
         damage=10,
         description="Ataque mágico a distancia. Vence a BREAK. Hit, desestabiliza, iniciativa."),

    # --- Defensas especiales ------------------------------------------------------------
    card(id="perfect_guard", name="Perfect Guard", short="PGD", card_type="GUARD", category=CATEGORY_SPECIAL,
         causes_instability=True,
         description="Si gana, además desestabiliza al rival."),
    card(id="unbreakable_guard", name="Unbreakable Guard", short="UGD", card_type="GUARD",
         category=CATEGORY_SPECIAL,
         description="No puede perder contra BREAK: lo vence.",
         effects=[{"type": "MODIFY_RESULT", "when": "pre", "vs": "BREAK", "result": "win"}]),
    card(id="desperation", name="Desperation", short="DSP", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Al jugarla recuperas Stability, ganes o pierdas.",
         effects=[{"type": "RECOVER_STABILITY", "when": "play"}]),
    card(id="parry", name="Parry", short="PRY", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Anula cualquier carta: la interacción queda en empate.",
         effects=[{"type": "CANCEL_CARD", "when": "pre"}]),
    card(id="iron_stance", name="Iron Stance", short="IRN", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Si pierdes, no pierdes Stability.",
         effects=[{"type": "PROTECT_STABILITY", "when": "lose"}]),
    card(id="mana_surge", name="Mana Surge", short="SRG", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Si gana: +1 Mana.",
         effects=[{"type": "GAIN_MANA", "when": "win", "amount": 1}]),

    # --- SPECIAL: acompañan a la acción principal (máx. 1 por interacción) ----------------
    card(id="recover", name="Recover", short="RCV", card_type="SPECIAL", category=CATEGORY_SPECIAL,
         description="Recupera STABLE inmediatamente, antes del enfrentamiento.",
         effects=[{"type": "RECOVER_STABILITY", "when": "special"}]),

    # --- Ofensivas especiales -----------------------------------------------------------
    card(id="revenge", name="Revenge", short="REV", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10,
         play_condition="unstable", recovers_stability=True,
         description="Solo estando UNSTABLE. Ignora la Stability en el empate. Si gana, recuperas Stability.",
         effects=[{"type": "IGNORE_STABILITY", "when": "pre"}]),
    card(id="overdrive", name="Overdrive", short="OVR", card_type="ATTACK", category=CATEGORY_SPECIAL, priority=1,
         damage=10,
         description="Prioridad 1: gana los empates entre ATTACK."),
    card(id="break_guard", name="Break Guard", short="BGD", card_type="BREAK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Si vence a GUARD: +1 hit extra.",
         effects=[{"type": "ADD_HIT", "when": "win", "vs": "GUARD", "amount": 1}]),
    card(id="feint", name="Feint", short="FNT", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Finta: también vence a GUARD.",
         effects=[{"type": "MODIFY_RESULT", "when": "pre", "vs": "GUARD", "result": "win"}]),
    card(id="heavy_blow", name="Heavy Blow", short="HVY", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Si gana: +10 de daño normal (20 en total).",
         effects=[{"type": "MODIFY_DAMAGE", "when": "win", "amount": 10}]),
    card(id="crescendo", name="Crescendo", short="CRS", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Si con ella llegas al Mega Combo: +10 de daño de Mega Combo.",
         effects=[{"type": "MODIFY_MEGA_DAMAGE", "when": "win", "amount": 10}]),
    card(id="focus", name="Focus", short="FCS", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Tu combo no se rompe en esta interacción aunque no hagas hit.",
         effects=[{"type": "PROTECT_COMBO", "when": "play"}]),
    card(id="drain", name="Drain", short="DRN", card_type="BREAK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Si gana: el rival pierde 1 Mana.",
         effects=[{"type": "REDUCE_MANA", "when": "win", "amount": 1}]),

    # --- MAGIC con elemento (el elemento NO aplica estados por sí mismo) -------------------
    card(id="fire_bolt", name="Fire Bolt", short="FBT", card_type="MAGIC", category=CATEGORY_SPECIAL,
         damage=10,
         element="FIRE", description="MAGIC de FIRE. Sin estados: para quemar hace falta FLAME."),

    # --- Status Effects (game/status.py) -------------------------------------------------
    # Un estado SOLO lo aplica un efecto explícito (APPLY_STATUS); nunca un elemento.
    card(id="flame", name="Flame", short="FLM", card_type="SPECIAL", category=CATEGORY_SPECIAL,
         description="Si ganas la interacción con una carta MAGIC: BURN al rival.",
         effects=[{"type": "APPLY_STATUS", "when": "special", "status": "BURN",
                   "if_outcome": "win", "if_main_type": "MAGIC"}]),
    # Cartas de prueba del mazo "estados" (no están en los mazos por defecto)
    card(id="searing_break", name="Searing Break", short="SRB", card_type="BREAK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Si gana: BURN al rival.",
         effects=[{"type": "APPLY_STATUS", "when": "win", "status": "BURN"}]),
    card(id="venom_strike", name="Venom Strike", short="VNM", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10,
         description="Si gana: POISON al rival.",
         effects=[{"type": "APPLY_STATUS", "when": "win", "status": "POISON"}]),
    card(id="stun_guard", name="Stun Guard", short="STN", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Si gana: PARALYZE al rival.",
         effects=[{"type": "APPLY_STATUS", "when": "win", "status": "PARALYZE"}]),
    card(id="frost_guard", name="Frost Guard", short="FRG", card_type="GUARD", category=CATEGORY_SPECIAL,
         description="Si gana: FREEZE al rival (ICE CUBE).",
         effects=[{"type": "APPLY_STATUS", "when": "win", "status": "FREEZE"}]),
    card(id="lullaby", name="Lullaby", short="LLB", card_type="SPECIAL", category=CATEGORY_SPECIAL,
         description="Si tu acción principal hace HIT: SLEEP al rival.",
         effects=[{"type": "APPLY_STATUS", "when": "special", "status": "SLEEP", "if_hit": True}]),
    # --- Hospital ------------------------------------------------------------------
    card(id="ice_shard", name="Ice Shard", short="ICS", card_type="MAGIC", category=CATEGORY_SPECIAL,
         damage=10, element="ICE",
         description="Como Magic, con elemento ICE (sin estados)."),
    card(id="taunt", name="Taunt", short="TNT", card_type="SPECIAL", category=CATEGORY_SPECIAL,
         description="Provocas al rival: +10 puntos de Estilo. Nada más.",
         effects=[{"type": "GAIN_STYLE", "when": "special", "amount": 10}]),
]

# Cartas EXCLUSIVAS de enemigos: el motor las usa como cualquier otra, pero no
# salen en el catálogo del editor ni se aceptan en los mazos del jugador.
ENEMY_CARD_DATA = [
    # Elemental Wolf: cambian su afinidad elemental (pasiva elemental_affinity)
    card(id="infernal_shift", name="Infernal Shift", short="INF", card_type="SPECIAL", category=CATEGORY_SPECIAL,
         exclusive_to="elemental_wolf",
         description="Al revelar: pasa a MODO FUEGO.",
         effects=[{"type": "SET_AFFINITY", "when": "special", "element": "FIRE"}]),
    card(id="glacial_shift", name="Glacial Shift", short="GLC", card_type="SPECIAL", category=CATEGORY_SPECIAL,
         exclusive_to="elemental_wolf",
         description="Al revelar: pasa a MODO HIELO.",
         effects=[{"type": "SET_AFFINITY", "when": "special", "element": "ICE"}]),
    card(id="flame_fang", name="Flame Fang", short="FFG", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10, element="FIRE", exclusive_to="elemental_wolf",
         description="ATTACK de FUEGO. Al jugarla pasa a MODO FUEGO.",
         effects=[{"type": "SET_AFFINITY", "when": "play", "element": "FIRE"}]),
    card(id="frost_fang", name="Frost Fang", short="FRF", card_type="ATTACK", category=CATEGORY_SPECIAL,
         damage=10, element="ICE", exclusive_to="elemental_wolf",
         description="ATTACK de HIELO. Al jugarla pasa a MODO HIELO.",
         effects=[{"type": "SET_AFFINITY", "when": "play", "element": "ICE"}]),
]

CARDS = {d["id"]: d for d in CARD_DATA + ENEMY_CARD_DATA}
PLAYER_CARDS = {d["id"] for d in CARD_DATA}     # las que el jugador puede poner en sus mazos

DECKS = {
    # Mazo por defecto: las tres defensas distintas y dos formas de recuperar Stability
    "duelo": ["attack", "attack", "break", "break", "guard", "perfect_guard", "unbreakable_guard",
              "revenge", "overdrive", "recover"],
    # Mazo inicial del primer documento de diseño
    "starter": ["attack", "attack", "attack", "guard", "guard", "break", "break",
                "perfect_guard", "revenge", "overdrive"],
    # Para trastear con todos los efectos
    "laboratorio": ["unbreakable_guard", "break_guard", "heavy_blow", "crescendo", "drain",
                    "focus", "feint", "iron_stance", "desperation", "overdrive"],
    # Para probar los cinco Status Effects (python main.py --deck estados)
    "estados": ["attack", "break", "guard", "searing_break", "venom_strike", "stun_guard",
                "frost_guard", "lullaby", "recover", "attack"],
    # Para probar MAGIC y FLAME (python main.py --deck arcano)
    "arcano": ["magic", "magic", "fire_bolt", "attack", "break", "guard", "guard",
               "flame", "flame", "recover"],
    # Para el hospital: FUEGO e HIELO para aprovechar la debilidad del Elemental Wolf
    "elemental": ["attack", "attack", "fire_bolt", "ice_shard", "ice_shard", "break", "guard",
                  "perfect_guard", "recover", "taunt"],
}

# Mazos de los enemigos (no salen en los menús del jugador). El mapa los nombra
# en "deck" (entities/enemy.py).
ENEMY_DECKS = {
    "security_droid": ["guard", "guard", "perfect_guard", "iron_stance", "break", "break", "break_guard",
                       "attack", "drain", "recover"],
    "elemental_wolf": ["flame_fang", "flame_fang", "frost_fang", "frost_fang", "infernal_shift",
                       "glacial_shift", "guard", "perfect_guard", "break", "recover"],
    # Lobos del hospital (piso 2 y piso 3): atacan con su elemento
    "fire_wolf": ["attack", "attack", "fire_bolt", "fire_bolt", "flame", "break", "break",
                  "guard", "perfect_guard", "recover"],
    "ice_wolf": ["attack", "attack", "ice_shard", "ice_shard", "frost_guard", "break", "break",
                 "guard", "perfect_guard", "recover"],
}


def make_card(card_id):
    """Crea una instancia nueva de la carta (cada copia del mazo es independiente)."""
    if card_id not in CARDS:
        raise KeyError(f"Carta desconocida: {card_id}")
    return Card(**copy.deepcopy(CARDS[card_id]))


def make_deck_cards(deck_name):
    """Mazo del jugador (DECKS) o, si no existe, de un enemigo (ENEMY_DECKS)."""
    ids = DECKS[deck_name] if deck_name in DECKS else ENEMY_DECKS[deck_name]
    return [make_card(cid) for cid in ids]
