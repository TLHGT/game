"""Clase base de todo lo que existe en el mundo y se dibuja ordenado por Y.

Convenciones:
- (x, y) es el *punto base* del objeto en coordenadas de mundo: el centro de
  sus pies / de su base. Es lo que se usa para ordenar la profundidad 2.5D.
- La hitbox (colisión) es un rectángulo pequeño apoyado en ese punto base,
  independiente del tamaño del sprite.
- El sprite se dibuja con su borde inferior centrado en (x, y).
- Las entidades NO se dibujan a sí mismas: solo dicen qué imagen usar
  (get_image). El renderizado vive en render/renderer.py.
"""
import pygame


class Entity:
    solid = False

    def __init__(self, x, y, sprite_key=None, hitbox=(0, 0), shadow=None):
        self.x = float(x)
        self.y = float(y)
        self.sprite_key = sprite_key
        self.hitbox_w, self.hitbox_h = hitbox
        self.shadow = shadow                 # (ancho, alto) de la sombra o None
        self.sprite_offset = (0, 0)          # desplazamiento visual extra
        self.fade_when_occluding = False     # se vuelve translúcido si tapa al jugador
        self.visible = True
        self.id = None

    @property
    def rect(self):
        """Rectángulo de colisión (los 'pies')."""
        r = pygame.Rect(0, 0, self.hitbox_w, self.hitbox_h)
        r.midbottom = (round(self.x), round(self.y))
        return r

    @property
    def sort_y(self):
        return self.y

    def update(self, dt, ctx):
        pass

    def get_image(self, assets):
        return assets.get(self.sprite_key) if self.sprite_key else None


class RectEntity(Entity):
    """Entidad definida por un rectángulo de suelo (muros, puertas).

    `height` es la altura visual que "sube" por encima de su huella para
    simular volumen (cara superior + cara frontal).
    """

    def __init__(self, rect, height=64, sprite_key=None):
        rect = pygame.Rect(rect)
        super().__init__(rect.centerx, rect.bottom, sprite_key, hitbox=rect.size)
        self.footprint = rect
        self.height = height

    @property
    def rect(self):
        return self.footprint.copy()
