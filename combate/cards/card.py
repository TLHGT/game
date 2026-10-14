"""Definición de carta.

Cuatro responsabilidades independientes:

    TIPO        card_type           ATTACK / MAGIC / GUARD / BREAK  -> ¿contra qué gana?
                                    (MAGIC se enfrenta como ATTACK: RulesConfig.MATCHUP_AS)
    INICIATIVA  has_initiative      ¿mantiene la secuencia viva tras resolver?
    RESULTADO   damage, generates_hit, causes_instability, recovers_stability
                                    -> qué pasa SI ESTA CARTA GANA
                (damage y generates_hit son independientes: puede haber cartas
                 que hagan daño sin sumar hit o que sumen hit sin hacer daño)
    EFECTOS     effects             todo lo demás (data-driven, cards/card_effects.py)
    DAÑO        damage_channel, element   de dónde viene el daño (físico/mágico, FIRE...)
                                    No deciden quién gana ni aplican estados.

El motor nunca deduce nada del tipo: un ATTACK sin iniciativa o un GUARD que
desestabiliza son igual de válidos. PASS se representa como None.
"""
from dataclasses import dataclass, field

CATEGORY_BASIC = "basic"        # solo para la UI: las básicas no muestran descripción
CATEGORY_SPECIAL = "special"


@dataclass
class Card:
    id: str
    name: str
    description: str = ""
    card_type: str = None             # "ATTACK" | "MAGIC" | "GUARD" | "BREAK" | "SPECIAL"
    has_initiative: bool = False
    damage: int = 0                   # al ganar: daño normal de la interacción
    generates_hit: bool = False       # al ganar: +1 hit de combo
    causes_instability: bool = False  # al ganar: el rival queda UNSTABLE
    recovers_stability: bool = False  # al ganar: quien la juega vuelve a STABLE
    priority: int = 0                 # desempate tras tipo y Stability
    effects: list = field(default_factory=list)
    play_condition: str = None        # None | "unstable" | "stable"
    category: str = CATEGORY_BASIC
    short: str = ""                   # abreviatura (ATK, GRD...)
    # Daño: canal y elemento son propiedades separadas del tipo de acción. Un
    # elemento NO aplica estados: eso solo lo hace un efecto APPLY_STATUS.
    damage_channel: str = None        # "physical" | "magic" | None
    element: str = None               # "FIRE", "ICE", "LIGHTNING"... o None
    # Definitiva de Estilo: copia temporal de una carta normal. No está en la mano
    # ni en el mazo y no cambia ninguna regla (game/style.py).
    is_ultimate: bool = False
    # Carta exclusiva de un enemigo (id de su personaje): no sale en el catálogo
    # ni se puede poner en los mazos del jugador (cards/card_database.py: ENEMY_CARD_DATA).
    exclusive_to: str = None

    @property
    def is_special(self):
        """SPECIAL: no es acción principal ni entra en el matchup; acompaña a una."""
        return self.card_type == "SPECIAL"

    def effects_when(self, when):
        return [e for e in self.effects if e.get("when") == when]

    def has_effect(self, effect_type, when=None):
        return any(e["type"] == effect_type and (when is None or e.get("when") == when)
                   for e in self.effects)

    def can_play(self, player, cost=0):
        """¿Puede `player` elegir esta carta pagando `cost`? El coste NO es de la
        carta: lo calcula el motor según la interacción (CombatEngine.play_cost)."""
        if player.mana < cost:
            return False
        if self.play_condition == "unstable" and player.stable:
            return False
        if self.play_condition == "stable" and not player.stable:
            return False
        return True

    def __repr__(self):
        return f"Card({self.id})"


def has_initiative(card):
    """PASS (None) nunca tiene iniciativa. Las SPECIAL tampoco cuentan nunca."""
    return card is not None and not card.is_special and card.has_initiative
