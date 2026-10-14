"""Personaje y pasiva durante el combate.

    ficha corta   bajo el HUD de cada jugador: HERO · combo 1/3 · próximo HIT +5%
    ficha larga   al pasar el ratón: descripción, pasiva y su efecto completo
"""
import math

import pygame

from combate.ui import theme as T
from combate.ui.player_hud import HUD_W, hud_anchor

CHIP_H, CHIP_W = 24, 310        # ancho de la columna lateral: no pisa la zona de batalla


def draw_character_chip(surface, engine, player, pulse=0.0):
    x, y = hud_anchor(player.index)
    if player.index == 1:
        x += HUD_W - CHIP_W
    rect = pygame.Rect(x, y + 122, CHIP_W, CHIP_H)
    color = T.PLAYER_COLORS[player.index]
    glow = 0.5 + 0.5 * math.sin(min(1.0, pulse) * math.pi) if pulse else 0.0
    border = T.mix(T.mix(T.LINE, color, 0.5), T.GOLD, glow)
    pygame.draw.rect(surface, (24, 27, 38), rect, border_radius=7)
    pygame.draw.rect(surface, border, rect, 2, border_radius=7)
    name = player.character.name.upper()
    T.text(surface, name, 15, color, (rect.x + 10, rect.centery), "midleft")
    nx = rect.x + 18 + T.font(15).size(name)[0]
    text = player.passive.status_text(player, engine)
    size = 13
    while size > 10 and T.font(size).size(text)[0] > rect.right - 10 - nx:
        size -= 1
    T.text(surface, text, size, T.GOLD if glow else (200, 204, 218), (nx, rect.centery), "midleft")
    return rect


def draw_character_panel(surface, engine, player):
    x, y = hud_anchor(player.index)
    rect = pygame.Rect(x, y + 150, HUD_W, 112)
    color = T.PLAYER_COLORS[player.index]
    T.panel(surface, rect, color=(22, 25, 36), border=color, alpha=245)
    ch, pas = player.character, player.passive
    T.text(surface, ch.name.upper(), 20, color, (rect.x + 12, rect.y + 8))
    T.text(surface, ch.description, 13, T.DIM, (rect.x + 14 + T.font(20).size(ch.name.upper())[0] + 8, rect.y + 14),
           bold=False)
    T.text(surface, f"PASIVA · {pas.name}", 15, T.GOLD, (rect.x + 12, rect.y + 38))
    yy = rect.y + 60
    for line in T.wrap(pas.summary(), 13, rect.w - 24)[:2]:
        T.text(surface, line, 13, (210, 214, 228), (rect.x + 12, yy), bold=False)
        yy += 16
    T.text(surface, f"Ahora: {pas.status_text(player, engine)}", 12, T.DIM, (rect.x + 12, rect.bottom - 18),
           bold=False)
