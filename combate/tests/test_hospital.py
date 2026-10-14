"""Hospital: carta Taunt, pasivas de los enemigos (Alerta, Afinidad elemental),
cartas y mazos exclusivos de enemigos y personajes jugables."""
import unittest

from helpers import PASS, Phase, engine_with_hands, make_card, settle

from combate.cards.card_database import DECKS, ENEMY_DECKS, PLAYER_CARDS, make_deck_cards
from combate.cards.deck_store import DeckStore
from combate.game.ai import CardAI
from combate.game.characters import playable_characters
from combate.game.combat import CombatEngine
from combate.game.deck_editor import CATALOG, DeckEditor, MenuState
from combate.game.status import StatusId

WOLF = 1


def pick(engine, player, card_id, special=None):
    """Elige (y confirma) acción principal + SPECIAL opcional."""
    hand = engine.players[player].hand
    if special:
        assert engine.select(player, next(i for i, c in enumerate(hand) if c.id == special))
    if card_id == PASS:
        assert engine.select(player, PASS)
    else:
        assert engine.select(player, next(i for i, c in enumerate(hand) if c.id == card_id)), card_id
    assert engine.confirm(player)


def duel(e, c0, c1, s0=None, s1=None):
    pick(e, 0, c0, s0)
    pick(e, 1, c1, s1)
    r = e.result
    settle(e)
    return r


def wolf_engine(hand0, hand1, element="FIRE", wolf_hp=100, player_char=None):
    e = engine_with_hands(hand0, hand1, characters=(player_char, "elemental_wolf"))
    e.players[WOLF].passive.element = element
    e.players[WOLF].hp = wolf_hp
    return e


class TestTaunt(unittest.TestCase):
    def test_gains_ten_style_and_nothing_else(self):
        e = engine_with_hands(["guard", "taunt"], ["guard", "guard"])
        r = duel(e, PASS, "guard", s0="taunt")    # PASS sin recibir HIT: el resultado no resta
        p = e.players[0]
        self.assertEqual(p.style.points, 10)
        self.assertEqual(p.style.streak, 0)
        self.assertEqual(p.mana, 3 - 1, "Como toda SPECIAL, cuesta 1 Mana")
        self.assertEqual((p.hp, p.stable), (100, True))
        self.assertTrue(any("+10 ESTILO" in line for line in r.consequences))

    def test_keeps_the_win_streak(self):
        e = engine_with_hands(["attack", "taunt"], ["break", "guard"])
        duel(e, "attack", "break", s0="taunt")
        p = e.players[0]
        self.assertEqual((p.style.points, p.style.streak), (10 + 3, 1))

    def test_is_a_player_card(self):
        self.assertIn("taunt", PLAYER_CARDS)
        self.assertIn("taunt", CATALOG)


class TestElementalWolf(unittest.TestCase):
    def test_attack_hit_in_fire_mode_burns_the_attacker(self):
        e = wolf_engine(["attack", "guard"], ["break", "guard"], "FIRE")
        duel(e, "attack", "break")
        self.assertTrue(e.players[0].has_status(StatusId.BURN))
        self.assertEqual(e.players[WOLF].hp, 90)

    def test_attack_hit_in_ice_mode_freezes_the_attacker(self):
        e = wolf_engine(["attack", "guard"], ["break", "guard"], "ICE")
        duel(e, "attack", "break")
        self.assertTrue(e.players[0].has_status(StatusId.FREEZE))

    def test_no_status_without_a_hit_or_with_magic(self):
        e = wolf_engine(["attack", "magic", "guard"], ["guard", "break", "guard"], "FIRE")
        duel(e, "attack", "guard")                 # GUARD gana: no hay HIT
        self.assertIsNone(e.players[0].status)
        e = wolf_engine(["magic", "guard"], ["break", "guard"], "FIRE")
        duel(e, "magic", "break")                  # MAGIC: a distancia, no es contacto
        self.assertIsNone(e.players[0].status)

    def test_same_element_heals_opposite_does_x1_5(self):
        e = wolf_engine(["fire_bolt", "guard"], ["break", "guard"], "FIRE", wolf_hp=70)
        duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 80, "FUEGO en modo FUEGO: le cura")
        e = wolf_engine(["fire_bolt", "guard"], ["break", "guard"], "ICE", wolf_hp=70)
        duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 55, "FUEGO en modo HIELO: 10 x1.5 = 15")
        e = wolf_engine(["ice_shard", "guard"], ["break", "guard"], "FIRE", wolf_hp=70)
        duel(e, "ice_shard", "break")
        self.assertEqual(e.players[WOLF].hp, 55, "HIELO en modo FUEGO: x1.5")
        e = wolf_engine(["ice_shard", "guard"], ["break", "guard"], "ICE", wolf_hp=70)
        duel(e, "ice_shard", "break")
        self.assertEqual(e.players[WOLF].hp, 80, "HIELO en modo HIELO: le cura")

    def test_heal_is_capped(self):
        e = wolf_engine(["fire_bolt", "guard"], ["break", "guard"], "FIRE", wolf_hp=95)
        duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 100)

    def test_blaze_bonus_then_weakness(self):
        e = wolf_engine(["fire_bolt", "guard"], ["break", "guard"], "ICE", player_char="blaze")
        r = duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 100 - 17, "10 +10% (Blaze) = 11, x1.5 = 16.5 -> 17")
        self.assertTrue(any("DÉBIL A FIRE" in line for line in r.consequences))

    def test_shift_specials_change_mode_before_the_matchup(self):
        e = wolf_engine(["fire_bolt", "guard"], ["break", "glacial_shift", "guard"], "FIRE")
        duel(e, "fire_bolt", "break", s1="glacial_shift")
        self.assertEqual(e.players[WOLF].passive.element, "ICE")
        self.assertEqual(e.players[WOLF].hp, 85, "Ya en HIELO cuando llega el fuego: x1.5")
        e = wolf_engine(["guard"], ["guard", "infernal_shift"], "ICE")
        duel(e, "guard", "guard", s1="infernal_shift")
        self.assertEqual(e.players[WOLF].passive.element, "FIRE")

    def test_fangs_switch_mode_when_played(self):
        e = wolf_engine(["guard"], ["flame_fang", "guard"], "ICE")
        duel(e, "guard", "flame_fang")            # pierde, pero cambia igual (al jugarla)
        self.assertEqual(e.players[WOLF].passive.element, "FIRE")
        e = wolf_engine(["break", "guard"], ["frost_fang", "guard"], "FIRE")
        duel(e, "break", "frost_fang")
        self.assertEqual(e.players[WOLF].passive.element, "ICE")
        self.assertEqual(e.players[0].hp, 90)

    def test_wolf_fire_damage_is_not_affected_by_its_own_passive(self):
        e = wolf_engine(["break", "guard"], ["flame_fang", "guard"], "FIRE")
        duel(e, "break", "flame_fang")
        self.assertEqual(e.players[0].hp, 90)
        self.assertIsNone(e.players[0].status)


class TestElementWolves(unittest.TestCase):
    """Fire Wolf / Ice Wolf: su elemento le cura, el contrario x1, el resto x0.5."""

    def wolf(self, char, hand0, hp=70):
        e = engine_with_hands(hand0, ["break", "guard"], characters=(None, char))
        e.players[WOLF].hp = hp
        return e

    def test_fire_wolf(self):
        e = self.wolf("fire_wolf", ["fire_bolt", "guard"])
        duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 80, "FUEGO le cura")
        e = self.wolf("fire_wolf", ["ice_shard", "guard"])
        duel(e, "ice_shard", "break")
        self.assertEqual(e.players[WOLF].hp, 60, "HIELO: daño normal")
        e = self.wolf("fire_wolf", ["magic", "guard"])
        r = duel(e, "magic", "break")
        self.assertEqual(e.players[WOLF].hp, 65, "sin elemento: 10 x0.5 = 5")
        self.assertTrue(any("RESISTE SIN ELEMENTO" in line for line in r.consequences))

    def test_ice_wolf(self):
        e = self.wolf("ice_wolf", ["ice_shard", "guard"])
        duel(e, "ice_shard", "break")
        self.assertEqual(e.players[WOLF].hp, 80, "HIELO le cura")
        e = self.wolf("ice_wolf", ["fire_bolt", "guard"])
        duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 60, "FUEGO: daño normal")
        e = self.wolf("ice_wolf", ["attack", "guard"])
        duel(e, "attack", "break")
        self.assertEqual(e.players[WOLF].hp, 65, "ATTACK sin elemento: x0.5")

    def test_half_rounds_up(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=("blaze", "ice_wolf"))
        duel(e, "fire_bolt", "break")
        self.assertEqual(e.players[WOLF].hp, 100 - 11, "Blaze 10 +10% = 11 contra su debilidad: x1")
        e = engine_with_hands(["attack", "guard"], ["break", "guard"], characters=("hero", "fire_wolf"))
        duel(e, "attack", "break")
        self.assertEqual(e.players[WOLF].hp, 100 - 5, "Hero 1er HIT +0% = 10 -> 5")

    def test_not_playable_and_decks(self):
        for wolf in ("fire_wolf", "ice_wolf"):
            self.assertNotIn(wolf, playable_characters())
            self.assertEqual(len(make_deck_cards(wolf)), 10)


class TestSecurityAlert(unittest.TestCase):
    def engine_at_turn(self, turn):
        e = CombatEngine(seed=1, characters=(None, "security_droid"))
        e.turn = turn
        e.advance()                                 # TURN_START
        return e

    def test_every_three_turns_the_opponent_becomes_unstable(self):
        for turn, stable in ((1, True), (2, True), (3, False), (4, True), (6, False)):
            e = self.engine_at_turn(turn)
            self.assertEqual(e.players[0].stable, stable, f"turno {turn}")
            self.assertTrue(e.players[1].stable)

    def test_hud_countdown(self):
        e = self.engine_at_turn(1)
        p = e.players[1]
        self.assertEqual(p.passive.status_text(p, e), "alerta en 2 turnos")
        e = self.engine_at_turn(3)
        self.assertEqual(e.players[1].passive.status_text(e.players[1], e), "¡ALERTA ESTE TURNO!")


class TestEnemyContent(unittest.TestCase):
    def test_enemies_are_not_playable(self):
        self.assertEqual(playable_characters(), ["blaze", "hero", "jurgenoid"])
        menu = MenuState(DeckStore(path="__no_existe__.json"), characters=("elemental_wolf", "security_droid"))
        self.assertEqual(menu.character, ["blaze", "blaze"])
        for _ in range(5):
            menu.cycle_character(0, 1)
            self.assertIn(menu.character[0], playable_characters())

    def test_exclusive_cards_stay_with_the_enemy(self):
        for cid in ("infernal_shift", "glacial_shift", "flame_fang", "frost_fang"):
            self.assertNotIn(cid, PLAYER_CARDS)
            self.assertNotIn(cid, CATALOG)
            self.assertEqual(make_card(cid).exclusive_to, "elemental_wolf")
        store = DeckStore(path="__no_existe__.json")
        bad = ["flame_fang"] + DECKS["duelo"][1:]
        self.assertTrue(any("exclusiva" in err for err in store.validate(bad)))
        ed = DeckEditor(store, selected="duelo")
        ed.remove("attack")
        self.assertFalse(ed.add("flame_fang"))
        self.assertEqual(set(CATALOG), PLAYER_CARDS)

    def test_enemy_decks_are_valid_but_not_player_decks(self):
        for name, ids in ENEMY_DECKS.items():
            self.assertEqual(len(ids), 10)
            self.assertNotIn(name, DECKS)
            self.assertEqual(len(make_deck_cards(name)), 10)

    def test_full_ai_games_against_the_enemies(self):
        for enemy, deck in (("elemental_wolf", "elemental_wolf"), ("security_droid", "security_droid"),
                            ("fire_wolf", "fire_wolf"), ("ice_wolf", "ice_wolf")):
            for player_char in ("hero", "blaze"):
                for seed in range(4):
                    e = CombatEngine(card_lists=(make_deck_cards("elemental"), make_deck_cards(deck)),
                                     seed=seed, characters=(player_char, enemy))
                    ais = [CardAI(0, seed=seed), CardAI(1, seed=seed + 50)]
                    for _ in range(20000):
                        if e.phase == Phase.GAME_OVER:
                            break
                        if e.sm.is_auto:
                            e.advance()
                            continue
                        for ai in ais:
                            ai.observe(e)
                            ai.act(e)
                    self.assertEqual(e.phase, Phase.GAME_OVER, f"{enemy} vs {player_char} seed {seed}")


if __name__ == "__main__":
    unittest.main()
