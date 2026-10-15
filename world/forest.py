"""Relleno procedural de bosque denso.

En vez de colocar cientos de árboles a mano, el mapa declara qué zonas son
caminables y aquí se llena el resto con árboles (semilla fija = mismo
bosque siempre). La colisión del bosque la da la rejilla, no cada árbol.

style "cave": en vez de árboles, estalagmitas y rocas de cueva
(`pine_ratio` pasa a ser la proporción de estalagmitas).
style "burnt": árboles muertos y quemados (aldea del vacío).
"""
import random

import pygame

from entities.props import Prop


def generate_forest(width, height, walkable, exclusions, spacing, seed=0, pine_ratio=0.25, style="forest"):
    rng = random.Random(seed)
    blocked = [pygame.Rect(r) for r in walkable] + [pygame.Rect(r) for r in exclusions]
    trees = []
    jitter = spacing * 0.38
    y = -spacing // 2
    row = 0
    while y < height + spacing * 2:
        x = -spacing // 2 + (spacing // 2 if row % 2 else 0)
        while x < width + spacing:
            tx = x + rng.uniform(-jitter, jitter)
            ty = y + rng.uniform(-jitter, jitter)
            # Hueco que debe estar libre: el tronco y un poco por encima,
            # para que las copas no invadan demasiado los caminos.
            probe = pygame.Rect(tx - 14, ty - 46, 28, 52)
            if probe.collidelist(blocked) == -1:
                if style == "cave":
                    kind = "stalagmite" if rng.random() < pine_ratio else "cave_rock"
                elif style == "burnt":
                    kind = "dead_tree"
                else:
                    kind = "pine" if rng.random() < pine_ratio else "tree"
                tree = Prop(kind, round(tx), round(ty), rng.randrange(4))
                tree.solid = False   # la rejilla de colisión ya bloquea el bosque
                tree.shadow = None   # bajo el follaje denso no se vería
                trees.append(tree)
            x += spacing
        y += int(spacing * 0.8)
        row += 1
    return trees
