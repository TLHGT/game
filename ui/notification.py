"""Mensajes breves de descubrimiento que aparecen y se desvanecen solos.

Estilos:
    "info"      mensaje normal
    "discovery" secreto / descubrimiento (acento dorado)
    "area"      nombre de zona (grande, sin panel)
"""
import pygame

from game import settings
from ui import text as T


class Notification:
    def __init__(self, text, style, duration):
        self.text = text
        self.style = style
        self.duration = duration
        self.age = 0.0

    @property
    def alpha(self):
        fade = 0.35
        if self.age < fade:
            return self.age / fade
        if self.age > self.duration - fade:
            return max(0.0, (self.duration - self.age) / fade)
        return 1.0


class NotificationManager:
    def __init__(self, screen_w):
        self.screen_w = screen_w
        self.queue = []
        self.current = None
        self.font = T.font(22, bold=True)
        self.area_font = T.font(40, bold=True)

    def push(self, text, style="info", duration=None):
        if style == "area":
            duration = duration or 3.2
        self.queue.append(Notification(text, style, duration or settings.NOTIFICATION_DURATION))

    def update(self, dt):
        if self.current is None and self.queue:
            self.current = self.queue.pop(0)
        if self.current:
            self.current.age += dt
            if self.current.age >= self.current.duration:
                self.current = None

    def draw(self, surface):
        n = self.current
        if n is None:
            return
        a = int(255 * n.alpha)
        if n.style == "area":
            label = self.area_font.render(n.text, True, settings.UI_TEXT)
            shadow = self.area_font.render(n.text, True, (0, 0, 0))
            rect = label.get_rect(midtop=(self.screen_w // 2, 70))
            shadow.set_alpha(a // 2)
            label.set_alpha(a)
            surface.blit(shadow, rect.move(2, 3))
            surface.blit(label, rect)
            line_w = int(rect.width * 0.6)
            line = pygame.Surface((line_w, 2), pygame.SRCALPHA)
            line.fill((*settings.UI_ACCENT, a))
            surface.blit(line, (self.screen_w // 2 - line_w // 2, rect.bottom + 6))
            return
        color = settings.UI_ACCENT if n.style == "discovery" else settings.UI_TEXT
        label = self.font.render(n.text, True, color)
        box = T.panel((label.get_width() + 48, label.get_height() + 22), alpha=215,
                      border=settings.UI_ACCENT if n.style == "discovery" else None)
        box.blit(label, (24, 11))
        box.set_alpha(a)
        slide = (1 - n.alpha) * -10
        surface.blit(box, box.get_rect(midtop=(self.screen_w // 2, 28 + slide)))
