"""Estados alterados (Status Effects): BURN, POISON, PARALYZE, FREEZE, SLEEP.

Sin Pygame y sin azar. Cada jugador tiene COMO MÁXIMO un estado
(`Player.status`). Los estados son independientes de la Stability, la
iniciativa, el Mana y los elementos: solo los aplica un efecto explícito
(`APPLY_STATUS` en cards/card_effects.py).

Cada estado es una definición (StatusDefinition) con ganchos que el motor
llama UNA sola vez por transición, desde un único sitio de game/combat.py:

    on_apply              al aplicarse (contadores iniciales)
    on_turn_start         CombatEngine._turn_start         (BURN daña, POISON descuenta, SLEEP despierta)
    on_interaction_start  CombatEngine._interaction_start  (POISON daña)
    on_interaction_end    final de CombatEngine._apply_result (PARALYZE expira, SLEEP descuenta)
    on_hit_received       tras confirmar un HIT real        (SLEEP despierta)

Un estado recién aplicado está "fresh" hasta que empieza la siguiente
interacción: no bloquea acciones ni cuenta la interacción que lo aplicó.

En este juego el turno es COMÚN a los dos jugadores (selección simultánea),
así que cada TURN_START es un "turno propio" de ambos.

`host` es el CombatEngine: los ganchos solo usan host.rules,
host.status_damage(player, amount, status) y host.expire_status(player, status, texto).
"""
from dataclasses import dataclass
from enum import Enum


class StatusId(str, Enum):
    BURN = "BURN"
    POISON = "POISON"
    PARALYZE = "PARALYZE"
    FREEZE = "FREEZE"
    SLEEP = "SLEEP"


# Inmunidad cruzada: mientras uno de estos esté activo, el jugador es inmune a
# TODOS ellos (evita encadenar PARALYZE y SLEEP). Termina con el estado.
PARALYZE_SLEEP_IMMUNITY = frozenset({StatusId.PARALYZE, StatusId.SLEEP})

# Qué puede hacer un jugador con el estado activo
LOCK_PASS = "pass"        # acción principal forzada a PASS, sin SPECIAL
LOCK_FREEZE = "freeze"    # solo acciones de estado: BREAK ICE o WAIT

# Acciones de estado del jugador congelado (no son cartas ni entran en el matchup)
BREAK_ICE = "BREAK_ICE"
WAIT = "WAIT"
STATUS_ACTIONS = (BREAK_ICE, WAIT)

# Resultados de intentar aplicar un estado
APPLIED, REPLACED, REFRESHED, IMMUNE, BLOCKED = "applied", "replaced", "refreshed", "immune", "blocked"


@dataclass
class StatusEffect:
    """Estado activo de un jugador. Solo datos: la lógica está en su definición."""
    id: StatusId
    turns_left: int = 0
    interactions_left: int = 0
    cube_hp: int = 0
    cube_max: int = 0
    fresh: bool = True        # aplicado en la interacción en curso: aún no cuenta

    @property
    def definition(self):
        return STATUS_DEFS[self.id]

    @property
    def name(self):
        return self.definition.name

    @property
    def lock(self):
        """Restricción de acciones; un estado recién aplicado no bloquea nada aún."""
        return None if self.fresh else self.definition.lock

    def counter_text(self):
        return self.definition.counter_text(self)


class StatusDefinition:
    id = None
    name = ""
    short = ""                # abreviatura para la UI (no depende del color)
    lock = None               # None | LOCK_PASS | LOCK_FREEZE
    blocks = frozenset()      # estados que NO se pueden aplicar mientras este está activo
    description = ""

    def on_apply(self, st, rules):
        pass

    def on_turn_start(self, st, player, host):
        pass

    def on_interaction_start(self, st, player, host):
        pass

    def on_interaction_end(self, st, player, host):
        pass

    def on_hit_received(self, st, player, host):
        pass

    def counter_text(self, st):
        return ""


class Burn(StatusDefinition):
    id, name, short = StatusId.BURN, "BURN", "BRN"
    description = "Daño al empezar cada turno"

    def on_apply(self, st, rules):
        st.turns_left = rules.BURN_TURNS

    def on_turn_start(self, st, player, host):
        host.status_damage(player, host.rules.BURN_DAMAGE, st)
        st.turns_left -= 1
        if st.turns_left <= 0:
            host.expire_status(player, st, "BURN ha terminado")

    def counter_text(self, st):
        return f"{st.turns_left} turno{'s' if st.turns_left != 1 else ''}"


class Poison(StatusDefinition):
    """La duración se mide en turnos; el daño se activa en cada interacción."""
    id, name, short = StatusId.POISON, "POISON", "PSN"
    description = "Daño al empezar cada interacción"

    def on_apply(self, st, rules):
        st.turns_left = rules.POISON_TURNS

    def on_turn_start(self, st, player, host):
        st.turns_left -= 1
        if st.turns_left <= 0:
            host.expire_status(player, st, "POISON ha terminado")

    def on_interaction_start(self, st, player, host):
        host.status_damage(player, host.rules.POISON_DAMAGE, st)

    def counter_text(self, st):
        return f"{st.turns_left} turno{'s' if st.turns_left != 1 else ''}"


class Paralyze(StatusDefinition):
    id, name, short = StatusId.PARALYZE, "PARALYZED", "PRZ"
    lock = LOCK_PASS
    blocks = PARALYZE_SLEEP_IMMUNITY
    description = "PASS obligatorio en la siguiente interacción"

    def on_apply(self, st, rules):
        st.interactions_left = rules.PARALYZE_INTERACTIONS

    def on_interaction_end(self, st, player, host):
        st.interactions_left -= 1
        if st.interactions_left <= 0:
            host.expire_status(player, st, "PARALYZE ha terminado")

    def counter_text(self, st):
        return _interactions(st.interactions_left)


class Freeze(StatusDefinition):
    """Atrapado en un ICE CUBE que absorbe el daño. Termina al romperse el cubo
    (lo gestiona CombatEngine._deal_damage), nunca por turnos."""
    id, name, short = StatusId.FREEZE, "FREEZE", "FRZ"
    lock = LOCK_FREEZE
    description = "ICE CUBE absorbe el daño · BREAK ICE o WAIT"

    def on_apply(self, st, rules):
        st.cube_hp = st.cube_max = rules.ICE_CUBE_HP

    def counter_text(self, st):
        return f"ICE CUBE {st.cube_hp}/{st.cube_max}"


class Sleep(StatusDefinition):
    id, name, short = StatusId.SLEEP, "SLEEP", "SLP"
    lock = LOCK_PASS
    blocks = PARALYZE_SLEEP_IMMUNITY
    description = "PASS obligatorio · despierta con un HIT"

    def on_apply(self, st, rules):
        st.interactions_left = rules.SLEEP_INTERACTIONS

    def _wake(self, st, player, host):
        host.expire_status(player, st, f"{player.name} ha despertado")

    def on_turn_start(self, st, player, host):
        self._wake(st, player, host)

    def on_interaction_end(self, st, player, host):
        st.interactions_left -= 1
        if st.interactions_left <= 0:
            self._wake(st, player, host)

    def on_hit_received(self, st, player, host):
        self._wake(st, player, host)

    def counter_text(self, st):
        return _interactions(st.interactions_left)


def _interactions(n):
    return f"{n} interacción" if n == 1 else f"{n} interacciones"


STATUS_DEFS = {d.id: d for d in (Burn(), Poison(), Paralyze(), Freeze(), Sleep())}


def try_apply_status(player, status_id, rules):
    """Regla de aplicación y reemplazo. Devuelve (resultado, estado anterior o None).

        1. inmune (propiedad del jugador)          -> IMMUNE, no cambia nada
        2. el estado activo lo bloquea (`blocks`: PARALYZE y SLEEP se bloquean
           entre sí y a sí mismos)            -> BLOCKED, no cambia nada
        3. si no: se elimina el anterior y se aplica el nuevo con contadores
           iniciales (REPLACED si era otro, REFRESHED si era el mismo).
    """
    status_id = StatusId(status_id)
    previous = player.status
    if status_id in player.immunities:
        return IMMUNE, previous
    if previous is not None and status_id in previous.definition.blocks:
        return BLOCKED, previous
    new = StatusEffect(status_id)
    new.definition.on_apply(new, rules)
    player.status = new
    if previous is None:
        return APPLIED, None
    return (REFRESHED if previous.id == status_id else REPLACED), previous
