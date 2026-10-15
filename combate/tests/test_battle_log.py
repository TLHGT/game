"""Registro del combate: al pasar el ratón por el nombre de una carta se ve la carta."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from helpers import engine_with_hands, play  # noqa: E402

from combate.ui import battle_log as L  # noqa: E402
from combate.ui import theme as T  # noqa: E402


class TestBattleLogHover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_card_names_are_found(self):
        e = engine_with_hands(["attack"] * 5, ["break"] * 5)
        log = L.BattleLog()
        play(e, "attack", "break", auto=False)
        log.observe(e, e.events)
        head = next(line for line in log.lines(e, 900) if "Interacción" in line[0])
        names = [card.name for _, _, card in L.card_spans(head[0], head[4])]
        self.assertEqual(sorted(names), ["Attack", "Break"])

    def test_longest_name_wins(self):
        e = engine_with_hands(["guard"] * 5, ["unbreakable_guard"] * 5)
        play(e, "guard", "unbreakable_guard", auto=False)
        spans = L.card_spans("A: Guard   vs   B: Unbreakable Guard", L._cards_of(e.result))
        self.assertEqual(sorted(c.name for _, _, c in spans), ["Guard", "Unbreakable Guard"])

    def test_hover_draws_card(self):
        e = engine_with_hands(["attack"] * 5, ["break"] * 5)
        log = L.BattleLog()
        play(e, "attack", "break", auto=False)
        log.observe(e, e.events)
        surf = pygame.Surface((T.SCREEN_W, T.SCREEN_H))
        body_x = L.PANEL.x + 20
        text, size, _, indent, cards = next(l for l in log.lines(e, L.PANEL.w - 56) if "Interacción" in l[0])
        a, b, card = L.card_spans(text, cards)[0]
        f = T.font(size, size >= 15)
        y = L.PANEL.y + 54 + L.LINE_H * [l[0] for l in log.lines(e, L.PANEL.w - 56)].index(text)
        mouse = (body_x + indent + (f.size(text[:a])[0] + f.size(text[:b])[0]) // 2, y + 5)
        self.assertIs(L._card_at(text, size, cards, body_x + indent, y, mouse), card)
        L.draw_battle_log(surf, log, e, 0, mouse)       # no falla al dibujar la carta


if __name__ == "__main__":
    unittest.main()
