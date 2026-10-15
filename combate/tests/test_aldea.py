"""Aldea del vacío: cartas Heal y Void Impact, pasiva Corrupted de los aldeanos
huecos y pasiva del Void Insect (crías, Part of the void, Void consumption)."""
import unittest

from helpers import PASS, Phase, engine_with_hands, play, resolve_only, settle

from combate.cards.card_database import ENEMY_DECKS, PLAYER_CARDS, make_card, make_deck_cards
from combate.game.ai import CardAI
from combate.game.combat import CombatEngine
from combate.game.status import StatusId

FOE = 1


class TestHeal(unittest.TestCase):
    def test_heals_thirty_up_to_max(self):
        e = engine_with_hands(["guard", "heal"], ["guard", "guard"], mana=(3, 3))
        e.players[0].hp = 50
        hand = e.players[0].hand
        assert e.select(0, hand.index(next(c for c in hand if c.id == "heal")))
        play(e, "guard", "guard")
        self.assertEqual(e.players[0].hp, 80)

    def test_never_above_max(self):
        e = engine_with_hands(["guard", "heal"], ["guard", "guard"], mana=(3, 3))
        e.players[0].hp = 90
        e.select(0, 1)
        play(e, "guard", "guard")
        self.assertEqual(e.players[0].hp, 100)

    def test_is_a_player_card(self):
        self.assertIn("heal", PLAYER_CARDS)
        self.assertEqual(make_card("heal").card_type, "SPECIAL")


class TestVoidImpact(unittest.TestCase):
    def test_card_data(self):
        c = make_card("void_impact")
        self.assertEqual((c.card_type, c.damage, c.element), ("ATTACK", 10, "VOID"))
        self.assertTrue(c.has_initiative and c.generates_hit and c.causes_instability and c.recovers_stability)
        self.assertIn("void_impact", PLAYER_CARDS)

    def test_win_costs_15_hp_paralyzes_and_stays_stable(self):
        e = engine_with_hands(["void_impact"], ["break"])
        r = resolve_only(e, "void_impact", "break")
        me, foe = e.players
        self.assertEqual(r.winner, 0)
        self.assertEqual(me.hp, 85, "pierde 15 de vida al jugarla")
        self.assertEqual(foe.hp, 90)
        self.assertTrue(me.stable, "si gana recupera la Stability")
        self.assertFalse(foe.stable)
        self.assertTrue(foe.has_status(StatusId.PARALYZE))

    def test_lose_costs_15_hp_and_leaves_unstable(self):
        e = engine_with_hands(["void_impact"], ["guard"])
        r = resolve_only(e, "void_impact", "guard")
        self.assertEqual(r.winner, FOE)
        self.assertEqual(e.players[0].hp, 85)
        self.assertFalse(e.players[0].stable, "queda UNSTABLE")
        self.assertIsNone(e.players[FOE].status)

    def test_draw_still_unstable(self):
        e = engine_with_hands(["void_impact"], ["attack"])
        r = resolve_only(e, "void_impact", "attack")
        self.assertEqual(r.outcome, "draw")
        self.assertFalse(e.players[0].stable)
        self.assertTrue(e.players[FOE].stable)

    def test_can_knock_out_its_user(self):
        e = engine_with_hands(["void_impact"], ["guard"])
        e.players[0].hp = 10
        play(e, "void_impact", "guard")
        self.assertEqual(e.players[0].hp, 0)
        e.run_auto()
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual(e.winner, FOE)


def villager(hand0, hand1, cid="herrero", hp=100):
    e = engine_with_hands(hand0, hand1, characters=(None, cid), mana=(5, 5))
    e.players[FOE].hp = e.players[FOE].max_hp = hp
    return e


class TestCorrupted(unittest.TestCase):
    def test_revives_once_with_half_life_and_transforms(self):
        e = villager(["attack", "attack", "attack"], ["break", "break", "break"])
        e.players[FOE].hp = 10
        play(e, "attack", "break")
        foe = e.players[FOE]
        self.assertTrue(foe.alive)
        self.assertEqual(foe.hp, 50, "recupera el 50% de su vida máxima")
        self.assertTrue(foe.passive.transformed)
        self.assertIn("CORRUPTO", foe.name)
        self.assertFalse(foe.stable, "el golpe que lo tumbó sigue desestabilizando a la forma nueva")
        events = [ev for ev in e.pop_events() if ev.kind == "transform"]
        self.assertEqual(events[0].data["sprite"], "villager_herrero_void")
        foe.hp = 5                                      # la segunda vez cae de verdad
        play(e, "attack", "break")
        e.run_auto()
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual(e.winner, 0)

    def test_transformed_hit_reduces_max_mana(self):
        e = villager(["break", "break"], ["attack", "attack"])
        e.players[FOE].passive.transformed = True
        play(e, "break", "attack")
        me = e.players[0]
        self.assertEqual(me.max_mana, 4)
        self.assertLessEqual(me.mana, 4)
        me.gain_mana(10)
        self.assertEqual(me.mana, 4, "el Mana nunca supera el nuevo máximo")

    def test_not_transformed_no_drain(self):
        e = villager(["break"], ["attack"])
        play(e, "break", "attack")
        self.assertEqual(e.players[0].max_mana, 5)

    def test_max_mana_never_below_one(self):
        e = villager(["guard"], ["guard"])
        for _ in range(8):
            e.reduce_max_mana(0, 1)
        self.assertEqual(e.players[0].max_mana, 1)

    def test_decks(self):
        for cid in ("herrero", "granjero", "vendedor"):
            cards = make_deck_cards(cid)
            self.assertEqual(len(cards), 10, cid)
            self.assertTrue(any(c.exclusive_to == cid for c in cards), cid)


def insect(hand0, hand1, charges=0):
    e = engine_with_hands(hand0, hand1, characters=(None, "void_insect"), mana=(5, 5))
    e.players[FOE].passive.charges = charges
    return e


class TestVoidInsect(unittest.TestCase):
    def test_breeding_one_charge_per_hit_max_ten(self):
        e = insect(["attack", "break_guard"], ["break", "guard"])
        play(e, "attack", "break")
        self.assertEqual(e.players[FOE].passive.charges, 1)
        e.players[FOE].passive.charges = 9
        play(e, "break_guard", "guard")                 # 2 HIT -> 11 -> tope 10
        self.assertEqual(e.players[FOE].passive.charges, 10)

    def test_void_damage_heals_double(self):
        e = insect(["void_impact"], ["break"])
        e.players[FOE].hp = 50
        play(e, "void_impact", "break")
        self.assertEqual(e.players[FOE].hp, 70, "10 de daño VOID -> +20 HP")

    def test_two_broods_then_rage(self):
        e = insect(["attack"] * 3, ["break"] * 3, charges=4)
        foe = e.players[FOE]
        foe.hp = 5
        play(e, "attack", "break")
        self.assertEqual((foe.passive.stage, foe.hp, foe.max_hp), ("brood1", 20, 20), "cargas x10 / 2")
        foe.hp = 5
        play(e, "attack", "break")
        self.assertEqual((foe.passive.stage, foe.hp, foe.max_hp), ("brood2", 20, 20))
        foe.hp = 5
        resolve_only(e, "attack", "break")             # (sin el Mega Combo de este 3er HIT)
        self.assertEqual((foe.passive.stage, foe.hp, foe.max_hp), ("rage", 50, 100))
        self.assertEqual(foe.name, "VOID INSECT")

    def test_no_charges_no_broods(self):
        e = insect(["attack"], ["break"], charges=0)
        e.players[FOE].hp = 5
        play(e, "attack", "break")
        self.assertEqual(e.players[FOE].passive.stage, "rage")

    def test_broods_heal_from_void_too(self):
        e = insect(["void_impact"], ["break"])
        foe = e.players[FOE]
        foe.passive.stage, foe.hp, foe.max_hp = "brood1", 10, 50
        play(e, "void_impact", "break")
        self.assertEqual(foe.hp, 30)

    def test_rage_consumes_twenty_percent_max_hp(self):
        e = insect(["break", "break"], ["attack", "attack"])
        e.players[FOE].passive.stage = "rage"
        play(e, "break", "attack")
        me = e.players[0]
        self.assertEqual(me.max_hp, 80)
        self.assertEqual(me.max_hp_lost, 20)
        self.assertLessEqual(me.hp, 80)

    def test_main_stage_does_not_consume(self):
        e = insect(["break"], ["attack"])
        play(e, "break", "attack")
        self.assertEqual(e.players[0].max_hp, 100)

    def test_dies_after_rage(self):
        e = insect(["attack"], ["break"])
        e.players[FOE].passive.stage = "rage"
        e.players[FOE].hp = 5
        play(e, "attack", "break")
        e.run_auto()
        self.assertEqual(e.winner, 0)


class TestVoidCards(unittest.TestCase):
    def test_void_sting_reduces_max_mana(self):
        e = engine_with_hands(["break"], ["void_sting"], mana=(5, 5))
        play(e, "break", "void_sting")
        self.assertEqual(e.players[0].max_mana, 4)

    def test_void_buzz_only_if_hit(self):
        e = engine_with_hands(["guard", "break"], ["attack", "void_buzz", "attack"], mana=(5, 5))
        e.select(1, 1)
        play(e, "guard", "attack")                     # GUARD gana: sin HIT
        self.assertEqual(e.players[0].max_mana, 5)

    def test_void_buzz_with_hit(self):
        e = engine_with_hands(["break"], ["attack", "void_buzz"], mana=(5, 5))
        e.select(1, 1)
        play(e, "break", "attack")
        self.assertEqual(e.players[0].max_mana, 4)

    def test_enemy_decks_have_ten(self):
        for deck in ("herrero", "granjero", "vendedor", "void_insect"):
            self.assertEqual(len(ENEMY_DECKS[deck]), 10, deck)

    def test_ai_plays_a_whole_fight(self):
        """La IA juega contra sí misma con los mazos de la aldea sin bloquearse."""
        for deck, cid in (("herrero", "herrero"), ("void_insect", "void_insect")):
            e = CombatEngine(decks=("duelo", deck), seed=4,
                             characters=("hero", cid))
            ais = [CardAI(0, seed=1), CardAI(1, seed=2)]
            for _ in range(3000):
                if e.phase == Phase.GAME_OVER:
                    break
                if e.sm.is_auto:
                    e.advance()
                    continue
                for ai in ais:
                    ai.act(e)
            self.assertEqual(e.phase, Phase.GAME_OVER, deck)


if __name__ == "__main__":
    unittest.main()
