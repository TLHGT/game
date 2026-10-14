"""Menú de elección pequeño (p. ej. los pisos del ascensor).

    menu.open("Ascensor", [(texto, disponible, valor), ...], on_choose)
    W/S o flechas: elegir · E / ENTER / ESPACIO: confirmar · ESC / TAB: cancelar

Las opciones no disponibles se ven en gris y no se pueden elegir. Al confirmar
se cierra y llama a on_choose(valor).
"""
import pygame

from game import settings
from ui import text as T

UP = (pygame.K_w, pygame.K_UP)
DOWN = (pygame.K_s, pygame.K_DOWN)
CONFIRM = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e, pygame.K_SPACE)
CANCEL = (pygame.K_ESCAPE, pygame.K_TAB)


class ChoiceMenu:
    def __init__(self):
        self.is_open = False
        self.title = ""
        self.options = []
        self.index = 0
        self._on_choose = None

    def open(self, title, options, on_choose):
        self.title = title
        self.options = list(options)
        self._on_choose = on_choose
        self.is_open = True
        enabled = [i for i, (_, ok, _) in enumerate(self.options) if ok]
        self.index = enabled[0] if enabled else 0

    def close(self):
        self.is_open = False

    def move(self, step):
        n = len(self.options)
        for k in range(1, n + 1):
            i = (self.index + step * k) % n
            if self.options[i][1]:
                self.index = i
                return

    def choose(self, index=None):
        """Confirma la opción `index` (o la seleccionada). False si no está disponible."""
        i = self.index if index is None else index
        label, ok, value = self.options[i]
        if not ok:
            return False
        self.close()
        self._on_choose(value)
        return True

    def handle_events(self, events):
        for ev in events:
            if ev.type != pygame.KEYDOWN or not self.is_open:
                continue
            if ev.key in CANCEL:
                self.close()
            elif ev.key in UP:
                self.move(-1)
            elif ev.key in DOWN:
                self.move(1)
            elif ev.key in CONFIRM:
                self.choose()

    def draw(self, surface):
        if not self.is_open:
            return
        w, h = surface.get_size()
        pw, ph = 420, 90 + 42 * len(self.options)
        x, y = (w - pw) // 2, (h - ph) // 2
        surface.blit(T.panel((pw, ph), border=settings.UI_ACCENT, alpha=240), (x, y))
        title = T.font(26, bold=True).render(self.title, True, settings.UI_ACCENT)
        surface.blit(title, title.get_rect(midtop=(w // 2, y + 14)))
        for i, (label, ok, _) in enumerate(self.options):
            rect = pygame.Rect(x + 20, y + 56 + i * 42, pw - 40, 36)
            if i == self.index and ok:
                pygame.draw.rect(surface, (60, 56, 40), rect, border_radius=8)
                pygame.draw.rect(surface, settings.UI_ACCENT, rect, 2, border_radius=8)
            color = settings.UI_TEXT if ok else (110, 108, 100)
            img = T.font(20, bold=ok).render(label, True, color)
            surface.blit(img, img.get_rect(midleft=(rect.x + 14, rect.centery)))
        hint = T.font(14).render("W/S: elegir  ·  E: ir  ·  ESC: cancelar", True, settings.UI_TEXT_DIM)
        surface.blit(hint, hint.get_rect(midbottom=(w // 2, y + ph - 8)))
