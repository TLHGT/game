"""Escenario del combate: poses y animaciones de los personajes (ui/fighters.py)."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from helpers import Phase, engine_with_hands, resolve_only  # noqa: E402

import pygame  # noqa: E402

from combate.game.status import StatusEffect, StatusId  # noqa: E402
from combate.ui import fighters as F  # noqa: E402
from combate.ui.battle_screen import View, draw_battle  # noqa: E402


class Fake:
    """Lo mínimo de View que leen las poses."""
    def __init__(self, t=0.0, phase_time=0.0):
        self.time, self.phase_time = t, phase_time
        self.fighter_keys = [None, None]


def pose_of(engine, i, phase_time, t=1.0):
    p = engine.players[i]
    f = 1 if i == 0 else -1
    pose, fx = F.Pose(), []
    F._base_pose(pose, engine, p, i, f, t)
    F._action_pose(pose, engine, Fake(t, phase_time), i, f, fx)
    return pose, fx


class FighterPoseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def engine_at_resolution(self, c0, c1, stable=(True, True)):
        e = engine_with_hands([c0], [c1], stable=stable)
        resolve_only(e, c0, c1)
        self.assertEqual(e.phase, Phase.CARD_RESOLUTION)
        return e

    def test_stable_and_unstable_poses_differ(self):
        e = engine_with_hands(["attack"], ["attack"], stable=(True, False))
        calm, _ = pose_of(e, 0, 0)
        dizzy, _ = pose_of(e, 1, 0)
        self.assertGreater(calm.sy, 0.95)
        self.assertLess(dizzy.sy, 0.9)                       # UNSTABLE: agachado

    def test_redraw_pose(self):
        e = engine_with_hands(["attack"], ["attack"])
        e.sm.phase = Phase.REDRAW
        pose, _ = pose_of(e, 0, 0)
        self.assertGreater(pose.angle, 0)                    # se echa atrás con las cartas

    def test_attack_lunges_and_loser_is_hit(self):
        e = self.engine_at_resolution("attack", "break")     # ATTACK vence a BREAK
        r = e.result
        self.assertEqual(r.winner, 0)
        self.assertTrue(r.received_hit[1])
        atk, fx = pose_of(e, 0, 0.3)
        self.assertGreater(atk.dx, 30)                       # avanza hacia la derecha
        self.assertTrue(fx)                                  # tajo
        hit, _ = pose_of(e, 1, F.IMPACT["ATTACK"] + 0.12)
        self.assertGreater(hit.dx, 10)                       # el de la derecha sale despedido
        self.assertGreater(hit.red + hit.white, 0)

    def test_guard_raises_shield_and_attacker_takes_counter(self):
        e = self.engine_at_resolution("attack", "guard")
        guard, fx = pose_of(e, 1, 0.3)
        self.assertGreater(guard.dx, 0)                      # retrocede (mira a la izquierda)
        self.assertTrue(any(kind == "front" for kind, _ in fx))  # escudo
        self.assertEqual(e.result.winner, 1)

    def test_no_hit_animation_without_hit(self):
        e = self.engine_at_resolution("attack", "guard")      # GUARD gana sin hacer hit
        self.assertFalse(e.result.received_hit[0])
        late, _ = pose_of(e, 0, 1.2)                          # acabada su embestida
        self.assertEqual((late.white, late.red), (0.0, 0.0))

    def test_magic_and_break_animate(self):
        for card in ("magic", "break"):
            e = self.engine_at_resolution(card, "guard")
            pose, fx = pose_of(e, 0, 0.4)                     # proyectil / onda en el suelo
            self.assertTrue(pose.dx or pose.dy, card)
            self.assertTrue(fx, card)

    def test_status_effects(self):
        """FREEZE congela la pose (y la tiñe); cada estado dibuja su efecto sin fallar."""
        e = engine_with_hands(["attack"], ["attack"], stable=(False, True))
        e.players[0].status = StatusEffect(StatusId.FREEZE, cube_hp=20, cube_max=30)
        frozen, _ = pose_of(e, 0, 0)
        self.assertTrue(frozen.ice)
        self.assertEqual((frozen.angle, frozen.sy), (0.0, 1.0))   # ni respira ni se tambalea
        surface = pygame.Surface((1280, 720))
        view = View(e.rules)
        for sid in StatusId:
            e.players[1].status = StatusEffect(sid, turns_left=2, cube_hp=20, cube_max=30)
            for t in (0.0, 0.4, 0.95):
                view.time = t
                F.draw_fighters(surface, e, view)

    def test_draw_battle_renders_stage(self):
        e = self.engine_at_resolution("attack", "break")
        view = View(e.rules)
        surface = pygame.Surface((1280, 720))
        for t in (0.0, 0.2, 0.4, 0.8):
            view.phase_time = t
            draw_battle(surface, e, view)


if __name__ == "__main__":
    unittest.main()
