"""Feedback visual sencillo: temblor, destello, textos emergentes y flotantes."""
import math
import random

import pygame

from combate.ui import theme as T


class Shake:
    def __init__(self):
        self.t = 0.0
        self.power = 0.0

    def add(self, power, duration=0.3):
        self.power = max(self.power, power)
        self.t = max(self.t, duration)

    def update(self, dt):
        self.t = max(0.0, self.t - dt)
        if self.t == 0:
            self.power = 0

    @property
    def offset(self):
        if self.t <= 0:
            return 0, 0
        p = self.power * min(1.0, self.t / 0.3)
        return random.uniform(-p, p), random.uniform(-p, p)


class Flash:
    def __init__(self):
        self.t = 0.0
        self.color = (255, 255, 255)

    def add(self, color, duration=0.25):
        self.color = color
        self.t = self.duration = duration

    def update(self, dt):
        self.t = max(0.0, self.t - dt)

    def draw(self, surface):
        if self.t > 0:
            veil = pygame.Surface(surface.get_size())
            veil.fill(self.color)
            veil.set_alpha(int(55 * self.t / self.duration))
            surface.blit(veil, (0, 0))


class Popup:
    """Texto grande que aparece escalando y se desvanece subiendo."""

    def __init__(self, text, pos, color, size=44, delay=0.0, life=1.1):
        self.text, self.pos, self.color, self.size = text, pos, color, size
        self.age = -delay
        self.life = life

    def update(self, dt):
        self.age += dt
        return self.age < self.life

    def draw(self, surface):
        if self.age < 0:
            return
        t = self.age / self.life
        pop = min(1.0, self.age / 0.12)
        scale = 0.6 + 0.4 * pop + 0.15 * math.sin(pop * math.pi)
        alpha = 255 if t < 0.7 else int(255 * (1 - (t - 0.7) / 0.3))
        img = T.font(int(self.size * scale)).render(self.text, True, self.color)
        shadow = T.font(int(self.size * scale)).render(self.text, True, (0, 0, 0))
        y = self.pos[1] - 26 * t
        rect = img.get_rect(center=(self.pos[0], y))
        rect.clamp_ip(surface.get_rect().inflate(-16, -16))     # nunca fuera de pantalla
        shadow.set_alpha(min(alpha, 170))
        img.set_alpha(alpha)
        surface.blit(shadow, rect.move(3, 4))
        surface.blit(img, rect)


class FloatText(Popup):
    """Número pequeño que flota (+1 MANA, -45 HP)."""

    def __init__(self, text, pos, color, delay=0.0):
        super().__init__(text, pos, color, size=24, delay=delay, life=1.0)

    def draw(self, surface):
        if self.age < 0:
            return
        t = self.age / self.life
        alpha = int(255 * (1 - t))
        T.text(surface, self.text, self.size, self.color, (self.pos[0], self.pos[1] - 34 * t), "center",
               alpha=alpha, shadow=True)


class Animations:
    def __init__(self):
        self.shake = Shake()
        self.flash = Flash()
        self.popups = []
        self._stagger = {}          # escalonado de popups por posición

    def popup(self, text, pos, color, size=44):
        key = (round(pos[0] / 100), round(pos[1] / 100))
        delay = self._stagger.get(key, 0.0)
        self._stagger[key] = delay + 0.32
        self.popups.append(Popup(text, pos, color, size, delay))

    def float_text(self, text, pos, color):
        self.popups.append(FloatText(text, pos, color))

    def update(self, dt):
        self.shake.update(dt)
        self.flash.update(dt)
        self.popups = [p for p in self.popups if p.update(dt)]
        for k in list(self._stagger):
            self._stagger[k] = max(0.0, self._stagger[k] - dt)

    def draw(self, surface):
        for p in self.popups:
            p.draw(surface)
        self.flash.draw(surface)
