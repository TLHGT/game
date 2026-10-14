"""Cuadro de diálogo con efecto máquina de escribir.

    dialogue.open(["Página 1", "Página 2"], speaker="Brann", on_close=fn)

E / Enter: si el texto aún se está escribiendo lo completa; si no, pasa
de página; en la última página cierra y llama a on_close.
"""
import math

import pygame

from game import settings
from ui import text as T

MAX_LINES = 3


class DialogueBox:
    def __init__(self, screen_w, screen_h):
        self.width = min(860, screen_w - 80)
        self.height = 132
        self.x = (screen_w - self.width) // 2
        self.y = screen_h - self.height - 28
        self.font = T.font(22)
        self.name_font = T.font(18, bold=True)
        self.pages = []
        self.page = 0
        self.speaker = None
        self.on_close = None
        self.visible_chars = 0.0
        self._time = 0.0
        self._bg = T.panel((self.width, self.height), border=(70, 74, 70))

    @property
    def is_open(self):
        return bool(self.pages)

    def open(self, pages, speaker=None, on_close=None):
        if isinstance(pages, str):
            pages = [pages]
        # Las páginas largas se trocean para no salirse del cuadro.
        self.pages = []
        for p in pages:
            lines = T.wrap(p, self.font, self.width - 56)
            for i in range(0, len(lines), MAX_LINES):
                self.pages.append(lines[i:i + MAX_LINES])
        self.page = 0
        self.speaker = speaker
        self.on_close = on_close
        self.visible_chars = 0.0

    def _page_len(self):
        return sum(len(l) for l in self.pages[self.page])

    def advance(self):
        if not self.is_open:
            return
        if self.visible_chars < self._page_len():
            self.visible_chars = self._page_len()
            return
        self.page += 1
        self.visible_chars = 0.0
        if self.page >= len(self.pages):
            self.close()

    def close(self):
        callback = self.on_close
        self.pages, self.page, self.speaker, self.on_close = [], 0, None, None
        if callback:
            callback()

    def update(self, dt):
        self._time += dt
        if self.is_open:
            self.visible_chars = min(self._page_len(),
                                     self.visible_chars + settings.DIALOGUE_CHARS_PER_SEC * dt)

    def draw(self, surface):
        if not self.is_open:
            return
        surface.blit(self._bg, (self.x, self.y))
        if self.speaker:
            label = self.name_font.render(self.speaker, True, settings.UI_PANEL)
            tab = pygame.Rect(self.x + 22, self.y - 16, label.get_width() + 24, 30)
            pygame.draw.rect(surface, settings.UI_ACCENT, tab, border_radius=8)
            surface.blit(label, label.get_rect(center=tab.center))

        remaining = int(self.visible_chars)
        ty = self.y + 26
        for line in self.pages[self.page]:
            shown = line[:max(0, remaining)]
            remaining -= len(line)
            if shown:
                surface.blit(self.font.render(shown, True, settings.UI_TEXT), (self.x + 28, ty))
            ty += 30

        if self.visible_chars >= self._page_len():
            # Triángulo "continuar" que sube y baja.
            bx = self.x + self.width - 34
            by = self.y + self.height - 26 + math.sin(self._time * 6) * 3
            pygame.draw.polygon(surface, settings.UI_ACCENT,
                                [(bx - 8, by - 5), (bx + 8, by - 5), (bx, by + 5)])
