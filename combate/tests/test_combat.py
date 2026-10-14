"""Tipos, empates, iniciativa, combos, PASS y flujo completo de partida."""
import unittest

from helpers import PASS, Phase, RulesConfig, engine_with_hands, make_card, play

from combate.cards.card import Card
from combate.game.combat import CombatEngine
from combate.game.config import RULES
from combate.game.rules import (DAMAGE_INTERACTION, DAMAGE_MEGA_COMBO, DRAW, WIN, DamageEvent, compare_types,
                        resolve_interaction, sequence_continues)

ATK, GRD, BRK = make_card("attack"), make_card("guard"), make_card("break")


class TestTypes(unittest.TestCase):
    def test_triangle(self):
        self.assertEqual(compare_types("GUARD", "ATTACK"), 1)
        self.assertEqual(compare_types("ATTACK", "BREAK"), 1)
        self.assertEqual(compare_types("BREAK", "GUARD"), 1)
        self.assertEqual(compare_types("ATTACK", "GUARD"), -1)

    def test_resolution_and_explanation(self):
        r = resolve_interaction(GRD, ATK, True, True)
        self.assertEqual((r.outcome, r.winner), (WIN, 0))
        self.assertEqual(r.lines[0], "GUARD > ATTACK")
        self.assertIn("BLOCK", r.tags)
        r = resolve_interaction(GRD, BRK, True, True)
        self.assertEqual((r.winner, r.lines[0]), (1, "BREAK > GUARD"))

    def test_mirror_draws(self):
        for c in (ATK, GRD, BRK):
            r = resolve_interaction(c, make_card(c.id), True, True)
            self.assertEqual(r.outcome, DRAW)
            self.assertEqual(r.lines[0], f"{c.card_type} = {c.card_type}")

    def test_relations_are_configurable(self):
        rules = RulesConfig()
        rules.BEATS = {"ATTACK": "GUARD", "GUARD": "BREAK", "BREAK": "ATTACK"}
        self.assertEqual(resolve_interaction(ATK, GRD, True, True, rules).winner, 0)


class TestInitiative(unittest.TestCase):
    """La iniciativa solo decide si hay otra interacción, no quién gana."""

    def test_rule_table(self):
        P = None
        cases = [
            (ATK, GRD, True), (BRK, GRD, True), (ATK, ATK, True), (BRK, BRK, True),
            (ATK, P, True), (P, BRK, True), (BRK, P, True), (P, ATK, True),
            (GRD, GRD, False), (P, P, False), (GRD, P, False), (P, GRD, False),
        ]
        for a, b, expected in cases:
            self.assertEqual(sequence_continues(a, b), expected, f"{a} + {b}")

    def _after(self, hand0, hand1, c0, c1):
        e = engine_with_hands(hand0, hand1)
        r = play(e, c0, c1)
        return e, r

    def test_attack_guard_continues(self):
        e, r = self._after(["attack", "guard"], ["guard", "guard"], "attack", "guard")
        self.assertTrue(r.continues)
        self.assertEqual(e.phase, Phase.CARD_SELECTION, "Vuelve a elegir carta inmediatamente")
        self.assertEqual(e.interaction_number, 2)

    def test_guard_guard_ends(self):
        e, r = self._after(["guard", "attack"], ["guard", "attack"], "guard", "guard")
        self.assertFalse(r.continues)
        self.assertEqual(e.phase, Phase.TURN_END, "El turno termina")

    def test_pass_guard_ends(self):
        e, r = self._after(["attack"], ["guard", "attack"], PASS, "guard")
        self.assertFalse(r.continues)
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_pass_attack_continues(self):
        e, r = self._after(["guard", "attack"], ["attack", "attack"], PASS, "attack")
        self.assertTrue(r.continues)
        self.assertEqual(e.phase, Phase.CARD_SELECTION)

    def test_break_pass_continues(self):
        e, r = self._after(["break", "attack"], ["guard"], "break", PASS)
        self.assertTrue(r.continues)

    def test_initiative_is_independent_of_type(self):
        """Un GUARD con iniciativa mantiene la secuencia; un ATTACK sin ella no."""
        guard_ini = Card(id="g", name="G", card_type="GUARD", has_initiative=True)
        attack_no = Card(id="a", name="A", card_type="ATTACK", has_initiative=False, generates_hit=True)
        self.assertTrue(sequence_continues(guard_ini, GRD))
        self.assertFalse(sequence_continues(attack_no, GRD))

    def test_effect_can_override_flow(self):
        stopper = Card(id="s", name="Stopper", card_type="ATTACK", has_initiative=True,
                       effects=[{"type": "END_SEQUENCE", "when": "play"}])
        e = engine_with_hands(["attack"], ["guard", "guard"])
        e.players[0].hand = [stopper, make_card("attack")]
        r = play(e, "s", "guard")
        self.assertFalse(r.continues)


class TestNoQuestions(unittest.TestCase):
    def test_no_continue_phase_exists(self):
        names = {p.value for p in Phase}
        self.assertNotIn("COMBO_DECISION", names)
        self.assertNotIn("INTERRUPTION_WINDOW", names)
        self.assertFalse(hasattr(CombatEngine, "combo_decision"))

    def test_sequence_flows_without_input(self):
        e = engine_with_hands(["attack", "attack", "attack"], ["break", "break", "break"])
        for _ in range(3):
            self.assertEqual(e.phase, Phase.CARD_SELECTION)
            play(e, "attack", "break")
        # Sin cartas: ambos pasan automáticamente y, sin iniciativa, termina el turno
        self.assertEqual(e.phase, Phase.TURN_END)


def step_resolution(e, c0, c1):
    """Juega una interacción y se para en CARD_RESOLUTION (daño normal y combo
    aplicados, Mega Combo todavía no)."""
    play(e, c0, c1, auto=False)
    e.advance()                             # CARD_REVEAL -> CARD_RESOLUTION
    return e.result


DMG = make_card("attack").damage            # daño de la propia carta (10)
MEGA = RULES.MEGA_COMBO_DAMAGE


class TestDamage(unittest.TestCase):
    def test_a_normal_damage_on_resolution(self):
        """Caso A: ATTACK vs BREAK -> J2 recibe el daño normal al resolver."""
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        self.assertEqual(e.players[1].hp, RULES.MAX_HP, "Nada de daño durante la selección")
        r = step_resolution(e, "attack", "break")
        self.assertEqual(e.phase, Phase.CARD_RESOLUTION)
        self.assertEqual(e.players[1].hp, RULES.MAX_HP - DMG)
        self.assertEqual(r.damage_events, [DamageEvent(DAMAGE_INTERACTION, 0, 1, DMG)])
        self.assertIn("PLAYER 2 -10 HP", r.consequences)
        hp_events = [ev for ev in e.pop_events() if ev.kind == "hp"]
        self.assertEqual([(ev.player, ev.data["amount"]) for ev in hp_events], [(1, -DMG)], "La UI recibe el daño")

    def test_guard_win_deals_no_damage(self):
        e = engine_with_hands(["attack", "guard"], ["guard", "guard"])
        r = step_resolution(e, "attack", "guard")
        self.assertEqual(r.damage_events, [])
        self.assertEqual(e.players[0].hp, RULES.MAX_HP)

    def test_damage_is_data_driven(self):
        """Cartas que hacen daño sin hit, y hit sin daño."""
        dmg_no_hit = Card(id="d", name="D", card_type="ATTACK", has_initiative=True, damage=7, generates_hit=False)
        hit_no_dmg = Card(id="h", name="H", card_type="ATTACK", has_initiative=True, damage=0, generates_hit=True)
        e = engine_with_hands(["attack"], ["break", "break"])
        e.players[0].hand = [dmg_no_hit, hit_no_dmg]
        r = step_resolution(e, "d", "break")
        self.assertEqual((e.players[1].hp, e.players[0].combo_hits), (RULES.MAX_HP - 7, 0))
        e.advance(); e.advance()            # -> nueva interacción -> selección
        r = step_resolution(e, "h", "break")
        self.assertEqual((e.players[1].hp, e.players[0].combo_hits), (RULES.MAX_HP - 7, 1))

    def test_pass_takes_normal_damage(self):
        """PASS es literalmente pasar: la carta del rival hace su daño entero."""
        e = engine_with_hands(["attack", "guard"], ["guard"])
        r = step_resolution(e, "attack", PASS)
        self.assertEqual(e.players[1].hp, RULES.MAX_HP - 10)
        self.assertEqual(e.players[0].combo_hits, 1, "El hit también cuenta")

    def test_old_pass_rule_still_available(self):
        """La regla antigua (PASS bloquea daño y protege la Stability) sigue en RulesConfig."""
        rules = RulesConfig(PASS_BLOCKS_DAMAGE=True, PASS_PROTECTS_STABILITY=True)
        e = engine_with_hands(["attack", "guard"], ["guard"], rules=rules)
        step_resolution(e, "attack", PASS)
        self.assertEqual((e.players[1].hp, e.players[1].stable), (rules.MAX_HP, True))


class TestCombo(unittest.TestCase):
    def _three_attacks(self):
        return engine_with_hands(["attack", "attack", "attack", "guard"], ["break", "break", "break", "guard"])

    def test_b_c_first_and_second_hit(self):
        e = self._three_attacks()
        step_resolution(e, "attack", "break")
        self.assertEqual((e.players[0].combo_hits, e.players[1].hp), (1, 90))       # Caso B
        e.advance(); e.advance()
        step_resolution(e, "attack", "break")
        self.assertEqual((e.players[0].combo_hits, e.players[1].hp), (2, 80))       # Caso C

    def test_d_third_hit_triggers_mega_combo(self):
        """Caso D: daño normal -> combo 3 -> Mega Combo -> daño adicional -> combo 0."""
        e = self._three_attacks()
        for _ in range(2):
            step_resolution(e, "attack", "break"); e.advance(); e.advance()
        r = step_resolution(e, "attack", "break")
        # En CARD_RESOLUTION: daño normal aplicado y combo en 3, Mega Combo aún no
        self.assertEqual(e.players[0].combo_hits, 3)
        self.assertEqual(e.players[1].hp, RULES.MAX_HP - 3 * DMG)
        self.assertEqual(r.mega_combo, 0)
        e.advance()                         # -> MEGA_COMBO
        self.assertEqual(e.phase, Phase.MEGA_COMBO)
        self.assertEqual(e.players[1].hp, RULES.MAX_HP - 3 * DMG - MEGA)
        self.assertEqual(e.players[0].combo_hits, 0, "Tras el Mega Combo, combo = 0")
        e.advance()                         # iniciativa (ATTACK/BREAK) -> sigue la secuencia
        self.assertEqual(e.phase, Phase.INTERACTION_START)

    def test_f_third_hit_is_normal_damage_plus_mega(self):
        """Caso F: el tercer hit hace daño normal Y Mega Combo, como dos eventos."""
        e = self._three_attacks()
        for _ in range(2):
            step_resolution(e, "attack", "break"); e.advance(); e.advance()
        hp_before = e.players[1].hp
        r = step_resolution(e, "attack", "break")
        e.advance()
        self.assertEqual(r.damage_events, [DamageEvent(DAMAGE_INTERACTION, 0, 1, DMG),
                                           DamageEvent(DAMAGE_MEGA_COMBO, 0, 1, MEGA)])
        self.assertEqual(hp_before - e.players[1].hp, DMG + MEGA)
        kinds = [ev.data.get("damage_type") for ev in e.pop_events() if ev.kind == "hp"]
        self.assertEqual(kinds[-2:], [DAMAGE_INTERACTION, DAMAGE_MEGA_COMBO], "Dos instancias de daño separadas")

    def test_e_combo_breaks_without_hit(self):
        """Caso E: con 2 hits, ATTACK contra GUARD -> sin hit -> combo 0, sin Mega Combo."""
        e = engine_with_hands(["attack", "attack", "attack"], ["break", "break", "guard"])
        for _ in range(2):
            step_resolution(e, "attack", "break"); e.advance(); e.advance()
        self.assertEqual(e.players[0].combo_hits, 2)
        r = step_resolution(e, "attack", "guard")
        self.assertEqual(e.players[0].combo_hits, 0)
        self.assertIsNone(r.mega_combo)
        self.assertIn("PLAYER 1: COMBO ROTO -> 0", r.consequences)
        self.assertEqual(e.players[1].hp, RULES.MAX_HP - 2 * DMG, "Sin daño de Mega Combo")

    def test_draw_also_breaks_combo(self):
        """Los hits deben ser consecutivos: un empate tampoco suma."""
        e = engine_with_hands(["attack", "attack", "guard"], ["guard", "attack", "guard"])
        step_resolution(e, "attack", PASS); e.advance(); e.advance()
        e.players[1].stable = True                 # mismo estado: ATTACK = ATTACK es empate
        r = step_resolution(e, "attack", "attack")
        self.assertEqual(r.outcome, DRAW)
        self.assertEqual(e.players[0].combo_hits, 0)

    def test_g_counters_are_independent(self):
        """Caso G: el combo es de cada jugador; nadie hereda el del otro."""
        e = engine_with_hands(["attack", "attack", "break", "guard"], ["break", "break", "attack", "guard"])
        step_resolution(e, "attack", "break"); e.advance(); e.advance()
        step_resolution(e, "attack", "break"); e.advance(); e.advance()
        self.assertEqual([p.combo_hits for p in e.players], [2, 0])
        r = step_resolution(e, "break", "attack")         # J2 gana: J1 pierde su cadena
        self.assertEqual([p.combo_hits for p in e.players], [0, 1], "J2 empieza desde 1, no hereda 2")
        self.assertEqual(r.combo_after, (0, 1))

    def test_no_infinite_combo(self):
        e = engine_with_hands(["break_guard", "attack"], ["guard", "break"])
        step_resolution(e, "break_guard", "guard")       # 1 + 1 extra = 2
        self.assertEqual(e.players[0].combo_hits, 2)
        e.advance(); e.advance()
        r = step_resolution(e, "attack", "break")
        self.assertEqual(e.players[0].combo_hits, RULES.MAX_COMBO_HITS)
        self.assertEqual(r.mega_combo, 0)

    def test_combo_effects(self):
        """Efectos de combo: proteger la cadena y daño extra de Mega Combo."""
        e = engine_with_hands(["attack", "focus"], ["break", "attack"], mana=(3, 3))
        step_resolution(e, "attack", "break"); e.advance(); e.advance()
        step_resolution(e, "focus", "attack")            # Guard sin hit, pero Focus protege
        self.assertEqual(e.players[0].combo_hits, 1)
        e = engine_with_hands(["attack", "attack", "crescendo"], ["break", "break", "break"], mana=(3, 3))
        for _ in range(2):
            step_resolution(e, "attack", "break"); e.advance(); e.advance()
        r = step_resolution(e, "crescendo", "break"); e.advance()
        self.assertEqual(r.damage_events[-1], DamageEvent(DAMAGE_MEGA_COMBO, 0, 1, MEGA + 10))

    def test_combo_and_initiative_are_independent(self):
        """Mega Combo con GUARD + ... no: tener combo no da iniciativa, ni al revés."""
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        step_resolution(e, "attack", "break"); e.advance(); e.advance()
        r = step_resolution(e, "guard", "guard")         # sin iniciativa
        self.assertFalse(r.continues, "Tener combo no mantiene la secuencia")
        e.advance()
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_ko_ends_game(self):
        e = engine_with_hands(["attack"], ["break"])
        e.players[1].hp = 5
        step_resolution(e, "attack", "break")
        e.run_auto()
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual(e.winner, 0)


class TestPass(unittest.TestCase):
    def test_pass_pass_ends_turn(self):
        e = engine_with_hands(["attack"], ["guard"])
        r = play(e, PASS, PASS)
        self.assertEqual(r.outcome, DRAW)
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_card_vs_pass(self):
        e = engine_with_hands(["attack", "guard"], ["guard"])
        r = play(e, "attack", PASS)
        self.assertEqual((r.outcome, r.winner), (WIN, 0))
        self.assertFalse(e.players[1].stable, "Quien pasa no se defiende: el ATTACK le desestabiliza")
        self.assertEqual(len(e.players[1].hand), 1, "Quien pasa conserva sus cartas")
        self.assertEqual(e.players[1].hp, e.rules.MAX_HP - 10, "Pasar recibe el daño de la carta")

    def test_empty_hand_auto_passes(self):
        e = engine_with_hands([], ["guard"])
        self.assertEqual(e.selection[0], PASS)
        self.assertTrue(e.confirmed[0])


class TestTurnFlow(unittest.TestCase):
    def test_turn_start_regen_draw_redraws(self):
        e = CombatEngine(seed=3)
        e.run_auto()
        p = e.players[0]
        self.assertEqual(len(p.hand), e.rules.MAX_HAND_SIZE)
        self.assertEqual(p.redraws_left, e.rules.MAX_REDRAWS)
        self.assertEqual(p.mana, e.rules.STARTING_MANA)
        old = p.hand[0]
        self.assertTrue(e.redraw(0, 0))
        self.assertIsNot(p.hand[0], old)
        self.assertTrue(e.redraw(0, 1))
        self.assertFalse(e.redraw(0, 2), "Solo 2 cambios")

    def test_every_card_is_selectable(self):
        """Ya no hay cartas de interrupción: todo lo que se puede pagar se puede jugar."""
        e = engine_with_hands(["desperation", "parry", "guard"], ["attack"], mana=(3, 3))
        for k in range(3):
            self.assertTrue(e.select(0, k))

    def test_deck_size(self):
        for p in CombatEngine(seed=3).players:
            self.assertEqual(len(p.deck), p.rules.DECK_SIZE)

    def test_full_game_reaches_game_over(self):
        """Dos bots deterministas juegan hasta que alguien llega a 0 HP."""
        e = CombatEngine(seed=7)
        for _ in range(5000):
            if e.phase == Phase.GAME_OVER:
                break
            if e.sm.is_auto:
                e.advance()
            elif e.phase == Phase.REDRAW:
                e.finish_redraw(0); e.finish_redraw(1)
            elif e.phase == Phase.CARD_SELECTION:
                for i, p in enumerate(e.players):
                    if e.confirmed[i]:
                        continue
                    playable = [k for k, c in enumerate(p.hand) if not c.is_special and e.can_play(i, c)]
                    pref = "ATTACK" if i == 0 else "BREAK"   # P1 vence a P2 por tipo
                    pick = next((k for k in playable if p.hand[k].card_type == pref),
                                playable[0] if playable else None)
                    e.select(i, PASS if pick is None else pick)
                    e.confirm(i)
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual(e.players[1 - e.winner].hp, 0)


if __name__ == "__main__":
    unittest.main()
