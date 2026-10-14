"""Status Effects: BURN, POISON, PARALYZE, FREEZE, SLEEP (game/status.py).

Convención de los tests: aplicar un estado con engine.apply_status() durante la
selección de la interacción k equivale a que una carta lo aplique en k (queda
"fresh": no bloquea ni cuenta hasta la interacción k+1).
"""
import unittest

from helpers import PASS, Phase, RulesConfig, choose, engine_with_hands, make_card, play, settle

from combate.cards.card import Card
from combate.cards.card_database import CARD_DATA, DECKS
from combate.game.combat import CombatEngine
from combate.game.config import RULES
from combate.game.rules import DRAW, WIN, InteractionResult
from combate.game.status import (APPLIED, BLOCKED, BREAK_ICE, IMMUNE, LOCK_FREEZE, LOCK_PASS, REFRESHED, REPLACED, WAIT,
                         StatusId)

BURN, POISON, PARALYZE, FREEZE, SLEEP = (StatusId.BURN, StatusId.POISON, StatusId.PARALYZE, StatusId.FREEZE,
                                         StatusId.SLEEP)
ALL = (BURN, POISON, PARALYZE, FREEZE, SLEEP)


def probe():
    """ATTACK con iniciativa que NO hace hit ni daño: alarga la secuencia sin despertar a nadie."""
    return Card(id="probe", name="Probe", card_type="ATTACK", has_initiative=True)


def next_turn(e, hands=None):
    """Termina el turno en curso (ya en TURN_END) y llega a la selección del siguiente."""
    settle(e)
    assert e.phase == Phase.TURN_END, e.phase
    e.advance()                       # TURN_END -> TURN_START
    e.advance()                       # TURN_START -> DRAW (o GAME_OVER)
    if e.phase == Phase.GAME_OVER:
        return
    e.advance()                       # DRAW -> REDRAW
    if hands:
        for p, ids in zip(e.players, hands):
            p.hand = [make_card(c) for c in ids]
    e.finish_redraw(0)
    e.finish_redraw(1)
    settle(e)


def end_turn(e):
    """PASS + PASS: empate sin iniciativa -> TURN_END."""
    r = play(e, PASS, PASS)
    assert e.phase == Phase.TURN_END
    return r


def hp(e):
    return [p.hp for p in e.players]


def kinds(events):
    return [ev.kind for ev in events]


# =====================================================================
# BURN
# =====================================================================
class TestBurn(unittest.TestCase):
    def test_applied_by_card_with_3_turns_and_no_immediate_damage(self):
        e = engine_with_hands(["searing_break", "guard"], ["guard", "guard"])
        r = play(e, "searing_break", "guard")
        st = e.players[1].status
        self.assertEqual((st.id, st.turns_left), (BURN, RULES.BURN_TURNS))
        self.assertEqual(hp(e), [100, 90], "Solo el daño normal de BREAK: BURN no daña al aplicarse")
        self.assertIn("BURN aplicado a PLAYER 2", r.consequences)

    def test_damage_each_turn_then_expires(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, BURN)
        end_turn(e)
        for expected_hp, left in ((95, 2), (90, 1), (85, None)):
            next_turn(e)
            self.assertEqual(e.players[1].hp, expected_hp)
            st = e.players[1].status
            self.assertEqual(st.turns_left if st else None, left)
            end_turn(e)
        next_turn(e)
        self.assertEqual(e.players[1].hp, 85, "Tras expirar no hace más daño")
        self.assertIsNone(e.players[1].status)
        self.assertIn((1, "BURN ha terminado"), e.status_log)

    def test_once_per_turn_not_per_interaction(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, BURN)
        end_turn(e)
        next_turn(e, hands=(["attack"] * 4, ["attack"] * 4))
        self.assertEqual(e.players[1].hp, 95)
        e.players[0].mana = e.players[1].mana = 5
        for _ in range(3):                    # ATTACK = ATTACK: empates con iniciativa
            play(e, "attack", "attack")
        self.assertEqual(e.interaction_number, 4)
        self.assertEqual(e.players[1].hp, 95, "BURN no se activa por interacción")

    def test_no_hit_no_combo_no_stability(self):
        e = engine_with_hands(["guard"], ["guard"], stable=(True, False))
        e.apply_status(1, BURN)
        end_turn(e)
        e.advance()                           # TURN_END -> TURN_START (combos a 0)
        e.players[1].combo_hits = 2
        e.pop_events()
        e.advance()                           # TURN_START: BURN
        evs = e.pop_events()
        self.assertIn("hp", kinds(evs))
        self.assertNotIn("hit", kinds(evs))
        self.assertEqual(e.players[1].combo_hits, 2)
        self.assertTrue(e.players[1].stable, "PASS + PASS fue empate: ambos STABLE, y BURN no lo cambia")

    def test_defeat_ends_combat_immediately(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, BURN)
        e.players[1].hp = 5
        end_turn(e)
        e.advance()
        e.advance()                           # TURN_START
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual(e.winner, 0)
        self.assertNotIn(Phase.DRAW, e.sm.history[-1:], "El derrotado no llega a robar ni actuar")


# =====================================================================
# POISON
# =====================================================================
class TestPoison(unittest.TestCase):
    def test_applied_by_card_with_3_turns_and_no_immediate_damage(self):
        e = engine_with_hands(["venom_strike", "guard"], ["break", "guard"])
        r = resolve_and_stop(e, "venom_strike", "break")
        self.assertEqual((e.players[1].status.id, e.players[1].status.turns_left), (POISON, RULES.POISON_TURNS))
        self.assertEqual(hp(e), [100, 90])
        self.assertIn("POISON aplicado a PLAYER 2", r.consequences)

    def test_damage_at_next_interaction_start(self):
        e = engine_with_hands(["venom_strike", "guard"], ["break", "guard"])
        play(e, "venom_strike", "break")      # ATTACK tiene iniciativa: hay interacción 2
        self.assertEqual(e.phase, Phase.CARD_SELECTION)
        self.assertEqual(e.players[1].hp, 87, "-10 del ATTACK y -3 al empezar la interacción 2")

    def test_several_interactions_several_activations_one_duration_tick(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, POISON)
        end_turn(e)
        next_turn(e, hands=(["attack"] * 4, ["attack"] * 4))
        self.assertEqual(e.players[1].hp, 97, "Interacción 1: -3")
        self.assertEqual(e.players[1].status.turns_left, 2, "La duración baja una vez al empezar el turno")
        e.players[0].mana = e.players[1].mana = 5
        for n in range(2, 5):
            play(e, "attack", "attack")
            self.assertEqual(e.interaction_number, n)
            self.assertEqual(e.players[1].hp, 100 - 3 * n)
        self.assertEqual(e.players[1].status.turns_left, 2, "No baja por interacción")

    def test_single_damage_per_transition(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, POISON)
        end_turn(e)
        before = e.players[1].hp
        next_turn(e)                          # cambio de turno + inicio de la interacción 1
        self.assertEqual(before - e.players[1].hp, RULES.POISON_DAMAGE, "Ni doble daño ni daño al cambiar de turno")

    def test_expires_after_three_turns_without_losing_activations(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, POISON)             # turno 1
        end_turn(e)
        next_turn(e)                          # turno 2: 3 -> 2, interacción 1: -3
        self.assertEqual((e.players[1].hp, e.players[1].status.turns_left), (97, 2))
        end_turn(e)
        next_turn(e)                          # turno 3: 2 -> 1, interacción 1: -3 (activación legítima)
        self.assertEqual((e.players[1].hp, e.players[1].status.turns_left), (94, 1))
        end_turn(e)
        next_turn(e)                          # turno 4: 1 -> 0, expira antes de la interacción 1
        self.assertIsNone(e.players[1].status)
        self.assertEqual(e.players[1].hp, 94)
        self.assertIn((1, "POISON ha terminado"), e.status_log)

    def test_defeat_ends_combat_immediately(self):
        e = engine_with_hands(["attack", "guard"], ["attack", "guard"])
        e.apply_status(1, POISON)
        e.players[1].hp = 3
        choose(e, 0, "attack")
        choose(e, 1, "attack")
        settle(e)                             # empate con iniciativa -> interacción 2 -> POISON
        self.assertEqual(e.phase, Phase.GAME_OVER)
        self.assertEqual(e.winner, 0)


def resolve_and_stop(e, c0, c1):
    play(e, c0, c1, auto=False)
    e.advance()
    return e.result


# =====================================================================
# PARALYZE
# =====================================================================
class TestParalyze(unittest.TestCase):
    def setUp(self):
        # Stun Guard vence a ATTACK: J1 queda PARALYZED; ATTACK tenía iniciativa
        self.e = engine_with_hands(["attack", "attack", "recover"], ["stun_guard", "stun_guard", "attack"],
                                   mana=(3, 3))
        play(self.e, "attack", "stun_guard")

    def test_forced_pass_and_no_special(self):
        e = self.e
        self.assertEqual(e.phase, Phase.CARD_SELECTION)
        self.assertTrue(e.players[0].has_status(PARALYZE))
        self.assertEqual(e.status_lock(0), LOCK_PASS)
        self.assertEqual((e.selection[0], e.confirmed[0]), (PASS, True))
        self.assertFalse(e.select(0, 0), "No puede elegir ATTACK")
        self.assertFalse(e.select(0, 2), "No puede elegir RECOVER")
        self.assertFalse(any(e.can_play(0, c) for c in e.players[0].hand))
        self.assertIn((0, "PLAYER 1 está PARALYZED: PASS obligatorio"), e.status_log)

    def test_no_mana_no_hp_and_removed_after_interaction(self):
        e = self.e
        mana, life = e.players[0].mana, e.players[0].hp
        choose(e, 1, "attack")
        e.advance()
        r = e.result
        self.assertEqual(r.cards[0], None)
        self.assertEqual(r.mana_paid[0], 0)
        self.assertEqual(e.players[0].mana, mana)
        self.assertEqual(e.players[0].hp, life - 10, "Pasar no protege: ATTACK contra PASS hace su daño normal")
        self.assertIsNone(e.players[0].status, "Desaparece al terminar la interacción")
        self.assertIn("PARALYZE ha terminado", r.consequences)

    def test_cannot_be_reapplied_while_active(self):
        e = self.e
        choose(e, 1, "stun_guard")            # GUARD vence a PASS: intentaría paralizar otra vez
        e.advance()
        r = e.result
        self.assertIn("PLAYER 1 está PARALYZED: inmune a PARALYZE", r.consequences)
        self.assertIsNone(e.players[0].status)
        self.assertFalse(r.continues, "Guard + PASS: sin iniciativa; la parálisis no crea interacciones")
        settle(e)
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_can_be_paralyzed_again_later(self):
        e = self.e
        choose(e, 1, "attack")
        settle(e)
        self.assertEqual(e.apply_status(0, PARALYZE), APPLIED)

    def test_other_statuses_still_apply(self):
        for sid in (BURN, POISON, FREEZE):         # SLEEP: inmunidad cruzada (TestCrossImmunity)
            e = engine_with_hands(["attack"], ["stun_guard"])
            e.apply_status(0, PARALYZE)
            self.assertEqual(e.apply_status(0, sid), REPLACED, sid)
            self.assertEqual(e.players[0].status.id, sid)

    def test_no_extra_interactions(self):
        e = self.e
        self.assertEqual(e.interaction_number, 2)
        choose(e, 1, "attack")
        settle(e)
        self.assertEqual(e.interaction_number, 3, "Una interacción por paso, nada extra")


# =====================================================================
# FREEZE
# =====================================================================
class TestFreeze(unittest.TestCase):
    def frozen(self, hand1=("attack", "attack", "guard", "attack"), mana=(5, 5)):
        """J1 queda congelado por Frost Guard en la interacción 1 (ATTACK sigue)."""
        e = engine_with_hands(["attack", "attack", "recover"], ["frost_guard", *hand1], mana=mana)
        play(e, "attack", "frost_guard")
        self.assertEqual(e.phase, Phase.CARD_SELECTION)
        return e

    def test_cube_created_with_30_hp(self):
        e = self.frozen()
        st = e.players[0].status
        self.assertEqual((st.id, st.cube_hp, st.cube_max), (FREEZE, 30, RULES.ICE_CUBE_HP))
        self.assertIn((0, "PLAYER 1 está FREEZE: ICE CUBE 30/30 HP"), e.status_log)

    def test_blocks_cards_and_specials(self):
        e = self.frozen()
        self.assertEqual(e.status_lock(0), LOCK_FREEZE)
        self.assertEqual(e.status_choices(0), [BREAK_ICE, WAIT])
        self.assertFalse(e.confirmed[0], "Debe elegir BREAK ICE o WAIT")
        self.assertFalse(e.select(0, 0), "ATTACK bloqueado")
        self.assertFalse(e.select(0, 2), "RECOVER (SPECIAL) bloqueado")
        self.assertFalse(e.confirm(0), "Nada elegido todavía")
        self.assertTrue(e.select(0, BREAK_ICE))
        self.assertFalse(e.select(1, BREAK_ICE), "BREAK ICE solo para el congelado")

    def test_damage_goes_to_cube_without_hit(self):
        e = self.frozen()
        e.players[1].combo_hits = 1
        self.assertTrue(e.select(0, WAIT) and e.confirm(0))
        choose(e, 1, "attack")
        e.advance()
        r = e.result
        self.assertEqual(r.lines[0], "ATTACK vs ICE CUBE")
        self.assertEqual(e.players[0].hp, 100, "HP protegido")
        self.assertEqual(e.players[0].status.cube_hp, 20)
        self.assertEqual(r.received_hit, (False, False), "Golpear el cubo no es HIT")
        self.assertEqual(r.hit_generated, 0)
        self.assertEqual([(d.amount, d.to_cube) for d in r.damage_events], [(10, True)])
        self.assertEqual(e.players[1].combo_hits, 0, "Sin HIT no suma combo (regla de combo existente)")
        self.assertTrue(e.players[0].stable, "El cubo también protege de desestabilizar")
        self.assertIn("ICE CUBE de PLAYER 1 -10 (20/30)", r.consequences)

    def test_break_ice_and_wait(self):
        e = self.frozen()
        mana = e.players[0].mana
        self.assertTrue(e.select(0, BREAK_ICE) and e.confirm(0))
        choose(e, 1, "guard")
        e.advance()
        r = e.result
        self.assertEqual(e.players[0].status.cube_hp, 15, "BREAK ICE: 15 al cubo")
        self.assertEqual(e.players[0].mana, mana, "BREAK ICE no cuesta Mana")
        self.assertEqual((r.hit_generated, r.received_hit), (0, (False, False)), "Ni HIT ni combo")
        self.assertEqual(hp(e), [100, 100])
        self.assertFalse(r.continues, "BREAK ICE no tiene iniciativa: GUARD + BREAK ICE termina")
        e2 = self.frozen()
        self.assertTrue(e2.select(0, PASS) and e2.selection[0] == WAIT, "PASS se interpreta como WAIT")
        e2.confirm(0)
        choose(e2, 1, "guard")
        e2.advance()
        self.assertEqual(e2.players[0].status.cube_hp, 30, "WAIT no daña el cubo")

    def test_destroying_cube_frees_without_overflow(self):
        e = self.frozen()
        e.players[0].status.cube_hp = 4
        self.assertTrue(e.select(0, BREAK_ICE) and e.confirm(0))
        choose(e, 1, "attack")
        e.advance()
        r = e.result
        self.assertIsNone(e.players[0].status, "Cubo destruido: FREEZE eliminado")
        self.assertEqual(e.players[0].hp, 100, "El daño sobrante no pasa al jugador")
        self.assertIn("ICE CUBE destruido: PLAYER 1 queda libre", r.consequences)
        self.assertIn("PLAYER 1: BREAK ICE (el cubo ya estaba roto)", r.consequences)
        self.assertEqual(r.cards[0], None, "Liberarse no da una acción ofensiva gratis")
        settle(e)
        self.assertEqual(e.status_choices(0), [], "En la siguiente interacción actúa con normalidad")
        self.assertTrue(e.playable_cards(0))

    def test_protected_during_whole_breaking_interaction(self):
        """Si BREAK ICE rompe el cubo, el daño del rival en ESA interacción tampoco llega."""
        e = self.frozen()
        e.players[0].status.cube_hp = 15
        self.assertTrue(e.select(0, BREAK_ICE) and e.confirm(0))
        choose(e, 1, "attack")
        e.advance()
        self.assertIsNone(e.players[0].status)
        self.assertEqual(e.players[0].hp, 100)

    def test_freeze_on_third_hit(self):
        """El 3er HIT congela: su daño normal llega al HP (el estado se aplica
        después) y el daño adicional del Mega Combo, ya congelado, va al cubo."""
        frost_atk = Card(id="frost_attack", name="Frost Attack", card_type="ATTACK", has_initiative=True,
                         damage=10, generates_hit=True, causes_instability=True,
                         effects=[{"type": "APPLY_STATUS", "when": "win", "status": "FREEZE"}])
        e = engine_with_hands(["guard"], ["break", "guard"])
        e.players[0].hand = [frost_atk]
        e.players[0].combo_hits = 2
        r = play(e, "frost_attack", "break", auto=False)
        e.advance()                           # CARD_RESOLUTION
        self.assertEqual(e.players[1].hp, 90)
        self.assertTrue(e.players[1].has_status(FREEZE))
        e.advance()                           # MEGA_COMBO
        self.assertEqual(e.phase, Phase.MEGA_COMBO)
        self.assertEqual((e.players[1].hp, e.players[1].status.cube_hp), (90, 10))
        self.assertEqual([(d.kind, d.to_cube) for d in r.damage_events],
                         [("interaction", False), ("mega_combo", True)])

    def test_recover_does_not_remove_freeze(self):
        e = engine_with_hands(["guard", "recover"], ["guard"])
        e.apply_status(0, FREEZE)
        end_turn(e)
        next_turn(e, hands=(["guard", "recover"], ["guard"]))
        self.assertFalse(e.playable_specials(0), "Congelado: no puede usar RECOVER")
        self.assertTrue(e.players[0].has_status(FREEZE))


# =====================================================================
# SLEEP
# =====================================================================
class TestSleep(unittest.TestCase):
    def test_applied_by_card_and_forces_pass(self):
        e = engine_with_hands(["attack", "lullaby", "attack", "recover"], ["break", "guard", "attack"],
                              mana=(5, 5))
        k = next(i for i, c in enumerate(e.players[0].hand) if c.id == "lullaby")
        self.assertTrue(e.select(0, k))
        choose(e, 0, "attack")
        choose(e, 1, "break")                 # ATTACK > BREAK con HIT -> SLEEP
        e.advance()
        r = e.result
        self.assertEqual(e.players[1].status.id, SLEEP)
        self.assertEqual(e.players[1].status.interactions_left, 3)
        self.assertIn("SLEEP aplicado a PLAYER 2", r.consequences)
        settle(e)
        self.assertEqual((e.selection[1], e.confirmed[1]), (PASS, True))
        self.assertFalse(e.select(1, 0))
        self.assertIn((1, "PLAYER 2 está SLEEP: PASS obligatorio"), e.status_log)

    def _asleep(self, hand0=("attack", "guard", "attack")):
        e = engine_with_hands([*hand0], ["guard", "guard"], mana=(5, 5))
        e.players[0].hand.append(probe())
        e.apply_status(1, SLEEP)
        play(e, "probe", PASS)                # interacción que lo aplica: no cuenta
        self.assertEqual(e.players[1].status.interactions_left, 3)
        self.assertEqual(e.phase, Phase.CARD_SELECTION)
        return e

    def test_wakes_on_real_hit(self):
        e = self._asleep()
        choose(e, 0, "attack")
        e.advance()
        r = e.result
        self.assertTrue(r.received_hit[1])
        self.assertIsNone(e.players[1].status)
        self.assertIn("PLAYER 2 ha despertado", r.consequences)
        self.assertEqual(r.cards[1], None, "No recupera una acción en esta interacción")

    def test_attack_without_hit_does_not_wake(self):
        e = self._asleep()
        choose(e, 0, "guard")                 # GUARD vence a PASS sin HIT
        e.advance()
        self.assertTrue(e.players[1].has_status(SLEEP))
        self.assertEqual(e.players[1].status.interactions_left, 2)

    def test_expires_after_three_later_interactions(self):
        e = self._asleep()
        for _ in range(2):
            e.players[0].hand.append(probe())
        left = []
        for _ in range(3):
            e.players[0].hand.append(probe())
            play(e, "probe", PASS)
            st = e.players[1].status
            left.append(st.interactions_left if st else None)
        self.assertEqual(left, [2, 1, None])
        self.assertIn((1, "PLAYER 2 ha despertado"), e.status_log)

    def test_expires_at_turn_start(self):
        e = engine_with_hands(["guard"], ["guard"])
        e.apply_status(1, SLEEP)
        end_turn(e)
        self.assertEqual(e.players[1].status.interactions_left, 3, "La interacción que lo aplicó no cuenta")
        next_turn(e)
        self.assertIsNone(e.players[1].status)
        self.assertFalse(e.confirmed[1], "Ya puede elegir con normalidad")

    def test_simultaneous_end_conditions_remove_once(self):
        e = self._asleep()
        e.players[1].status.interactions_left = 1     # el contador y el HIT coinciden
        e.pop_events()
        choose(e, 0, "attack")
        e.advance()
        removed = [ev for ev in e.pop_events() if ev.kind == "status" and ev.data["change"] == "removed"]
        self.assertEqual(len(removed), 1)
        self.assertEqual(e.result.consequences.count("PLAYER 2 ha despertado"), 1)
        settle(e)
        self.assertEqual(e.phase, Phase.CARD_SELECTION)
        self.assertFalse(e.confirmed[1])


# =====================================================================
# Reemplazo, inmunidad y extensibilidad
# =====================================================================
class TestReplacementAndImmunity(unittest.TestCase):
    def setUp(self):
        self.e = engine_with_hands(["guard"], ["guard"])

    def test_single_status_and_replacement(self):
        e = self.e
        self.assertEqual(e.apply_status(1, BURN), APPLIED)
        self.assertEqual(e.apply_status(1, SLEEP), REPLACED)
        self.assertEqual(e.players[1].status.id, SLEEP)
        self.assertIn((1, "PLAYER 2: BURN -> SLEEP"), e.status_log)

    def test_reapply_same_resets_counters(self):
        e = self.e
        e.apply_status(1, BURN)
        e.players[1].status.turns_left = 1
        self.assertEqual(e.apply_status(1, BURN), REFRESHED)
        self.assertEqual(e.players[1].status.turns_left, 3)
        e.apply_status(0, FREEZE)
        e.players[0].status.cube_hp = 3
        self.assertEqual(e.apply_status(0, FREEZE), REFRESHED)
        self.assertEqual(e.players[0].status.cube_hp, 30)

    def test_immunity(self):
        e = self.e
        e.players[1].immunities.add(BURN)
        self.assertEqual(e.apply_status(1, BURN), IMMUNE)
        self.assertIsNone(e.players[1].status)
        self.assertEqual(e.apply_status(1, POISON), APPLIED, "Inmune a BURN no lo es a POISON")
        self.assertEqual(e.apply_status(1, BURN), IMMUNE)
        self.assertEqual(e.players[1].status.id, POISON, "Un intento inmune no reemplaza el estado actual")

    def test_paralyze_immunity_only_while_active(self):
        e = self.e
        self.assertEqual(e.apply_status(1, PARALYZE), APPLIED)
        self.assertEqual(e.apply_status(1, PARALYZE), BLOCKED)
        e.remove_status(1)
        self.assertEqual(e.apply_status(1, PARALYZE), APPLIED)

    def test_remove_is_idempotent(self):
        e = self.e
        e.apply_status(1, BURN)
        self.assertTrue(e.remove_status(1))
        self.assertFalse(e.remove_status(1))

    def test_statuses_do_not_change_stability(self):
        for sid in ALL:
            for stable in (True, False):
                e = engine_with_hands(["guard"], ["guard"], stable=(stable, stable))
                e.apply_status(0, sid)
                self.assertEqual(e.players[0].stable, stable, sid)

    def test_recover_does_not_cleanse(self):
        e = engine_with_hands(["guard", "recover"], ["guard"], stable=(False, True))
        e.apply_status(0, POISON)
        k = next(i for i, c in enumerate(e.players[0].hand) if c.is_special)
        self.assertTrue(e.select(0, k))
        choose(e, 0, "guard")
        choose(e, 1, "guard")
        self.assertTrue(e.players[0].stable, "RECOVER sí recupera STABLE")
        self.assertTrue(e.players[0].has_status(POISON), "...pero no elimina estados")

    def test_only_explicit_effects_apply_statuses(self):
        """Sin RNG ni elementos: solo las cartas con APPLY_STATUS aplican estados."""
        with_status = {d["id"] for d in CARD_DATA if any(x["type"] == "APPLY_STATUS" for x in d.get("effects", []))}
        self.assertEqual(with_status, {"flame", "searing_break", "venom_strike", "stun_guard", "frost_guard",
                                       "lullaby"})
        for deck in ("duelo", "starter", "laboratorio"):
            self.assertFalse(with_status & set(DECKS[deck]), deck)
            e = CombatEngine(decks=(deck, deck), seed=3)
            run_bot_game(e)
            self.assertFalse(any(ev for ev in e._all_events if ev.kind == "status"), deck)

    def test_flame_not_in_default_decks(self):
        for name in ("duelo", "starter", "laboratorio", "estados"):
            self.assertNotIn("flame", DECKS[name], "Solo en el mazo de prueba arcano")


# =====================================================================
# Inmunidad cruzada PARALYZE / SLEEP
# =====================================================================
class TestCrossImmunity(unittest.TestCase):
    def setUp(self):
        self.e = engine_with_hands(["guard"], ["guard"])

    def test_matrix(self):
        cases = [
            (PARALYZE, PARALYZE, BLOCKED), (PARALYZE, SLEEP, BLOCKED),
            (SLEEP, PARALYZE, BLOCKED), (SLEEP, SLEEP, BLOCKED),
            (BURN, SLEEP, REPLACED), (POISON, PARALYZE, REPLACED), (FREEZE, SLEEP, REPLACED),
            (BURN, PARALYZE, REPLACED), (POISON, SLEEP, REPLACED), (FREEZE, PARALYZE, REPLACED),
        ]
        for current, new, expected in cases:
            e = engine_with_hands(["guard"], ["guard"])
            e.apply_status(1, current)
            self.assertEqual(e.apply_status(1, new), expected, (current, new))
            self.assertEqual(e.players[1].status.id, current if expected == BLOCKED else new, (current, new))

    def test_rejection_keeps_status_and_duration(self):
        e = self.e
        for current, attempts in ((PARALYZE, (SLEEP, PARALYZE)), (SLEEP, (PARALYZE, SLEEP))):
            e.remove_status(1)
            e.apply_status(1, current)
            st = e.players[1].status
            st.interactions_left, st.fresh = 1, False
            e.pop_events()
            for sid in attempts:
                self.assertEqual(e.apply_status(1, sid), BLOCKED)
            self.assertIs(e.players[1].status, st, "Mismo estado: ni reemplazado ni reiniciado")
            self.assertEqual((st.interactions_left, st.fresh), (1, False), "Sin extender la duración")
            self.assertNotIn("status", kinds(e.pop_events()), "Un rechazo no emite cambios de estado")
        self.assertIn((1, "PLAYER 2 está SLEEP: inmune a PARALYZE"), e.status_log)
        self.assertIn((1, "PLAYER 2 está PARALYZED: inmune a SLEEP"), e.status_log)

    def test_personal_immunity_checked_first(self):
        e = self.e
        e.players[1].immunities.add(SLEEP)
        e.apply_status(1, BURN)
        self.assertEqual(e.apply_status(1, SLEEP), IMMUNE)
        self.assertEqual(e.players[1].status.id, BURN)

    def test_after_paralyze_expires_both_apply_again(self):
        for sid in (SLEEP, PARALYZE):
            e = engine_with_hands(["attack", "attack"], ["stun_guard", "attack"], mana=(5, 5))
            play(e, "attack", "stun_guard")       # J1 PARALYZED para la interacción 2
            self.assertEqual(e.apply_status(0, sid), BLOCKED)
            choose(e, 1, "attack")
            settle(e)                             # fin de la interacción 2: PARALYZE termina
            self.assertIsNone(e.players[0].status)
            self.assertEqual(e.apply_status(0, sid), APPLIED, sid)

    def test_after_sleep_expires_both_apply_again(self):
        for sid in (PARALYZE, SLEEP):
            e = engine_with_hands(["guard"], ["guard"])
            e.apply_status(1, SLEEP)
            self.assertEqual(e.apply_status(1, sid), BLOCKED)
            end_turn(e)
            next_turn(e)                          # SLEEP despierta al empezar el turno
            self.assertIsNone(e.players[1].status)
            self.assertEqual(e.apply_status(1, sid), APPLIED, sid)

    def test_other_statuses_unchanged(self):
        e = self.e
        e.apply_status(1, BURN)
        e.players[1].status.turns_left = 1
        self.assertEqual(e.apply_status(1, BURN), REFRESHED)
        self.assertEqual(e.players[1].status.turns_left, RULES.BURN_TURNS)
        self.assertEqual(e.apply_status(1, POISON), REPLACED)
        self.assertEqual(e.apply_status(1, POISON), REFRESHED)
        self.assertEqual(e.apply_status(1, FREEZE), REPLACED)
        self.assertEqual(e.players[1].status.cube_hp, RULES.ICE_CUBE_HP)
        e.apply_status(1, PARALYZE)
        self.assertEqual(e.apply_status(1, BURN), REPLACED, "PARALYZE no bloquea BURN")
        e.apply_status(1, SLEEP)
        self.assertEqual(e.apply_status(1, FREEZE), REPLACED, "SLEEP no bloquea FREEZE")
        end_turn(e)
        next_turn(e)
        self.assertTrue(e.players[1].has_status(FREEZE), "FREEZE no expira por turno")

    def test_card_cannot_chain_sleep_onto_paralyze(self):
        """Lullaby hace HIT a un jugador PARALYZED: el SLEEP se rechaza y la
        interacción se resuelve exactamente igual (hit, combo, iniciativa)."""
        e = engine_with_hands(["attack", "attack", "lullaby"], ["stun_guard", "guard"], mana=(5, 5))
        play(e, "attack", "stun_guard")           # J1 PARALYZED
        e.players[0].hand = [make_card("attack")]
        e.players[1].hand = [make_card("attack"), make_card("lullaby")]
        e.select(1, 1)
        choose(e, 1, "attack")                    # ATTACK + LULLABY contra el PASS obligatorio
        e.advance()
        r = e.result
        self.assertEqual((r.winner, r.hit_generated, r.received_hit), (1, 1, (True, False)))
        self.assertIn("PLAYER 1 está PARALYZED: inmune a SLEEP", r.consequences)
        self.assertTrue(r.continues, "La iniciativa de ATTACK decide, no el estado")
        self.assertEqual(e.players[1].combo_hits, 1)
        self.assertEqual(e.players[0].hp, 90, "PASS no bloquea nada: el ATTACK hace su daño")
        self.assertIsNone(e.players[0].status, "PARALYZE termina con la interacción; SLEEP nunca se aplicó")
        settle(e)
        self.assertFalse(e.confirmed[0], "Siguiente interacción: puede actuar")

    def test_card_cannot_paralyze_sleeping_player(self):
        e = engine_with_hands(["stun_guard", "guard"], ["guard", "guard"], mana=(5, 5), stable=(True, False))
        e.players[0].hand.append(probe())
        e.apply_status(1, SLEEP)
        play(e, "probe", PASS)                    # interacción que aplica SLEEP: no cuenta
        mana = [p.mana for p in e.players]
        choose(e, 0, "stun_guard")                # GUARD vence al PASS de quien duerme
        e.advance()
        r = e.result
        self.assertIn("PLAYER 2 está SLEEP: inmune a PARALYZE", r.consequences)
        self.assertEqual(e.players[1].status.id, SLEEP)
        self.assertEqual(e.players[1].status.interactions_left, 2, "La duración de SLEEP sigue su curso normal")
        self.assertEqual((r.hit_generated, r.continues), (0, False))
        self.assertEqual([p.mana for p in e.players], [mana[0] - 1, mana[1]], "Solo el coste normal de la carta")
        self.assertTrue(e.players[1].stable, "Sin hit: recupera STABLE por la regla normal")


# =====================================================================
# FLAME: condición sobre el resultado real
# =====================================================================
class TestFlame(unittest.TestCase):
    def magic(self):
        return Card(id="bolt", name="Bolt", card_type="MAGIC", has_initiative=True, damage=10, generates_hit=True)

    def test_win_with_magic_applies_burn(self):
        e = engine_with_hands(["flame"], ["guard"])
        e.players[0].hand.append(self.magic())
        self.assertTrue(e.select(0, 0))           # FLAME
        self.assertTrue(e.select(0, 1))           # MAGIC (acción principal)
        self.assertTrue(e.confirm(0))
        self.assertEqual(e.result, None)
        choose(e, 1, PASS)
        e.advance()
        r = e.result
        self.assertEqual((r.outcome, r.winner), (WIN, 0))
        self.assertTrue(e.players[1].has_status(BURN))
        self.assertEqual(r.mana_paid[0], RULES.SPECIAL_MANA_COST, "FLAME paga como SPECIAL")

    def test_win_with_other_type_does_not_apply(self):
        e = engine_with_hands(["flame", "attack"], ["break"])
        self.assertTrue(e.select(0, 0))
        choose(e, 0, "attack")
        choose(e, 1, "break")
        e.advance()
        self.assertEqual((e.result.outcome, e.result.winner), (WIN, 0))
        self.assertIsNone(e.players[1].status, "Ganó, pero no con MAGIC")

    def test_condition_uses_real_outcome(self):
        flame = make_card("flame").effects[0]
        bolt, guard = self.magic(), make_card("guard")
        cases = [
            (InteractionResult(WIN, 0, (bolt, guard)), True),
            (InteractionResult(WIN, 1, (bolt, guard)), False),       # pierde aunque eligiera MAGIC
            (InteractionResult(DRAW, None, (bolt, bolt)), False),    # empate
            (InteractionResult(WIN, 0, (guard, None)), False),       # gana con otro tipo
        ]
        for r, expected in cases:
            self.assertEqual(CombatEngine._status_condition(flame, r, 0), expected, (r.outcome, r.winner))


# =====================================================================
# Integración
# =====================================================================
def run_bot_game(e, max_steps=5000):
    """Partida completa con un bot determinista. Guarda todos los eventos en e._all_events
    y comprueba invariantes en cada paso."""
    e._all_events = []
    steps = 0
    while e.phase != Phase.GAME_OVER and steps < max_steps:
        steps += 1
        for p in e.players:
            assert p.hp >= 0
            if p.status is not None and p.status.id == StatusId.FREEZE:
                assert 0 < p.status.cube_hp <= p.status.cube_max
        if e.sm.is_auto:
            e.advance()
        elif e.phase == Phase.REDRAW:
            e.finish_redraw(0)
            e.finish_redraw(1)
        else:
            for i in range(2):
                if e.confirmed[i]:
                    continue
                choices = e.status_choices(i)
                if choices:
                    assert e.select(i, choices[(e.turn + e.interaction_number) % len(choices)])
                else:
                    specials = e.playable_specials(i)
                    if specials and e.interaction_number % 2:
                        e.select(i, e.players[i].hand.index(specials[0]))
                    playable = e.playable_cards(i)
                    if playable and (e.turn + i) % 4:
                        pick = playable[(e.turn * 3 + e.interaction_number + i) % len(playable)]
                        assert e.select(i, e.players[i].hand.index(pick))
                    else:
                        e.select(i, PASS)
                assert e.confirm(i)
        e._all_events += e.pop_events()
    assert e.phase == Phase.GAME_OVER, "La partida debe terminar"
    return e


class TestIntegration(unittest.TestCase):
    def test_full_games_with_status_deck(self):
        seen = set()
        for seed in range(12):
            e = run_bot_game(CombatEngine(decks=("estados", "estados"), seed=seed))
            seen |= {ev.data["status"] for ev in e._all_events if ev.kind == "status" and ev.data["status"]}
        self.assertEqual(seen, {s.value for s in ALL}, "Los cinco estados aparecen jugando")

    def test_status_games_are_deterministic(self):
        a = run_bot_game(CombatEngine(decks=("estados", "estados"), seed=5))
        b = run_bot_game(CombatEngine(decks=("estados", "estados"), seed=5))
        self.assertEqual([(ev.kind, ev.player, ev.data) for ev in a._all_events],
                         [(ev.kind, ev.player, ev.data) for ev in b._all_events])

    def test_status_does_not_grant_initiative(self):
        e = engine_with_hands(["guard", "guard"], ["guard"])
        e.apply_status(1, POISON)
        r = play(e, "guard", PASS)
        self.assertFalse(r.continues)
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_status_damage_does_not_touch_mana_or_combo(self):
        e = engine_with_hands(["attack", "attack"], ["attack", "attack"], mana=(2, 2))
        e.apply_status(1, POISON)
        e.players[0].combo_hits = 1
        play(e, "attack", "attack")            # empate: sigue -> POISON en la interacción 2
        self.assertEqual(e.players[1].hp, 97)
        self.assertEqual([p.mana for p in e.players], [2, 2], "Interacción 1 gratis; POISON no gasta Mana")
        self.assertEqual(e.players[1].combo_hits, 0)

    def test_combo_and_mega_combo_still_work_with_status(self):
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        e.apply_status(0, BURN)                 # el atacante tiene un estado: no cambia nada
        e.players[0].combo_hits = 2
        r = play(e, "attack", "break", auto=False)
        e.advance()
        e.advance()                             # MEGA_COMBO
        self.assertEqual(e.phase, Phase.MEGA_COMBO)
        self.assertEqual([d.kind for d in r.damage_events], ["interaction", "mega_combo"])
        self.assertEqual(e.players[1].hp, 70)

    def test_custom_rules_values(self):
        rules = RulesConfig()
        rules.BURN_DAMAGE, rules.ICE_CUBE_HP, rules.BREAK_ICE_DAMAGE = 7, 50, 20
        e = engine_with_hands(["guard"], ["guard"], rules=rules)
        e.apply_status(1, BURN)
        e.apply_status(0, FREEZE)
        self.assertEqual(e.players[0].status.cube_hp, 50)
        end_turn(e)
        next_turn(e)
        self.assertEqual(e.players[1].hp, 93)


if __name__ == "__main__":
    unittest.main()
