"""Indicador discreto "E - Hablar" flotando sobre el objeto cercano.

Solo aparece cuando hay algo con lo que interactuar.
"""
import math

import pygame

from game import settings
from ui import text as T


class InteractionPrompt:
    def __init__(self):
        self.font = T.font(17, bold=True)
        self._target = None
        self._appear = 0.0      # 0..1 para animar la aparición
        self._time = 0.0
        self._cache = {}

    def update(self, dt, target):
        self._time += dt
        if target is not self._target:
            self._target = target
            self._appear = 0.0
        if target is not None:
            self._appear = min(1.0, self._appear + dt * 7)

    def _render_pill(self, text):
        if text not in self._cache:
            key_part, _, verb = text.partition(" - ")
            key_s = self.font.render(key_part, True, settings.UI_PANEL)
            verb_s = self.font.render(verb, True, settings.UI_TEXT)
            h = max(key_s.get_height(), verb_s.get_height()) + 8
            key_box = pygame.Rect(4, 4, key_s.get_width() + 12, h - 8)
            w = key_box.width + verb_s.get_width() + 20
            surf = T.panel((w, h), alpha=210, radius=h // 2)
            pygame.draw.rect(surf, settings.UI_ACCENT, key_box, border_radius=(h - 8) // 2)
            surf.blit(key_s, key_s.get_rect(center=key_box.center))
            surf.blit(verb_s, (key_box.right + 8, (h - verb_s.get_height()) // 2))
            self._cache[text] = surf
        return self._cache[text]

    def draw(self, surface, camera, assets):
        target = self._target
        if target is None:
            return
        pill = self._render_pill(target.get_prompt())
        img = target.get_image(assets)
        top = target.y - (img.get_height() if img else 40)
        sx, sy = camera.world_to_screen(target.x, top)
        bob = math.sin(self._time * 3) * 2
        ease = 1 - (1 - self._appear) ** 3
        rect = pill.get_rect(midbottom=(sx, sy - 8 + bob + (1 - ease) * 8))
        rect.clamp_ip(surface.get_rect().inflate(-12, -12))
        pill.set_alpha(int(255 * ease))
        surface.blit(pill, rect)
