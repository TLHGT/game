"""Cartas especiales y efectos data-driven."""
import unittest

from helpers import Phase, engine_with_hands, make_card, play

from combate.cards.card_database import CARD_DATA, DAMAGE_TYPES, DECKS, TYPE_DEFAULTS, card
from combate.cards.card_effects import EFFECTS
from combate.game.config import DEFAULT_DECKS, RULES
from combate.game.rules import DRAW, resolve_interaction


class TestDatabase(unittest.TestCase):
    def test_every_damage_card_declares_its_damage(self):
        damage_cards = [d for d in CARD_DATA if d["card_type"] in DAMAGE_TYPES]
        self.assertEqual(len(damage_cards), 14)
        for data in damage_cards:
            self.assertEqual(data["damage"], 10, data["id"])
            self.assertEqual(make_card(data["id"]).damage, 10, data["id"])
        for data in CARD_DATA:
            if data["card_type"] not in DAMAGE_TYPES:
                self.assertEqual(data["damage"], 0, f"{data['id']}: GUARD y SPECIAL no hacen daño")

    def test_damage_is_not_inherited_from_type(self):
        self.assertNotIn("damage", TYPE_DEFAULTS["ATTACK"])
        with self.assertRaises(ValueError):
            card(id="sin_dano", name="X", card_type="MAGIC")
        self.assertEqual(card(id="tanteo", name="X", card_type="ATTACK", damage=0)["damage"], 0,
                         "0 a propósito sí vale")
        self.assertEqual(card(id="grande", name="X", card_type="BREAK", damage=25)["damage"], 25)

    def test_all_effects_are_implemented(self):
        for data in CARD_DATA:
            for eff in data.get("effects", []):
                self.assertIn(eff["type"], EFFECTS, f"{data['id']}: {eff['type']}")

    def test_required_effects_exist(self):
        for name in ["RECOVER_STABILITY", "IGNORE_STABILITY", "ADD_HIT", "CANCEL_CARD", "MODIFY_RESULT",
                     "MODIFY_DAMAGE", "GAIN_MANA", "REDUCE_MANA", "PROTECT_STABILITY",
                     "MODIFY_MEGA_DAMAGE", "PROTECT_COMBO", "BREAK_COMBO"]:
            self.assertIn(name, EFFECTS)

    def test_no_interrupt_category(self):
        for data in CARD_DATA:
            self.assertNotEqual(data.get("category"), "interrupt", data["id"])
            self.assertIn(data["card_type"], ("ATTACK", "MAGIC", "GUARD", "BREAK", "SPECIAL"), data["id"])

    def test_decks_have_deck_size(self):
        for name, ids in DECKS.items():
            self.assertEqual(len(ids), RULES.DECK_SIZE, name)

    def test_default_decks_include_new_guards(self):
        for deck in DEFAULT_DECKS:
            self.assertIn("perfect_guard", DECKS[deck])
            self.assertIn("unbreakable_guard", DECKS[deck])


class TestPerfectGuard(unittest.TestCase):
    def test_beats_attack_destabilizes_no_initiative(self):
        """Ejemplo 2."""
        pg = make_card("perfect_guard")
        self.assertEqual(pg.card_type, "GUARD")
        self.assertFalse(pg.has_initiative)
        e = engine_with_hands(["attack", "attack"], ["perfect_guard", "guard"])
        r = play(e, "attack", "perfect_guard")
        self.assertEqual(r.winner, 1)
        self.assertFalse(e.players[0].stable, "Perfect Guard desestabiliza")
        self.assertEqual(r.hit_generated, 0)
        self.assertIn("COUNTER", r.tags)
        self.assertTrue(r.continues, "Sigue porque ATTACK tenía iniciativa")

    def test_with_another_guard_ends_turn(self):
        e = engine_with_hands(["guard", "attack"], ["perfect_guard", "attack"])
        r = play(e, "guard", "perfect_guard")
        self.assertFalse(r.continues)
        self.assertEqual(e.phase, Phase.TURN_END)


class TestUnbreakableGuard(unittest.TestCase):
    def test_beats_break(self):
        """Ejemplo 3: gana, sin hit, sin desestabilizar, sin iniciativa."""
        ug = make_card("unbreakable_guard")
        self.assertFalse(ug.has_initiative)
        r = resolve_interaction(make_card("break"), ug, True, True)
        self.assertEqual(r.winner, 1)
        self.assertEqual(r.lines[0], "UNBREAKABLE GUARD > BREAK")
        e = engine_with_hands(["break", "break"], ["unbreakable_guard", "guard"])
        r = play(e, "break", "unbreakable_guard")
        self.assertEqual((r.winner, r.hit_generated), (1, 0))
        self.assertTrue(e.players[0].stable)
        self.assertTrue(r.continues, "Sigue solo porque BREAK tenía iniciativa")

    def test_still_a_guard_against_attack(self):
        self.assertEqual(resolve_interaction(make_card("attack"), make_card("unbreakable_guard"), True, True).winner, 1)


class TestOtherCards(unittest.TestCase):
    def test_break_guard_extra_hit_only_vs_guard(self):
        e = engine_with_hands(["break_guard"], ["guard"])
        play(e, "break_guard", "guard", auto=False); e.advance()
        self.assertEqual(e.players[0].combo_hits, 2)

    def test_revenge_requires_unstable_and_ignores_stability(self):
        e = engine_with_hands(["revenge", "attack"], ["guard"])
        self.assertFalse(e.select(0, 0), "Revenge no se puede jugar estando STABLE")
        r = resolve_interaction(make_card("revenge"), make_card("attack"), False, True)
        self.assertEqual(r.outcome, DRAW)

    def test_overdrive_priority(self):
        r = resolve_interaction(make_card("overdrive"), make_card("attack"), True, True)
        self.assertEqual(r.winner, 0)
        self.assertIn("OVERDRIVE: PRIORIDAD 1 > 0", r.lines)

    def test_desperation_recovers_even_when_losing(self):
        e = engine_with_hands(["attack"], ["desperation", "guard"], mana=(3, 1), stable=(True, False))
        play(e, "attack", "desperation")             # Guard vence a Attack...
        self.assertTrue(e.players[1].stable)
        e = engine_with_hands(["break"], ["desperation", "guard"], mana=(3, 1), stable=(True, False))
        play(e, "break", "desperation")              # ...y aunque pierda contra Break
        self.assertTrue(e.players[1].stable)

    def test_parry_cancels(self):
        self.assertEqual(resolve_interaction(make_card("break"), make_card("parry"), True, True).outcome, DRAW)

    def test_feint_beats_guard(self):
        self.assertEqual(resolve_interaction(make_card("feint"), make_card("guard"), True, True).winner, 0)

    def test_iron_stance_protects(self):
        e = engine_with_hands(["break"], ["iron_stance"], mana=(3, 3))
        play(e, "break", "iron_stance")
        self.assertTrue(e.players[1].stable)

    def test_mana_effects_and_damage(self):
        e = engine_with_hands(["mana_surge"], ["attack"], mana=(2, 2))
        play(e, "mana_surge", "attack", auto=False); e.advance()   # solo resolver
        self.assertEqual(e.players[0].mana, 3)
        e = engine_with_hands(["drain"], ["guard"], mana=(2, 2))
        play(e, "drain", "guard", auto=False); e.advance()
        self.assertEqual(e.players[1].mana, 1)
        e = engine_with_hands(["heavy_blow"], ["break"], mana=(2, 3))
        play(e, "heavy_blow", "break", auto=False); e.advance()
        self.assertEqual(e.players[1].hp, RULES.MAX_HP - (make_card("heavy_blow").damage + 10), "Daño normal 10 + 10")


if __name__ == "__main__":
    unittest.main()
