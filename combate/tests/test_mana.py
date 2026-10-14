"""Mana definitivo.

    Máx. 5 · inicio 3 · +1 al empezar cada turno · nunca se regenera durante el turno.
    Interacción 1 del turno: jugar carta = GRATIS.
    Interacción 2+:          jugar carta = 1 Mana (ATTACK, GUARD y BREAK por igual).
    PASS:                    siempre gratis y no reinicia el contador de interacciones.
    El coste se paga al CONFIRMAR, gane o pierda la carta.
"""
import unittest

from helpers import PASS, Phase, choose, engine_with_hands, play, resolve_only

from combate.cards.card import Card
from combate.game.combat import CombatEngine


def mana(e):
    return [p.mana for p in e.players]


def next_interaction(e):
    """Desde CARD_RESOLUTION avanza hasta la selección de la siguiente interacción."""
    while e.phase != Phase.CARD_SELECTION:
        e.advance()


class TestBase(unittest.TestCase):
    def test_starting_mana(self):
        e = CombatEngine(seed=1)
        e.run_auto()
        self.assertEqual(mana(e), [3, 3])

    def test_regen_each_turn_capped(self):
        e = engine_with_hands(["guard"], ["guard"], mana=(2, 4))
        play(e, "guard", "guard")                 # sin iniciativa -> fin de turno
        e.run_auto()
        self.assertEqual(e.turn, 2)
        self.assertEqual(mana(e), [3, 5])
        e = engine_with_hands(["guard"], ["guard"], mana=(5, 5))
        play(e, "guard", "guard")
        e.run_auto()
        self.assertEqual(mana(e), [5, 5], "4 -> 5, nunca 6")

    def test_mana_bounds(self):
        p = CombatEngine(seed=1).players[0]
        p.gain_mana(99)
        self.assertEqual(p.mana, p.rules.MAX_MANA)
        p.gain_mana(-99)
        self.assertEqual(p.mana, 0)

    def test_no_card_has_individual_cost(self):
        from combate.cards.card_database import CARD_DATA
        for data in CARD_DATA:
            self.assertNotIn("mana_cost", data, data["id"])


class TestInteractionCost(unittest.TestCase):
    def test_1_first_interaction_is_free(self):
        e = engine_with_hands(["attack", "guard"], ["guard", "guard"], mana=(3, 3))
        self.assertEqual(e.interaction_number, 1)
        r = resolve_only(e, "attack", "guard")
        self.assertEqual(mana(e), [3, 3])
        self.assertEqual(r.mana_paid, (0, 0))

    def test_2_second_interaction_costs_one(self):
        """El ejemplo del punto 11: 3 -> (+1 al empezar) ... aquí ya en 4; 1ª gratis; 2ª -1."""
        e = engine_with_hands(["attack", "guard", "guard"], ["guard", "guard", "guard"], mana=(4, 4))
        resolve_only(e, "attack", "guard")        # ATTACK da iniciativa: hay 2ª interacción
        self.assertEqual(mana(e), [4, 4])
        next_interaction(e)
        self.assertEqual(e.interaction_number, 2)
        resolve_only(e, "guard", "guard")
        self.assertEqual(mana(e), [3, 3])

    def test_3_all_types_cost_the_same(self):
        for card_id in ("attack", "guard", "break"):
            e = engine_with_hands(["attack", card_id], ["attack", "guard", "attack"], mana=(3, 3))
            resolve_only(e, "attack", "attack")   # empate con iniciativa: sigue
            next_interaction(e)
            r = resolve_only(e, card_id, "guard")
            self.assertEqual(r.mana_paid[0], 1, card_id)
            self.assertEqual(e.players[0].mana, 2, card_id)

    def test_4_pass_is_free(self):
        e = engine_with_hands(["attack", "attack"], ["attack", "attack"], mana=(3, 3))
        resolve_only(e, "attack", "attack")
        next_interaction(e)
        r = resolve_only(e, PASS, "attack")
        self.assertEqual(r.mana_paid, (0, 1))
        self.assertEqual(mana(e), [3, 2])

    def test_5_pass_does_not_reset_counter(self):
        """1ª: PASS vs ATTACK (gratis) · 2ª: ATTACK cuesta 1."""
        e = engine_with_hands(["attack", "attack"], ["attack", "attack"], mana=(3, 3))
        resolve_only(e, PASS, "attack")           # ATTACK tiene iniciativa: sigue
        next_interaction(e)
        self.assertEqual(e.interaction_number, 2)
        r = resolve_only(e, "attack", "attack")
        self.assertEqual(r.mana_paid, (1, 1))
        self.assertEqual(mana(e), [2, 2])

    def test_first_interaction_is_per_interaction_not_per_card(self):
        """Aunque nadie jugara carta en la 1ª, la 2ª ya cuesta (punto 10)."""
        e = engine_with_hands(["attack"], ["attack", "attack"], mana=(3, 3))
        e.players[0].hand = []                    # J1 sin cartas: PASS automático en la 1ª
        resolve_only(e, PASS, "attack")
        next_interaction(e)
        r = resolve_only(e, PASS, "attack")
        self.assertEqual(r.interaction_number, 2)
        self.assertEqual(e.players[1].mana, 2)

    def test_6_zero_mana_only_pass(self):
        e = engine_with_hands(["attack", "attack", "guard", "break"], ["attack", "attack"], mana=(1, 3))
        resolve_only(e, "attack", "attack")
        next_interaction(e)
        e.players[0].mana = 0
        for k, card in enumerate(e.players[0].hand):
            self.assertFalse(e.can_play(0, card), f"{card.card_type} no disponible con 0 Mana")
            self.assertFalse(e.select(0, k))
        self.assertTrue(e.select(0, PASS), "PASS sí está disponible")

    def test_zero_mana_auto_pass_in_new_interaction(self):
        e = engine_with_hands(["attack", "guard"], ["attack", "attack"], mana=(0, 3))
        resolve_only(e, "attack", "attack")       # 1ª gratis aunque tenga 0
        next_interaction(e)
        self.assertEqual(e.selection[0], PASS, "Con 0 Mana desde la 2ª: PASS automático")
        self.assertTrue(e.confirmed[0])

    def test_7_new_turn_resets_counter(self):
        e = engine_with_hands(["attack", "guard", "guard"], ["guard", "guard", "guard"], mana=(3, 3))
        resolve_only(e, "attack", "guard")        # T1 · interacción 1: gratis
        next_interaction(e)
        resolve_only(e, "guard", "guard")         # T1 · interacción 2: -1 y fin (sin iniciativa)
        self.assertEqual(mana(e), [2, 2])
        e.run_auto()                              # turno 2: +1 Mana
        self.assertEqual(e.turn, 2)
        self.assertEqual(mana(e), [3, 3])
        e.finish_redraw(0); e.finish_redraw(1); e.run_auto()
        self.assertEqual(e.interaction_number, 1)
        choose(e, 0, e.players[0].hand[0].id); choose(e, 1, e.players[1].hand[0].id)
        self.assertEqual(mana(e), [3, 3], "T2 · interacción 1: otra vez gratis")

    def test_8_cost_does_not_depend_on_result(self):
        for rival, outcome in (("break", "gana"), ("guard", "pierde")):
            e = engine_with_hands(["attack", "attack"], ["attack", rival], mana=(3, 3))
            resolve_only(e, "attack", "attack")
            next_interaction(e)
            resolve_only(e, "attack", rival)
            self.assertEqual(e.players[0].mana, 2, f"ATTACK {outcome}: igualmente -1")

    def test_9_both_pay_independently(self):
        e = engine_with_hands(["attack", "guard"], ["attack", "break"], mana=(3, 2))
        resolve_only(e, "attack", "attack")
        next_interaction(e)
        r = resolve_only(e, "guard", "break")
        self.assertEqual(r.mana_paid, (1, 1))
        self.assertEqual(mana(e), [2, 1])

    def test_10_pass_vs_card(self):
        e = engine_with_hands(["attack", "guard"], ["attack", "attack"], mana=(3, 3))
        resolve_only(e, "attack", "attack")
        next_interaction(e)
        resolve_only(e, PASS, "attack")
        self.assertEqual(mana(e), [3, 2])

    def test_paid_on_confirm_shown_on_reveal(self):
        """Se cobra al confirmar, pero la UI no lo enseña hasta el REVEAL."""
        e = engine_with_hands(["attack", "break"], ["attack", "guard"], mana=(2, 3))
        resolve_only(e, "attack", "attack")
        next_interaction(e)
        choose(e, 0, "break")
        self.assertEqual(e.players[0].mana, 1, "Cobrado al confirmar")
        self.assertEqual(e.displayed_mana(0), 2, "...sin delatarlo antes del REVEAL")
        choose(e, 1, "guard")                     # ambos confirman -> REVEAL
        self.assertEqual(e.displayed_mana(0), 1)

    def test_no_mana_gain_from_winning_or_losing(self):
        e = engine_with_hands(["attack", "guard"], ["break", "attack"], mana=(3, 3))
        resolve_only(e, "attack", "break")        # gana J1: nadie gana Mana
        self.assertEqual(mana(e), [3, 3])

    def test_future_cost_modifier_effect(self):
        """Las reglas especiales de Mana irán como efectos, sin romper la base."""
        pricey = Card(id="p", name="Pricey", card_type="ATTACK", has_initiative=True,
                      effects=[{"type": "MODIFY_PLAY_COST", "when": "cost", "amount": 1}])
        e = engine_with_hands(["attack"], ["guard"], mana=(3, 3))
        self.assertEqual(e.play_cost(0, pricey), 1, "1ª interacción: 0 + 1")
        e.interaction_number = 2
        self.assertEqual(e.play_cost(0, pricey), 2, "2ª interacción: 1 + 1")


if __name__ == "__main__":
    unittest.main()
