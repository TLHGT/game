"""Categoría SPECIAL y carta RECOVER.

SPECIAL: acompaña a la acción principal (ATTACK/GUARD/BREAK/PASS), máx. 1 por
interacción, no entra en el matchup, nunca tiene iniciativa, cuesta siempre
SPECIAL_MANA_COST y se resuelve ANTES del matchup.
"""
import unittest

from helpers import PASS, Phase, engine_with_hands, make_card

from combate.cards.card_database import DECKS
from combate.game.combat import CombatEngine
from combate.game.config import DEFAULT_DECKS, RULES
from combate.game.rules import DRAW, WIN


def pick(e, i, main, special=None):
    """Elige acción principal (id o PASS) + SPECIAL opcional (id) y confirma."""
    hand = e.players[i].hand
    if special:
        k = next(k for k, c in enumerate(hand) if c.id == special)
        assert e.select(i, k), f"No se pudo elegir la SPECIAL {special}"
    if main == PASS:
        assert e.select(i, PASS)
    else:
        k = next(k for k, c in enumerate(hand) if c.id == main and not c.is_special)
        assert e.select(i, k), f"No se pudo elegir {main}"
    return e.confirm(i)


def resolve(e, p1, p2):
    """p1/p2: (main, special). Juega y se para en CARD_RESOLUTION."""
    assert pick(e, 0, *p1) and pick(e, 1, *p2)
    e.advance()
    return e.result


def to_interaction_2(e):
    """ATTACK = ATTACK (empate con iniciativa) para llegar a la 2ª interacción."""
    resolve(e, ("attack", None), ("attack", None))
    while e.phase != Phase.CARD_SELECTION:
        e.advance()
    assert e.interaction_number == 2


class TestRecoverBasic(unittest.TestCase):
    def test_card_definition(self):
        rc = make_card("recover")
        self.assertTrue(rc.is_special)
        self.assertEqual(rc.card_type, "SPECIAL")
        self.assertFalse(rc.has_initiative)
        self.assertFalse(rc.generates_hit)
        self.assertEqual(rc.damage, 0)
        self.assertEqual(rc.effects, [{"type": "RECOVER_STABILITY", "when": "special"}])

    def test_unstable_becomes_stable(self):
        e = engine_with_hands(["attack", "recover"], ["guard"], stable=(False, True))
        r = resolve(e, ("attack", "recover"), ("guard", None))
        self.assertIn("PLAYER 1: RECOVER -> STABLE", r.special_lines)
        self.assertTrue(e.players[0].stable)

    def test_stable_stays_stable_and_still_pays(self):
        e = engine_with_hands(["attack", "recover"], ["guard"], mana=(3, 3))
        r = resolve(e, ("attack", "recover"), ("guard", None))
        self.assertTrue(e.players[0].stable)
        self.assertEqual(e.players[0].mana, 2, "El Mana se consume aunque no cambie nada")
        self.assertIn("PLAYER 1: RECOVER (ya estaba STABLE)", r.special_lines)

    def test_recover_card_leaves_hand(self):
        e = engine_with_hands(["attack", "recover", "guard"], ["guard"])
        resolve(e, ("attack", "recover"), ("guard", None))
        self.assertEqual([c.id for c in e.players[0].hand], ["guard"])


class TestCost(unittest.TestCase):
    def test_costs_one_in_interaction_1(self):
        e = engine_with_hands(["attack", "recover"], ["guard"], mana=(3, 3))
        r = resolve(e, ("attack", "recover"), ("guard", None))
        self.assertEqual(r.mana_paid[0], 1, "ATTACK gratis + RECOVER 1 = 1 en total")

    def test_costs_one_in_interaction_2(self):
        e = engine_with_hands(["attack", "attack", "recover"], ["attack", "guard"], mana=(3, 3))
        to_interaction_2(e)
        self.assertEqual(e.play_cost(0, make_card("recover")), 1)
        r = resolve(e, (PASS, "recover"), ("guard", None))
        self.assertEqual(r.mana_paid[0], 1)

    def test_costs_one_in_any_interaction(self):
        e = engine_with_hands(["attack"], ["guard"])
        for n in (1, 2, 3, 7):
            e.interaction_number = n
            self.assertEqual(e.play_cost(0, make_card("recover")), RULES.SPECIAL_MANA_COST, f"interacción {n}")

    def test_pass_plus_recover_costs_one(self):
        e = engine_with_hands(["recover", "guard"], ["guard"], mana=(3, 3))
        r = resolve(e, (PASS, "recover"), ("guard", None))
        self.assertEqual(r.mana_paid[0], 1)

    def test_attack_plus_recover_interaction_2_costs_two(self):
        e = engine_with_hands(["attack", "attack", "recover"], ["attack", "guard"], mana=(3, 3))
        to_interaction_2(e)
        r = resolve(e, ("attack", "recover"), ("guard", None))
        self.assertEqual(r.mana_paid[0], 2)
        self.assertEqual(e.players[0].mana, 1)


class TestResolution(unittest.TestCase):
    def test_applied_before_matchup(self):
        """J1 UNSTABLE con RECOVER + ATTACK vs ATTACK: se resuelve STABLE vs STABLE -> DRAW."""
        e = engine_with_hands(["attack", "recover"], ["attack"], stable=(False, True))
        r = resolve(e, ("attack", "recover"), ("attack", None))
        self.assertEqual(r.outcome, DRAW, "Sin Recover, J2 habría ganado por Stability")
        self.assertIn("AMBOS STABLE", r.lines)

    def test_without_recover_unstable_loses_tiebreak(self):
        e = engine_with_hands(["attack", "recover"], ["attack"], stable=(False, True))
        r = resolve(e, ("attack", None), ("attack", None))
        self.assertEqual((r.outcome, r.winner), (WIN, 1))

    def test_no_extra_interaction(self):
        e = engine_with_hands(["attack", "recover", "guard"], ["guard", "guard"])
        r = resolve(e, ("attack", "recover"), ("guard", None))
        self.assertEqual(r.interaction_number, 1)
        while e.phase != Phase.CARD_SELECTION:
            e.advance()
        self.assertEqual(e.interaction_number, 2, "La SPECIAL no gasta una interacción propia")

    def test_no_initiative_hit_combo_or_damage(self):
        e = engine_with_hands(["recover", "guard"], ["guard"], stable=(False, True))
        r = resolve(e, (PASS, "recover"), ("guard", None))
        self.assertFalse(r.continues, "PASS + RECOVER vs GUARD: nadie tiene iniciativa")
        self.assertEqual((r.hit_generated, r.damage_events), (0, []))
        self.assertEqual([p.combo_hits for p in e.players], [0, 0])
        self.assertEqual([p.hp for p in e.players], [RULES.MAX_HP, RULES.MAX_HP])

    def test_recover_pass_vs_pass_ends(self):
        e = engine_with_hands(["recover"], ["guard"])
        r = resolve(e, (PASS, "recover"), (PASS, None))
        self.assertFalse(r.continues)
        e.advance()
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_hit_after_recover_destabilizes_again(self):
        """Recover es inmediato; si luego recibe un hit, la Stability normal sigue actuando."""
        e = engine_with_hands(["guard", "recover"], ["break"], stable=(False, True))
        resolve(e, ("guard", "recover"), ("break", None))
        self.assertFalse(e.players[0].stable)

    def test_only_one_special_per_interaction(self):
        e = engine_with_hands(["attack", "recover", "recover"], ["guard"], mana=(3, 3))
        self.assertTrue(e.select(0, 1))
        self.assertTrue(e.select(0, 2))            # cambia de SPECIAL, no suma otra
        self.assertIs(e.special_selection[0], e.players[0].hand[2])
        self.assertTrue(e.select(0, 2))            # volver a pulsarla la quita
        self.assertIsNone(e.special_selection[0])

    def test_special_never_used_as_main_action(self):
        e = engine_with_hands(["recover"], ["guard"])
        self.assertEqual(e.selection[0], PASS, "Solo tiene una SPECIAL: la acción principal es PASS")
        self.assertFalse(e.confirmed[0], "...pero puede añadir la SPECIAL antes de confirmar")


class TestNotEnoughMana(unittest.TestCase):
    def test_one_mana_recover_attack_interaction_2_invalid(self):
        e = engine_with_hands(["attack", "attack", "recover"], ["attack", "guard"], mana=(1, 3))
        to_interaction_2(e)
        k_rec = next(k for k, c in enumerate(e.players[0].hand) if c.is_special)
        k_atk = next(k for k, c in enumerate(e.players[0].hand) if c.id == "attack")
        self.assertTrue(e.select(0, k_rec))
        self.assertFalse(e.select(0, k_atk), "1 Mana no paga RECOVER (1) + ATTACK (1)")
        self.assertFalse(e.can_play(0, e.players[0].hand[k_atk]))

    def test_one_mana_recover_pass_valid(self):
        e = engine_with_hands(["attack", "attack", "recover"], ["attack", "guard"], mana=(1, 3))
        to_interaction_2(e)
        self.assertTrue(pick(e, 0, PASS, "recover"))
        self.assertEqual(e.players[0].mana, 0)

    def test_mana_never_negative(self):
        e = engine_with_hands(["attack", "recover"], ["guard"], mana=(0, 3))
        k_rec = next(k for k, c in enumerate(e.players[0].hand) if c.is_special)
        self.assertFalse(e.select(0, k_rec), "Con 0 Mana no se puede elegir RECOVER")
        self.assertTrue(pick(e, 0, "attack"))      # la 1ª interacción sigue siendo gratis
        self.assertEqual(e.players[0].mana, 0)


class TestDeck(unittest.TestCase):
    def test_default_deck_has_10_with_recover(self):
        for name in DEFAULT_DECKS:
            self.assertEqual(len(DECKS[name]), RULES.DECK_SIZE)
            self.assertIn("recover", DECKS[name])

    def test_recover_is_drawn_normally(self):
        """Con el mazo por defecto, Recover acaba saliendo por el robo normal."""
        seen = False
        for seed in range(20):
            e = CombatEngine(seed=seed)
            e.run_auto()
            if any(c.id == "recover" for p in e.players for c in p.hand):
                seen = True
                self.assertEqual(len(e.players[0].hand), RULES.MAX_HAND_SIZE)
                break
        self.assertTrue(seen)

    def test_recover_can_be_redrawn_for_free(self):
        e = CombatEngine(seed=0)
        e.run_auto()
        p = e.players[0]
        p.hand[0] = make_card("recover")
        mana = p.mana
        self.assertTrue(e.redraw(0, 0))
        self.assertEqual(p.mana, mana, "Los cambios no gastan Mana")
        self.assertEqual(len(p.hand), RULES.MAX_HAND_SIZE)


if __name__ == "__main__":
    unittest.main()
