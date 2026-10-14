"""Utilidades para montar situaciones concretas en los tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from combate.cards.card_database import make_card  # noqa: E402
from combate.game.combat import PASS, CombatEngine  # noqa: E402
from combate.game.config import RulesConfig  # noqa: E402
from combate.game.state_machine import Phase  # noqa: E402


def engine_with_hands(hand0, hand1, rules=None, mana=None, stable=(True, True), seed=1, characters=(None, None)):
    """Motor en CARD_SELECTION con las manos indicadas (listas de ids)."""
    e = CombatEngine(rules=rules or RulesConfig(), seed=seed, characters=characters)
    e.run_auto()                                   # TURN_START -> DRAW -> REDRAW
    assert e.phase == Phase.REDRAW
    for p, ids in zip(e.players, (hand0, hand1)):
        p.hand = [make_card(cid) for cid in ids]
    if mana is not None:
        for p, m in zip(e.players, mana):
            p.mana = m
    for p, s in zip(e.players, stable):
        p.stable = s
    e.finish_redraw(0)
    e.finish_redraw(1)
    settle(e)                                      # INTERACTION_START -> CARD_SELECTION
    return e


def settle(engine):
    """Avanza las fases automáticas hasta el siguiente input, pero se detiene en
    TURN_END (antes de que empiece otro turno, que reinicia combos y da Mana)."""
    while engine.sm.is_auto and engine.phase != Phase.TURN_END:
        engine.advance()


def choose(engine, player, card_id):
    """Selecciona y confirma `card_id` (o PASS) para `player`."""
    if engine.confirmed[player]:          # PASS automático (sin cartas jugables)
        assert card_id == PASS and engine.selection[player] == PASS
        return
    if card_id == PASS:
        assert engine.select(player, PASS)
    else:
        hand = engine.players[player].hand
        idx = next(i for i, c in enumerate(hand) if c.id == card_id)
        assert engine.select(player, idx), f"No se pudo elegir {card_id}"
    assert engine.confirm(player)


def play(engine, card0, card1, auto=True):
    """Juega una interacción completa y avanza hasta el siguiente input.
    Devuelve el InteractionResult."""
    choose(engine, 0, card0)
    choose(engine, 1, card1)
    result = engine.result
    if auto:
        settle(engine)
    return result


def resolve_only(engine, card0, card1):
    """Juega una interacción y se detiene en CARD_RESOLUTION: efectos, hits,
    daño, Stability y combo ya aplicados; nada de lo que viene después."""
    play(engine, card0, card1, auto=False)
    engine.advance()                    # CARD_REVEAL -> CARD_RESOLUTION
    return engine.result
