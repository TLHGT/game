"""Jugador: movimiento continuo en 8 direcciones.

El jugador solo calcula su velocidad deseada; el desplazamiento real con
colisiones lo aplica world/collision.py (move_and_collide).
"""
import math

import pygame

from entities.entity import Entity
from game import settings


DEFAULT_AVATAR = "player"


class Player(Entity):
    def __init__(self, x=0, y=0):
        super().__init__(x, y, "player_down_0", hitbox=settings.PLAYER_HITBOX, shadow=(28, 10))
        self.speed = settings.PLAYER_SPEED
        self.velocity = pygame.Vector2()
        self.facing = "down"
        self.moving = False
        self.anim_time = 0.0
        self.avatar = DEFAULT_AVATAR    # aspecto en el mapa: lo fija el personaje elegido
        # Punto de extensión: estadísticas, equipo, etc. se colgarán de aquí
        # (o de un componente aparte) cuando existan esos sistemas.

    def set_move_input(self, direction):
        """direction: Vector2 de longitud <= 1 (ya normalizado por InputHandler)."""
        self.velocity = pygame.Vector2(direction) * self.speed
        self.moving = direction.length_squared() > 0.01
        if self.moving:
            self.facing = self._facing_from(direction)

    def _facing_from(self, d):
        # En diagonal se mantiene la orientación actual si es uno de los ejes
        # pulsados: evita "parpadeos" del sprite.
        horiz = "right" if d.x > 0 else "left"
        vert = "down" if d.y > 0 else "up"
        if abs(d.x) > 0.1 and abs(d.y) > 0.1:
            return self.facing if self.facing in (horiz, vert) else horiz
        return horiz if abs(d.x) >= abs(d.y) else vert

    def stop(self):
        self.velocity.update(0, 0)
        self.moving = False

    def update(self, dt, ctx=None):
        if self.moving:
            self.anim_time += dt
            frame = 1 + int(self.anim_time * 8) % 2
            bob = -abs(math.sin(self.anim_time * 8 * math.pi / 2)) * 2
        else:
            self.anim_time = 0.0
            frame, bob = 0, 0
        self.sprite_key = f"{self.avatar}_{self.facing}_{frame}"
        self.sprite_offset = (0, round(bob))

    @property
    def facing_vector(self):
        return {
            "up": pygame.Vector2(0, -1), "down": pygame.Vector2(0, 1),
            "left": pygame.Vector2(-1, 0), "right": pygame.Vector2(1, 0),
        }[self.facing]
