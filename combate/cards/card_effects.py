"""Efectos de carta genéricos y data-driven.

Cada efecto es una función registrada con @effect("NOMBRE") que recibe:
    data: el diccionario del efecto ({"type": ..., "amount": ...})
    ctx:  EffectContext con el motor, el dueño de la carta, el rival y las
          banderas de la resolución en curso.

Los efectos "pre" (MODIFY_RESULT, CANCEL_CARD, IGNORE_STABILITY) cambian
QUIÉN GANA y los lee game/rules.py al comparar. El resto cambia LAS
CONSECUENCIAS y se ejecuta en CombatEngine._apply_result.

Para crear un efecto nuevo: escribe la función, regístrala y úsala en
cards/card_database.py. El motor no sabe nada de cartas concretas.
"""
from dataclasses import dataclass, field

EFFECTS = {}


def effect(name):
    def register(fn):
        EFFECTS[name] = fn
        return fn
    return register


@dataclass
class EffectContext:
    engine: object
    owner: object           # Player que juega la carta
    opponent: object
    card: object
    opponent_card: object = None
    flags: dict = field(default_factory=dict)


def applies(data, opponent_card):
    """Condiciones opcionales: `vs` (tipo de la carta rival, p. ej. "MAGIC") y
    `vs_channel` (canal de daño de la carta rival, p. ej. "magic")."""
    vs, channel = data.get("vs"), data.get("vs_channel")
    if vs is not None and (opponent_card is None or opponent_card.card_type != vs):
        return False
    if channel is not None and (opponent_card is None or opponent_card.damage_channel != channel):
        return False
    return True


def run_effects(card, when, ctx):
    """Ejecuta los efectos de `card` con momento `when`. Devuelve ctx.flags."""
    if card is None:
        return ctx.flags
    for data in card.effects_when(when):
        if not applies(data, ctx.opponent_card):
            continue
        handler = EFFECTS.get(data["type"])
        if handler is None:
            raise KeyError(f"Efecto sin implementar: {data['type']}")
        handler(data, ctx)
    return ctx.flags


# ---------------------------------------------------------------------------
# Efectos que cambian QUIÉN GANA (los evalúa game/rules.py)
# ---------------------------------------------------------------------------
@effect("MODIFY_RESULT")
def _modify_result(data, ctx):
    """{"result": "win" | "draw"} contra el tipo `vs`."""


@effect("CANCEL_CARD")
def _cancel_card(data, ctx):
    """Anula la carta rival: la interacción queda en empate."""


@effect("IGNORE_STABILITY")
def _ignore_stability(data, ctx):
    """La Stability no desempata esta interacción."""


# ---------------------------------------------------------------------------
# Efectos que cambian LAS CONSECUENCIAS
# ---------------------------------------------------------------------------
@effect("RECOVER_STABILITY")
def _recover_stability(data, ctx):
    ctx.flags["recover_stability"] = True


@effect("PROTECT_STABILITY")
def _protect_stability(data, ctx):
    ctx.flags["protect_stability"] = True


@effect("CAUSE_INSTABILITY")
def _cause_instability(data, ctx):
    ctx.flags["cause_instability"] = True


@effect("ADD_HIT")
def _add_hit(data, ctx):
    ctx.flags["extra_hits"] = ctx.flags.get("extra_hits", 0) + data.get("amount", 1)


@effect("MODIFY_DAMAGE")
def _modify_damage(data, ctx):
    """Suma (o resta) daño NORMAL de la interacción."""
    ctx.flags["damage_bonus"] = ctx.flags.get("damage_bonus", 0) + data.get("amount", 0)


@effect("MODIFY_MEGA_DAMAGE")
def _modify_mega_damage(data, ctx):
    """Suma daño al Mega Combo si esta interacción lo activa."""
    ctx.flags["mega_bonus"] = ctx.flags.get("mega_bonus", 0) + data.get("amount", 0)


@effect("PROTECT_COMBO")
def _protect_combo(data, ctx):
    """El combo de quien juega la carta no se rompe aunque no haga hit."""
    ctx.flags["protect_combo"] = True


@effect("BREAK_COMBO")
def _break_combo(data, ctx):
    """Rompe el combo del rival aunque estuviera protegido."""
    ctx.flags["break_opponent_combo"] = True


@effect("MODIFY_PLAY_COST")
def _modify_play_cost(data, ctx):
    """{"when": "cost", "amount": +1/-1}: cambia lo que cuesta JUGAR esta carta,
    por encima de la regla base. Lo lee CombatEngine.play_cost; ninguna carta lo
    usa todavía."""


@effect("GAIN_MANA")
def _gain_mana(data, ctx):
    gained = ctx.owner.gain_mana(data.get("amount", 1))
    if gained:
        ctx.engine.emit("mana", ctx.owner.index, amount=gained)


@effect("REDUCE_MANA")
def _reduce_mana(data, ctx):
    lost = -ctx.opponent.gain_mana(-data.get("amount", 1))
    if lost:
        ctx.engine.emit("mana", ctx.opponent.index, amount=-lost)


@effect("APPLY_STATUS")
def _apply_status(data, ctx):
    """Aplica un estado alterado (game/status.py). No se aplica aquí: queda
    pendiente y CombatEngine._apply_pending_statuses lo aplica UNA vez, tras el
    daño y el combo, si se cumplen sus condiciones sobre el resultado REAL:

        {"type": "APPLY_STATUS", "when": "special", "status": "BURN",
         "target": "opponent",           # "opponent" (por defecto) | "self"
         "if_outcome": "win",            # opcional: "win" | "lose" | "draw"
         "if_main_type": "MAGIC",        # opcional: tipo de TU acción principal
         "if_hit": True}                 # opcional: tu acción hizo un HIT real

    Sirve en cualquier momento (`special`, `play`, `win`, `lose`); los
    momentos ya filtran el resultado y las condiciones afinan el resto."""
    ctx.flags["apply_status"] = ctx.flags.get("apply_status", []) + [dict(data)]


@effect("GAIN_STYLE")
def _gain_style(data, ctx):
    """Puntos de Estilo directos, sin ganar la interacción (Taunt)."""
    ctx.engine.gain_style(ctx.owner.index, data.get("amount", 10))


@effect("HEAL")
def _heal(data, ctx):
    """{"amount": 30}: quien juega la carta recupera HP (hasta su vida máxima). Heal, Harvest."""
    ctx.engine.card_heal(ctx.owner.index, data.get("amount", 0))


@effect("SELF_DAMAGE")
def _self_damage(data, ctx):
    """{"amount": 15}: quien juega la carta pierde HP. No es un HIT ni daño de
    interacción (no pasa por las pasivas). Void Impact."""
    ctx.engine.self_damage(ctx.owner.index, data.get("amount", 0), ctx.card.name)


@effect("SELF_UNSTABLE")
def _self_unstable(data, ctx):
    """Quien juega la carta queda UNSTABLE (se aplica en el paso de Stability,
    antes de las recuperaciones: si la carta gana y recupera Stability, vuelve a STABLE)."""
    ctx.flags["self_instability"] = True


@effect("REDUCE_MAX_MANA")
def _reduce_max_mana(data, ctx):
    """{"amount": 1}: el Mana MÁXIMO del rival baja (todo el combate; nunca de 1).
    Como APPLY_STATUS, se aplica tras el daño y admite if_outcome / if_hit."""
    ctx.flags["reduce_max_mana"] = ctx.flags.get("reduce_max_mana", []) + [dict(data)]


@effect("SET_AFFINITY")
def _set_affinity(data, ctx):
    """{"element": "FIRE" | "ICE"}: cambia la afinidad elemental de la pasiva
    del dueño (Elemental Wolf). Sin esa pasiva, no hace nada."""
    ctx.engine.set_affinity(ctx.owner.index, data["element"])


# ---------------------------------------------------------------------------
# Efectos que cambian EL FLUJO (excepciones a la regla de iniciativa)
# ---------------------------------------------------------------------------
@effect("END_SEQUENCE")
def _end_sequence(data, ctx):
    ctx.flags["end_sequence"] = True


@effect("KEEP_SEQUENCE")
def _keep_sequence(data, ctx):
    ctx.flags["keep_sequence"] = True
