"""Pinta el suelo del mapa una sola vez en una superficie grande.

Lee la sección "ground" del JSON:
    "ground": {
      "seed": 1,
      "theme": "forest" | "cave",     # cave: roca oscura fuera, tierra de cueva dentro
      "background": "void",           # interiores: fuera de las salas no hay nada
      "areas":   [{"type": "stone" | "stairs" | "dirt", "rect": [x, y, w, h]}],
      "paths":   [{"points": [[x, y], ...], "width": 110, "style": "main" | "trail" | "faint" | "cave"}],
      "details": [{"type": "flowers" | "mushrooms" | "pebbles" | "puddles", "rect": [...], "count": 20}]
    }

Si existen assets/ground_grass.png o assets/ground_forest.png se usan como
textura repetida en lugar del color procedural.
"""
import math
import random

import pygame

GRASS = (96, 152, 74)
FOREST_FLOOR = (30, 56, 38)
CAVE_WALL = (24, 22, 30)
CAVE_FLOOR = (78, 70, 66)

PATH_STYLES = {
    "main":  dict(edge=(132, 104, 68), fill=(192, 162, 114), light=(210, 184, 138)),
    "trail": dict(edge=(110, 92, 62), fill=(156, 132, 94), light=(170, 148, 108)),
    "cave":  dict(edge=(64, 58, 56), fill=(100, 90, 80), light=(116, 106, 94)),
}


def _tile(surface, tile, rect=None):
    rect = rect or surface.get_rect()
    tw, th = tile.get_size()
    for y in range(rect.top - rect.top % th, rect.bottom, th):
        for x in range(rect.left - rect.left % tw, rect.right, tw):
            surface.blit(tile, (x, y), area=None)


def build_ground(world, assets):
    spec = world.ground
    rng = random.Random(spec.get("seed", 1))
    W, H = world.width, world.height
    surf = pygame.Surface((W, H)).convert()

    # 1. Suelo del bosque (todo) ----------------------------------------
    forest_tile = assets.get_tile("ground_forest")
    cave = spec.get("theme") == "cave"
    void = spec.get("background") == "void"
    if void:
        surf.fill((14, 14, 18))     # interiores: fuera de las salas no hay nada
    elif cave:
        surf.fill(CAVE_WALL)
        for _ in range(W * H // 900):
            c = rng.choice([(18, 16, 24), (34, 30, 40), (28, 26, 34)])
            pygame.draw.circle(surf, c, (rng.randrange(W), rng.randrange(H)), rng.randint(3, 10))
    elif forest_tile:
        _tile(surf, forest_tile)
    else:
        surf.fill(FOREST_FLOOR)
        for _ in range(W * H // 900):
            c = rng.choice([(24, 46, 32), (38, 66, 44), (34, 60, 36)])
            pygame.draw.circle(surf, c, (rng.randrange(W), rng.randrange(H)), rng.randint(3, 9))

    # 2. Suelo de las zonas caminables -----------------------------------
    #    bosque: hierba con borde suave; cueva: tierra; interior: nada
    #    (en los interiores lo pintan las áreas "tiles").
    if cave:
        _cave_floor(surf, world.walkable, rng)
    elif not void:
        _grass(surf, world.walkable, assets.get_tile("ground_grass"), rng)

    # 3. Áreas especiales -------------------------------------------------
    for area in spec.get("areas", []):
        r = pygame.Rect(area["rect"])
        kind = area["type"]
        if kind == "stone":
            _stone_floor(surf, r, rng)
        elif kind == "stairs":
            _stairs(surf, r)
        elif kind == "tiles":
            _tiles(surf, r, rng)
        elif kind == "dirt":
            pygame.draw.rect(surf, PATH_STYLES["trail"]["fill"], r, border_radius=18)

    # 4. Caminos -----------------------------------------------------------
    for path in spec.get("paths", []):
        _path(surf, path["points"], path.get("width", 60), path.get("style", "trail"), rng)

    # 5. Detalles planos ---------------------------------------------------
    for det in spec.get("details", []):
        r = pygame.Rect(det["rect"])
        for _ in range(det.get("count", 10)):
            x, y = rng.randint(r.left, r.right), rng.randint(r.top, r.bottom)
            if det["type"] == "flowers":
                _flower(surf, x, y, rng)
            elif det["type"] == "mushrooms":
                _mushroom(surf, x, y, rng)
            elif det["type"] == "pebbles":
                pygame.draw.ellipse(surf, (150, 146, 136), (x, y, rng.randint(4, 8), rng.randint(3, 5)))
            elif det["type"] == "puddles":
                w, h = rng.randint(24, 60), rng.randint(10, 20)
                pygame.draw.ellipse(surf, (40, 48, 62), (x - 2, y - 2, w + 4, h + 4))
                pygame.draw.ellipse(surf, (58, 74, 96), (x, y, w, h))
                pygame.draw.ellipse(surf, (110, 140, 170), (x + w // 4, y + 2, w // 3, 3))

    # 6. Sombra del bosque sobre los bordes de las zonas caminables -------
    _forest_shadow(surf, world, (0, 0, 0, 170) if cave else (6, 20, 10, 120))
    return surf


# ---------------------------------------------------------------------------
def _grass(surf, walkable, grass_tile, rng):
    for r in walkable:
        pygame.draw.rect(surf, (64, 110, 58), r.inflate(14, 14), border_radius=10)
    for r in walkable:
        if grass_tile:
            surf.set_clip(r)
            _tile(surf, grass_tile, r)
            surf.set_clip(None)
        else:
            pygame.draw.rect(surf, GRASS, r)
    if grass_tile:
        return
    for r in walkable:
        for _ in range(r.w * r.h // 2200):
            c = rng.choice([(104, 160, 80), (88, 142, 68), (110, 166, 84)])
            x, y = rng.randint(r.left, r.right), rng.randint(r.top, r.bottom)
            pygame.draw.ellipse(surf, c, (x - 20, y - 10, rng.randint(24, 60), rng.randint(12, 26)))
        for _ in range(r.w * r.h // 1400):
            x, y = rng.randint(r.left, r.right), rng.randint(r.top, r.bottom)
            _tuft(surf, x, y, rng)


def _cave_floor(surf, walkable, rng):
    """Tierra apisonada de cueva con manchas y piedrecitas."""
    for r in walkable:
        pygame.draw.rect(surf, (52, 48, 52), r.inflate(14, 14), border_radius=10)
    for r in walkable:
        pygame.draw.rect(surf, CAVE_FLOOR, r)
    for r in walkable:
        for _ in range(r.w * r.h // 2200):
            c = rng.choice([(84, 76, 70), (70, 64, 60), (90, 82, 74)])
            x, y = rng.randint(r.left, r.right), rng.randint(r.top, r.bottom)
            pygame.draw.ellipse(surf, c, (x - 20, y - 10, rng.randint(24, 60), rng.randint(12, 26)))
        for _ in range(r.w * r.h // 1800):
            x, y = rng.randint(r.left, r.right), rng.randint(r.top, r.bottom)
            pygame.draw.ellipse(surf, (110, 102, 96), (x, y, rng.randint(3, 6), rng.randint(2, 4)))


def _tuft(surf, x, y, rng):
    c = rng.choice([(70, 124, 56), (80, 136, 60)])
    for dx in (-3, 0, 3):
        pygame.draw.line(surf, c, (x, y), (x + dx * 2, y - rng.randint(4, 8)), 2)


def _flower(surf, x, y, rng):
    color = rng.choice([(238, 226, 120), (236, 140, 160), (180, 160, 236), (250, 250, 240)])
    for a in range(5):
        ang = a * math.tau / 5
        pygame.draw.circle(surf, color, (x + round(math.cos(ang) * 3), y + round(math.sin(ang) * 3)), 2)
    pygame.draw.circle(surf, (240, 190, 70), (x, y), 2)


def _mushroom(surf, x, y, rng):
    pygame.draw.rect(surf, (236, 226, 206), (x - 1, y - 4, 3, 5))
    pygame.draw.ellipse(surf, (196, 60, 52), (x - 5, y - 8, 11, 6))
    pygame.draw.circle(surf, (250, 240, 230), (x - 1, y - 6), 1)


def _stone_floor(surf, r, rng):
    pygame.draw.rect(surf, (104, 112, 92), r, border_radius=12)
    for y in range(r.top + 2, r.bottom - 10, 30):
        x = r.left + 2 + (18 if (y // 30) % 2 else 0)
        while x < r.right - 10:
            w = rng.randint(28, 40)
            if rng.random() > 0.18:   # algunas losas faltan: aspecto de ruina
                c = rng.choice([(150, 146, 134), (140, 136, 124), (160, 156, 142)])
                stone = pygame.Rect(x, y, min(w - 3, r.right - x - 2), 27)
                pygame.draw.rect(surf, c, stone, border_radius=3)
                pygame.draw.line(surf, (176, 172, 160), stone.topleft, (stone.right - 2, stone.top), 1)
            x += w


def _tiles(surf, r, rng):
    """Baldosas de hospital, sucias y con alguna rota."""
    pygame.draw.rect(surf, (150, 156, 150), r)
    size = 40
    for y in range(r.top, r.bottom, size):
        for x in range(r.left, r.right, size):
            t = pygame.Rect(x + 1, y + 1, min(size - 2, r.right - x - 2), min(size - 2, r.bottom - y - 2))
            if t.w <= 0 or t.h <= 0:
                continue
            roll = rng.random()
            if roll < 0.05:
                c = (98, 102, 96)          # baldosa rota
            elif roll < 0.25:
                c = (176, 182, 172)
            else:
                c = rng.choice([(196, 202, 192), (204, 208, 198), (188, 196, 186)])
            pygame.draw.rect(surf, c, t)
            if roll < 0.05:
                pygame.draw.line(surf, (70, 72, 68), t.topleft, t.bottomright, 1)
            elif rng.random() < 0.08:      # manchas
                pygame.draw.ellipse(surf, (160, 150, 120), (t.x + 6, t.y + 8, 18, 10))


def _stairs(surf, r):
    steps = 6
    for i in range(steps):
        t = i / steps
        c = (int(120 - 100 * t), int(116 - 98 * t), int(106 - 92 * t))
        y = r.top + i * r.h // steps
        pygame.draw.rect(surf, c, (r.left + i * 3, y, r.w - i * 6, r.h // steps + 1))
        pygame.draw.line(surf, (40, 38, 34), (r.left + i * 3, y), (r.right - i * 3, y), 2)


def _segment_poly(a, b, half):
    d = pygame.Vector2(b) - pygame.Vector2(a)
    if d.length_squared() == 0:
        return None
    n = pygame.Vector2(-d.y, d.x).normalize() * half
    a, b = pygame.Vector2(a), pygame.Vector2(b)
    return [a + n, b + n, b - n, a - n]


def _path(surf, points, width, style, rng):
    if style == "faint":
        # Solo pisadas sueltas: un camino que "casi" no se ve.
        for a, b in zip(points, points[1:]):
            a, b = pygame.Vector2(a), pygame.Vector2(b)
            length = a.distance_to(b)
            for i in range(int(length // 28) + 1):
                p = a.lerp(b, min(1.0, i * 28 / max(1, length)))
                jx, jy = rng.randint(-8, 8), rng.randint(-6, 6)
                pygame.draw.ellipse(surf, (134, 128, 84), (p.x + jx - 10, p.y + jy - 6,
                                                           rng.randint(14, 22), rng.randint(8, 12)))
        return
    colors = PATH_STYLES[style]
    for color, w in ((colors["edge"], width + 8), (colors["fill"], width)):
        half = w / 2
        for a, b in zip(points, points[1:]):
            poly = _segment_poly(a, b, half)
            if poly:
                pygame.draw.polygon(surf, color, poly)
        for p in points:
            pygame.draw.circle(surf, color, p, int(half))
    # Bordes irregulares y textura
    for a, b in zip(points, points[1:]):
        a, b = pygame.Vector2(a), pygame.Vector2(b)
        length = a.distance_to(b)
        if length == 0:
            continue
        d = (b - a) / length
        n = pygame.Vector2(-d.y, d.x)
        for i in range(int(length // 14)):
            p = a + d * (i * 14)
            side = rng.choice((-1, 1))
            q = p + n * side * (width / 2 + rng.uniform(-4, 3))
            pygame.draw.circle(surf, colors["fill"], q, rng.randint(4, 9))
            inner = p + n * rng.uniform(-width / 3, width / 3)
            if rng.random() < 0.35:
                pygame.draw.ellipse(surf, colors["light"], (inner.x, inner.y, rng.randint(8, 20), rng.randint(4, 8)))
            if rng.random() < 0.18:
                pygame.draw.ellipse(surf, (150, 144, 132), (inner.x, inner.y, rng.randint(3, 7), rng.randint(3, 5)))
            if style == "trail" and rng.random() < 0.45:
                _tuft(surf, int(inner.x), int(inner.y), rng)


def _forest_shadow(surf, world, color=(6, 20, 10, 120)):
    """Oscurece suavemente los bordes de las zonas caminables pegadas al
    bosque. Se calcula a baja resolución y se escala (desenfoque gratis)."""
    grid = world.collision
    scale = 8
    cell = grid.cell // scale
    small = pygame.Surface((grid.cols * cell, grid.rows * cell), pygame.SRCALPHA)
    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.solid[r][c]:
                pygame.draw.rect(small, color, (c * cell - 2, r * cell - 2, cell + 4, cell + 4))
    for _ in range(2):   # doble suavizado
        small = pygame.transform.smoothscale(small, (small.get_width() // 2, small.get_height() // 2))
        small = pygame.transform.smoothscale(small, (small.get_width() * 2, small.get_height() * 2))
    big = pygame.transform.smoothscale(small, (grid.cols * grid.cell, grid.rows * grid.cell))
    surf.blit(big, (0, 0))
