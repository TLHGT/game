"""MAGIC: acción ofensiva a distancia. Se enfrenta como ATTACK (RulesConfig.MATCHUP_AS)
y se distingue por su tipo, su canal de daño ("magic") y, si lo tiene, su elemento."""
import unittest

from helpers import PASS, Phase, engine_with_hands, make_card, play, settle
from test_status import run_bot_game

from combate.cards.card import Card
from combate.cards.card_database import DECKS
from combate.game.combat import CombatEngine
from combate.game.config import CHANNEL_MAGIC, CHANNEL_PHYSICAL, RULES
from combate.game.rules import DRAW, WIN, compare_types, resolve_interaction, sequence_continues
from combate.game.status import LOCK_FREEZE, StatusId

MAG, ATK, GRD, BRK = (make_card(c) for c in ("magic", "attack", "guard", "break"))


def resolve_now(e):
    """Tras confirmar ambos: CARD_REVEAL -> CARD_RESOLUTION."""
    e.advance()
    return e.result


def pick(e, i, main, special=None):
    hand = e.players[i].hand
    if special:
        assert e.select(i, next(k for k, c in enumerate(hand) if c.id == special))
    if main == PASS:
        assert e.select(i, PASS)
    else:
        assert e.select(i, next(k for k, c in enumerate(hand) if c.id == main and not c.is_special)), main
    return e.confirm(i)


class TestDefinition(unittest.TestCase):
    def test_magic_is_its_own_action(self):
        self.assertEqual(MAG.card_type, "MAGIC")
        self.assertTrue(MAG.has_initiative and MAG.generates_hit and MAG.causes_instability)
        self.assertEqual(MAG.damage, 10)
        self.assertEqual(MAG.damage_channel, CHANNEL_MAGIC)
        self.assertEqual(ATK.damage_channel, CHANNEL_PHYSICAL)
        self.assertIsNone(MAG.element, "Una MAGIC no tiene por qué tener elemento")
        self.assertFalse(MAG.is_special)

    def test_element_is_separate_from_type_and_channel(self):
        fb = make_card("fire_bolt")
        self.assertEqual((fb.card_type, fb.damage_channel, fb.element), ("MAGIC", CHANNEL_MAGIC, "FIRE"))
        self.assertEqual(fb.effects, [], "El elemento no trae efectos implícitos")

    def test_default_decks_unchanged(self):
        self.assertEqual(DECKS["duelo"], ["attack", "attack", "break", "break", "guard", "perfect_guard",
                                          "unbreakable_guard", "revenge", "overdrive", "recover"])
        for name in ("duelo", "starter", "laboratorio", "estados"):
            self.assertFalse({"magic", "fire_bolt", "flame"} & set(DECKS[name]), name)
        self.assertEqual(len(DECKS["arcano"]), RULES.DECK_SIZE)


class TestMatchups(unittest.TestCase):
    def test_magic_beats_break(self):
        r = resolve_interaction(MAG, BRK, True, True)
        self.assertEqual((r.outcome, r.winner, r.lines[0]), (WIN, 0, "MAGIC > BREAK"))

    def test_guard_beats_magic(self):
        r = resolve_interaction(GRD, MAG, True, True)
        self.assertEqual((r.winner, r.lines[0], r.tags), (0, "GUARD > MAGIC", ["BLOCK"]))
        r = resolve_interaction(make_card("perfect_guard"), MAG, True, True)
        self.assertEqual((r.winner, r.tags), (0, ["COUNTER"]))

    def test_break_still_beats_guard_vs_magic_irrelevant(self):
        self.assertEqual(compare_types("MAGIC", "GUARD"), -1)
        self.assertEqual(compare_types("BREAK", "MAGIC"), -1)

    def test_magic_vs_magic_uses_stability(self):
        cases = {(True, True): (DRAW, None), (False, False): (DRAW, None),
                 (True, False): (WIN, 0), (False, True): (WIN, 1)}
        for (sa, sb), (outcome, winner) in cases.items():
            r = resolve_interaction(MAG, make_card("magic"), sa, sb)
            self.assertEqual((r.outcome, r.winner), (outcome, winner), (sa, sb))
            self.assertEqual(r.lines[0], "MAGIC = MAGIC")

    def test_magic_vs_attack_no_automatic_advantage(self):
        for a, b in ((MAG, ATK), (ATK, MAG)):
            r = resolve_interaction(a, b, True, True)
            self.assertEqual(r.outcome, DRAW, "Ambos STABLE: empate, como ATTACK = ATTACK")
            r = resolve_interaction(a, b, True, False)
            self.assertEqual((r.winner, r.decided_by), (0, "stability"))
        self.assertEqual(compare_types("MAGIC", "ATTACK"), 0)
        r = resolve_interaction(make_card("overdrive"), MAG, True, True)
        self.assertEqual((r.winner, r.decided_by), (0, "priority"), "La prioridad de carta sigue funcionando")

    def test_draw_resets_both_to_stable(self):
        e = engine_with_hands(["magic", "guard"], ["magic", "guard"], stable=(False, False))
        play(e, "magic", "magic")
        self.assertEqual([p.stable for p in e.players], [True, True])

    def test_triangle_unchanged(self):
        expected = {("ATTACK", "BREAK"): 1, ("BREAK", "GUARD"): 1, ("GUARD", "ATTACK"): 1,
                    ("BREAK", "ATTACK"): -1, ("GUARD", "BREAK"): -1, ("ATTACK", "GUARD"): -1}
        for (a, b), v in expected.items():
            self.assertEqual(compare_types(a, b), v, (a, b))
        self.assertEqual(RULES.BEATS, {"ATTACK": "BREAK", "BREAK": "GUARD", "GUARD": "ATTACK"})

    def test_card_level_exceptions_without_global_rules(self):
        """Una MAGIC que ignora GUARD se expresa con un efecto de la carta."""
        piercing = Card(id="piercing", name="Piercing Ray", card_type="MAGIC", has_initiative=True, damage=10,
                        generates_hit=True, damage_channel=CHANNEL_MAGIC,
                        effects=[{"type": "MODIFY_RESULT", "when": "pre", "vs": "GUARD", "result": "win"}])
        self.assertEqual(resolve_interaction(piercing, GRD, True, True).winner, 0)
        self.assertEqual(resolve_interaction(MAG, GRD, True, True).winner, 1, "La MAGIC normal sigue perdiendo")

    def test_effects_can_react_to_magic_channel(self):
        ward = Card(id="ward", name="Spell Ward", card_type="GUARD",
                    effects=[{"type": "GAIN_MANA", "when": "win", "vs_channel": CHANNEL_MAGIC, "amount": 1}])
        for opp, gained in (("magic", 1), ("attack", 0)):
            e = engine_with_hands(["guard"], [opp, "guard"], mana=(2, 2))
            e.players[0].hand = [ward]
            play(e, "ward", opp)
            self.assertEqual(e.players[0].mana, 2 + gained, opp)


class TestCost(unittest.TestCase):
    def test_free_first_then_one(self):
        e = engine_with_hands(["magic", "magic"], ["attack", "attack"], mana=(3, 3))
        self.assertEqual(e.play_cost(0, MAG), 0)
        r = play(e, "magic", "attack")             # MAGIC = ATTACK: empate con iniciativa
        self.assertEqual(r.mana_paid, (0, 0))
        self.assertEqual(e.interaction_number, 2)
        self.assertEqual(e.play_cost(0, MAG), RULES.PLAY_MANA_COST)
        r = play(e, "magic", PASS)
        self.assertEqual(r.mana_paid, (1, 0), "PASS sigue siendo gratis")

    def test_special_plus_magic(self):
        e = engine_with_hands(["magic", "magic", "recover", "recover"], ["attack", "attack"], mana=(3, 3))
        self.assertTrue(pick(e, 0, "magic", "recover"))
        pick(e, 1, "attack")
        r = e.result
        settle(e)
        self.assertEqual(r.mana_paid[0], 1, "Interacción 1: MAGIC gratis + SPECIAL 1")
        self.assertTrue(pick(e, 0, "magic", "recover"))
        self.assertEqual(e.players[0].mana, 0, "Interacción 2: MAGIC 1 + SPECIAL 1")

    def test_cannot_confirm_unaffordable_combo(self):
        e = engine_with_hands(["magic", "magic", "recover"], ["attack", "attack"], mana=(1, 3))
        play(e, "magic", "attack")
        k_rec = next(k for k, c in enumerate(e.players[0].hand) if c.is_special)
        k_mag = next(k for k, c in enumerate(e.players[0].hand) if c.id == "magic")
        self.assertTrue(e.select(0, k_rec))
        self.assertFalse(e.select(0, k_mag), "1 Mana no paga SPECIAL + MAGIC en la interacción 2")


class TestDamageHitCombo(unittest.TestCase):
    def test_hit_damage_and_origin(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"])
        r = play(e, "fire_bolt", "break")
        self.assertEqual(e.players[1].hp, 90)
        self.assertEqual((r.hit_generated, e.players[0].combo_hits), (1, 1))
        ev = r.damage_events[0]
        self.assertEqual((ev.action, ev.channel, ev.element), ("MAGIC", CHANNEL_MAGIC, "FIRE"))
        self.assertIn("PLAYER 2 -10 HP (MAGIC · FIRE)", r.consequences)
        self.assertFalse(e.players[1].stable)

    def test_physical_damage_message_unchanged(self):
        e = engine_with_hands(["attack", "guard"], ["break", "guard"])
        r = play(e, "attack", "break")
        self.assertIn("PLAYER 2 -10 HP", r.consequences)
        self.assertEqual(r.damage_events[0].channel, CHANNEL_PHYSICAL)

    def test_magic_completes_mega_combo(self):
        e = engine_with_hands(["magic", "guard"], ["break", "guard"])
        e.players[0].combo_hits = 2
        r = play(e, "magic", "break", auto=False)
        e.advance()
        e.advance()
        self.assertEqual(e.phase, Phase.MEGA_COMBO)
        self.assertEqual([d.kind for d in r.damage_events], ["interaction", "mega_combo"])
        self.assertEqual(e.players[1].hp, 100 - 10 - RULES.MEGA_COMBO_DAMAGE)
        self.assertEqual(e.players[0].combo_hits, 0)

    def test_mixed_attack_and_magic_hits_chain(self):
        e = engine_with_hands(["attack", "magic", "attack"], ["break", "break", "break"], mana=(5, 5))
        for card in ("attack", "magic"):
            play(e, card, "break")
        self.assertEqual(e.players[0].combo_hits, 2, "Los HIT de MAGIC y ATTACK cuentan en el mismo combo")

    def test_magic_without_hit(self):
        soft = Card(id="soft", name="Soft Bolt", card_type="MAGIC", has_initiative=True, damage=10,
                    generates_hit=False, damage_channel=CHANNEL_MAGIC)
        e = engine_with_hands(["guard"], ["break", "guard"])
        e.players[0].hand = [soft]
        e.players[0].combo_hits = 1
        r = play(e, "soft", "break")
        self.assertEqual((r.hit_generated, r.received_hit), (0, (False, False)))
        self.assertEqual(e.players[0].combo_hits, 0, "Sin HIT no suma (y la regla general rompe el combo)")
        self.assertEqual(e.players[1].hp, 90, "Hace daño aunque no haga HIT")


class TestStatusCompatibility(unittest.TestCase):
    def _flame(self, opp, opp_hand=("guard", "magic", "break")):
        e = engine_with_hands(["flame", "magic", "attack"], list(opp_hand))
        return e, pick(e, 0, "magic", "flame") and pick(e, 1, opp) and resolve_now(e)

    def test_flame_magic_win_applies_burn(self):
        e, r = self._flame("break")
        self.assertEqual((r.outcome, r.winner), (WIN, 0))
        self.assertTrue(e.players[1].has_status(StatusId.BURN))
        self.assertEqual(r.mana_paid[0], RULES.SPECIAL_MANA_COST)

    def test_flame_needs_real_win(self):
        for opp, outcome in (("guard", WIN), ("magic", DRAW)):
            e, r = self._flame(opp)
            self.assertEqual(r.outcome, outcome)
            self.assertIsNone(e.players[1].status, f"MAGIC contra {opp}: no gana, no hay BURN")

    def test_flame_with_attack_does_nothing(self):
        e = engine_with_hands(["flame", "magic", "attack"], ["break"])
        pick(e, 0, "attack", "flame")
        pick(e, 1, "break")
        r = resolve_now(e)
        self.assertEqual(r.winner, 0)
        self.assertIsNone(e.players[1].status)

    def test_element_never_applies_status(self):
        e = engine_with_hands(["fire_bolt", "guard"], ["break", "guard"])
        play(e, "fire_bolt", "break")
        self.assertIsNone(e.players[1].status, "FIRE no implica BURN")

    def test_immunity_still_checked(self):
        e = engine_with_hands(["flame", "magic"], ["break"])
        e.players[1].immunities.add(StatusId.BURN)
        e.apply_status(1, StatusId.POISON)
        pick(e, 0, "magic", "flame")
        pick(e, 1, "break")
        r = resolve_now(e)
        self.assertIn("PLAYER 2 es inmune a BURN", r.consequences)
        self.assertTrue(e.players[1].has_status(StatusId.POISON), "La inmunidad se comprueba antes de reemplazar")

    def test_locked_players_cannot_play_magic(self):
        for sid, lock_pass in ((StatusId.PARALYZE, True), (StatusId.SLEEP, True), (StatusId.FREEZE, False)):
            e = engine_with_hands(["guard", "guard"], ["guard"])
            e.apply_status(0, sid)
            play(e, PASS, PASS)
            e.advance(); e.advance(); e.advance()        # TURN_END -> TURN_START -> DRAW -> REDRAW
            e.players[0].hand = [make_card("magic"), make_card("magic")]
            e.finish_redraw(0); e.finish_redraw(1)
            settle(e)
            if sid == StatusId.SLEEP:                     # SLEEP despierta al empezar el turno
                self.assertIsNone(e.players[0].status)
                continue
            self.assertFalse(e.can_play(0, e.players[0].hand[0]), sid)
            self.assertFalse(e.select(0, 0), sid)
            if lock_pass:
                self.assertEqual(e.selection[0], PASS)
            else:
                self.assertEqual(e.status_lock(0), LOCK_FREEZE)

    def test_magic_hits_ice_cube_not_player(self):
        e = engine_with_hands(["frost_guard", "magic", "magic"], ["attack", "guard"], mana=(5, 5))
        play(e, "frost_guard", "attack")       # J2 congelado
        self.assertTrue(e.players[1].has_status(StatusId.FREEZE))
        pick(e, 0, "magic")
        e.select(1, PASS); e.confirm(1)        # WAIT
        r = resolve_now(e)
        self.assertEqual((e.players[1].hp, e.players[1].status.cube_hp), (100, 20))
        self.assertEqual(r.received_hit, (False, False))


class TestInitiativeAndFlow(unittest.TestCase):
    def test_magic_has_initiative(self):
        for other, cont in ((GRD, True), (None, True), (BRK, True), (ATK, True)):
            self.assertEqual(sequence_continues(MAG, other), cont)
        self.assertFalse(sequence_continues(make_card("recover"), None), "SPECIAL nunca tiene iniciativa")

    def test_one_interaction_per_step(self):
        e = engine_with_hands(["magic", "magic", "guard"], ["guard", "guard", "guard"], mana=(5, 5))
        r = play(e, "magic", "guard")
        self.assertTrue(r.continues)
        self.assertEqual(e.interaction_number, 2)
        r = play(e, "guard", "guard")
        self.assertFalse(r.continues)
        self.assertEqual(e.phase, Phase.TURN_END)

    def test_previous_actions_unchanged(self):
        """Matriz ATTACK/GUARD/BREAK/PASS: mismo resultado que antes de MAGIC."""
        P = None
        expected = [
            (ATK, GRD, WIN, 1), (ATK, BRK, WIN, 0), (BRK, GRD, WIN, 0), (ATK, ATK, DRAW, None),
            (GRD, GRD, DRAW, None), (BRK, BRK, DRAW, None), (ATK, P, WIN, 0), (P, GRD, WIN, 1),
            (P, P, DRAW, None),
        ]
        for a, b, outcome, winner in expected:
            r = resolve_interaction(a, b, True, True)
            self.assertEqual((r.outcome, r.winner), (outcome, winner), (a, b))


class TestFullGame(unittest.TestCase):
    def test_arcano_games_end_without_errors(self):
        burned = False
        for seed in range(10):
            e = run_bot_game(CombatEngine(decks=("arcano", "arcano"), seed=seed))
            magic_damage = [ev for ev in e._all_events if ev.kind == "hp" and ev.data.get("channel") == CHANNEL_MAGIC]
            self.assertTrue(magic_damage, seed)
            burned |= any(ev.kind == "status" and ev.data["status"] == "BURN" for ev in e._all_events)
        self.assertTrue(burned, "FLAME + MAGIC aplica BURN en partidas reales")


if __name__ == "__main__":
    unittest.main()
