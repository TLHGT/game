"""Personajes jugables y sus pasivas. Sin Pygame.

    Character   datos: id, nombre, descripción, qué pasiva usa y con qué configuración
    Passive     reglas de la pasiva (una clase por tipo de pasiva, registrada con @passive)
                Cada jugador recibe SU instancia al empezar la partida (Player.passive).

Ganchos que llama el motor (todos opcionales; la clase base no hace nada):
    damage_bonus_pct(event, engine, r)   % extra al daño que CAUSA el dueño, UNA vez
                                         por evento (CombatEngine._apply_passive)
    incoming_damage(event, engine, r)    el dueño RECIBE un daño de combate: puede
                                         cambiar event.amount o curarse (event.heal = True)
    on_turn_start(owner, engine)         al empezar cada turno (tras los estados)
    after_interaction(owner, engine, r)  al final de cada interacción (tras los estados de las cartas)
    set_affinity(element)                lo usan cartas con el efecto SET_AFFINITY
El daño de los estados (BURN, POISON) no pasa por los ganchos de daño, y los
datos de las cartas nunca se modifican.

Personajes JUGABLES (playable=True): los que el jugador puede elegir (Hero,
Blaze). Cada uno tiene además una habilidad de AVENTURA para la exploración
(`adventure`): Blaze quema paredes de hojas, Hero salta a lugares altos.
Los enemigos son personajes como los demás, con su pasiva, pero
playable=False: nunca salen en los menús de selección.

Añadir un personaje = register_character(Character(...)) con una pasiva
existente o una nueva clase @passive. El motor no cambia.

Redondeo: el daño es entero; un porcentaje se redondea al entero más cercano
y los medios hacia arriba (10 +5% = 10.5 -> 11). Ver apply_pct.
"""
from dataclasses import dataclass, field

from combate.game.rules import DAMAGE_INTERACTION, DAMAGE_MEGA_COMBO
from combate.game.status import StatusId

PASSIVES = {}
CHARACTERS = {}


def passive(passive_id):
    def register(cls):
        cls.id = passive_id
        PASSIVES[passive_id] = cls
        return cls
    return register


def apply_pct(amount, pct):
    """amount + pct %, entero, medios hacia arriba (sin flotantes)."""
    return (amount * (100 + pct) + 50) // 100


class Passive:
    id = ""
    name = ""

    def __init__(self, **config):
        self.config = config

    def summary(self):
        """Efecto resumido (selección de personaje y ficha)."""
        return ""

    def damage_bonus_pct(self, event, engine, r):
        """% extra para un evento de daño que causa el dueño de la pasiva. 0 = nada."""
        return 0

    def status_text(self, player, engine):
        """Progreso o recordatorio para el HUD durante el combate."""
        return self.summary()

    def incoming_damage(self, event, engine, r):
        """El dueño recibe `event` (daño de combate). Puede cambiar event.amount
        o marcar event.heal = True para curarse esa cantidad en lugar de perderla."""

    def on_turn_start(self, owner, engine):
        pass

    def after_interaction(self, owner, engine, r):
        pass


@passive("fire_affinity")
class FireAffinity(Passive):
    """Las cartas que hacen daño de un elemento (FIRE) hacen un % más de daño directo."""
    name = "Afinidad ígnea"

    def summary(self):
        return f"Cartas de {self.config['element']}: +{self.config['bonus_pct']}% de daño"

    def damage_bonus_pct(self, event, engine, r):
        if event.kind == DAMAGE_INTERACTION and event.amount > 0 and event.element == self.config["element"]:
            return self.config["bonus_pct"]
        return 0

    def status_text(self, player, engine):
        return f"{self.name}: {self.config['element']} +{self.config['bonus_pct']}%"


@passive("consecutive_momentum")
class ConsecutiveMomentum(Passive):
    """Bonificación según el nº de HIT consecutivos. Lee el combo del motor
    (CombatEngine.combo_after_hit): no lleva un contador propio."""
    name = "Impulso consecutivo"

    def hit_bonus(self, step):
        return self.config["hit_bonus_pct"].get(step, 0)

    def summary(self):
        steps = " · ".join(f"{n}º HIT +{pct}%" for n, pct in sorted(self.config["hit_bonus_pct"].items()))
        return f"{steps} · MEGA COMBO +{self.config['mega_bonus_pct']}%"

    def damage_bonus_pct(self, event, engine, r):
        if event.kind == DAMAGE_MEGA_COMBO:
            return self.config["mega_bonus_pct"]
        if event.kind == DAMAGE_INTERACTION and r.hit_generated > 0:
            step = engine.combo_after_hit(event.source, r.hit_generated)
            event.combo_step = step
            return self.hit_bonus(step)
        return 0            # daño sin HIT: no avanza ni bonifica

    def status_text(self, player, engine):
        nxt = min(player.combo_hits + 1, engine.rules.MAX_COMBO_HITS)
        text = f"combo {player.combo_hits}/{engine.rules.MAX_COMBO_HITS} · próximo HIT +{self.hit_bonus(nxt)}%"
        if nxt == engine.rules.MAX_COMBO_HITS:
            text += f" · MEGA +{self.config['mega_bonus_pct']}%"
        return text


def pct_of(amount, tenths_pct):
    """`tenths_pct` décimas de % de `amount`, entero, medios hacia arriba (sin flotantes).
    pct_of(100, 5) = 0.5% de 100 = 0.5 -> 1."""
    return (amount * tenths_pct + 500) // 1000


@passive("undead")
class Undead(Passive):
    """Cada HIT recibido deja una marca (no se pierden en todo el combate). Al empezar
    cada turno se cura marcas x `heal_tenths_pct` décimas de % de su vida máxima
    (config 5 = 0.5% por marca). Un golpe con 2 HIT (Break Guard) deja 2 marcas."""
    name = "Undead"

    def __init__(self, **config):
        super().__init__(**config)
        self.marks = 0

    def heal_amount(self, owner):
        return pct_of(owner.max_hp, self.marks * self.config["heal_tenths_pct"])

    def summary(self):
        pct = self.config["heal_tenths_pct"] / 10
        return (f"Cada HIT recibido le da una marca. Al empezar cada turno se cura "
                f"{pct:g}% de su vida máxima por marca")

    def after_interaction(self, owner, engine, r):
        if r.received_hit[owner.index] and r.hit_generated:
            self.marks += r.hit_generated
            engine.passive_note(f"{owner.name}: UNDEAD +{r.hit_generated} marca -> {self.marks}")

    def on_turn_start(self, owner, engine):
        amount = self.heal_amount(owner)
        if amount:
            engine.passive_heal(owner.index, amount, f"UNDEAD ({self.marks} marcas)")

    def status_text(self, player, engine):
        return f"marcas {self.marks} · +{self.heal_amount(player)} HP por turno"


ELEMENT_NAMES = {"FIRE": "FUEGO", "ICE": "HIELO"}
OPPOSITE_ELEMENT = {"FIRE": "ICE", "ICE": "FIRE"}


@passive("security_alert")
class SecurityAlert(Passive):
    """Cada `every` turnos emite una señal de alerta: el rival queda UNSTABLE."""
    name = "Alerta"

    def summary(self):
        return f"Cada {self.config['every']} turnos lanza una señal de alerta: el rival queda UNSTABLE"

    def turns_left(self, engine):
        every = self.config["every"]
        return every - (engine.turn % every) if engine.turn % every else 0

    def on_turn_start(self, owner, engine):
        if engine.turn % self.config["every"] == 0:
            engine.passive_alert(owner.index)

    def status_text(self, player, engine):
        left = self.turns_left(engine)
        return "¡ALERTA ESTE TURNO!" if left == 0 else f"alerta en {left} turno{'s' if left > 1 else ''}"


@passive("element_ward")
class ElementWard(Passive):
    """Elemento fijo (lobos de fuego y de hielo del hospital), solo contra daño de cartas:

        - Su MISMO elemento le cura esa cantidad.
        - El elemento CONTRARIO le hace el daño normal (x1).
        - Sin elemento (o cualquier otro elemento): x0.5 (resist_pct = 50).
    El Mega Combo no es daño de una carta: le hace el daño normal.
    """

    def __init__(self, **config):
        super().__init__(**config)
        self.element = config["element"]
        self.name = config.get("name", f"Elemento {ELEMENT_NAMES[self.element].lower()}")

    def summary(self):
        own, opp = ELEMENT_NAMES[self.element], ELEMENT_NAMES[OPPOSITE_ELEMENT[self.element]]
        return (f"Las cartas de {own} le curan; las de {opp} le hacen daño normal; "
                f"el resto, la mitad")

    def status_text(self, player, engine):
        return f"{self.name}: solo le daña {ELEMENT_NAMES[OPPOSITE_ELEMENT[self.element]]}"

    def incoming_damage(self, event, engine, r):
        if event.kind != DAMAGE_INTERACTION:
            return
        if event.element == self.element:
            event.heal = True
        elif event.element != OPPOSITE_ELEMENT[self.element]:
            event.weak_base = event.amount
            event.amount = apply_pct(event.amount, -self.config.get("resist_pct", 50))


@passive("elemental_affinity")
class ElementalAffinity(Passive):
    """Afinidad elemental cambiante (FUEGO / HIELO), que se cambia con cartas (SET_AFFINITY).

        - Recibir daño de su MISMO elemento le cura esa cantidad.
        - Recibir daño del elemento CONTRARIO: x1.5 (weak_pct = 50).
        - Si le hacen HIT con una carta de tipo ATTACK (contacto), el atacante
          sufre BURN (en modo FUEGO) o FREEZE (en modo HIELO).
    """
    name = "Afinidad elemental"

    def __init__(self, **config):
        super().__init__(**config)
        self.element = config.get("start", "FIRE")

    def summary(self):
        return ("Cambia entre FUEGO e HIELO. Su elemento le cura; el contrario le hace x1.5. "
                "Golpearle con ATTACK: BURN en FUEGO, FREEZE en HIELO")

    def status_text(self, player, engine):
        el = self.element
        return f"MODO {ELEMENT_NAMES[el]} · débil a {ELEMENT_NAMES[OPPOSITE_ELEMENT[el]]}"

    def set_affinity(self, element):
        changed = element != self.element
        self.element = element
        return changed

    def incoming_damage(self, event, engine, r):
        if event.kind != DAMAGE_INTERACTION or event.element not in OPPOSITE_ELEMENT:
            return
        if event.element == self.element:
            event.heal = True
        elif event.element == OPPOSITE_ELEMENT[self.element]:
            event.weak_base = event.amount
            event.amount = apply_pct(event.amount, self.config["weak_pct"])

    def after_interaction(self, owner, engine, r):
        attacker = 1 - owner.index
        card = r.cards[attacker]
        if r.received_hit[owner.index] and card is not None and card.card_type in self.config["contact_types"]:
            engine.passive_status(owner.index, attacker, self.config["contact"][self.element], r,
                                  f"{ELEMENT_NAMES[self.element]}")


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    description: str
    passive_id: str
    passive_config: dict = field(default_factory=dict)
    playable: bool = True           # False: personaje de un enemigo (no se puede elegir)
    # Habilidad de AVENTURA (exploración, no combate): qué objetos del mapa puede usar.
    # La exploración la lee en entities/adventure.py; el combate la ignora.
    adventure: str = None           # "burn" | "jump" | None
    adventure_name: str = ""
    adventure_desc: str = ""
    # AVATAR: sprite del personaje al explorar el mapa (clave de imagen en
    # render/placeholders.py o PNG en assets/: "<avatar>_<dirección>_<paso>").
    # None = el avatar por defecto ("player").
    avatar: str = None

    @property
    def passive_class(self):
        return PASSIVES[self.passive_id]

    def make_passive(self):
        """Instancia de la pasiva para UN jugador en UNA partida."""
        return self.passive_class(**self.passive_config)


def register_character(character):
    if character.id in CHARACTERS:
        raise ValueError(f"Personaje repetido: {character.id}")
    if character.passive_id not in PASSIVES:
        raise KeyError(f"Pasiva desconocida: {character.passive_id}")
    CHARACTERS[character.id] = character
    return character


def get_character(character_id):
    return None if character_id is None else CHARACTERS[character_id]


def playable_characters():
    """Ids de los personajes que puede elegir el jugador, en orden de registro."""
    return [cid for cid, ch in CHARACTERS.items() if ch.playable]


register_character(Character(
    id="blaze", name="Blaze",
    description="Especialista en daño de FUEGO.",
    passive_id="fire_affinity", passive_config={"element": "FIRE", "bonus_pct": 10},
    adventure="burn", adventure_name="Quemar",
    adventure_desc="Quema las paredes de hojas que cierran el paso.",
    avatar="avatar_blaze"))

register_character(Character(
    id="hero", name="Hero",
    description="Especialista en combos y HIT consecutivos.",
    passive_id="consecutive_momentum",
    passive_config={"hit_bonus_pct": {1: 0, 2: 5, 3: 10}, "mega_bonus_pct": 15},
    adventure="jump", adventure_name="Saltar",
    adventure_desc="Salta a lugares altos desde los puntos de salto."))      # avatar por defecto, por ahora

register_character(Character(
    id="jurgenoid", name="Jurgenoid",
    description="No muerto que se recompone con cada golpe que recibe.",
    passive_id="undead", passive_config={"heal_tenths_pct": 5},       # sin habilidad de aventura por ahora
    avatar="avatar_jurgenoid"))

# --- Personajes de enemigos (no jugables) ------------------------------------------
register_character(Character(
    id="fire_wolf", name="Fire Wolf",
    description="Lobo de fuego del hospital: el fuego le cura y solo el hielo le hace daño completo.",
    passive_id="element_ward", passive_config={"element": "FIRE", "name": "Fire element", "resist_pct": 50},
    playable=False))

register_character(Character(
    id="ice_wolf", name="Ice Wolf",
    description="Lobo de hielo del hospital: el hielo le cura y solo el fuego le hace daño completo.",
    passive_id="element_ward", passive_config={"element": "ICE", "name": "Ice element", "resist_pct": 50},
    playable=False))

register_character(Character(
    id="security_droid", name="Dron de seguridad",
    description="Robot vigilante del hospital.",
    passive_id="security_alert", passive_config={"every": 3}, playable=False))

register_character(Character(
    id="elemental_wolf", name="Elemental Wolf",
    description="Lobo espectral de fuego y hielo.",
    passive_id="elemental_affinity",
    passive_config={"start": "FIRE", "weak_pct": 50, "contact_types": ("ATTACK",),
                    "contact": {"FIRE": StatusId.BURN.value, "ICE": StatusId.FREEZE.value}},
    playable=False))
