"""Jurgenoid y su pasiva Undead: una marca por HIT recibido; al empezar cada turno
se cura 0.5% de su vida máxima por marca (redondeo: medios hacia arriba)."""
import unittest

from helpers import PASS, Phase, engine_with_hands, play

from combate.game.characters import pct_of, playable_characters
from combate.game.combat import CombatEngine

J = 1       # Jurgenoid es el jugador 2 en estas pruebas


def jurgen(hand0, hand1, marks=0, hp=None):
    e = engine_with_hands(hand0, hand1, characters=(None, "jurgenoid"))
    e.players[J].passive.marks = marks
    if hp is not None:
        e.players[J].hp = hp
    return e


def start_next_turn(e):
    """Termina el turno y ejecuta el inicio del siguiente (ahí se cura)."""
    while e.phase != Phase.TURN_START:
        if e.sm.is_auto:
            e.advance()
        else:
            raise AssertionError(f"Esperaba fin de turno, fase {e.phase}")
    e.advance()


class TestUndead(unittest.TestCase):
    def test_playable(self):
        self.assertIn("jurgenoid", playable_characters())

    def test_rounding(self):
        self.assertEqual([pct_of(100, 5 * m) for m in (0, 1, 2, 3, 4, 10)], [0, 1, 1, 2, 2, 5])

    def test_each_hit_received_gives_a_mark(self):
        e = jurgen(["attack", "guard"], ["break", "guard"])
        r = play(e, "attack", "break")
        self.assertEqual(e.players[J].passive.marks, 1)
        self.assertTrue(any("UNDEAD +1 marca -> 1" in c for c in r.consequences))

    def test_no_mark_without_a_hit(self):
        e = jurgen(["attack", "guard"], ["guard", "guard"])
        play(e, "attack", "guard")                      # GUARD gana: nadie recibe HIT
        e2 = jurgen(["break", "guard"], ["attack", "guard"])
        play(e2, "break", "attack")                     # Jurgenoid gana
        self.assertEqual((e.players[J].passive.marks, e2.players[J].passive.marks), (0, 0))

    def test_double_hit_gives_two_marks(self):
        e = jurgen(["break_guard", "guard"], ["guard", "guard"])
        play(e, "break_guard", "guard")                 # Break Guard contra GUARD: 2 HIT
        self.assertEqual(e.players[J].passive.marks, 2)

    def test_pass_also_receives_the_hit(self):
        e = jurgen(["attack", "guard"], ["guard"])
        play(e, "attack", PASS)
        self.assertEqual(e.players[J].passive.marks, 1)

    def test_heals_at_turn_start(self):
        e = jurgen(["guard"], ["guard"], marks=3, hp=50)
        play(e, "guard", "guard")                       # sin iniciativa: fin del turno
        start_next_turn(e)
        self.assertEqual(e.players[J].hp, 52, "3 marcas x 0.5% de 100 = 1.5 -> 2")

    def test_heal_is_capped_and_needs_marks(self):
        e = jurgen(["guard"], ["guard"], marks=10, hp=98)
        play(e, "guard", "guard")
        start_next_turn(e)
        self.assertEqual(e.players[J].hp, 100)
        e = jurgen(["guard"], ["guard"], marks=0, hp=50)
        play(e, "guard", "guard")
        start_next_turn(e)
        self.assertEqual(e.players[J].hp, 50)

    def test_uses_max_hp(self):
        e = jurgen(["guard"], ["guard"], marks=4, hp=30)
        e.players[J].max_hp = 60                        # p. ej. si empezara con menos vida
        play(e, "guard", "guard")
        start_next_turn(e)
        self.assertEqual(e.players[J].hp, 31, "4 x 0.5% de 60 = 1.2 -> 1")

    def test_hud_text(self):
        e = jurgen(["guard"], ["guard"], marks=3)
        p = e.players[J]
        self.assertEqual(p.passive.status_text(p, e), "marcas 3 · +2 HP por turno")

    def test_full_games_complete(self):
        from test_status import run_bot_game
        for seed in range(4):
            e = run_bot_game(CombatEngine(decks=("duelo", "duelo"), seed=seed, characters=("hero", "jurgenoid")))
            self.assertEqual(e.phase, Phase.GAME_OVER)


if __name__ == "__main__":
    unittest.main()
