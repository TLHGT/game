"""Cámara que sigue al jugador y convierte coordenadas de mundo a pantalla.

    screen_x = world_x - camera_x
    screen_y = world_y - camera_y

camera_x / camera_y es la esquina superior izquierda de la vista en el mundo.
"""
import math

import pygame

from game import settings


class Camera:
    def __init__(self, view_width, view_height):
        self.view_width = view_width
        self.view_height = view_height
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.world_width = view_width
        self.world_height = view_height
        self.smoothing = settings.CAMERA_SMOOTHING

    def set_world_size(self, width, height):
        self.world_width = width
        self.world_height = height

    # ------------------------------------------------------------------
    def _clamp(self, x, y):
        """Evita mostrar fuera del mapa. Si el mapa es más pequeño que la
        pantalla, lo centra."""
        if self.world_width <= self.view_width:
            x = (self.world_width - self.view_width) / 2
        else:
            x = max(0.0, min(x, self.world_width - self.view_width))
        if self.world_height <= self.view_height:
            y = (self.world_height - self.view_height) / 2
        else:
            y = max(0.0, min(y, self.world_height - self.view_height))
        return x, y

    def _target_for(self, world_x, world_y):
        return self._clamp(world_x - self.view_width / 2,
                           world_y + settings.CAMERA_LOOK_OFFSET_Y - self.view_height / 2)

    def snap_to(self, world_x, world_y):
        """Coloca la cámara al instante (al cargar mapa, teletransportes...)."""
        self.camera_x, self.camera_y = self._target_for(world_x, world_y)

    def update(self, dt, world_x, world_y):
        tx, ty = self._target_for(world_x, world_y)
        if self.smoothing <= 0:
            self.camera_x, self.camera_y = tx, ty
            return
        # Interpolación exponencial: independiente de los FPS.
        t = 1.0 - math.exp(-self.smoothing * dt)
        self.camera_x += (tx - self.camera_x) * t
        self.camera_y += (ty - self.camera_y) * t
        self.camera_x, self.camera_y = self._clamp(self.camera_x, self.camera_y)

    # ------------------------------------------------------------------
    @property
    def offset(self):
        """Desplazamiento entero usado para dibujar (evita temblores)."""
        return round(self.camera_x), round(self.camera_y)

    def world_to_screen(self, world_x, world_y):
        ox, oy = self.offset
        return round(world_x) - ox, round(world_y) - oy

    def screen_to_world(self, screen_x, screen_y):
        return screen_x + self.camera_x, screen_y + self.camera_y

    @property
    def view_rect(self):
        ox, oy = self.offset
        return pygame.Rect(ox, oy, self.view_width, self.view_height)
