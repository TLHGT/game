"""Gráficos provisionales generados con primitivas de pygame.

Este módulo SOLO dibuja: no sabe nada de la lógica del juego. Cada función
devuelve una Surface con transparencia cuyo borde inferior central es el
"punto base" del objeto. Cuando haya arte real, este archivo deja de usarse
automáticamente (el AssetManager prioriza los PNG de assets/).
"""
import math
import random

import pygame

from render import village_sprites

OUTLINE = (28, 30, 34)


def shade(color, f):
    return tuple(max(0, min(255, int(c * f))) for c in color[:3])


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _circle(s, color, center, r, outline=True):
    if outline:
        pygame.draw.circle(s, OUTLINE, center, r + 2)
    pygame.draw.circle(s, color, center, r)


# ---------------------------------------------------------------------------
# Personajes
# ---------------------------------------------------------------------------
def _humanoid(direction, frame, tunic, skin=(238, 198, 158), hair=(86, 54, 36),
              scarf=None, hat=None, hood=None, beard=None, w=34, h=56):
    s = _surf(w, h)
    cx = w // 2
    feet = h - 2
    # Piernas (alternan al andar)
    lift_l = 3 if frame == 1 else 0
    lift_r = 3 if frame == 2 else 0
    legs = (58, 50, 46)
    if direction in ("left", "right"):
        step = 3 if frame == 1 else (-3 if frame == 2 else 0)
        for dx in (-step, step):
            r = pygame.Rect(cx - 3 + dx, feet - 12, 7, 12)
            pygame.draw.rect(s, OUTLINE, r.inflate(2, 2), border_radius=2)
            pygame.draw.rect(s, legs, r, border_radius=2)
    else:
        for dx, lift in ((-5, lift_l), (5, lift_r)):
            r = pygame.Rect(cx + dx - 3, feet - 12, 7, 12 - lift)
            pygame.draw.rect(s, OUTLINE, r.inflate(2, 2), border_radius=2)
            pygame.draw.rect(s, legs, r, border_radius=2)
    # Cuerpo
    body = pygame.Rect(cx - 10, feet - 30, 20, 20)
    pygame.draw.rect(s, OUTLINE, body.inflate(4, 4), border_radius=6)
    pygame.draw.rect(s, tunic, body, border_radius=6)
    pygame.draw.rect(s, shade(tunic, 0.75), (body.x, body.bottom - 6, body.w, 6),
                     border_bottom_left_radius=6, border_bottom_right_radius=6)
    pygame.draw.line(s, (92, 62, 36), (body.x + 1, body.y + 13), (body.right - 2, body.y + 13), 2)
    # Brazos
    swing = {0: 0, 1: 2, 2: -2}[frame]
    if direction in ("down", "up"):
        for side, sw in ((-1, swing), (1, -swing)):
            arm = pygame.Rect(0, 0, 6, 13)
            arm.midtop = (cx + side * 12, body.y + 2 + sw)
            pygame.draw.rect(s, OUTLINE, arm.inflate(2, 2), border_radius=3)
            pygame.draw.rect(s, shade(tunic, 0.9), arm, border_radius=3)
    else:
        arm = pygame.Rect(0, 0, 6, 13)
        arm.midtop = (cx + swing, body.y + 3)
        pygame.draw.rect(s, OUTLINE, arm.inflate(2, 2), border_radius=3)
        pygame.draw.rect(s, shade(tunic, 0.85), arm, border_radius=3)
    if scarf:
        pygame.draw.rect(s, scarf, (body.x - 1, body.y - 1, body.w + 2, 5), border_radius=2)
        if direction in ("left", "right"):
            tail_x = body.right - 2 if direction == "left" else body.x - 4
            pygame.draw.rect(s, scarf, (tail_x, body.y + 2, 6, 9), border_radius=2)
    # Cabeza
    head = (cx, feet - 41)
    if hood:
        _circle(s, hood, head, 13)
        pygame.draw.circle(s, skin, (head[0], head[1] + 2), 8)
    else:
        _circle(s, skin, head, 11)
        if direction == "up":
            pygame.draw.circle(s, hair, head, 11)
        else:
            pygame.draw.ellipse(s, hair, (head[0] - 11, head[1] - 12, 22, 12))
            if direction == "left":
                pygame.draw.rect(s, hair, (head[0] + 2, head[1] - 6, 9, 10), border_radius=3)
            elif direction == "right":
                pygame.draw.rect(s, hair, (head[0] - 11, head[1] - 6, 9, 10), border_radius=3)
    if beard and direction != "up":
        pygame.draw.ellipse(s, beard, (head[0] - 8, head[1] + 2, 16, 10))
    # Ojos
    eye = (30, 26, 30)
    ey = head[1] + (2 if hood else 0)
    if direction == "down":
        pygame.draw.rect(s, eye, (head[0] - 5, ey, 3, 4))
        pygame.draw.rect(s, eye, (head[0] + 3, ey, 3, 4))
    elif direction == "left":
        pygame.draw.rect(s, eye, (head[0] - 7, ey, 3, 4))
    elif direction == "right":
        pygame.draw.rect(s, eye, (head[0] + 5, ey, 3, 4))
    if hat:
        pygame.draw.ellipse(s, OUTLINE, (head[0] - 17, head[1] - 9, 34, 10))
        pygame.draw.ellipse(s, hat, (head[0] - 16, head[1] - 8, 32, 8))
        pygame.draw.rect(s, OUTLINE, (head[0] - 9, head[1] - 19, 18, 13), border_radius=4)
        pygame.draw.rect(s, hat, (head[0] - 8, head[1] - 18, 16, 12), border_radius=4)
        pygame.draw.rect(s, shade(hat, 0.6), (head[0] - 8, head[1] - 10, 16, 3))
    return s


def player(direction="down", frame=0):
    return _humanoid(direction, frame, tunic=(58, 108, 188), scarf=(206, 64, 58))


# ---------------------------------------------------------------------------
# Avatares de los personajes jugables (Character.avatar)
# Clave: "avatar_<id>_<dirección>_<paso>". Sin avatar propio -> player().
# ---------------------------------------------------------------------------
def avatar(name, direction="down", frame=0):
    maker = {"blaze": blaze, "jurgenoid": jurgenoid}.get(name)
    return maker(direction, frame) if maker else player(direction, frame)


def _flame(s, x, y, size, flicker=0):
    """Llamita (fuego en la mano de Blaze)."""
    pygame.draw.polygon(s, OUTLINE, [(x - size - 1, y + 1), (x + flicker, y - size * 2 - 2), (x + size + 1, y + 1)])
    pygame.draw.polygon(s, (240, 110, 40), [(x - size, y), (x + flicker, y - size * 2), (x + size, y)])
    pygame.draw.polygon(s, (255, 214, 90), [(x - size // 2, y), (x + flicker // 2, y - size), (x + size // 2, y)])


def blaze(direction="down", frame=0):
    """Blaze: chaqueta roja y carbón, bufanda naranja, pelo en punta como
    una llama y fuego en la mano."""
    w, h = 34, 66
    s = _humanoid(direction, frame, tunic=(150, 50, 42), hair=(196, 58, 36),
                  scarf=(246, 160, 48), w=w, h=h)
    cx, feet = w // 2, h - 2
    hx, hy = cx, feet - 41
    # Pelo en punta: tres mechones de llama
    shift = {"left": -3, "right": 3}.get(direction, 0)
    for dx, tall in ((-7, 9), (0, 13), (7, 9)):
        x = hx + dx + shift
        tip = x - shift // 2
        pygame.draw.polygon(s, OUTLINE, [(x - 6, hy - 5), (tip, hy - 10 - tall), (x + 6, hy - 5)])
        pygame.draw.polygon(s, (214, 66, 38), [(x - 5, hy - 6), (tip, hy - 8 - tall), (x + 5, hy - 6)])
        pygame.draw.polygon(s, (250, 150, 60), [(x - 2, hy - 7), (tip, hy - 4 - tall), (x + 2, hy - 7)])
    if direction != "up":
        pygame.draw.ellipse(s, (196, 58, 36), (hx - 11, hy - 12, 22, 9))
    # Fuego en la mano visible
    flick = (-1, 1, 0)[frame]
    if direction == "down":
        _flame(s, cx + 12, feet - 15, 3, flick)
    elif direction in ("left", "right"):
        _flame(s, cx + (-6 if direction == "left" else 6), feet - 15, 3, flick)
    return s


def jurgenoid(direction="down", frame=0):
    """Jurgenoid: caballero no muerto del viento al estilo de un guerrero
    erune con armadura pesada y guadaña gigante (inspiración: Vaseraga de
    Granblue Fantasy, pero en jade y blanco de aire). Orejas erune, piel
    pálida, ojos que brillan y capa hecha jirones por el viento."""
    if direction == "left":
        return pygame.transform.flip(jurgenoid("right", frame), True, False)
    W, H = 66, 98
    s = _surf(W, H)
    cx, feet = 30, H - 2
    armor, armor_hi = (46, 52, 60), (74, 84, 92)
    jade, jade_hi = (64, 186, 140), (150, 236, 200)
    skin, hair = (176, 190, 182), (222, 232, 228)
    cape, cape_dark = (196, 228, 212), (140, 182, 166)
    glow = (130, 255, 214)
    wind = (210, 255, 236, 150)
    flutter = (0, 3, -2)[frame]
    side = direction == "right"
    front = direction == "down"
    back = direction == "up"

    def scythe():
        """Asta larga y hoja curva enorme, con un remolino de viento."""
        sx = cx - 16 if side else (cx - 22 if back else cx + 24)
        top = 4                     # la hoja queda por encima de las orejas
        pygame.draw.line(s, OUTLINE, (sx, top), (sx, feet - 2), 6)
        pygame.draw.line(s, (78, 64, 52), (sx, top), (sx, feet - 2), 3)
        pygame.draw.rect(s, jade, (sx - 3, feet - 30, 7, 5))            # empuñadura
        d = 1 if (side or back) else -1                                  # hacia dónde apunta la hoja
        pts = [(sx, top + 2), (sx + d * 14, top - 3), (sx + d * 28, top + 2), (sx + d * 38, top + 14),
               (sx + d * 27, top + 9), (sx + d * 14, top + 6), (sx, top + 10)]
        pygame.draw.polygon(s, (196, 236, 222), pts)
        pygame.draw.polygon(s, OUTLINE, pts, 2)
        pygame.draw.line(s, jade_hi, (sx + d * 6, top + 1), (sx + d * 26, top + 4), 2)
        ws = _surf(W, H)
        pygame.draw.arc(ws, wind, (sx + min(0, d * 44) - 2, top - 6, 46, 26), 0.3, 2.6, 2)
        s.blit(ws, (0, 0))

    def cape_shape(over=False):
        """Capa con el borde hecho jirones; ondea al andar."""
        top_y, base = feet - 46, feet - 4
        if side:
            pts = [(cx + 4, top_y), (cx - 8, top_y + 2), (cx - 18 + flutter, base - 6),
                   (cx - 12 + flutter, base - 10), (cx - 8 + flutter, base), (cx - 2, base - 8), (cx + 4, base - 4)]
        else:
            pts = [(cx - 15, top_y), (cx + 15, top_y)]
            for i, x in enumerate(range(cx + 17, cx - 18, -7)):
                pts.append((x + flutter, base - (7 if i % 2 else 0)))
        pygame.draw.polygon(s, cape if over else cape_dark, pts)
        pygame.draw.polygon(s, OUTLINE, pts, 2)
        if over:
            pygame.draw.line(s, cape_dark, (cx, top_y + 4), (cx + flutter, base - 6), 2)
            pygame.draw.line(s, jade, (cx - 14, top_y + 2), (cx + 14, top_y + 2), 3)

    if not back:
        scythe()
    cape_shape()

    # Piernas (grebas)
    if side:
        step = (0, 4, -4)[frame]
        legs = [(cx - 4 - step, 0), (cx + 2 + step, 0)]
    else:
        legs = [(cx - 11, 3 if frame == 1 else 0), (cx + 3, 3 if frame == 2 else 0)]
    for lx, lift in legs:
        r = pygame.Rect(lx, feet - 18, 9, 18 - lift)
        pygame.draw.rect(s, OUTLINE, r.inflate(2, 2), border_radius=2)
        pygame.draw.rect(s, armor, r, border_radius=2)
        pygame.draw.rect(s, jade, (r.x, r.y + 5, r.w, 2))
        pygame.draw.rect(s, armor_hi, (r.x + 1, r.bottom - 4, r.w - 2, 3))

    # Torso: armadura pesada
    half = 10 if side else 14
    body = pygame.Rect(cx - half, feet - 46, half * 2, 30)
    pygame.draw.rect(s, OUTLINE, body.inflate(4, 4), border_radius=7)
    pygame.draw.rect(s, armor, body, border_radius=7)
    pygame.draw.rect(s, armor_hi, (body.x + 3, body.y + 3, body.w - 6, 8), border_radius=4)
    pygame.draw.rect(s, jade, (body.x, body.bottom - 9, body.w, 3))          # cinturón
    if front:
        pygame.draw.polygon(s, jade, [(cx - 6, body.bottom - 6), (cx + 6, body.bottom - 6), (cx, body.bottom + 8)])
        pygame.draw.polygon(s, glow, [(cx - 3, body.y + 13), (cx + 3, body.y + 13), (cx, body.y + 19)])  # gema
    # Hombreras enormes con filo de jade y pincho
    for px in ([cx] if side else [cx - 16, cx + 16]):
        r = pygame.Rect(0, 0, 20 if side else 18, 13)
        r.center = (px, body.y + 3)
        pygame.draw.ellipse(s, OUTLINE, r.inflate(4, 4))
        pygame.draw.ellipse(s, armor_hi, r)
        pygame.draw.arc(s, jade, r, 0.2, math.pi - 0.2, 3)
        tip = 1 if (side or px > cx) else -1
        spike = [(px + tip * 3, r.top + 3), (px + tip * 10, r.top - 6), (px + tip * 9, r.top + 5)]
        pygame.draw.polygon(s, jade_hi, spike)
        pygame.draw.polygon(s, OUTLINE, spike, 1)
    # Brazos / guanteletes
    swing = (0, 2, -2)[frame]
    for ax, sw in ([(cx + 4 + swing, 0)] if side else [(cx - 19, swing), (cx + 19, -swing)]):
        arm = pygame.Rect(0, 0, 8, 15)
        arm.midtop = (ax, body.y + 8 + sw)
        pygame.draw.rect(s, OUTLINE, arm.inflate(2, 2), border_radius=3)
        pygame.draw.rect(s, armor, arm, border_radius=3)
        pygame.draw.rect(s, jade, (arm.x, arm.bottom - 5, arm.w, 5), border_radius=2)

    if back:
        cape_shape(over=True)
        scythe()

    # Cabeza: orejas erune, pelo plateado, ojos que brillan, cuello alto
    hx, hy = cx + (2 if side else 0), feet - 57
    if side:
        ears = [[(hx - 7, hy - 4), (hx - 8, hy - 22), (hx + 2, hy - 6)]]
    else:
        ears = [[(hx - 10, hy - 4), (hx - 9, hy - 22), (hx - 1, hy - 7)],
                [(hx + 10, hy - 4), (hx + 9, hy - 22), (hx + 1, hy - 7)]]
    for ear in ears:
        pygame.draw.polygon(s, hair, ear)
        pygame.draw.polygon(s, OUTLINE, ear, 2)
        (x0, y0), (x1, y1), (x2, y2) = ear
        inner = [((x0 * 2 + x2) // 3, y0 - 2), (x1, y1 + 6), ((x0 + x2 * 2) // 3, y2 - 1)]
        pygame.draw.polygon(s, (150, 160, 170), inner)
    _circle(s, skin, (hx, hy), 10)
    if back:
        pygame.draw.circle(s, hair, (hx, hy), 10)
        pygame.draw.polygon(s, hair, [(hx - 7, hy + 4), (hx + 7, hy + 4),
                                      (hx + 2 + flutter, hy + 16), (hx - 3 + flutter, hy + 14)])
    else:
        pygame.draw.ellipse(s, hair, (hx - 11, hy - 12, 22, 11))
        if side:
            pygame.draw.rect(s, hair, (hx - 11, hy - 6, 9, 12), border_radius=3)
            pygame.draw.rect(s, glow, (hx + 4, hy - 1, 4, 3))
        else:
            pygame.draw.polygon(s, hair, [(hx - 10, hy - 4), (hx - 4, hy - 3), (hx - 8, hy + 4)])
            pygame.draw.polygon(s, hair, [(hx + 10, hy - 4), (hx + 3, hy - 3), (hx + 8, hy + 3)])
            pygame.draw.rect(s, glow, (hx - 5, hy - 1, 3, 3))
            pygame.draw.rect(s, glow, (hx + 3, hy - 1, 3, 3))
    collar = pygame.Rect(hx - (7 if side else 9), hy + 4, 17 if side else 18, 7)
    pygame.draw.rect(s, OUTLINE, collar.inflate(2, 2), border_radius=3)
    pygame.draw.rect(s, armor, collar, border_radius=3)
    pygame.draw.line(s, jade, (collar.x + 1, collar.y + 2), (collar.right - 2, collar.y + 2), 1)

    # Viento a los pies
    ws = _surf(W, H)
    pygame.draw.arc(ws, wind, (cx - 22 + flutter, feet - 10, 20, 10), 0.4, 2.8, 2)
    pygame.draw.arc(ws, wind, (cx + 6 - flutter, feet - 14, 18, 9), 0.4, 2.8, 2)
    s.blit(ws, (0, 0))
    return s


NPC_LOOKS = {
    "woodcutter": dict(tunic=(88, 128, 64), hat=(126, 84, 44), beard=(140, 96, 58)),
    "traveler": dict(tunic=(112, 74, 142), hood=(92, 58, 120), skin=(214, 172, 132)),
    "default": dict(tunic=(160, 138, 96)),
}


def droid():
    """Dron de seguridad flotante."""
    s = _surf(44, 56)
    pygame.draw.ellipse(s, (0, 0, 0, 60), (10, 48, 24, 7))       # sombra propia (flota)
    body = pygame.Rect(6, 12, 32, 28)
    pygame.draw.ellipse(s, OUTLINE, body.inflate(4, 4))
    pygame.draw.ellipse(s, (150, 160, 170), body)
    pygame.draw.ellipse(s, (190, 198, 206), (10, 14, 18, 10))
    pygame.draw.rect(s, OUTLINE, (12, 22, 20, 9), border_radius=4)
    pygame.draw.rect(s, (230, 60, 50), (14, 24, 16, 5), border_radius=3)   # visor rojo
    pygame.draw.line(s, OUTLINE, (22, 12), (22, 3), 2)
    pygame.draw.circle(s, (240, 200, 80), (22, 3), 3)
    for x in (10, 30):
        pygame.draw.line(s, OUTLINE, (x + 2, 38), (x, 44), 2)
    return s


def npc(look="default"):
    if look == "droid":
        return droid()
    return _humanoid("down", 0, **NPC_LOOKS.get(look, NPC_LOOKS["default"]), w=40, h=60)


# ---------------------------------------------------------------------------
# Naturaleza
# ---------------------------------------------------------------------------
TREE_GREENS = [(56, 122, 62), (72, 136, 58), (46, 106, 72), (86, 142, 60)]


def tree(variant=0):
    rng = random.Random(100 + variant)
    green = TREE_GREENS[variant % len(TREE_GREENS)]
    w, h = 96, 122
    s = _surf(w, h)
    trunk = pygame.Rect(w // 2 - 7, h - 40, 14, 40)
    pygame.draw.rect(s, OUTLINE, trunk.inflate(4, 2), border_radius=3)
    pygame.draw.rect(s, (98, 68, 42), trunk, border_radius=3)
    pygame.draw.rect(s, (76, 52, 32), (trunk.right - 5, trunk.y, 5, trunk.h))
    pygame.draw.ellipse(s, (98, 68, 42), (trunk.x - 5, h - 8, trunk.w + 10, 8))
    blobs = [(48, 54, 33), (26, 62, 23), (70, 62, 23), (40, 34, 24), (60, 36, 22), (48, 70, 26)]
    blobs = [(x + rng.randint(-3, 3), y + rng.randint(-3, 3), r) for x, y, r in blobs]
    for x, y, r in blobs:
        pygame.draw.circle(s, OUTLINE, (x, y), r + 2)
    for x, y, r in blobs:
        pygame.draw.circle(s, shade(green, 0.72), (x, y + 3), r)
    for x, y, r in blobs:
        pygame.draw.circle(s, green, (x, y), r - 3)
    for x, y, r in blobs[:4]:
        pygame.draw.circle(s, shade(green, 1.22), (x - r // 3, y - r // 3), r // 3)
    return s


def pine(variant=0):
    green = [(44, 98, 70), (52, 112, 78)][variant % 2]
    w, h = 74, 124
    s = _surf(w, h)
    trunk = pygame.Rect(w // 2 - 5, h - 26, 10, 26)
    pygame.draw.rect(s, OUTLINE, trunk.inflate(4, 2))
    pygame.draw.rect(s, (92, 64, 40), trunk)
    for i, (half, top, bottom) in enumerate([(34, 46, 100), (28, 24, 74), (20, 4, 48)]):
        pts = [(w // 2, top), (w // 2 - half, bottom), (w // 2 + half, bottom)]
        pygame.draw.polygon(s, OUTLINE, [(pts[0][0], pts[0][1] - 3), (pts[1][0] - 3, pts[1][1] + 2),
                                         (pts[2][0] + 3, pts[2][1] + 2)])
        pygame.draw.polygon(s, shade(green, 0.8 + i * 0.1), pts)
        pygame.draw.polygon(s, shade(green, 1.15 + i * 0.05),
                            [pts[0], (w // 2 - half // 2, bottom - 6), (w // 2 - 2, bottom - 8)])
    return s


def rock():
    s = _surf(50, 36)
    pygame.draw.ellipse(s, OUTLINE, (1, 4, 48, 31))
    pygame.draw.ellipse(s, (112, 112, 106), (3, 6, 44, 27))
    pygame.draw.ellipse(s, (142, 142, 134), (6, 6, 34, 18))
    pygame.draw.ellipse(s, (168, 168, 160), (12, 9, 14, 7))
    return s


def stump():
    s = _surf(38, 32)
    pygame.draw.rect(s, OUTLINE, (3, 8, 32, 22), border_radius=6)
    pygame.draw.rect(s, (104, 72, 44), (5, 10, 28, 19), border_radius=5)
    pygame.draw.ellipse(s, OUTLINE, (3, 2, 32, 14))
    pygame.draw.ellipse(s, (184, 146, 98), (5, 4, 28, 10))
    pygame.draw.ellipse(s, (150, 112, 70), (12, 6, 14, 6), 1)
    return s


def log():
    s = _surf(86, 32)
    pygame.draw.rect(s, OUTLINE, (2, 6, 78, 24), border_radius=10)
    pygame.draw.rect(s, (110, 76, 46), (4, 8, 74, 20), border_radius=9)
    pygame.draw.line(s, (88, 60, 36), (10, 14), (60, 14), 2)
    pygame.draw.line(s, (88, 60, 36), (16, 21), (70, 21), 2)
    pygame.draw.ellipse(s, OUTLINE, (66, 5, 18, 26))
    pygame.draw.ellipse(s, (186, 148, 100), (68, 7, 14, 22))
    pygame.draw.ellipse(s, (146, 108, 68), (71, 12, 8, 12), 1)
    pygame.draw.circle(s, (70, 130, 60), (30, 8), 5)   # musgo
    return s


def bush():
    s = _surf(50, 40)
    for x, y, r in [(16, 24, 13), (34, 24, 13), (25, 16, 13)]:
        pygame.draw.circle(s, OUTLINE, (x, y), r + 2)
    for x, y, r in [(16, 24, 13), (34, 24, 13), (25, 16, 13)]:
        pygame.draw.circle(s, (62, 128, 58), (x, y), r)
    pygame.draw.circle(s, (92, 158, 72), (21, 13), 5)
    pygame.draw.circle(s, (210, 70, 80), (34, 20), 2)
    pygame.draw.circle(s, (210, 70, 80), (14, 26), 2)
    return s


def tall_grass():
    s = _surf(44, 34)
    rng = random.Random(7)
    for _ in range(14):
        x = rng.randint(4, 40)
        top = rng.randint(2, 14)
        lean = rng.randint(-6, 6)
        color = rng.choice([(70, 132, 56), (88, 150, 62), (60, 116, 52)])
        pygame.draw.line(s, color, (x, 33), (x + lean, top), 3)
    return s


# ---------------------------------------------------------------------------
# Cueva
# ---------------------------------------------------------------------------
CAVE_ROCK = [(92, 86, 96), (104, 96, 104), (84, 80, 92)]


def stalagmite(variant=0):
    """Columna de roca puntiaguda (sustituye a los árboles en las cuevas)."""
    rng = random.Random(300 + variant)
    base = CAVE_ROCK[variant % len(CAVE_ROCK)]
    w, h = 70, [112, 92, 126][variant % 3]
    s = _surf(w, h)
    cx = w // 2
    spikes = [(cx, 2, 20), (cx - 14 + rng.randint(-2, 2), h // 3, 13), (cx + 14 + rng.randint(-2, 2), h // 2, 11)]
    for x, top, half in spikes[::-1]:
        pts = [(x, top), (x - half, h - 4), (x + half, h - 4)]
        pygame.draw.polygon(s, OUTLINE, [(x, top - 3), (x - half - 3, h - 2), (x + half + 3, h - 2)])
        pygame.draw.polygon(s, shade(base, 0.8), pts)
        pygame.draw.polygon(s, shade(base, 1.18), [(x, top), (x - half + 3, h - 6), (x - 2, h - 6)])
        for k in range(3):   # vetas
            y = top + (h - top) * (k + 1) // 4
            pygame.draw.line(s, shade(base, 0.6), (x - 3, y), (x + 4, y + 2), 1)
    pygame.draw.ellipse(s, OUTLINE, (cx - 26, h - 10, 52, 10))
    pygame.draw.ellipse(s, shade(base, 0.7), (cx - 24, h - 9, 48, 8))
    return s


def cave_rock(variant=0):
    base = CAVE_ROCK[(variant + 1) % len(CAVE_ROCK)]
    w, h = 58, [44, 52][variant % 2]
    s = _surf(w, h)
    pygame.draw.polygon(s, OUTLINE, [(2, h - 2), (8, 12), (24, 2), (42, 6), (56, 20), (55, h - 2)])
    pygame.draw.polygon(s, shade(base, 0.85), [(5, h - 4), (10, 14), (24, 5), (41, 9), (53, 21), (52, h - 4)])
    pygame.draw.polygon(s, shade(base, 1.2), [(12, 15), (24, 7), (36, 10), (26, 20)])
    pygame.draw.line(s, shade(base, 0.55), (30, 22), (36, h - 8), 2)
    return s


def crystal(variant=0):
    """Racimo de cristales que brillan: la única luz de la cueva."""
    color = [(110, 200, 230), (190, 130, 230)][variant % 2]
    w, h = 54, 62
    s = _surf(w, h)
    glow = _surf(w, h)
    pygame.draw.ellipse(glow, (*color, 60), (0, h - 34, w, 34))
    s.blit(glow, (0, 0))
    for x, top, half in [(16, 22, 7), (38, 26, 7), (27, 4, 9)]:
        pts = [(x, top), (x + half, top + 12), (x + half - 2, h - 6), (x - half + 2, h - 6), (x - half, top + 12)]
        pygame.draw.polygon(s, color, pts)
        pygame.draw.polygon(s, shade(color, 1.3), [(x, top + 3), (x + half - 2, top + 12), (x, h - 8)])
        pygame.draw.polygon(s, OUTLINE, pts, 2)
    return s


def glowshroom():
    s = _surf(30, 22)
    for x, y, r in [(8, 14, 5), (19, 10, 6), (24, 17, 4)]:
        pygame.draw.circle(s, (120, 230, 200, 70), (x, y), r + 4)
        pygame.draw.line(s, (200, 220, 210), (x, y), (x, y + 6), 2)
        pygame.draw.circle(s, OUTLINE, (x, y), r + 1)
        pygame.draw.circle(s, (110, 220, 190), (x, y), r)
        pygame.draw.circle(s, (210, 255, 240), (x - 1, y - 2), max(1, r // 3))
    return s


def pillar(broken=False):
    h = 54 if broken else 92
    s = _surf(40, h)
    body = pygame.Rect(7, 14, 26, h - 22)
    pygame.draw.rect(s, OUTLINE, (4, h - 12, 32, 11), border_radius=2)
    pygame.draw.rect(s, (126, 124, 114), (6, h - 11, 28, 9))
    pygame.draw.rect(s, OUTLINE, body.inflate(4, 0))
    pygame.draw.rect(s, (156, 152, 140), body)
    pygame.draw.rect(s, (124, 120, 110), (body.right - 7, body.y, 7, body.h))
    for x in (body.x + 6, body.x + 13):
        pygame.draw.line(s, (130, 126, 116), (x, body.y + 4), (x, body.bottom - 4), 1)
    if broken:
        pygame.draw.polygon(s, (182, 178, 166), [(7, 14), (14, 8), (20, 13), (27, 6), (33, 14)])
        pygame.draw.polygon(s, OUTLINE, [(7, 14), (14, 8), (20, 13), (27, 6), (33, 14)], 2)
    else:
        pygame.draw.rect(s, OUTLINE, (2, 4, 36, 13), border_radius=2)
        pygame.draw.rect(s, (182, 178, 166), (4, 6, 32, 9))
    pygame.draw.circle(s, (74, 132, 64), (12, h - 16), 4)
    return s


def bed():
    s = _surf(46, 78)
    pygame.draw.rect(s, OUTLINE, (2, 4, 42, 70), border_radius=4)
    pygame.draw.rect(s, (150, 156, 160), (4, 6, 38, 66), border_radius=3)    # armazón
    pygame.draw.rect(s, (214, 218, 210), (6, 8, 34, 60), border_radius=3)    # colchón
    pygame.draw.rect(s, (236, 238, 232), (9, 10, 28, 12), border_radius=4)   # almohada
    pygame.draw.rect(s, (150, 176, 168), (6, 30, 34, 38), border_radius=3)   # sábana
    pygame.draw.line(s, (120, 146, 138), (6, 30), (40, 30), 2)
    pygame.draw.ellipse(s, (130, 110, 80, 160), (14, 42, 16, 10))           # mancha
    for x in (5, 39):
        pygame.draw.rect(s, OUTLINE, (x - 1, 70, 4, 6))
    return s


def cabinet():
    s = _surf(48, 74)
    pygame.draw.rect(s, OUTLINE, (2, 2, 44, 70), border_radius=3)
    pygame.draw.rect(s, (176, 186, 182), (4, 4, 40, 10))                     # tapa
    pygame.draw.rect(s, (140, 150, 148), (4, 14, 40, 56))
    pygame.draw.line(s, OUTLINE, (24, 16), (24, 68), 2)
    for x in (19, 29):
        pygame.draw.rect(s, (220, 220, 200), (x, 38, 2, 8))
    pygame.draw.rect(s, (220, 60, 60), (8, 18, 10, 10))                      # cruz roja
    pygame.draw.rect(s, (250, 250, 250), (12, 19, 2, 8))
    pygame.draw.rect(s, (250, 250, 250), (9, 22, 8, 2))
    pygame.draw.line(s, (90, 96, 94), (32, 50), (40, 60), 1)                 # arañazo
    return s


def rubble():
    s = _surf(52, 30)
    rng = random.Random(9)
    for _ in range(9):
        x, y = rng.randint(6, 44), rng.randint(10, 24)
        w, h = rng.randint(8, 16), rng.randint(6, 10)
        c = rng.choice([(150, 148, 140), (128, 126, 120), (176, 172, 160), (196, 200, 190)])
        pygame.draw.rect(s, OUTLINE, (x - w // 2 - 1, y - h // 2 - 1, w + 2, h + 2), border_radius=2)
        pygame.draw.rect(s, c, (x - w // 2, y - h // 2, w, h), border_radius=2)
    pygame.draw.line(s, (90, 70, 50), (8, 14), (30, 6), 3)                   # tablón
    return s


def switch(on=False):
    s = _surf(30, 52)
    pygame.draw.rect(s, OUTLINE, (11, 24, 8, 28))
    pygame.draw.rect(s, (110, 112, 116), (12, 24, 6, 28))                   # poste
    box = pygame.Rect(3, 2, 24, 26)
    pygame.draw.rect(s, OUTLINE, box.inflate(4, 4), border_radius=4)
    pygame.draw.rect(s, (90, 96, 104), box, border_radius=4)
    pygame.draw.circle(s, OUTLINE, box.center, 8)
    pygame.draw.circle(s, (120, 30, 26) if on else (230, 50, 40), box.center, 7)
    if on:
        pygame.draw.circle(s, (130, 255, 140), (box.right - 4, box.y + 4), 3)
    else:
        pygame.draw.circle(s, (255, 170, 160), (box.centerx - 2, box.centery - 2), 2)
    return s


def monitor():
    s = _surf(50, 56)
    pygame.draw.rect(s, OUTLINE, (2, 30, 46, 24), border_radius=3)
    pygame.draw.rect(s, (110, 116, 120), (4, 32, 42, 20))                    # mesa
    screen = pygame.Rect(6, 4, 38, 28)
    pygame.draw.rect(s, OUTLINE, screen.inflate(4, 4), border_radius=3)
    pygame.draw.rect(s, (40, 46, 50), screen, border_radius=3)
    pts = [(8, 20), (16, 20), (19, 10), (23, 28), (27, 16), (31, 20), (42, 20)]
    pygame.draw.lines(s, (90, 230, 140), False, pts, 2)                     # electro
    return s


def operating_table():
    s = _surf(78, 60)
    pygame.draw.rect(s, OUTLINE, (6, 40, 6, 18))
    pygame.draw.rect(s, OUTLINE, (66, 40, 6, 18))
    pygame.draw.rect(s, OUTLINE, (2, 18, 74, 26), border_radius=6)
    pygame.draw.rect(s, (170, 196, 196), (4, 20, 70, 20), border_radius=5)
    pygame.draw.rect(s, (120, 150, 150), (4, 36, 70, 6))
    pygame.draw.circle(s, OUTLINE, (39, 8), 9)                               # lámpara
    pygame.draw.circle(s, (250, 240, 190), (39, 8), 7)
    return s


def wolf_ghost():
    """Lobo espectral: mitad fuego, mitad hielo."""
    w, h = 112, 84
    s = _surf(w, h)
    for r, a in ((48, 40), (36, 60)):
        glow = _surf(r * 2, r * 2)
        pygame.draw.circle(glow, (180, 210, 255, a), (r, r), r)
        s.blit(glow, (w // 2 - r, 46 - r))
    fire, ice = (236, 110, 60), (140, 200, 250)
    body = [(18, 50), (34, 34), (70, 32), (88, 40), (92, 60), (70, 66), (30, 66)]
    pygame.draw.polygon(s, OUTLINE, body)
    pygame.draw.polygon(s, fire, [(20, 50), (35, 36), (56, 34), (56, 64), (31, 64)])
    pygame.draw.polygon(s, ice, [(56, 34), (70, 34), (86, 41), (90, 59), (70, 64), (56, 64)])
    pygame.draw.polygon(s, OUTLINE, [(78, 36), (96, 20), (104, 30), (110, 38), (96, 46)])
    pygame.draw.polygon(s, ice, [(80, 37), (95, 23), (102, 31), (107, 38), (95, 44)])
    pygame.draw.polygon(s, (240, 250, 255), [(93, 18), (99, 8), (101, 24)])  # oreja
    pygame.draw.circle(s, (255, 255, 255), (98, 33), 3)
    for x, c in ((30, fire), (44, fire), (66, ice), (80, ice)):               # patas
        pygame.draw.rect(s, OUTLINE, (x - 4, 62, 9, 20), border_radius=3)
        pygame.draw.rect(s, c, (x - 3, 63, 7, 18), border_radius=3)
    pygame.draw.polygon(s, fire, [(20, 50), (4, 36), (8, 52)])                # cola
    for fx in (26, 36, 46):                                                    # llamas
        pygame.draw.polygon(s, (255, 200, 90), [(fx, 36), (fx + 4, 24), (fx + 8, 36)])
    return s


def wolf_grey():
    """Lobo del bosque (enemigo común). Mira a la derecha; el juego lo voltea."""
    w, h = 76, 54
    s = _surf(w, h)
    fur, dark, belly = (128, 124, 120), (88, 84, 82), (176, 170, 160)
    body = [(10, 30), (22, 20), (48, 19), (60, 26), (60, 40), (46, 44), (16, 44)]
    pygame.draw.polygon(s, OUTLINE, body)
    pygame.draw.polygon(s, fur, [(12, 30), (23, 22), (47, 21), (58, 27), (58, 39), (46, 42), (17, 42)])
    pygame.draw.polygon(s, belly, [(22, 40), (46, 40), (44, 36), (24, 36)])
    head = [(50, 22), (64, 10), (70, 16), (75, 24), (64, 31)]
    pygame.draw.polygon(s, OUTLINE, head)
    pygame.draw.polygon(s, fur, [(52, 22), (64, 13), (69, 18), (72, 24), (63, 29)])
    pygame.draw.polygon(s, dark, [(61, 12), (64, 3), (67, 14)])                 # oreja
    pygame.draw.circle(s, (250, 220, 90), (65, 19), 2)                         # ojo
    pygame.draw.circle(s, OUTLINE, (73, 24), 2)                                # hocico
    for x in (18, 28, 44, 54):                                                 # patas
        pygame.draw.rect(s, OUTLINE, (x - 3, 40, 7, 13), border_radius=2)
        pygame.draw.rect(s, dark, (x - 2, 41, 5, 11), border_radius=2)
    pygame.draw.polygon(s, OUTLINE, [(12, 30), (0, 18), (3, 34)])              # cola
    pygame.draw.polygon(s, dark, [(11, 30), (2, 21), (4, 32)])
    return s


def _wolf(fur, dark, belly, eye, aura=None, spikes=None):
    """Lobo base (misma silueta que wolf_grey) recoloreado, con aura y crines."""
    w, h = 80, 60
    s = _surf(w, h)
    oy = 6
    if aura:
        glow = _surf(w, h)
        pygame.draw.ellipse(glow, (*aura, 70), (4, 14, 74, 44))
        s.blit(glow, (0, 0))
    body = [(10, 30), (22, 20), (48, 19), (60, 26), (60, 40), (46, 44), (16, 44)]
    body = [(x, y + oy) for x, y in body]
    pygame.draw.polygon(s, OUTLINE, body)
    pygame.draw.polygon(s, fur, [(12, 30 + oy), (23, 22 + oy), (47, 21 + oy), (58, 27 + oy), (58, 39 + oy),
                                 (46, 42 + oy), (17, 42 + oy)])
    pygame.draw.polygon(s, belly, [(22, 40 + oy), (46, 40 + oy), (44, 36 + oy), (24, 36 + oy)])
    if spikes:   # crin de llamas / carámbanos sobre el lomo
        for i, x in enumerate(range(18, 54, 7)):
            tall = 9 + (i % 2) * 5
            pts = [(x - 4, 22 + oy), (x + (2 if spikes == "fire" else 0), 22 + oy - tall), (x + 4, 22 + oy)]
            col = (250, 130, 40) if spikes == "fire" else (200, 240, 255)
            tip = (255, 220, 90) if spikes == "fire" else (255, 255, 255)
            pygame.draw.polygon(s, OUTLINE, [(pts[0][0] - 1, pts[0][1]), (pts[1][0], pts[1][1] - 2),
                                             (pts[2][0] + 1, pts[2][1])])
            pygame.draw.polygon(s, col, pts)
            pygame.draw.line(s, tip, (pts[1][0], pts[1][1] + 1), (x, 20 + oy), 2)
    head = [(50, 22), (64, 10), (70, 16), (75, 24), (64, 31)]
    pygame.draw.polygon(s, OUTLINE, [(x, y + oy) for x, y in head])
    pygame.draw.polygon(s, fur, [(52, 22 + oy), (64, 13 + oy), (69, 18 + oy), (72, 24 + oy), (63, 29 + oy)])
    pygame.draw.polygon(s, dark, [(61, 12 + oy), (64, 3 + oy), (67, 14 + oy)])
    pygame.draw.circle(s, eye, (65, 19 + oy), 2)
    pygame.draw.circle(s, OUTLINE, (73, 24 + oy), 2)
    for x in (18, 28, 44, 54):
        pygame.draw.rect(s, OUTLINE, (x - 3, 40 + oy, 7, 13), border_radius=2)
        pygame.draw.rect(s, dark, (x - 2, 41 + oy, 5, 11), border_radius=2)
    tail_col = (250, 150, 50) if spikes == "fire" else (210, 245, 255) if spikes == "ice" else dark
    pygame.draw.polygon(s, OUTLINE, [(12, 30 + oy), (0, 16 + oy), (3, 34 + oy)])
    pygame.draw.polygon(s, tail_col, [(11, 30 + oy), (2, 19 + oy), (4, 32 + oy)])
    return s


def wolf_fire():
    """Fire Wolf (pisos del hospital): pelaje rojo, crin y cola de llamas."""
    return _wolf((176, 70, 44), (110, 40, 30), (232, 150, 90), (255, 236, 120), aura=(255, 120, 40), spikes="fire")


def wolf_ice():
    """Ice Wolf (pisos del hospital): pelaje azul claro, carámbanos en el lomo."""
    return _wolf((140, 186, 214), (80, 120, 156), (220, 240, 250), (160, 240, 255), aura=(150, 220, 255), spikes="ice")


# Máquinas de ventajas (homenaje a las perks de los zombis de Black Ops)
PERKS = {
    "quick_revive": dict(body=(70, 150, 210), trim=(220, 240, 255), logo="cross"),
    "juggernog":    dict(body=(176, 40, 44), trim=(250, 210, 120), logo="shield"),
    "speed_cola":   dict(body=(56, 150, 70), trim=(240, 250, 210), logo="bolt"),
    "double_tap":   dict(body=(200, 130, 40), trim=(255, 236, 170), logo="double"),
    "pack_a_punch": dict(body=(70, 60, 110), trim=(220, 200, 255), logo="fist"),
}


def perk_machine(perk="juggernog", on=False):
    """Máquina expendedora alta. Apagada: colores apagados. Encendida: brilla."""
    cfg = PERKS.get(perk, PERKS["juggernog"])
    body, trim = cfg["body"], cfg["trim"]
    if not on:
        body, trim = shade(body, 0.45), shade(trim, 0.5)
    w, h = 50, 86
    s = _surf(w, h)
    if on:
        glow = _surf(w, h)
        pygame.draw.rect(glow, (*cfg["body"], 70), (0, 0, w, h - 4), border_radius=10)
        s.blit(glow, (0, 0))
    box = pygame.Rect(5, 6, 40, 76)
    pygame.draw.rect(s, OUTLINE, box.inflate(4, 4), border_radius=6)
    pygame.draw.rect(s, body, box, border_radius=6)
    pygame.draw.rect(s, shade(body, 0.7), (box.right - 8, box.y, 8, box.h), border_radius=6)
    sign = pygame.Rect(box.x + 4, box.y + 4, box.w - 8, 16)            # cartel luminoso
    pygame.draw.rect(s, trim, sign, border_radius=4)
    pygame.draw.rect(s, OUTLINE, sign, 1, border_radius=4)
    c = (sign.centerx, sign.centery)
    ink = shade(cfg["body"], 0.6 if on else 0.4)
    logo = cfg["logo"]
    if logo == "cross":
        pygame.draw.rect(s, ink, (c[0] - 2, c[1] - 6, 4, 12))
        pygame.draw.rect(s, ink, (c[0] - 6, c[1] - 2, 12, 4))
    elif logo == "shield":
        pygame.draw.polygon(s, ink, [(c[0] - 6, c[1] - 6), (c[0] + 6, c[1] - 6), (c[0] + 5, c[1] + 2), (c[0], c[1] + 7),
                                     (c[0] - 5, c[1] + 2)])
    elif logo == "bolt":
        pygame.draw.polygon(s, ink, [(c[0] + 2, c[1] - 7), (c[0] - 5, c[1] + 1), (c[0], c[1] + 1), (c[0] - 2, c[1] + 7),
                                     (c[0] + 5, c[1] - 1), (c[0], c[1] - 1)])
    elif logo == "double":
        for dx in (-4, 4):
            pygame.draw.rect(s, ink, (c[0] + dx - 2, c[1] - 6, 4, 12), border_radius=2)
    else:
        pygame.draw.rect(s, ink, (c[0] - 6, c[1] - 4, 12, 9), border_radius=3)
    win = pygame.Rect(box.x + 5, box.y + 26, box.w - 14, 30)            # escaparate con latas
    pygame.draw.rect(s, (30, 34, 40), win)
    for i in range(3):
        for j in range(2):
            pygame.draw.rect(s, trim, (win.x + 3 + i * 8, win.y + 3 + j * 14, 5, 10), border_radius=2)
    pygame.draw.rect(s, OUTLINE, win, 1)
    pygame.draw.rect(s, (24, 24, 28), (box.x + 8, box.bottom - 16, box.w - 18, 8), border_radius=2)  # ranura
    if on:
        pygame.draw.circle(s, (120, 255, 140), (box.right - 12, box.y + 62), 3)
    return s


def generator(on=False):
    """Activador de energía del piso: cuadro eléctrico con palanca."""
    w, h = 44, 58
    s = _surf(w, h)
    box = pygame.Rect(4, 8, 36, 46)
    pygame.draw.rect(s, OUTLINE, box.inflate(4, 4), border_radius=4)
    pygame.draw.rect(s, (150, 150, 140), box, border_radius=4)
    pygame.draw.rect(s, (110, 112, 104), (box.x, box.bottom - 10, box.w, 10), border_radius=4)
    pygame.draw.polygon(s, (240, 200, 50), [(22, 14), (16, 26), (21, 26), (18, 34), (27, 22), (22, 22), (25, 14)])
    pygame.draw.polygon(s, OUTLINE, [(22, 14), (16, 26), (21, 26), (18, 34), (27, 22), (22, 22), (25, 14)], 1)
    lever_y = 38 if on else 46
    pygame.draw.line(s, OUTLINE, (box.right - 6, 44), (box.right + 2, lever_y - 8), 5)
    pygame.draw.line(s, (60, 60, 64), (box.right - 6, 44), (box.right + 2, lever_y - 8), 3)
    pygame.draw.circle(s, (200, 50, 50), (box.right + 2, lever_y - 8), 4)
    light = (120, 255, 140) if on else (90, 40, 40)
    pygame.draw.circle(s, OUTLINE, (12, 44), 4)
    pygame.draw.circle(s, light, (12, 44), 3)
    return s


def _rubble_block(s, w, depth, height):
    """Derrumbe que tapa un paso: montón de cascotes y vigas."""
    rng = random.Random(w * 13 + height)
    total = depth + height
    for _ in range(max(6, w * total // 120)):
        x, y = rng.randint(0, w), rng.randint(total // 3, total)
        r = rng.randint(6, 14)
        c = rng.choice([(150, 146, 136), (120, 118, 110), (176, 170, 158), (100, 98, 92)])
        pygame.draw.circle(s, OUTLINE, (x, y), r + 1)
        pygame.draw.circle(s, c, (x, y), r)
    for _ in range(2):   # vigas
        x = rng.randint(0, max(1, w - 10))
        pygame.draw.line(s, OUTLINE, (x, total - 4), (x + rng.randint(-20, 20), total // 4), 7)
        pygame.draw.line(s, (130, 96, 60), (x, total - 4), (x + rng.randint(-20, 20), total // 4), 4)


def shroom():
    """Seta venenosa andante (enemigo común)."""
    w, h = 44, 50
    s = _surf(w, h)
    pygame.draw.ellipse(s, OUTLINE, (12, 22, 20, 26))
    pygame.draw.ellipse(s, (236, 224, 196), (14, 24, 16, 22))                  # tallo
    pygame.draw.circle(s, OUTLINE, (17, 33), 2)                                # ojos
    pygame.draw.circle(s, OUTLINE, (27, 33), 2)
    pygame.draw.ellipse(s, OUTLINE, (1, 4, 42, 26))
    pygame.draw.ellipse(s, (150, 70, 170), (3, 6, 38, 22))                     # sombrero
    for cx, cy, r in ((12, 14, 3), (24, 10, 4), (32, 17, 3), (19, 20, 2)):
        pygame.draw.circle(s, (210, 240, 120), (cx, cy), r)                    # motas tóxicas
    for x in (16, 26):
        pygame.draw.rect(s, OUTLINE, (x, 44, 4, 6), border_radius=2)
    return s


# ---------------------------------------------------------------------------
# Interactuables
# ---------------------------------------------------------------------------
def chest(opened=False):
    s = _surf(46, 42)
    wood, dark, gold = (148, 94, 44), (104, 64, 30), (226, 184, 82)
    body = pygame.Rect(3, 18, 40, 22)
    if opened:
        lid = pygame.Rect(3, 2, 40, 12)
        pygame.draw.rect(s, OUTLINE, lid.inflate(4, 4), border_radius=4)
        pygame.draw.rect(s, dark, lid, border_radius=4)
        pygame.draw.rect(s, OUTLINE, (3, 13, 40, 8))
        pygame.draw.rect(s, (40, 26, 16), (5, 14, 36, 6))
        pygame.draw.circle(s, (255, 236, 150), (16, 17), 2)
    else:
        lid = pygame.Rect(3, 6, 40, 14)
        pygame.draw.rect(s, OUTLINE, lid.inflate(4, 4), border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.rect(s, shade(wood, 1.15), lid, border_top_left_radius=7, border_top_right_radius=7)
        pygame.draw.rect(s, gold, (lid.x + 6, lid.y, 4, lid.h))
        pygame.draw.rect(s, gold, (lid.right - 10, lid.y, 4, lid.h))
    pygame.draw.rect(s, OUTLINE, body.inflate(4, 4), border_radius=3)
    pygame.draw.rect(s, wood, body, border_radius=3)
    pygame.draw.rect(s, dark, (body.x, body.bottom - 5, body.w, 5))
    pygame.draw.rect(s, gold, (body.x + 6, body.y, 4, body.h))
    pygame.draw.rect(s, gold, (body.right - 10, body.y, 4, body.h))
    if not opened:
        pygame.draw.rect(s, OUTLINE, (19, 16, 8, 10))
        pygame.draw.rect(s, gold, (20, 17, 6, 8))
    return s


def sign():
    s = _surf(42, 52)
    pygame.draw.rect(s, OUTLINE, (17, 22, 8, 30))
    pygame.draw.rect(s, (110, 76, 44), (18, 22, 6, 30))
    board = pygame.Rect(3, 4, 36, 22)
    pygame.draw.rect(s, OUTLINE, board.inflate(4, 4), border_radius=3)
    pygame.draw.rect(s, (176, 132, 82), board, border_radius=3)
    for y in (10, 15, 20):
        pygame.draw.line(s, (120, 86, 52), (9, y), (33, y), 2)
    return s


def tablet():
    s = _surf(46, 50)
    pygame.draw.rect(s, OUTLINE, (3, 4, 40, 44), border_top_left_radius=16, border_top_right_radius=16)
    pygame.draw.rect(s, (150, 148, 138), (5, 6, 36, 40), border_top_left_radius=14, border_top_right_radius=14)
    pygame.draw.rect(s, (120, 118, 110), (5, 38, 36, 8))
    for y in (16, 22, 28):
        pygame.draw.line(s, (100, 98, 92), (12, y), (34, y), 2)
    pygame.draw.circle(s, (78, 136, 66), (36, 40), 5)
    return s


def shrine():
    s = _surf(64, 70)
    pygame.draw.rect(s, OUTLINE, (6, 36, 52, 32), border_radius=3)
    pygame.draw.rect(s, (130, 128, 120), (8, 38, 48, 28))
    pygame.draw.rect(s, OUTLINE, (2, 28, 60, 12), border_radius=3)
    pygame.draw.rect(s, (170, 166, 154), (4, 30, 56, 8))
    for r, a in ((18, 40), (12, 70), (8, 120)):
        glow = _surf(r * 2, r * 2)
        pygame.draw.circle(glow, (120, 230, 255, a), (r, r), r)
        s.blit(glow, (32 - r, 16 - r))
    pygame.draw.polygon(s, OUTLINE, [(32, 4), (41, 16), (32, 28), (23, 16)])
    pygame.draw.polygon(s, (110, 220, 250), [(32, 7), (38, 16), (32, 25), (26, 16)])
    pygame.draw.polygon(s, (220, 250, 255), [(32, 7), (35, 13), (30, 15)])
    pygame.draw.circle(s, (80, 140, 70), (12, 60), 6)
    pygame.draw.circle(s, (80, 140, 70), (52, 44), 4)
    return s


def radio(state="off"):
    s = _surf(46, 50)
    # Taburete de madera
    pygame.draw.rect(s, OUTLINE, (9, 30, 28, 20), border_radius=4)
    pygame.draw.rect(s, (104, 72, 44), (11, 32, 24, 17), border_radius=3)
    # Caja de la radio
    box = pygame.Rect(4, 12, 38, 22)
    pygame.draw.rect(s, OUTLINE, box.inflate(4, 4), border_radius=5)
    pygame.draw.rect(s, (128, 86, 52), box, border_radius=5)
    pygame.draw.rect(s, (98, 64, 38), (box.x, box.bottom - 5, box.w, 5))
    pygame.draw.circle(s, (54, 40, 30), (15, 23), 7)
    for dx in (-3, 0, 3):
        for dy in (-3, 0, 3):
            pygame.draw.circle(s, (92, 72, 52), (15 + dx, 23 + dy), 1)
    pygame.draw.rect(s, (226, 210, 160), (26, 17, 12, 6))
    pygame.draw.line(s, (180, 40, 40), (31, 17), (31, 22), 1)
    pygame.draw.circle(s, (60, 46, 34), (32, 28), 3)
    # Antena
    pygame.draw.line(s, OUTLINE, (36, 12), (42, 1), 2)
    tip = {"off": (90, 90, 90), "static": (230, 200, 90), "on": (120, 255, 140)}[state]
    if state == "on":
        glow = _surf(16, 16)
        pygame.draw.circle(glow, (120, 255, 140, 90), (8, 8), 8)
        s.blit(glow, (34, -6))
    pygame.draw.circle(s, tip, (42, 2), 2)
    if state != "off":
        for x, y in ((3, 6), (8, 2), (12, 7)):
            pygame.draw.line(s, (240, 240, 230), (x, y), (x + 3, y - 2), 1)
    return s


# ---------------------------------------------------------------------------
# Bloques (muros / puertas) con volumen: cara superior + cara frontal
# ---------------------------------------------------------------------------
def _stone_block(s, w, depth, height, top, front, ruined=False, seed=0):
    rng = random.Random(seed + w * 7 + height)
    pygame.draw.rect(s, top, (0, 0, w, depth))
    pygame.draw.rect(s, front, (0, depth, w, height))
    # Hileras de sillares en la cara frontal
    row_h = 14
    for i, y in enumerate(range(depth, depth + height, row_h)):
        pygame.draw.line(s, shade(front, 0.78), (0, y), (w, y), 1)
        offset = 0 if i % 2 else 14
        for x in range(offset, w, 28):
            pygame.draw.line(s, shade(front, 0.78), (x, y), (x, min(y + row_h, depth + height)), 1)
    pygame.draw.line(s, shade(top, 1.12), (0, 1), (w, 1), 2)
    pygame.draw.rect(s, OUTLINE, (0, 0, w, depth + height), 2)
    pygame.draw.line(s, OUTLINE, (0, depth), (w, depth), 2)
    if ruined:
        for _ in range(max(2, w // 50)):
            x = rng.randint(0, w)
            pygame.draw.circle(s, (74, 132, 64), (x, rng.randint(0, depth)), rng.randint(5, 10))
            pygame.draw.line(s, (60, 116, 54), (x, depth), (x + rng.randint(-4, 4),
                             depth + rng.randint(10, height - 4)), 3)
        for _ in range(max(1, w // 90)):
            x = rng.randint(8, max(9, w - 8))
            y = depth + rng.randint(4, height - 10)
            pygame.draw.lines(s, shade(front, 0.6), False,
                              [(x, y), (x + 4, y + 6), (x + 1, y + 12)], 1)


def _plaster_block(s, w, depth, height, seed=0):
    """Pared de hospital: yeso claro con zócalo verde y desconchones."""
    rng = random.Random(seed + w * 3 + height)
    total = depth + height
    band = height // 3
    pygame.draw.rect(s, (206, 208, 196), (0, 0, w, depth))                 # cara superior
    pygame.draw.rect(s, (186, 190, 176), (0, depth, w, height))             # cara frontal
    pygame.draw.rect(s, (104, 140, 120), (0, total - band, w, band))        # zócalo
    pygame.draw.line(s, (80, 110, 94), (0, total - band), (w, total - band), 2)
    for _ in range(max(1, w // 60)):
        x = rng.randint(4, max(5, w - 20))
        y = depth + rng.randint(14, max(15, height // 2))
        pygame.draw.ellipse(s, (150, 146, 128), (x, y, rng.randint(8, 18), rng.randint(5, 9)))
        pygame.draw.lines(s, (120, 118, 108), False, [(x + 4, y), (x + 8, y - 6), (x + 6, y - 12)], 1)
    pygame.draw.rect(s, OUTLINE, (0, 0, w, total), 2)
    pygame.draw.line(s, OUTLINE, (0, depth), (w, depth), 2)


def _cave_block(s, w, depth, height):
    """Pared de roca de cueva: bloque irregular con grietas."""
    rng = random.Random(w * 5 + height)
    total = depth + height
    top, front = (98, 92, 104), (70, 66, 78)
    pygame.draw.rect(s, top, (0, 0, w, depth))
    pygame.draw.rect(s, front, (0, depth, w, height))
    for _ in range(max(2, w * height // 500)):
        x, y = rng.randint(0, w), rng.randint(depth, total)
        pygame.draw.ellipse(s, shade(front, rng.choice((0.8, 1.15))), (x - 10, y - 6, rng.randint(14, 30), rng.randint(8, 14)))
    for _ in range(max(1, w // 60)):
        x = rng.randint(6, max(7, w - 6))
        pygame.draw.lines(s, shade(front, 0.55), False,
                          [(x, depth + 2), (x + rng.randint(-6, 6), depth + height // 2), (x + rng.randint(-6, 6), total - 2)], 2)
    pygame.draw.rect(s, OUTLINE, (0, 0, w, total), 2)
    pygame.draw.line(s, OUTLINE, (0, depth), (w, depth), 2)


def darkness(w, h):
    s = _surf(w, h)
    s.fill((4, 6, 10, 238))
    return s


def _leaf_wall(s, w, depth, height, burning=None, roots=False):
    """Pared de hojas y enredaderas (o de raíces secas, roots=True).
    burning: None, 0 o 1 (fotograma de las llamas)."""
    rng = random.Random(w * 7 + height)
    total = depth + height
    base = (52, 104, 48) if burning is None else (96, 70, 36)
    if roots and burning is None:
        base = (88, 66, 44)
    pygame.draw.rect(s, OUTLINE, (0, 0, w, total), border_radius=6)
    pygame.draw.rect(s, base, (2, 2, w - 4, total - 4), border_radius=6)
    for _ in range(w * total // 60):
        x, y = rng.randint(2, w - 3), rng.randint(2, total - 3)
        r = rng.randint(3, 7)
        if roots and burning is None:
            col = rng.choice(((120, 90, 58), (70, 52, 34), (140, 108, 70), (100, 76, 50)))
            pygame.draw.line(s, col, (x, y), (x + rng.randint(-8, 8), y + rng.randint(6, 16)), rng.randint(2, 4))
            continue
        if burning is None:
            col = rng.choice(((70, 132, 58), (88, 150, 66), (44, 92, 42), (110, 168, 74)))
        else:
            col = rng.choice(((120, 84, 40), (70, 52, 30), (150, 100, 44)))
        pygame.draw.circle(s, col, (x, y), r)
    if burning is not None:
        for k in range(max(2, w // 14)):
            fx = 4 + k * 14 + (6 if burning else 0)
            fy = total - rng.randint(6, max(7, total // 2))
            h = rng.randint(14, 26)
            pygame.draw.polygon(s, (250, 120, 40), [(fx - 6, total - 4), (fx, fy - h), (fx + 6, total - 4)])
            pygame.draw.polygon(s, (255, 214, 90), [(fx - 3, total - 4), (fx, fy - h // 2), (fx + 3, total - 4)])


def jump_spot():
    """Punto de salto: losa con flecha hacia arriba (marca dónde puede saltar Hero)."""
    s = _surf(40, 26)
    pygame.draw.ellipse(s, OUTLINE, (0, 6, 40, 20))
    pygame.draw.ellipse(s, (182, 176, 150), (2, 8, 36, 16))
    pygame.draw.polygon(s, OUTLINE, [(20, 0), (29, 11), (24, 11), (24, 19), (16, 19), (16, 11), (11, 11)])
    pygame.draw.polygon(s, (250, 206, 92), [(20, 3), (26, 10), (22, 10), (22, 17), (18, 17), (18, 10), (14, 10)])
    return s


def make_block(key, w, depth, height):
    village = village_sprites.make_block(key, w, depth, height)    # aldea del vacío
    if village is not None:
        return village
    total = depth + height
    s = _surf(w, total)
    if key == "leafwall":
        _leaf_wall(s, w, depth, height)
        return s
    if key.startswith("leafwall_burning"):
        _leaf_wall(s, w, depth, height, burning=int(key[-1]))
        return s
    if key == "rootwall":
        _leaf_wall(s, w, depth, height, roots=True)
        return s
    if key.startswith("rootwall_burning"):
        _leaf_wall(s, w, depth, height, burning=int(key[-1]), roots=True)
        return s
    stone_top, stone_front = (162, 160, 148), (116, 114, 104)
    if key == "wall_stone":
        _stone_block(s, w, depth, height, stone_top, stone_front)
    elif key == "wall_hospital":
        _plaster_block(s, w, depth, height)
    elif key.startswith("door_metal"):
        _plaster_block(s, w, depth, height)
        door = pygame.Rect(6, depth + 4, w - 12, height - 4)
        if key.endswith("closed"):
            pygame.draw.rect(s, OUTLINE, door.inflate(4, 2))
            pygame.draw.rect(s, (150, 158, 166), door)
            pygame.draw.line(s, OUTLINE, (door.centerx, door.y), (door.centerx, door.bottom), 2)
            pygame.draw.rect(s, (240, 190, 70), (door.centerx - 8, depth - 2, 16, 6))  # indicador
        else:
            s.fill((10, 12, 14, 120), door)
            pygame.draw.rect(s, (150, 158, 166), (door.x, door.y, 5, door.h))
            pygame.draw.rect(s, (150, 158, 166), (door.right - 5, door.y, 5, door.h))
            pygame.draw.rect(s, (120, 230, 130), (door.centerx - 8, depth - 2, 16, 6))
    elif key == "wall_rubble":
        _rubble_block(s, w, depth, height)
    elif key == "wall_cave":
        _cave_block(s, w, depth, height)
    elif key == "wall_ruin":
        _stone_block(s, w, depth, height, (150, 150, 136), (110, 108, 98), ruined=True)
    elif key.startswith("door_gate"):
        iron = (64, 66, 74)
        if key.endswith("closed"):
            for x in range(4, w, 10):
                pygame.draw.line(s, OUTLINE, (x, 0), (x, total), 4)
                pygame.draw.line(s, iron, (x, 0), (x, total), 2)
                pygame.draw.circle(s, iron, (x, 2), 3)
            for y in (depth + 6, total - 10):
                pygame.draw.rect(s, OUTLINE, (0, y - 2, w, 6))
                pygame.draw.rect(s, (92, 80, 70), (1, y - 1, w - 2, 4))
            lock = pygame.Rect(w // 2 - 6, depth + height // 2 - 6, 12, 14)
            pygame.draw.rect(s, OUTLINE, lock.inflate(2, 2), border_radius=2)
            pygame.draw.rect(s, (176, 120, 60), lock, border_radius=2)
        else:
            for x in (4, w - 5):
                pygame.draw.line(s, OUTLINE, (x, 0), (x, total), 4)
                pygame.draw.line(s, iron, (x, 0), (x, total), 2)
    elif key.startswith("door_secret"):
        if key.endswith("closed"):
            _stone_block(s, w, depth, height, (150, 150, 136), (110, 108, 98), ruined=True, seed=3)
            # Contorno de arco casi invisible: la pista para el jugador atento.
            pygame.draw.arc(s, (96, 94, 86), (14, depth + 8, w - 28, height), 0, math.pi, 2)
            rng = random.Random(42)
            for _ in range(26):   # hiedra espesa
                x, y = rng.randint(4, w - 4), rng.randint(depth - 4, total - 6)
                pygame.draw.circle(s, rng.choice([(58, 118, 54), (72, 136, 58), (48, 100, 50)]),
                                   (x, y), rng.randint(5, 9))
        else:
            # Paso abierto: queda el dintel arriba y un hueco translúcido
            # (el jugador se ve "dentro" del umbral al cruzarlo).
            _stone_block(s, w, depth, height, (150, 150, 136), (110, 108, 98), seed=3)
            opening = pygame.Rect(10, depth + 14, w - 20, height - 14)
            s.fill((12, 16, 14, 90), opening)
            pygame.draw.arc(s, OUTLINE, (10, depth + 2, w - 20, 28), 0, math.pi, 2)
            pygame.draw.rect(s, OUTLINE, (8, depth + 14, 2, height - 14))
            pygame.draw.rect(s, OUTLINE, (w - 10, depth + 14, 2, height - 14))
    elif key.startswith("door_wood"):
        _stone_block(s, w, depth, height, stone_top, stone_front)
        door = pygame.Rect(8, depth + 6, w - 16, height - 6)
        if key.endswith("closed"):
            pygame.draw.rect(s, OUTLINE, door.inflate(4, 2), border_top_left_radius=12, border_top_right_radius=12)
            pygame.draw.rect(s, (120, 80, 44), door, border_top_left_radius=12, border_top_right_radius=12)
            for x in range(door.x + 8, door.right, 10):
                pygame.draw.line(s, (92, 60, 32), (x, door.y + 4), (x, door.bottom), 2)
        else:
            s.fill((0, 0, 0, 0), door)
    else:
        s.fill((255, 0, 255, 160))
    return s


def cover(w, h, seed=0):
    """Follaje denso que oculta zonas secretas."""
    rng = random.Random(seed)
    s = _surf(w, h)
    pygame.draw.rect(s, (30, 64, 40), (24, 24, w - 48, h - 48), border_radius=30)
    for _ in range(int(w * h / 900)):
        x, y = rng.randint(10, w - 10), rng.randint(10, h - 10)
        r = rng.randint(22, 38)
        g = rng.choice(TREE_GREENS)
        pygame.draw.circle(s, OUTLINE, (x, y), r + 2)
        pygame.draw.circle(s, shade(g, 0.7), (x, y + 3), r)
        pygame.draw.circle(s, g, (x, y), r - 4)
        pygame.draw.circle(s, shade(g, 1.2), (x - r // 3, y - r // 3), r // 4)
    return s


def missing(key):
    s = _surf(32, 32)
    s.fill((255, 0, 255, 200))
    pygame.draw.line(s, (0, 0, 0), (0, 0), (31, 31), 2)
    print(f"[placeholders] Sin placeholder para '{key}'")
    return s


# ---------------------------------------------------------------------------
def make(key):
    """Devuelve el placeholder para una clave de asset."""
    parts = key.split("_")
    head = parts[0]
    if head == "player":
        direction = parts[1] if len(parts) > 1 else "down"
        frame = int(parts[2]) if len(parts) > 2 else 0
        return player(direction, frame)
    if head == "avatar":
        name = parts[1] if len(parts) > 1 else ""
        direction = parts[2] if len(parts) > 2 else "down"
        frame = int(parts[3]) if len(parts) > 3 else 0
        return avatar(name, direction, frame)
    if head == "npc":
        return npc(parts[1] if len(parts) > 1 else "default")
    if head == "tree":
        return tree(int(parts[1]) if len(parts) > 1 else 0)
    if head == "pine":
        return pine(int(parts[1]) if len(parts) > 1 else 0)
    if head == "chest":
        return chest(opened=key.endswith("open"))
    if head == "radio":
        return radio(parts[1] if len(parts) > 1 else "off")
    if head == "switch":
        return switch(on=key.endswith("on"))
    if head == "pillar":
        return pillar(broken=key.endswith("broken"))
    if head == "perk":
        # perk_<nombre>_<on|off>  (el nombre puede llevar "_": perk_quick_revive_on)
        on = parts[-1] == "on"
        name = "_".join(parts[1:-1]) if parts[-1] in ("on", "off") else "_".join(parts[1:])
        return perk_machine(name, on)
    if head == "generator":
        return generator(on=key.endswith("on"))
    if head == "stalagmite":
        return stalagmite(int(parts[1]) if len(parts) > 1 else 0)
    if key.startswith("cave_rock"):
        return cave_rock(int(parts[2]) if len(parts) > 2 else 0)
    if head == "crystal":
        return crystal(int(parts[1]) if len(parts) > 1 else 0)
    simple = {"rock": rock, "stump": stump, "log": log, "bush": bush, "tall_grass": tall_grass,
              "sign": sign, "tablet": tablet, "shrine": shrine, "bed": bed, "cabinet": cabinet,
              "rubble": rubble, "monitor": monitor, "operating_table": operating_table,
              "wolf_ghost": wolf_ghost, "wolf_grey": wolf_grey,
              "wolf_fire": wolf_fire, "wolf_ice": wolf_ice, "shroom": shroom,
              "jump_spot": jump_spot, "glowshroom": glowshroom}
    if key in simple:
        return simple[key]()
    village = village_sprites.make(key)            # aldea del vacío
    if village is not None:
        return village
    return missing(key)
