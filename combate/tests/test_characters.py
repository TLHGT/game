"""Personajes jugables: Blaze (Afinidad ígnea) y Hero (Impulso consecutivo)."""
import unittest

from helpers import PASS, Phase, choose, engine_with_hands, make_card, play, settle
from test_status import end_turn, next_turn, run_bot_game

from combate.cards.card import Card
from combate.cards.card_database import CARDS
from combate.game.characters import (CHARACTERS, PASSIVES, Character, apply_pct, playable_characters,
                                     register_character)
from combate.game.combat import CombatEngine
from combate.game.config import CHANNEL_MAGIC, CHANNEL_PHYSICAL, RULES
from combate.game.rules import DAMAGE_INTERACTION, DAMAGE_MEGA_COMBO
from combate.game.status import StatusId

BLAZE, HERO = ("blaze", None), ("hero", None)


def offense(id_, card_type="ATTACK", damage=10, element=None, hit=True):
    channel = CHANNEL_MAGIC if card_type == "MAGIC" else CHANNEL_PHYSICAL
    return Card(id=id_, name=id_.title(), card_type=card_type, has_initiative=True, damage=damage,
                generates_hit=hit, causes_instability=True, damage_channel=channel, element=element)


def interaction_damage(r):
    return [d for d in r.damage_events if d.kind == DAMAGE_INTERACTION]


class TestRounding(unittest.TestCase):
    def test_apply_pct(self):
        self.assertEqual([apply_pct(10, 10), apply_pct(10, 5), apply_pct(20, 15), apply_pct(10, 0)], [11, 11, 23, 10])
        self.assertEqual(apply_pct(30, 5), 32, "31.5 -> 32: los medios redondean hacia arriba")
        self.assertEqual(apply_pct(0, 10), 0)


# =====================================================================
# Blaze: Afinidad ígnea
# =====================================================================
class TestBlaze(unittest.TestCase):
    def duel(self, card, characters=BLAZE):
        e = engine_with_hands(["guard"], ["break", "guard"], characters=characters)
        e.players[0].hand = [card]
        return e, play(e, card.id, "break")

    def test_fire_magic_gets_10_percent(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=BLAZE)
        r = play(e, "fire_bolt", "break")
        ev = interaction_damage(r)[0]
        self.assertEqual((ev.base_amount, ev.passive_pct, ev.amount), (10, 10, 11))
        self.assertEqual(e.players[1].hp, 89)
        self.assertIn("BLAZE: AFINIDAD ÍGNEA +10% (10 -> 11)", r.consequences)

    def test_fire_attack_also_counts(self):
        e, r = self.duel(offense("fire_punch", "ATTACK", element="FIRE"))
        self.assertEqual(e.players[1].hp, 89, "Lo que cuenta es el elemento, no el tipo")

    def test_other_element_and_no_element(self):
        for card in (offense("ice_bolt", "MAGIC", element="ICE"), make_card("magic"), make_card("attack")):
            e, r = self.duel(card)
            self.assertEqual(e.players[1].hp, 90, card.id)
            self.assertEqual(interaction_damage(r)[0].passive_pct, 0)

    def test_bigger_fire_damage_uses_same_rounding(self):
        e, r = self.duel(offense("inferno", "MAGIC", damage=25, element="FIRE"))
        self.assertEqual(e.players[1].hp, 100 - apply_pct(25, 10))      # 27.5 -> 28

    def test_mega_combo_damage_is_not_fire(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=BLAZE)
        e.players[0].combo_hits = 2
        r = play(e, "fire_bolt", "break", auto=False)
        e.advance()
        e.advance()                                # MEGA_COMBO
        self.assertEqual([(d.kind, d.amount) for d in r.damage_events],
                         [(DAMAGE_INTERACTION, 11), (DAMAGE_MEGA_COMBO, RULES.MEGA_COMBO_DAMAGE)])

    def test_status_damage_not_boosted(self):
        e = engine_with_hands(["guard"], ["guard"], characters=BLAZE)
        e.apply_status(1, StatusId.BURN)
        end_turn(e)
        next_turn(e)
        self.assertEqual(e.players[1].hp, 100 - RULES.BURN_DAMAGE)
        e2 = engine_with_hands(["guard"], ["guard"], characters=BLAZE)
        e2.apply_status(1, StatusId.POISON)
        end_turn(e2)
        next_turn(e2)
        self.assertEqual(e2.players[1].hp, 100 - RULES.POISON_DAMAGE)

    def test_flame_burn_is_not_automatic(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=BLAZE)
        play(e, "fire_bolt", "break")
        self.assertIsNone(e.players[1].status, "La pasiva no quema: eso lo hace un efecto como FLAME")

    def test_applied_once_per_event(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=BLAZE)
        r = play(e, "fire_bolt", "break")
        ev = interaction_damage(r)[0]
        e._apply_passive(r, ev)                     # una segunda llamada no hace nada
        self.assertEqual(ev.amount, 11)
        self.assertEqual(sum("AFINIDAD" in c for c in r.consequences), 1)

    def test_cards_not_modified(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=BLAZE)
        played = e.players[0].hand[0]
        play(e, "fire_bolt", "break")
        self.assertEqual(played.damage, 10)
        self.assertEqual(CARDS["fire_bolt"]["damage"], 10)
        self.assertEqual(make_card("fire_bolt").damage, 10)

    def test_ice_cube_takes_boosted_damage(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["guard"], characters=BLAZE)
        e.apply_status(1, StatusId.FREEZE)
        end_turn(e)
        next_turn(e, hands=(["fire_bolt", "guard"], ["guard"]))
        choose(e, 0, "fire_bolt")
        choose(e, 1, PASS)                           # WAIT
        e.advance()
        self.assertEqual((e.players[1].hp, e.players[1].status.cube_hp), (100, 30 - 11))


# =====================================================================
# Hero: Impulso consecutivo
# =====================================================================
class TestHero(unittest.TestCase):
    def chain(self, characters=HERO, damage=20, n=3):
        """Hero encadena `n` HIT con una carta de `damage` contra BREAK."""
        e = engine_with_hands(["guard"], ["break"] * n, mana=(5, 5), characters=characters)
        e.players[0].hand = [offense(f"big{k}", damage=damage) for k in range(n)]
        results = []
        for k in range(n):
            results.append(play(e, f"big{k}", "break", auto=k < n - 1))
        e.advance()                                  # el último: CARD_REVEAL -> CARD_RESOLUTION
        return e, results

    def test_progression_and_mega(self):
        e, rs = self.chain()
        steps = [(d.base_amount or d.amount, d.passive_pct, d.amount) for d in map(lambda r: interaction_damage(r)[0], rs)]
        self.assertEqual(steps, [(20, 0, 20), (20, 5, 21), (20, 10, 22)], "1º +0% · 2º +5% · 3º +10%")
        e.advance()                                  # MEGA_COMBO
        self.assertEqual(e.phase, Phase.MEGA_COMBO)
        mega = rs[2].damage_events[-1]
        self.assertEqual((mega.kind, mega.base_amount, mega.passive_pct, mega.amount),
                         (DAMAGE_MEGA_COMBO, RULES.MEGA_COMBO_DAMAGE, 15, apply_pct(RULES.MEGA_COMBO_DAMAGE, 15)))
        self.assertEqual([(d.kind, d.passive_pct) for d in rs[2].damage_events],
                         [(DAMAGE_INTERACTION, 10), (DAMAGE_MEGA_COMBO, 15)], "Cada % en su componente, sin sumarse")
        self.assertEqual(e.players[1].hp, 100 - 20 - 21 - 22 - 23)

    def test_basic_cards_round_up(self):
        e, rs = self.chain(damage=10)
        self.assertEqual([interaction_damage(r)[0].amount for r in rs], [10, 11, 11])

    def test_no_hit_does_not_advance(self):
        e = engine_with_hands(["guard"], ["break", "break"], mana=(5, 5), characters=HERO)
        soft = offense("soft", damage=10, hit=False)
        e.players[0].hand = [soft, offense("big", damage=20)]
        r = play(e, "soft", "break")
        self.assertEqual((interaction_damage(r)[0].passive_pct, e.players[0].combo_hits), (0, 0))
        r = play(e, "big", "break")
        self.assertEqual(interaction_damage(r)[0].passive_pct, 0, "El siguiente HIT sigue siendo el 1º")

    def test_blocked_attack_does_not_advance(self):
        e = engine_with_hands(["attack", "attack"], ["guard", "break"], mana=(5, 5), characters=HERO)
        play(e, "attack", "guard")                   # GUARD bloquea: sin HIT
        self.assertEqual(e.players[0].combo_hits, 0)
        r = play(e, "attack", "break")
        self.assertEqual(interaction_damage(r)[0].passive_pct, 0)

    def test_chain_break_resets(self):
        e = engine_with_hands(["guard"], ["break", "guard", "break"], mana=(5, 5), characters=HERO)
        e.players[0].hand = [offense("a", damage=20), offense("b", damage=20), offense("c", damage=20)]
        play(e, "a", "break")
        self.assertEqual(e.players[0].combo_hits, 1)
        play(e, "b", "guard")                        # pierde: el combo se rompe
        self.assertEqual(e.players[0].combo_hits, 0)
        r = play(e, "c", "break")
        self.assertEqual((interaction_damage(r)[0].passive_pct, interaction_damage(r)[0].amount), (0, 20))

    def test_turn_end_resets_like_the_combo(self):
        e = engine_with_hands(["attack", "guard"], ["break", "guard"], characters=HERO)
        play(e, "attack", "break")
        play(e, "guard", "guard")
        self.assertEqual(e.phase, Phase.TURN_END)
        next_turn(e, hands=(["attack"], ["break"]))
        self.assertEqual(e.players[0].combo_hits, 0, "El combo existente se reinicia al acabar el turno")
        r = play(e, "attack", "break")
        self.assertEqual(interaction_damage(r)[0].passive_pct, 0, "...y la pasiva con él")

    def test_status_damage_does_not_count(self):
        e = engine_with_hands(["venom_strike", "guard"], ["break", "break"], mana=(5, 5), characters=HERO)
        e.players[0].hand.append(offense("big", damage=20))
        play(e, "venom_strike", "break")             # HIT 1 + POISON al rival
        self.assertEqual(e.players[1].hp, 100 - 10 - RULES.POISON_DAMAGE, "POISON: daño sin bonificación")
        self.assertEqual(e.players[0].combo_hits, 1, "El daño de estado no suma combo")
        r = play(e, "big", "break")
        self.assertEqual(interaction_damage(r)[0].passive_pct, 5, "Este es el 2º HIT")

    def test_ice_cube_is_not_a_hit(self):
        e = engine_with_hands(["frost_guard", "attack", "attack"], ["attack", "guard"], mana=(5, 5),
                              characters=HERO)
        play(e, "frost_guard", "attack")
        choose(e, 0, "attack")
        choose(e, 1, PASS)                           # WAIT
        e.advance()
        self.assertEqual(interaction_damage(e.result)[0].passive_pct, 0)
        self.assertEqual(e.players[0].combo_hits, 0)

    def test_others_do_not_get_hero_bonus(self):
        for characters in ((None, None), ("blaze", None)):
            e, rs = self.chain(characters=characters)
            self.assertEqual([interaction_damage(r)[0].amount for r in rs], [20, 20, 20], characters)
        e = engine_with_hands(["guard"], ["break"], characters=(None, "hero"))
        e.players[0].combo_hits = 1
        e.players[0].hand = [offense("big", damage=20)]
        r = play(e, "big", "break")
        self.assertEqual(interaction_damage(r)[0].amount, 20, "La pasiva es de quien CAUSA el daño")

    def test_never_desyncs_from_combo(self):
        """En partidas completas, el paso que usa Hero es siempre el combo real tras la interacción."""
        checked = 0
        for seed in range(8):
            for decks in (("duelo", "starter"), ("arcano", "estados")):
                e = CombatEngine(decks=decks, seed=seed, characters=("hero", "hero"))
                original = e._apply_result

                def checked_apply(r, _e=e, _orig=original):
                    nonlocal checked
                    _orig(r)
                    for d in interaction_damage(r):
                        if d.combo_step is not None:
                            self.assertEqual(d.combo_step, r.combo_after[d.source])
                            self.assertEqual(d.passive_pct, {1: 0, 2: 5, 3: 10}[d.combo_step])
                            checked += 1
                        elif d.passive_pct:
                            self.fail("Bonificación sin HIT")
                e._apply_result = checked_apply
                run_bot_game(e)
        self.assertGreater(checked, 50)


# =====================================================================
# Sistema de personajes
# =====================================================================
class TestCharacterSystem(unittest.TestCase):
    def test_registry(self):
        self.assertEqual(set(playable_characters()), {"blaze", "hero", "jurgenoid"})
        self.assertEqual(set(CHARACTERS) - set(playable_characters()),
                         {"security_droid", "elemental_wolf", "fire_wolf", "ice_wolf",
                          "herrero", "granjero", "vendedor", "void_insect"},
                         "Los enemigos son personajes, pero no jugables")
        for ch in CHARACTERS.values():
            self.assertTrue(ch.name and ch.description and ch.passive_id in PASSIVES)
            pas = ch.make_passive()
            self.assertTrue(pas.name and pas.summary())

    def test_different_and_same_characters(self):
        e = CombatEngine(seed=1, characters=("blaze", "hero"))
        self.assertEqual([p.character.id for p in e.players], ["blaze", "hero"])
        e = CombatEngine(seed=1, characters=("hero", "hero"))
        self.assertEqual([p.character.id for p in e.players], ["hero", "hero"])
        self.assertIsNot(e.players[0].passive, e.players[1].passive, "Cada jugador tiene su propia pasiva")

    def test_kept_for_the_whole_game(self):
        e = CombatEngine(decks=("arcano", "duelo"), seed=4, characters=("blaze", "hero"))
        passives = [p.passive for p in e.players]
        run_bot_game(e)
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual([p.passive for p in e.players], passives)
        self.assertEqual([p.character.id for p in e.players], ["blaze", "hero"])

    def test_character_does_not_change_deck_or_rules(self):
        a = CombatEngine(seed=9)
        b = CombatEngine(seed=9, characters=("hero", "blaze"))
        for e in (a, b):
            e.run_auto()
        for pa, pb in zip(a.players, b.players):
            self.assertEqual([c.id for c in pa.hand], [c.id for c in pb.hand])
            self.assertEqual([c.id for c in pa.deck.draw_pile], [c.id for c in pb.deck.draw_pile])
            self.assertEqual((pa.hp, pa.mana, pa.stable, pa.combo_hits), (pb.hp, pb.mana, pb.stable, pb.combo_hits))
        self.assertIs(a.rules, b.rules)

    def test_no_character_means_no_passive(self):
        e = CombatEngine(seed=1)
        self.assertEqual([(p.character, p.passive) for p in e.players], [(None, None), (None, None)])

    def test_new_character_without_engine_changes(self):
        ch = Character("pyro_test", "Pyro", "Prueba.", "fire_affinity", {"element": "FIRE", "bonus_pct": 50})
        register_character(ch)
        try:
            e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"], characters=("pyro_test", None))
            play(e, "fire_bolt", "break")
            self.assertEqual(e.players[1].hp, 85)
            with self.assertRaises(ValueError):
                register_character(ch)
            with self.assertRaises(KeyError):
                register_character(Character("x_test", "X", "", "no_existe"))
        finally:
            CHARACTERS.pop("pyro_test", None)

    def test_full_pvp_games_complete(self):
        for chars in (("blaze", "hero"), ("hero", "hero"), ("blaze", "blaze")):
            for seed in range(3):
                e = run_bot_game(CombatEngine(decks=("arcano", "duelo"), seed=seed, characters=chars))
                self.assertEqual(e.phase, Phase.GAME_OVER)
                self.assertTrue(any(p.hp == 0 for p in e.players))


class TestAvatars(unittest.TestCase):
    """Avatar de exploración: Blaze y Jurgenoid tienen el suyo; Hero usa el de por defecto."""

    def test_avatars(self):
        self.assertEqual(CHARACTERS["blaze"].avatar, "avatar_blaze")
        self.assertEqual(CHARACTERS["jurgenoid"].avatar, "avatar_jurgenoid")
        self.assertEqual(CHARACTERS["hero"].avatar, "avatar_hero")


if __name__ == "__main__":
    unittest.main()
