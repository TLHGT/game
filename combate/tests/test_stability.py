"""Stability definitiva.

    A. Empate real                -> ambos STABLE.
    B. Sin empate                 -> UNSTABLE que NO recibió hit -> STABLE;
                                     UNSTABLE que recibió hit   -> sigue UNSTABLE.
    C. Efectos explícitos (al final) -> desestabilizar / recuperar.
    La iniciativa NO interviene en la recuperación. Nunca se acumula.
"""
import unittest

from helpers import PASS, Phase, engine_with_hands, make_card, resolve_only

from combate.cards.card import Card
from combate.game.rules import DRAW, WIN, resolve_interaction

S, U = True, False      # STABLE / UNSTABLE
ATK = make_card("attack")


def states(e):
    return [p.stable for p in e.players]


class TestTiebreak(unittest.TestCase):
    """La Stability solo desempata cuando el tipo es el mismo."""

    def test_stable_vs_stable_draw(self):
        self.assertEqual(resolve_interaction(ATK, make_card("attack"), S, S).outcome, DRAW)

    def test_stable_vs_unstable_stable_wins(self):
        r = resolve_interaction(ATK, make_card("attack"), S, U)
        self.assertEqual((r.outcome, r.winner), (WIN, 0))
        self.assertIn("P1 STABLE > P2 UNSTABLE", r.lines)
        r = resolve_interaction(ATK, make_card("attack"), U, S)
        self.assertEqual((r.outcome, r.winner), (WIN, 1))

    def test_unstable_vs_unstable_draw(self):
        self.assertEqual(resolve_interaction(ATK, make_card("attack"), U, U).outcome, DRAW)

    def test_type_beats_stability(self):
        self.assertEqual(resolve_interaction(make_card("guard"), ATK, U, S).winner, 0)


class TestDrawResetsBoth(unittest.TestCase):
    """A. Un empate real devuelve a ambos a STABLE."""

    def test_stable_stable_same_type(self):
        e = engine_with_hands(["attack", "guard"], ["attack", "guard"], stable=(S, S))
        r = resolve_only(e, "attack", "attack")
        self.assertEqual((r.outcome, states(e)), (DRAW, [S, S]))

    def test_unstable_unstable_same_type(self):
        """Doc 2 · Test 5."""
        e = engine_with_hands(["attack", "guard"], ["attack", "guard"], stable=(U, U))
        r = resolve_only(e, "attack", "attack")
        self.assertEqual((r.outcome, states(e)), (DRAW, [S, S]))
        self.assertIn("EMPATE: ambos STABLE", r.consequences)

    def test_guard_guard_stable_unstable(self):
        """Doc 2 · Test 2: J1 STABLE, J2 UNSTABLE, GUARD vs GUARD -> DRAW, ambos STABLE."""
        e = engine_with_hands(["guard", "attack"], ["guard", "attack"], stable=(S, U))
        r = resolve_only(e, "guard", "guard")
        self.assertEqual((r.outcome, states(e)), (DRAW, [S, S]))

    def test_guard_guard_both_unstable_ends_sequence(self):
        """Doc 2 · Test 6: ambos STABLE y la secuencia termina (nadie con iniciativa)."""
        e = engine_with_hands(["guard", "attack"], ["guard", "attack"], stable=(U, U))
        r = resolve_only(e, "guard", "guard")
        self.assertEqual(states(e), [S, S])
        self.assertFalse(r.continues)
        e.advance()
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_pass_pass_is_a_draw_too(self):
        e = engine_with_hands(["guard"], ["guard"], stable=(U, U))
        resolve_only(e, PASS, PASS)
        self.assertEqual(states(e), [S, S])

    def test_parry_cancel_is_a_draw(self):
        e = engine_with_hands(["break"], ["parry"], mana=(3, 3), stable=(U, U))
        r = resolve_only(e, "break", "parry")
        self.assertEqual((r.outcome, states(e)), (DRAW, [S, S]))


class TestRecoveryByHit(unittest.TestCase):
    """B. Sin empate: recupera quien NO recibió hit; sigue UNSTABLE quien sí."""

    def test_1_stable_beats_unstable_same_type(self):
        """Doc 2 · Test 1: ATTACK = ATTACK, gana el STABLE; el UNSTABLE recibe hit y sigue UNSTABLE."""
        e = engine_with_hands(["attack", "guard"], ["attack", "guard"], stable=(S, U))
        r = resolve_only(e, "attack", "attack")
        self.assertEqual((r.winner, r.decided_by), (0, "stability"))
        self.assertEqual(r.received_hit, (False, True))
        self.assertEqual(states(e), [S, U])
        self.assertEqual(r.stability_changes, {}, "Ganar por Stability no cambia ningún estado")

    def test_3_unstable_receives_hit_stays(self):
        """Doc 2 · Test 3: ATTACK vs BREAK, J2 UNSTABLE recibe hit -> sigue UNSTABLE."""
        e = engine_with_hands(["attack", "guard"], ["break", "guard"], stable=(S, U))
        r = resolve_only(e, "attack", "break")
        self.assertTrue(r.received_hit[1])
        self.assertEqual(states(e), [S, U])
        self.assertIn("PLAYER 2 sigue UNSTABLE (ATTACK)", r.consequences)

    def test_4_unstable_without_hit_recovers(self):
        """Doc 2 · Test 4: J1 UNSTABLE, ATTACK vs GUARD; Guard gana sin hit -> J1 STABLE."""
        e = engine_with_hands(["attack", "guard"], ["guard", "guard"], stable=(U, S))
        r = resolve_only(e, "attack", "guard")
        self.assertEqual((r.winner, r.received_hit), (1, (False, False)))
        self.assertEqual(states(e), [S, S])
        self.assertIn("PLAYER 1 -> STABLE (no recibió hit)", r.consequences)

    def test_unstable_winner_recovers(self):
        """Quien gana no recibe hit: si estaba UNSTABLE, recupera (regla del hit)."""
        e = engine_with_hands(["attack", "guard"], ["break", "guard"], stable=(U, S))
        resolve_only(e, "attack", "break")
        self.assertEqual(states(e), [S, U])

    def test_initiative_is_not_used_for_recovery(self):
        """La iniciativa (propia o del rival) no decide la recuperación: solo el hit."""
        # Rival CON iniciativa, pero no hay hit -> recupera
        e = engine_with_hands(["guard", "guard"], ["attack", "guard"], stable=(U, S))
        resolve_only(e, "guard", "attack")            # Guard (J1) vence a Attack
        self.assertTrue(e.players[0].stable)
        # Rival SIN iniciativa, pero hace hit -> NO recupera
        heavy_guard = Card(id="hg", name="Heavy Guard", card_type="GUARD", has_initiative=False,
                           generates_hit=True, damage=5)
        e = engine_with_hands(["attack", "guard"], ["guard", "guard"], stable=(U, S))
        e.players[1].hand = [heavy_guard, make_card("guard")]
        r = resolve_only(e, "attack", "hg")
        self.assertTrue(r.received_hit[0])
        self.assertFalse(e.players[0].stable)

    def test_hit_and_damage_are_separate(self):
        """Lo que cuenta para Stability es el HIT, no el daño."""
        hit_no_dmg = Card(id="h", name="Tap", card_type="ATTACK", has_initiative=True, generates_hit=True, damage=0)
        dmg_no_hit = Card(id="d", name="Chip", card_type="ATTACK", has_initiative=True, generates_hit=False, damage=7)
        e = engine_with_hands(["attack"], ["break", "break"], stable=(S, U))
        e.players[0].hand = [hit_no_dmg, dmg_no_hit]
        r = resolve_only(e, "h", "break")
        self.assertEqual((r.received_hit[1], e.players[1].stable), (True, False), "Hit sin daño: sigue UNSTABLE")
        e.advance(); e.advance()
        e.players[1].stable = False
        r = resolve_only(e, "d", "break")
        self.assertEqual((r.received_hit[1], e.players[1].stable), (False, True), "Daño sin hit: recupera")

    def test_no_accumulation(self):
        e = engine_with_hands(["attack", "attack"], ["break", "break"], stable=(S, U))
        r = resolve_only(e, "attack", "break")
        self.assertIs(e.players[1].stable, False)       # un simple booleano, nunca "x2"
        self.assertIn("PLAYER 2 sigue UNSTABLE (ATTACK)", r.consequences)
        e.advance(); e.advance()
        resolve_only(e, "attack", "break")
        self.assertIs(e.players[1].stable, False)


class TestExplicitEffects(unittest.TestCase):
    """C. Los efectos explícitos se aplican al final y no se anulan por la regla general."""

    def test_attack_win_destabilizes(self):
        e = engine_with_hands(["attack"], ["break"])
        r = resolve_only(e, "attack", "break")
        self.assertEqual(states(e), [S, U])
        self.assertEqual(r.stability_changes, {1: False})

    def test_guard_does_not_destabilize(self):
        e = engine_with_hands(["attack", "guard"], ["guard", "guard"])
        r = resolve_only(e, "attack", "guard")
        self.assertEqual(states(e), [S, S])
        self.assertIn("GUARD no desestabiliza", r.consequences)

    def test_perfect_guard_beats_recovery(self):
        """Doc 1 · Caso 7: Perfect Guard deja UNSTABLE aunque el rival no recibiera hit."""
        for start in (S, U):
            e = engine_with_hands(["attack", "guard"], ["perfect_guard", "guard"], stable=(start, S))
            r = resolve_only(e, "attack", "perfect_guard")
            self.assertEqual(r.received_hit, (False, False))
            self.assertFalse(e.players[0].stable, f"J1 empezando {'STABLE' if start else 'UNSTABLE'}")
            self.assertEqual(r.consequences.count("PLAYER 1 -> STABLE (no recibió hit)"), 0,
                             "No se muestra un STABLE fantasma antes del UNSTABLE")

    def test_desperation_recovers_even_after_being_hit(self):
        e = engine_with_hands(["break"], ["desperation", "guard"], mana=(3, 1), stable=(S, U))
        r = resolve_only(e, "break", "desperation")    # Break vence a Guard: hit
        self.assertTrue(r.received_hit[1])
        self.assertTrue(e.players[1].stable, "La recuperación explícita va al final")

    def test_iron_stance_protects(self):
        e = engine_with_hands(["break"], ["iron_stance"], mana=(3, 3))
        resolve_only(e, "break", "iron_stance")
        self.assertTrue(e.players[1].stable)

    def test_pass_does_not_protect_from_instability(self):
        e = engine_with_hands(["attack", "guard"], ["guard"])
        resolve_only(e, "attack", PASS)
        self.assertFalse(e.players[1].stable)

    def test_turn_change_alone_does_not_touch_stability(self):
        """Cambiar de turno no recupera ni quita Stability: solo las interacciones."""
        e = engine_with_hands(["guard"], ["guard"])
        resolve_only(e, "guard", "guard")
        e.advance()
        self.assertEqual(e.phase, Phase.TURN_END)
        e.players[1].stable = False                     # forzado (p. ej. por un efecto futuro)
        e.run_auto()                                    # TURN_END -> TURN_START -> ... -> REDRAW
        self.assertEqual(e.turn, 2)
        self.assertFalse(e.players[1].stable)


if __name__ == "__main__":
    unittest.main()
