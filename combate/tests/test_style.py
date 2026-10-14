"""Estilo: puntos por victorias consecutivas, rangos, penalizaciones y definitiva."""
import unittest

from helpers import PASS, Phase, choose, engine_with_hands, make_card, play, settle
from test_status import end_turn, next_turn, run_bot_game

from combate.game.combat import CombatEngine
from combate.game.config import RULES
from combate.game.rules import DRAW, WIN
from combate.game.status import StatusId
from combate.game.style import DRAW as S_DRAW, LOSE, ULTIMATE_CATEGORIES, WIN as S_WIN, StyleState, rank_for, \
    rank_progress


def wins(n, start=None):
    st = start or StyleState()
    gains = [st.record(S_WIN, RULES).delta for _ in range(n)]
    return st, gains


def style_events(events):
    return [ev for ev in events if ev.kind == "style"]


# =====================================================================
# Reglas puras (StyleState)
# =====================================================================
class TestRewards(unittest.TestCase):
    def test_reward_per_consecutive_win(self):
        st, gains = wins(8)
        self.assertEqual(gains, [3, 6, 12, 24, 48, 48, 48, 48])
        self.assertEqual(st.streak, 8)

    def test_accumulated_examples(self):
        for n, total in ((1, 3), (3, 21), (5, 93), (7, 189), (10, 333)):
            self.assertEqual(wins(n)[0].points, total, n)

    def test_loss_resets_streak_and_keeps_points_minus_penalty(self):
        st, _ = wins(3)                                # 21 -> rango B
        change = st.record(LOSE, RULES)
        self.assertEqual((change.rank_before, change.delta, st.points, st.streak), ("B", -21, 0, 0),
                         "-30 de B, sin bajar de 0")
        self.assertTrue(change.streak_reset)
        self.assertEqual(st.record(S_WIN, RULES).delta, 3, "La siguiente victoria empieza otra racha")

    def test_draw_resets_streak_and_penalizes(self):
        st, _ = wins(2)                                # 9 -> rango C
        change = st.record(S_DRAW, RULES)
        self.assertEqual((change.rank_before, change.delta, st.points, st.streak), ("C", -8, 1, 0))

    def test_penalty_table(self):
        cases = {"D": (5, 3, 6), "C": (15, 8, 16), "B": (40, 15, 30), "A": (200, 30, 60), "S": (400, 50, 100)}
        for rank, (points, draw_pen, lose_pen) in cases.items():
            for outcome, pen in ((S_DRAW, draw_pen), (LOSE, lose_pen)):
                st = StyleState(points=points)
                self.assertEqual(st.rank(RULES), rank)
                self.assertEqual(st.record(outcome, RULES).delta, -min(pen, points), (rank, outcome))

    def test_penalty_uses_rank_before_resolution(self):
        st = StyleState(points=320, streak=4)
        change = st.record(LOSE, RULES)
        self.assertEqual((st.points, st.rank(RULES), st.streak, change.rank_before), (220, "A", 0, "S"))
        st = StyleState(points=45)                     # A justo en el umbral: empate -30 (no -15 de B)
        st.record(S_DRAW, RULES)
        self.assertEqual((st.points, st.rank(RULES)), (15, "C"))

    def test_never_below_zero(self):
        for points in (0, 2, 5):
            st = StyleState(points=points)
            st.record(LOSE, RULES)
            self.assertEqual(st.points, 0)

    def test_rank_thresholds(self):
        expected = {0: "D", 8: "D", 9: "C", 20: "C", 21: "B", 44: "B", 45: "A", 299: "A", 300: "S", 5000: "S"}
        for points, rank in expected.items():
            self.assertEqual(rank_for(points, RULES)[0], rank, points)
        self.assertEqual(rank_for(300, RULES)[1], "Supremo")
        self.assertEqual(rank_progress(5000, RULES), 1.0, "En S: máximo, sin tope de puntos")
        self.assertAlmostEqual(rank_progress(33, RULES), (33 - 21) / (45 - 21))


class TestUltimateState(unittest.TestCase):
    def test_unlock_lock_and_regain(self):
        st = StyleState(points=299)
        self.assertFalse(st.ultimate_unlocked(RULES))
        st.points = 300
        self.assertTrue(st.ultimate_unlocked(RULES))
        st.record(LOSE, RULES)                          # 300 -> 200 (A)
        self.assertFalse(st.ultimate_unlocked(RULES), "Al bajar de S se bloquea")
        st.points = 310
        self.assertTrue(st.ultimate_unlocked(RULES), "Recupera S y aún no la usó")

    def test_use_once(self):
        st = StyleState(points=400)
        self.assertTrue(st.use_ultimate(RULES))
        self.assertTrue(st.ultimate_used)
        self.assertFalse(st.ultimate_unlocked(RULES))
        self.assertFalse(st.use_ultimate(RULES), "Segunda vez: no")
        st.record(LOSE, RULES)
        st.points = 500
        self.assertFalse(st.ultimate_unlocked(RULES), "El uso no se olvida al volver a S")
        self.assertFalse(StyleState(points=10).use_ultimate(RULES), "Bloqueada: no se puede gastar")


# =====================================================================
# Integración con el combate
# =====================================================================
class TestCombatIntegration(unittest.TestCase):
    def test_win_and_loss_from_real_result(self):
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        e.players[1].style.points = 30                  # B
        r = play(e, "attack", "break")
        self.assertEqual((r.outcome, r.winner), (WIN, 0))
        self.assertEqual([(c.outcome, c.delta) for c in r.style_changes], [(S_WIN, 3), (LOSE, -30)])
        self.assertEqual([p.style.points for p in e.players], [3, 0])

    def test_winner_without_damage_still_wins_style(self):
        e = engine_with_hands(["guard"], ["attack"])
        r = play(e, "guard", "attack")                  # GUARD gana sin daño ni HIT
        self.assertEqual([c.outcome for c in r.style_changes], [S_WIN, LOSE])

    def test_draw_penalizes_both_by_their_own_rank(self):
        e = engine_with_hands(["attack", "guard"], ["attack", "guard"])
        e.players[0].style.points, e.players[1].style.points = 50, 10      # A y C
        r = play(e, "attack", "attack")
        self.assertEqual(r.outcome, DRAW)
        self.assertEqual([c.delta for c in r.style_changes], [-30, -8])

    def test_players_are_independent(self):
        # una carta más en cada mano: si no, la 4ª interacción sería PASS + PASS automático (empate)
        e = engine_with_hands(["attack"] * 3 + ["guard"], ["break"] * 3 + ["guard"], mana=(5, 5))
        for _ in range(3):
            play(e, "attack", "break")
        self.assertEqual((e.players[0].style.points, e.players[0].style.streak), (21, 3))
        self.assertEqual((e.players[1].style.points, e.players[1].style.streak), (0, 0))
        self.assertIsNot(e.players[0].style, e.players[1].style)

    def test_one_update_per_interaction(self):
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        e.pop_events()
        r = play(e, "attack", "break", auto=False)
        e.advance()
        e._apply_style(r)                               # una segunda llamada no hace nada
        self.assertEqual(e.players[0].style.points, 3)
        self.assertEqual(len(style_events(e.pop_events())), 2, "Un evento de Estilo por jugador")

    def test_mega_combo_gives_no_extra_style(self):
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        e.players[0].combo_hits = 2
        r = play(e, "attack", "break", auto=False)
        e.advance()
        e.advance()                                     # MEGA_COMBO
        self.assertEqual(e.phase, Phase.MEGA_COMBO)
        self.assertEqual(e.players[0].style.points, 3, "Solo la victoria de la interacción")
        self.assertEqual(len(r.style_changes), 2)

    def test_periodic_damage_gives_no_style(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, StatusId.BURN)
        e.apply_status(0, StatusId.POISON)
        end_turn(e)                                     # PASS + PASS: empate (D: -3, ya en 0)
        e.pop_events()
        next_turn(e)                                    # BURN y POISON hacen daño
        evs = e.pop_events()
        self.assertTrue(any(ev.kind == "hp" for ev in evs))
        self.assertEqual(style_events(evs), [])
        self.assertEqual([p.style.points for p in e.players], [0, 0])

    def test_style_is_not_the_combo(self):
        e = engine_with_hands(["guard", "attack"], ["attack", "break"], mana=(5, 5))
        play(e, "guard", "attack")                      # gana sin HIT: combo 0, racha 1
        self.assertEqual((e.players[0].combo_hits, e.players[0].style.streak), (0, 1))

    def test_new_game_resets_style(self):
        e = CombatEngine(seed=1)
        e.players[0].style.points, e.players[0].style.ultimate_used = 400, True
        e2 = CombatEngine(seed=1)
        self.assertEqual((e2.players[0].style.points, e2.players[0].style.ultimate_used), (0, False))


class TestPassKeepsStreak(unittest.TestCase):
    """PASS sin recibir un HIT: ni penalización de puntos ni reinicio de racha."""

    def streak_engine(self, hand0, hand1, streak=3, points=40):
        e = engine_with_hands(hand0, hand1, mana=(5, 5))
        e.players[0].style.streak, e.players[0].style.points = streak, points
        return e

    def test_pass_without_hit_keeps_points_and_streak(self):
        e = self.streak_engine(["guard"], ["guard"])
        r = play(e, PASS, "guard")                      # GUARD vence a PASS sin HIT: J1 pierde
        change = r.style_changes[0]
        self.assertEqual((change.outcome, change.delta), (LOSE, 0), "Pierde, pero no le quitan puntos")
        self.assertEqual((e.players[0].style.points, e.players[0].style.streak, change.streak_reset),
                         (40, 3, False), "...ni la racha")
        self.assertEqual(r.style_changes[1].delta, 3, "El ganador suma con normalidad")

    def test_pass_with_hit_applies_normal_penalty(self):
        e = self.streak_engine(["guard"], ["attack"])
        r = play(e, PASS, "attack")                     # ATTACK vence a PASS con HIT
        self.assertTrue(r.received_hit[0])
        self.assertEqual(r.style_changes[0].delta, -30, "Derrota en B: -30")
        self.assertEqual((e.players[0].style.points, e.players[0].style.streak), (10, 0))
        self.assertTrue(r.style_changes[0].streak_reset)

    def test_pass_pass_draw_keeps_both_streaks(self):
        e = self.streak_engine(["guard"], ["guard"])
        e.players[1].style.streak, e.players[1].style.points = 2, 5
        r = play(e, PASS, PASS)
        self.assertEqual(r.outcome, DRAW)
        self.assertEqual([p.style.streak for p in e.players], [3, 2])
        self.assertEqual([c.delta for c in r.style_changes], [0, 0], "Nadie recibió HIT: sin penalización")

    def test_streak_continues_after_pass(self):
        e = self.streak_engine(["guard", "attack"], ["guard", "break"])
        play(e, PASS, "guard")                          # pierde sin HIT: racha 3 se conserva
        self.assertEqual(e.phase, Phase.TURN_END)
        next_turn(e, hands=(["attack"], ["break"]))
        r = play(e, "attack", "break")
        self.assertEqual((r.style_changes[0].delta, e.players[0].style.streak), (24, 4), "4ª victoria: +24")

    def test_playing_a_card_and_losing_still_penalizes(self):
        e = self.streak_engine(["attack"], ["guard"])
        r = play(e, "attack", "guard")                  # pierde con carta (sin recibir HIT)
        self.assertEqual((r.style_changes[0].delta, e.players[0].style.streak), (-30, 0))
        e = self.streak_engine(["attack", "guard"], ["attack", "guard"])
        r = play(e, "attack", "attack")                 # empate con carta
        self.assertEqual((r.style_changes[0].delta, e.players[0].style.streak), (-15, 0))

    def test_forced_pass_without_hit_keeps_streak(self):
        e = self.streak_engine(["attack", "attack"], ["stun_guard", "guard"])
        play(e, "attack", "stun_guard")                 # pierde con carta: racha 0
        e.players[0].style.streak = 2
        points = e.players[0].style.points
        r = play(e, PASS, "guard")                      # PASS obligatorio (PARALYZE) contra GUARD
        self.assertIsNone(r.cards[0])
        self.assertEqual((e.players[0].style.streak, e.players[0].style.points), (2, points))

    def test_frozen_player_is_not_a_pass(self):
        e = self.streak_engine(["guard"], ["guard"])
        e.apply_status(0, StatusId.FREEZE)
        end_turn(e)                                     # PASS + PASS: conserva la racha 3
        next_turn(e, hands=(["guard"], ["guard"]))
        choose(e, 0, PASS)                              # congelado: WAIT (no es PASS)
        choose(e, 1, "guard")
        e.advance()
        self.assertEqual(e.result.status_actions[0], "WAIT")
        self.assertEqual(e.players[0].style.streak, 0, "WAIT no es PASS: la regla normal reinicia la racha")
        self.assertEqual(e.result.style_changes[0].delta, -30, "...y aplica la penalización")


# =====================================================================
# Definitiva provisional
# =====================================================================
class TestUltimate(unittest.TestCase):
    def s_engine(self, hand0=("attack", "guard"), hand1=("break", "guard"), mana=(3, 3), **kw):
        e = engine_with_hands(list(hand0), list(hand1), mana=mana, **kw)
        e.players[0].style.points = 320
        return e

    def test_not_available_below_s(self):
        e = engine_with_hands(["attack"], ["break"])
        e.players[0].style.points = 299
        self.assertEqual(e.ultimate_options(0), [])
        self.assertFalse(e.select_ultimate(0, "ATTACK"))

    def test_all_five_categories_at_s(self):
        e = self.s_engine()
        self.assertEqual(e.ultimate_options(0), list(ULTIMATE_CATEGORIES))
        self.assertEqual(e.ultimate_options(1), [], "El rival no está en S")

    def test_attack_ultimate_resolves_like_a_normal_attack(self):
        normal = engine_with_hands(["attack", "guard"], ["break", "guard"])
        rn = play(normal, "attack", "break", auto=False)
        normal.advance()
        e = self.s_engine()
        hand_before = [c.id for c in e.players[0].hand]
        deck_before = (len(e.players[0].deck), len(e.players[0].deck.discard_pile))
        self.assertTrue(e.select_ultimate(0, "ATTACK"))
        self.assertTrue(e.confirm(0))
        choose(e, 1, "break")
        e.advance()
        r = e.result
        self.assertEqual(r.ultimates, ("ATTACK", None))
        self.assertTrue(r.cards[0].is_ultimate)
        self.assertEqual((r.outcome, r.winner, r.lines, r.hit_generated), (rn.outcome, rn.winner, rn.lines,
                                                                            rn.hit_generated))
        self.assertEqual([d.amount for d in r.damage_events], [d.amount for d in rn.damage_events])
        self.assertEqual(r.stability_changes, rn.stability_changes)
        self.assertEqual(e.players[0].combo_hits, 1)
        self.assertEqual([c.id for c in e.players[0].hand], hand_before, "No gasta ninguna carta de la mano")
        self.assertEqual((len(e.players[0].deck), len(e.players[0].deck.discard_pile)), deck_before,
                         "No entra en el mazo ni en el descarte")
        self.assertTrue(e.players[0].style.ultimate_used)
        self.assertIn("PLAYER 1: DEFINITIVA (ATTACK)", r.consequences)

    def test_ultimate_loses_by_normal_rules(self):
        e = self.s_engine(hand1=("guard",))
        e.select_ultimate(0, "ATTACK")
        e.confirm(0)
        choose(e, 1, "guard")
        e.advance()
        self.assertEqual((e.result.winner, e.result.lines[0]), (1, "GUARD > ATTACK"), "Sin ventajas")

    def test_special_ultimate_is_a_normal_special(self):
        e = self.s_engine(hand0=("attack",), hand1=("attack",), stable=(False, True))
        self.assertTrue(e.select_ultimate(0, "SPECIAL"))
        self.assertTrue(e.special_selection[0].is_special)
        choose(e, 0, "attack")                          # la acción principal se elige aparte
        choose(e, 1, "attack")
        e.advance()
        r = e.result
        self.assertEqual((r.ultimates[0], r.outcome), ("SPECIAL", DRAW), "Recover antes del choque: STABLE = STABLE")
        self.assertEqual(r.mana_paid[0], 0, "La definitiva SPECIAL no cuesta Mana")

    def test_costs_no_mana(self):
        e = self.s_engine(hand0=("attack", "attack"), hand1=("attack", "attack"), mana=(3, 3))
        e.players[0].style.points = 400                 # el empate (-50) no le saca de S
        play(e, "attack", "attack")                     # interacción 2: una carta normal costaría 1
        self.assertTrue(e.select_ultimate(0, "MAGIC"))
        self.assertTrue(e.confirm(0))
        self.assertEqual(e.players[0].mana, 3, "La definitiva no descuenta Mana")
        e2 = self.s_engine(hand0=("attack", "attack"), hand1=("attack", "attack"), mana=(0, 3))
        e2.players[0].style.points = 400
        play(e2, "attack", "attack")
        self.assertEqual(e2.ultimate_options(0), list(ULTIMATE_CATEGORIES), "Sin Mana también puede usarla")

    def test_once_per_game(self):
        e = self.s_engine(hand0=("attack", "attack", "attack"), hand1=("break", "break", "break"), mana=(5, 5))
        e.select_ultimate(0, "ATTACK")
        e.confirm(0)
        choose(e, 1, "break")
        settle(e)
        self.assertGreaterEqual(e.players[0].style.points, 300)
        self.assertEqual(e.ultimate_options(0), [], "Sigue en S, pero ya la usó")
        self.assertFalse(e.select_ultimate(0, "ATTACK"))

    def test_lost_requirements_block_confirm(self):
        e = self.s_engine()
        e.select_ultimate(0, "ATTACK")
        e.players[0].style.points = 100                 # deja de estar en S antes de confirmar
        self.assertFalse(e.confirm(0))
        self.assertFalse(e.players[0].style.ultimate_used)

    def test_drop_from_s_blocks_and_regain_unlocks(self):
        e = self.s_engine(hand0=("attack", "attack"), hand1=("guard", "break"), mana=(5, 5))
        play(e, "attack", "guard")                      # pierde en S: 320 -> 220
        self.assertEqual((e.players[0].style.points, e.ultimate_options(0)), (220, []))
        e.players[0].style.points = 300
        self.assertTrue(e.ultimate_options(0), "De vuelta en S y sin usar: disponible")

    def test_deselect_and_replace_do_not_consume(self):
        e = self.s_engine()
        e.select_ultimate(0, "ATTACK")
        self.assertTrue(e.select_ultimate(0, "ATTACK"), "Pulsarla otra vez la quita")
        self.assertIsNone(e.selection[0])
        e.select_ultimate(0, "BREAK")
        k = next(k for k, c in enumerate(e.players[0].hand) if c.id == "guard")
        e.select(0, k)                                  # una carta normal ocupa su hueco
        self.assertIsNone(e.ultimate_pick[0])
        e.confirm(0)
        choose(e, 1, "break")
        self.assertEqual(e.result.ultimates, (None, None))
        self.assertFalse(e.players[0].style.ultimate_used)

    def test_consumed_once_even_with_repeated_confirm(self):
        e = self.s_engine()
        e.select_ultimate(0, "ATTACK")
        self.assertTrue(e.confirm(0))
        self.assertFalse(e.confirm(0))
        choose(e, 1, "break")
        e.advance()
        self.assertTrue(e.players[0].style.ultimate_used)
        self.assertEqual(sum(1 for c in e.result.consequences if "DEFINITIVA" in c), 1)

    def test_locked_player_cannot_use_it(self):
        e = self.s_engine(hand0=("attack", "attack"), hand1=("stun_guard", "attack"), mana=(5, 5))
        play(e, "attack", "stun_guard")                 # J1 PARALYZED (y baja a A al perder)
        e.players[0].style.points = 400
        self.assertEqual(e.ultimate_options(0), [])

    def test_no_cards_but_ultimate_is_not_auto_passed(self):
        e = engine_with_hands([], ["guard"])
        e.players[0].style.points = 300
        play(e, PASS, "guard")
        self.assertEqual(e.phase, Phase.TURN_END)
        next_turn(e, hands=([], ["guard"]))
        self.assertFalse(e.confirmed[0], "Puede elegir su definitiva aunque no tenga cartas")
        self.assertTrue(e.select_ultimate(0, "GUARD"))


class TestUltimateCostsNoMana(unittest.TestCase):
    """La definitiva cuesta 0 Mana; la disponibilidad (rango S, 1 uso) es aparte."""

    def second_interaction(self, mana, points=(400, 0), hand0=("attack", "attack"), hand1=("attack", "attack")):
        """Motor en la interacción 2 (las cartas normales ya cuestan PLAY_MANA_COST)."""
        e = engine_with_hands(list(hand0), list(hand1), mana=(5, 5))
        for p, pts in zip(e.players, points):
            p.style.points = pts
        play(e, "attack", "attack")                     # empate: S 400 -> 350, sigue en S
        for p, m in zip(e.players, mana):
            p.mana = m
        self.assertEqual(e.phase, Phase.CARD_SELECTION)
        return e

    def test_zero_mana_can_use_it(self):
        e = self.second_interaction(mana=(0, 3))
        self.assertEqual(e.playable_cards(0), [], "Sin Mana no puede jugar cartas normales")
        self.assertFalse(e.confirmed[0], "No se le confirma un PASS automático: tiene la definitiva")
        self.assertTrue(e.select_ultimate(0, "ATTACK"))
        self.assertEqual(e.total_cost(0, e.selection[0], e.special_selection[0]), 0)
        self.assertTrue(e.confirm(0))
        choose(e, 1, "attack")
        e.advance()
        self.assertEqual(e.result.ultimates[0], "ATTACK")
        self.assertEqual(e.result.mana_paid[0], 0)
        self.assertEqual(e.players[0].mana, 0)
        self.assertTrue(e.players[0].style.ultimate_used)

    def test_positive_mana_is_not_spent_nor_gained(self):
        for category in ULTIMATE_CATEGORIES:
            e = self.second_interaction(mana=(2, 3), hand0=("attack", "attack", "attack"))
            self.assertTrue(e.select_ultimate(0, category))
            if category == "SPECIAL":
                self.assertTrue(e.select(0, PASS))
            self.assertTrue(e.confirm(0))
            self.assertEqual((e.players[0].mana, e.displayed_mana(0)), (2, 2), category)
            choose(e, 1, "attack")
            e.advance()
            self.assertEqual(e.result.mana_paid[0], 0, category)
            self.assertEqual(e.players[0].mana, 2, f"{category}: ni descuenta ni concede Mana")

    def test_out_of_s_with_lots_of_mana(self):
        e = engine_with_hands(["attack"], ["break"], mana=(5, 5))
        e.players[0].style.points = 299
        self.assertEqual(e.ultimate_options(0), [])
        self.assertFalse(e.select_ultimate(0, "ATTACK"))

    def test_used_cannot_be_reused_even_with_zero_mana_back_in_s(self):
        e = self.second_interaction(mana=(0, 3), hand1=("attack", "break", "break"))
        e.select_ultimate(0, "ATTACK")
        e.confirm(0)
        choose(e, 1, "break")
        settle(e)
        e.players[0].style.points = 500
        self.assertTrue(e.players[0].style.ultimate_used)
        self.assertEqual(e.ultimate_options(0), [])
        self.assertFalse(e.select_ultimate(0, "ATTACK"))

    def test_regain_s_with_zero_mana_unlocks_again(self):
        e = self.second_interaction(mana=(0, 3))
        e.players[0].style.points = 250
        self.assertEqual(e.ultimate_options(0), [])
        e.players[0].style.points = 300
        self.assertEqual(e.ultimate_options(0), list(ULTIMATE_CATEGORIES))

    def test_normal_cards_keep_their_costs(self):
        e = self.second_interaction(mana=(0, 1), hand1=("attack", "attack", "recover"))
        self.assertFalse(e.select(0, 0), "Carta normal en la interacción 2 con 0 Mana: no")
        # SPECIAL definitiva + acción principal normal: solo se paga la principal
        e.players[0].mana = 1
        self.assertTrue(e.select_ultimate(0, "SPECIAL"))
        self.assertTrue(e.select(0, 0))
        self.assertTrue(e.confirm(0))
        self.assertEqual(e.players[0].mana, 1 - RULES.PLAY_MANA_COST)
        # el rival sigue necesitando 1 (principal) + 1 (SPECIAL) y solo tiene 1
        self.assertTrue(e.select(1, 0))
        k = next(k for k, c in enumerate(e.players[1].hand) if c.id == "recover")
        self.assertFalse(e.select(1, k), "SPECIAL normal: coste y validación de siempre")

    def test_players_are_independent(self):
        e = self.second_interaction(mana=(0, 4), points=(400, 400))
        self.assertTrue(e.select_ultimate(0, "ATTACK"))
        self.assertTrue(e.select_ultimate(1, "GUARD"))
        self.assertTrue(e.confirm(0))
        self.assertTrue(e.confirm(1))
        e.advance()
        r = e.result
        self.assertEqual(r.ultimates, ("ATTACK", "GUARD"))
        self.assertEqual(r.lines[0], "GUARD > ATTACK", "Resolución normal de su categoría")
        self.assertEqual(r.mana_paid, (0, 0))
        self.assertEqual((e.players[0].mana, e.players[1].mana), (0, 4))
        self.assertTrue(all(p.style.ultimate_used for p in e.players))


class TestFullGames(unittest.TestCase):
    def test_games_with_style_and_ultimates(self):
        used = 0
        for seed in range(6):
            e = CombatEngine(decks=("duelo", "arcano"), seed=seed, characters=("blaze", "hero"))
            for p in e.players:
                p.style.points = 300 + 100 * seed
            original = e.select

            def select(i, choice, _e=e, _orig=original):    # el bot prueba su definitiva cuando puede
                options = _e.ultimate_options(i)
                if options and choice != PASS and not _e.ultimate_pick[i]:
                    return _e.select_ultimate(i, options[(_e.turn + i) % len(options)]) or _orig(i, choice)
                return _orig(i, choice)
            e.select = select
            run_bot_game(e)
            used += sum(p.style.ultimate_used for p in e.players)
            for p in e.players:
                self.assertGreaterEqual(p.style.points, 0)
                self.assertEqual(len(p.hand) + len(p.deck) + len(p.deck.discard_pile), RULES.DECK_SIZE,
                                 "La definitiva no añade ni quita cartas")
        self.assertGreater(used, 0)


if __name__ == "__main__":
    unittest.main()
