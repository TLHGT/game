"""Gráficos provisionales de la Aldea del vacío (solo dibujo, como placeholders.py).

Aldeanos huecos: un aldeano normal con manchas moradas de corrupción; al
transformarse (pasiva Corrupted, sprite "<clave>_void") les salen tentáculos,
ojos de más y una boca vertical: partes "lovecraftianas".
Todos miran a la derecha (el juego los voltea).
"""
import math
import random

import pygame

OUTLINE = (28, 30, 34)
VOID = (150, 70, 210)
VOID_DARK = (70, 26, 100)
VOID_LIGHT = (210, 160, 255)


def shade(color, f):
    return tuple(max(0, min(255, int(c * f))) for c in color[:3])


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _glow(s, center, radius, color, alpha=70):
    g = _surf(radius * 2, radius * 2)
    pygame.draw.circle(g, (*color, alpha), (radius, radius), radius)
    s.blit(g, (center[0] - radius, center[1] - radius))


def _font(size):
    try:
        return pygame.font.Font(None, size)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Aldeanos
# ---------------------------------------------------------------------------
VILLAGERS = {
    "herrero": dict(tunic=(96, 70, 56), apron=(70, 50, 36), skin=(214, 170, 130), hair=(40, 34, 30),
                    beard=(60, 46, 36), tool="hammer"),
    "granjero": dict(tunic=(70, 104, 150), apron=None, skin=(232, 190, 150), hair=(150, 104, 56),
                     hat=(206, 176, 96), tool="pitchfork"),
    "vendedor": dict(tunic=(150, 44, 52), apron=None, skin=(200, 150, 112), hair=(30, 26, 30),
                     hat=(70, 44, 90), vest=(230, 190, 80), tool="pouch"),
}


def villager(kind="herrero", corrupted=False):
    cfg = VILLAGERS.get(kind, VILLAGERS["herrero"])
    w, h = (64, 82) if corrupted else (44, 64)
    s = _surf(w, h)
    cx, feet = w // 2 - (2 if corrupted else 0), h - 2
    rng = random.Random(len(kind) * 7 + corrupted)
    if corrupted:                               # tentáculos que salen de la espalda
        for k, (dx, length, phase) in enumerate(((-14, 30, 0.0), (-8, 38, 1.2), (-18, 24, 2.4))):
            pts = []
            for i in range(9):
                t = i / 8
                pts.append((cx + dx - t * length * 0.6 + math.sin(t * 5 + phase) * 6,
                            feet - 34 - t * length))
            pygame.draw.lines(s, OUTLINE, False, pts, 8 - k)
            pygame.draw.lines(s, VOID, False, pts, 5 - k)
            for p in pts[2::3]:
                pygame.draw.circle(s, VOID_LIGHT, (int(p[0]), int(p[1])), 1)
        _glow(s, (cx, feet - 30), 26, VOID, 50)
    # Piernas
    for dx in (-5, 5):
        r = pygame.Rect(cx + dx - 3, feet - 13, 7, 13)
        pygame.draw.rect(s, OUTLINE, r.inflate(2, 2), border_radius=2)
        pygame.draw.rect(s, (54, 46, 42), r, border_radius=2)
    # Cuerpo
    bw = 24 if corrupted else 20
    body = pygame.Rect(cx - bw // 2, feet - 33, bw, 22)
    pygame.draw.rect(s, OUTLINE, body.inflate(4, 4), border_radius=6)
    pygame.draw.rect(s, cfg["tunic"], body, border_radius=6)
    if cfg.get("apron"):
        pygame.draw.rect(s, cfg["apron"], (body.x + 3, body.y + 6, body.w - 6, body.h - 4), border_radius=3)
    if cfg.get("vest"):
        pygame.draw.rect(s, cfg["vest"], (body.x, body.y, 5, body.h), border_radius=2)
        pygame.draw.rect(s, cfg["vest"], (body.right - 5, body.y, 5, body.h), border_radius=2)
    if kind == "granjero":                       # tirantes del peto
        pygame.draw.line(s, (60, 80, 120), (body.x + 4, body.y), (body.x + 4, body.bottom), 3)
        pygame.draw.line(s, (60, 80, 120), (body.right - 5, body.y), (body.right - 5, body.bottom), 3)
    # Brazo y herramienta
    arm = pygame.Rect(0, 0, 7, 14)
    arm.midtop = (cx + bw // 2, body.y + 3)
    pygame.draw.rect(s, OUTLINE, arm.inflate(2, 2), border_radius=3)
    pygame.draw.rect(s, cfg["skin"], arm, border_radius=3)
    hx, hy = arm.centerx + 3, arm.bottom
    if cfg["tool"] == "hammer":
        pygame.draw.line(s, OUTLINE, (hx, hy + 2), (hx + 6, hy - 14), 4)
        pygame.draw.line(s, (120, 84, 50), (hx, hy + 2), (hx + 6, hy - 14), 2)
        pygame.draw.rect(s, OUTLINE, (hx, hy - 20, 14, 9), border_radius=2)
        pygame.draw.rect(s, (130, 134, 140), (hx + 1, hy - 19, 12, 7), border_radius=2)
    elif cfg["tool"] == "pitchfork":
        pygame.draw.line(s, OUTLINE, (hx, hy + 6), (hx + 2, hy - 30), 4)
        pygame.draw.line(s, (140, 100, 60), (hx, hy + 6), (hx + 2, hy - 30), 2)
        for dx in (-4, 0, 4):
            pygame.draw.line(s, (170, 170, 176), (hx + 2 + dx, hy - 30), (hx + 2 + dx, hy - 40), 2)
        pygame.draw.line(s, (170, 170, 176), (hx - 2, hy - 30), (hx + 6, hy - 30), 2)
    else:
        pygame.draw.circle(s, OUTLINE, (hx, hy + 2), 6)
        pygame.draw.circle(s, (176, 134, 70), (hx, hy + 2), 5)
        pygame.draw.circle(s, (250, 220, 90), (hx + 1, hy - 2), 2)
    # Cabeza
    head = (cx + 2, feet - 44)
    pygame.draw.circle(s, OUTLINE, head, 13)
    pygame.draw.circle(s, cfg["skin"], head, 11)
    pygame.draw.ellipse(s, cfg["hair"], (head[0] - 11, head[1] - 12, 22, 10))
    if cfg.get("beard"):
        pygame.draw.ellipse(s, cfg["beard"], (head[0] - 6, head[1] + 3, 16, 9))
    if cfg.get("hat"):
        pygame.draw.ellipse(s, OUTLINE, (head[0] - 16, head[1] - 10, 32, 9))
        pygame.draw.ellipse(s, cfg["hat"], (head[0] - 15, head[1] - 9, 30, 7))
        pygame.draw.rect(s, cfg["hat"], (head[0] - 8, head[1] - 17, 16, 9), border_radius=4)
    # Ojos: vacíos y morados (huecos por dentro)
    eye = VOID_LIGHT if not corrupted else (255, 230, 120)
    pygame.draw.circle(s, (20, 10, 30), (head[0] + 5, head[1] + 1), 3)
    pygame.draw.circle(s, eye, (head[0] + 5, head[1] + 1), 1)
    # Manchas moradas de la corrupción
    for _ in range(7 if corrupted else 4):
        x = rng.randint(body.x + 2, body.right - 4)
        y = rng.randint(body.y + 2, body.bottom - 3)
        pygame.draw.ellipse(s, VOID, (x, y, rng.randint(3, 6), rng.randint(3, 5)))
    pygame.draw.ellipse(s, VOID, (head[0] - 8, head[1] + 2, 5, 4))
    pygame.draw.ellipse(s, VOID_DARK, (head[0] - 3, head[1] - 5, 4, 3))
    if corrupted:
        # Ojos de más por el cuerpo y una boca vertical llena de dientes en el pecho
        for ex, ey in ((body.x + 4, body.y + 5), (body.right - 6, body.y + 12), (head[0] - 6, head[1] - 3)):
            pygame.draw.circle(s, OUTLINE, (ex, ey), 4)
            pygame.draw.circle(s, (250, 240, 200), (ex, ey), 3)
            pygame.draw.circle(s, VOID_DARK, (ex, ey), 1)
        mouth = pygame.Rect(body.centerx - 3, body.y + 4, 7, 14)
        pygame.draw.ellipse(s, (30, 6, 30), mouth)
        for y in range(mouth.y + 2, mouth.bottom - 2, 3):
            pygame.draw.line(s, (240, 230, 220), (mouth.x + 1, y), (mouth.x + 3, y), 1)
            pygame.draw.line(s, (240, 230, 220), (mouth.right - 2, y + 1), (mouth.right - 4, y + 1), 1)
        # Antenas / cuernos de quitina
        pygame.draw.line(s, OUTLINE, (head[0] - 4, head[1] - 10), (head[0] - 12, head[1] - 22), 4)
        pygame.draw.line(s, VOID, (head[0] - 4, head[1] - 10), (head[0] - 12, head[1] - 22), 2)
        pygame.draw.line(s, OUTLINE, (head[0] + 4, head[1] - 10), (head[0] + 10, head[1] - 24), 4)
        pygame.draw.line(s, VOID, (head[0] + 4, head[1] - 10), (head[0] + 10, head[1] - 24), 2)
    return s


# ---------------------------------------------------------------------------
# Void Insect (mosca grande morada), sus crías y su forma final
# ---------------------------------------------------------------------------
def void_insect(variant="main"):
    scale = {"main": 1.0, "brood": 0.55, "rage": 1.15}[variant]
    w, h = int(120 * scale) + 8, int(96 * scale) + 8
    s = _surf(w, h)
    k = scale
    cx, cy = w // 2 - int(4 * k), int(52 * k)
    body_col = (122, 54, 170) if variant != "rage" else (150, 40, 150)
    _glow(s, (cx, cy), int(46 * k), VOID, 45 if variant != "rage" else 80)
    # Alas (translúcidas)
    for side, ang in ((-1, -0.5), (1, -0.3)):
        wing = _surf(w, h)
        r = pygame.Rect(0, 0, int(58 * k), int(26 * k))
        r.center = (cx + side * int(6 * k) - int(18 * k), cy - int(22 * k))
        pygame.draw.ellipse(wing, (200, 180, 255, 110), r)
        pygame.draw.ellipse(wing, (90, 60, 140, 200), r, 2)
        pygame.draw.line(wing, (90, 60, 140, 160), r.midright, r.midleft, 1)
        s.blit(pygame.transform.rotate(wing, 0), (0, int(side * 4 * k)))
    # Patas
    for i in range(3):
        x = cx - int(16 * k) + i * int(14 * k)
        pygame.draw.lines(s, OUTLINE, False, [(x, cy + int(10 * k)), (x - int(6 * k), cy + int(26 * k)),
                                               (x - int(2 * k), cy + int(38 * k))], max(2, int(3 * k)))
    # Abdomen y tórax
    abdomen = pygame.Rect(0, 0, int(56 * k), int(36 * k))
    abdomen.center = (cx - int(18 * k), cy + int(4 * k))
    pygame.draw.ellipse(s, OUTLINE, abdomen.inflate(4, 4))
    pygame.draw.ellipse(s, body_col, abdomen)
    for i in range(3):
        x = abdomen.x + int((12 + i * 12) * k)
        pygame.draw.line(s, shade(body_col, 0.6), (x, abdomen.y + 3), (x - 2, abdomen.bottom - 3), 2)
    thorax = pygame.Rect(0, 0, int(34 * k), int(30 * k))
    thorax.center = (cx + int(14 * k), cy)
    pygame.draw.ellipse(s, OUTLINE, thorax.inflate(4, 4))
    pygame.draw.ellipse(s, shade(body_col, 1.15), thorax)
    # Cabeza con ojos compuestos
    head = (cx + int(34 * k), cy - int(2 * k))
    pygame.draw.circle(s, OUTLINE, head, int(15 * k) + 2)
    pygame.draw.circle(s, shade(body_col, 0.9), head, int(15 * k))
    eye_col = (230, 40, 60) if variant != "brood" else (255, 120, 200)
    for ex, ey in ((head[0] + int(4 * k), head[1] - int(5 * k)), (head[0] + int(4 * k), head[1] + int(6 * k))):
        pygame.draw.circle(s, OUTLINE, (ex, ey), int(8 * k) + 1)
        pygame.draw.circle(s, eye_col, (ex, ey), int(8 * k))
        for dx in (-3, 0, 3):
            pygame.draw.circle(s, shade(eye_col, 1.3), (ex + int(dx * k), ey - int(2 * k)), max(1, int(1.5 * k)))
    pygame.draw.line(s, OUTLINE, (head[0] + int(12 * k), head[1] + int(4 * k)),
                     (head[0] + int(20 * k), head[1] + int(14 * k)), max(2, int(3 * k)))  # trompa
    if variant == "rage":                         # grietas que brillan
        for x0 in (abdomen.x + 10, abdomen.x + 30, thorax.x + 8):
            pygame.draw.lines(s, VOID_LIGHT, False, [(x0, cy - 8), (x0 + 5, cy), (x0 + 1, cy + 9)], 2)
    return s


# ---------------------------------------------------------------------------
# Objetos de la aldea
# ---------------------------------------------------------------------------
def clock_activator(hour=12, on=False):
    s = _surf(40, 56)
    if on:
        _glow(s, (20, 26), 20, VOID, 90)
    pygame.draw.polygon(s, OUTLINE, [(8, 54), (6, 18), (20, 4), (34, 18), (32, 54)])
    pygame.draw.polygon(s, (110, 104, 112) if not on else (90, 60, 120),
                        [(10, 52), (9, 19), (20, 7), (31, 19), (30, 52)])
    rune = VOID_LIGHT if on else (70, 64, 74)
    pygame.draw.circle(s, rune, (20, 22), 8, 2)
    font = _font(20)
    if font:
        t = font.render(str(hour), True, (255, 240, 255) if on else (40, 36, 44))
        s.blit(t, t.get_rect(center=(20, 40)))
    return s


def diary():
    s = _surf(30, 34)
    pygame.draw.rect(s, OUTLINE, (12, 14, 6, 20))
    pygame.draw.rect(s, (110, 76, 48), (13, 14, 4, 20))
    pygame.draw.polygon(s, OUTLINE, [(1, 16), (15, 10), (29, 16), (29, 4), (15, 0), (1, 4)])
    pygame.draw.polygon(s, (230, 220, 190), [(3, 14), (15, 9), (15, 1), (3, 5)])
    pygame.draw.polygon(s, (214, 204, 176), [(27, 14), (15, 9), (15, 1), (27, 5)])
    for y in (5, 8):
        pygame.draw.line(s, (120, 110, 100), (5, y), (12, y - 2), 1)
        pygame.draw.line(s, (120, 110, 100), (18, y - 2), (25, y), 1)
    return s


def plush_void():
    s = _surf(34, 34)
    _glow(s, (17, 20), 16, VOID, 80)
    pygame.draw.circle(s, OUTLINE, (17, 22), 11)
    pygame.draw.circle(s, (196, 160, 120), (17, 22), 9)            # cuerpo de trapo
    pygame.draw.circle(s, OUTLINE, (17, 10), 8)
    pygame.draw.circle(s, (206, 172, 132), (17, 10), 6)             # cabeza
    for ex in (11, 23):
        pygame.draw.circle(s, OUTLINE, (ex, 4), 4)
        pygame.draw.circle(s, (206, 172, 132), (ex, 4), 2)          # orejas
    pygame.draw.line(s, OUTLINE, (14, 9), (16, 11), 1)              # ojos de botón cosidos
    pygame.draw.line(s, OUTLINE, (16, 9), (14, 11), 1)
    pygame.draw.circle(s, VOID_DARK, (20, 10), 2)
    pygame.draw.line(s, VOID, (11, 24), (23, 20), 2)                # costura rota
    return s


def void_part(index=0):
    s = _surf(34, 30)
    _glow(s, (17, 18), 15, VOID, 90)
    if index == 0:          # pata
        pygame.draw.lines(s, OUTLINE, False, [(4, 24), (14, 12), (28, 18)], 6)
        pygame.draw.lines(s, (120, 60, 160), False, [(4, 24), (14, 12), (28, 18)], 3)
        for x, y in ((9, 18), (21, 15)):
            pygame.draw.line(s, OUTLINE, (x, y), (x + 2, y - 4), 2)
    elif index == 1:        # ala
        pygame.draw.ellipse(s, (210, 190, 255, 200), (3, 8, 28, 14))
        pygame.draw.ellipse(s, VOID_DARK, (3, 8, 28, 14), 2)
        pygame.draw.line(s, VOID_DARK, (5, 15), (29, 15), 1)
    else:                   # aguijón
        pygame.draw.polygon(s, OUTLINE, [(4, 22), (30, 14), (6, 10)])
        pygame.draw.polygon(s, (150, 80, 190), [(7, 20), (27, 14), (8, 12)])
        pygame.draw.circle(s, VOID_LIGHT, (27, 14), 2)
    return s


def void_circle(filled=0):
    w, h = 120, 60
    s = _surf(w, h)
    pulse = filled / 3
    pygame.draw.ellipse(s, (*VOID_DARK, 160), (4, 8, w - 8, h - 12))
    pygame.draw.ellipse(s, VOID if filled < 3 else VOID_LIGHT, (4, 8, w - 8, h - 12), 3)
    pygame.draw.ellipse(s, VOID, (22, 17, w - 44, h - 30), 2)
    for i in range(10):                                  # runas
        a = i * math.tau / 10
        x, y = w / 2 + math.cos(a) * 46, h / 2 + 2 + math.sin(a) * 19
        pygame.draw.line(s, VOID_LIGHT, (x - 3, y - 2), (x + 3, y + 2), 2)
    for i in range(filled):                              # almas dentro
        x = w // 2 - 22 + i * 22
        _glow(s, (x, 30), 9, (220, 190, 255), 140)
        pygame.draw.circle(s, (240, 230, 255), (x, 30), 4)
    if pulse >= 1:
        _glow(s, (w // 2, h // 2), 30, (230, 200, 255), 70)
    return s


def anvil():
    s = _surf(56, 40)
    pygame.draw.rect(s, OUTLINE, (16, 22, 24, 18), border_radius=2)
    pygame.draw.rect(s, (60, 60, 66), (18, 23, 20, 16))
    pygame.draw.polygon(s, OUTLINE, [(2, 8), (54, 8), (50, 22), (8, 22)])
    pygame.draw.polygon(s, (86, 88, 96), [(5, 10), (51, 10), (48, 20), (10, 20)])
    pygame.draw.polygon(s, (86, 88, 96), [(0, 10), (8, 10), (8, 15)])
    pygame.draw.line(s, (150, 152, 160), (6, 10), (50, 10), 2)
    pygame.draw.rect(s, OUTLINE, (30, 0, 6, 10))                 # martillo encima
    pygame.draw.rect(s, (130, 134, 140), (24, 1, 18, 6), border_radius=2)
    return s


def void_barrier():
    w, h = 200, 170
    s = _surf(w, h)
    dome = pygame.Rect(10, 6, w - 20, h - 12)
    pygame.draw.ellipse(s, (150, 80, 220, 70), dome)
    pygame.draw.ellipse(s, (210, 160, 255, 170), dome, 3)
    for i in range(5):
        a = 0.6 + i * 0.5
        pygame.draw.arc(s, (230, 200, 255, 120), dome.inflate(-20 - i * 18, -16 - i * 14), a, a + 1.2, 2)
    for i in range(9):                                   # hexágonos de energía
        x = 30 + (i % 3) * 60 + (i // 3 % 2) * 30
        y = 40 + (i // 3) * 36
        pts = [(x + 10 * math.cos(k * math.tau / 6), y + 10 * math.sin(k * math.tau / 6)) for k in range(6)]
        pygame.draw.polygon(s, (220, 180, 255, 90), pts, 1)
    return s


def barrel(state="whole"):
    s = _surf(34, 42)
    if state == "whole":
        body = pygame.Rect(4, 4, 26, 36)
        pygame.draw.ellipse(s, OUTLINE, body.inflate(4, 2))
        pygame.draw.rect(s, OUTLINE, (body.x - 1, body.y + 4, body.w + 2, body.h - 8))
        pygame.draw.rect(s, (130, 86, 48), (body.x + 1, body.y + 4, body.w - 2, body.h - 8))
        pygame.draw.ellipse(s, (150, 100, 58), (body.x + 1, body.y, body.w - 2, 9))
        for y in (12, 30):
            pygame.draw.rect(s, (70, 70, 74), (body.x, y, body.w, 3))
        pygame.draw.ellipse(s, (40, 34, 30), (body.x + 3, 22, 8, 6))   # chamuscado
        return s
    for x, y, a in ((4, 34, 20), (14, 36, -30), (22, 33, 60), (8, 30, -70)):     # duelas rotas
        plank = _surf(6, 16)
        plank.fill((118, 78, 44))
        s.blit(pygame.transform.rotate(plank, a), (x, y - 12))
    pygame.draw.ellipse(s, (60, 60, 64), (5, 34, 24, 6), 2)
    if state == "seeds":
        _glow(s, (17, 34), 12, VOID, 120)
        for x, y in ((12, 33), (16, 35), (20, 32), (15, 31), (22, 35), (18, 33)):
            pygame.draw.ellipse(s, (210, 170, 255), (x, y, 3, 2))
    return s


def chicken(humanoid=False):
    if humanoid:
        s = _surf(40, 66)
        _glow(s, (20, 34), 22, VOID, 70)
        for dx in (-5, 5):                                      # piernas humanas
            pygame.draw.line(s, OUTLINE, (20 + dx, 64), (20 + dx, 44), 6)
            pygame.draw.line(s, (220, 170, 120), (20 + dx, 64), (20 + dx, 44), 4)
        pygame.draw.ellipse(s, OUTLINE, (8, 18, 26, 30))
        pygame.draw.ellipse(s, (244, 240, 230), (10, 20, 22, 26))
        pygame.draw.circle(s, OUTLINE, (22, 12), 9)
        pygame.draw.circle(s, (244, 240, 230), (22, 12), 7)
        pygame.draw.polygon(s, (230, 60, 50), [(18, 4), (22, 0), (26, 4)])
        pygame.draw.polygon(s, (240, 180, 50), [(28, 12), (35, 14), (28, 16)])
        pygame.draw.circle(s, VOID, (24, 10), 2)
        pygame.draw.line(s, OUTLINE, (10, 28), (2, 38), 4)                 # brazos con alas
        pygame.draw.line(s, OUTLINE, (32, 28), (38, 38), 4)
        return s
    s = _surf(28, 26)
    pygame.draw.ellipse(s, OUTLINE, (2, 8, 20, 15))
    pygame.draw.ellipse(s, (246, 242, 232), (3, 9, 18, 13))
    pygame.draw.polygon(s, (220, 214, 200), [(4, 12), (0, 6), (6, 9)])         # cola
    pygame.draw.circle(s, OUTLINE, (19, 7), 6)
    pygame.draw.circle(s, (246, 242, 232), (19, 7), 5)
    pygame.draw.polygon(s, (230, 60, 50), [(17, 2), (19, 0), (21, 2)])         # cresta
    pygame.draw.polygon(s, (240, 180, 50), [(23, 7), (27, 8), (23, 10)])       # pico
    pygame.draw.circle(s, OUTLINE, (20, 6), 1)
    for x in (10, 14):
        pygame.draw.line(s, (240, 180, 50), (x, 22), (x, 25), 2)
    return s


def well():
    s = _surf(64, 70)
    pygame.draw.line(s, OUTLINE, (10, 46), (10, 8), 5)
    pygame.draw.line(s, OUTLINE, (54, 46), (54, 8), 5)
    pygame.draw.line(s, (110, 76, 48), (10, 46), (10, 8), 3)
    pygame.draw.line(s, (110, 76, 48), (54, 46), (54, 8), 3)
    pygame.draw.polygon(s, OUTLINE, [(2, 12), (32, 0), (62, 12)])
    pygame.draw.polygon(s, (90, 56, 40), [(5, 11), (32, 2), (59, 11)])
    pygame.draw.line(s, (90, 80, 70), (32, 10), (32, 34), 1)
    pygame.draw.rect(s, OUTLINE, (26, 30, 12, 8))
    pygame.draw.rect(s, (120, 84, 50), (27, 31, 10, 6))
    pygame.draw.ellipse(s, OUTLINE, (4, 40, 56, 28))
    pygame.draw.ellipse(s, (124, 120, 112), (6, 42, 52, 24))
    pygame.draw.ellipse(s, (12, 10, 14), (14, 46, 36, 12))
    for x in range(10, 56, 10):
        pygame.draw.line(s, (96, 92, 86), (x, 54), (x, 64), 1)
    return s


# ---------------------------------------------------------------------------
# Decorado de la aldea (entities/props.py)
# ---------------------------------------------------------------------------
def dead_tree(variant=0):
    rng = random.Random(500 + variant)
    s = _surf(70, 110)
    trunk = (46, 38, 36)
    pygame.draw.polygon(s, OUTLINE, [(29, 108), (31, 40), (39, 40), (43, 108)])
    pygame.draw.polygon(s, trunk, [(31, 106), (33, 42), (37, 42), (41, 106)])
    for _ in range(4 + variant):
        y = rng.randint(20, 70)
        side = rng.choice((-1, 1))
        end = (35 + side * rng.randint(16, 30), y - rng.randint(14, 30))
        pygame.draw.line(s, OUTLINE, (35, y + 10), end, 5)
        pygame.draw.line(s, trunk, (35, y + 10), end, 3)
        pygame.draw.line(s, trunk, end, (end[0] + side * 6, end[1] - 8), 2)
    pygame.draw.line(s, OUTLINE, (35, 42), (35 + rng.randint(-6, 6), 4), 5)
    pygame.draw.line(s, trunk, (35, 42), (35 + rng.randint(-6, 6), 6), 3)
    for _ in range(3):
        pygame.draw.circle(s, rng.choice([(250, 120, 40), (200, 70, 30)]), (rng.randint(30, 40), rng.randint(60, 100)), 1)
    return s


def flames(variant=0):
    rng = random.Random(900 + variant)
    s = _surf(60, 70)
    _glow(s, (30, 50), 28, (255, 140, 40), 60)
    pygame.draw.ellipse(s, (30, 24, 22), (6, 54, 48, 14))                 # escombros quemados
    for _ in range(4):
        pygame.draw.line(s, (40, 30, 26), (rng.randint(8, 50), 62), (rng.randint(8, 50), 50), 4)
    for k in range(5):
        x = 10 + k * 10 + rng.randint(-2, 2)
        hgt = rng.randint(22, 44)
        pygame.draw.polygon(s, (240, 100, 30), [(x - 7, 60), (x, 60 - hgt), (x + 7, 60)])
        pygame.draw.polygon(s, (255, 200, 80), [(x - 3, 60), (x, 60 - hgt // 2), (x + 3, 60)])
    return s


def fountain():
    s = _surf(110, 80)
    pygame.draw.ellipse(s, OUTLINE, (2, 30, 106, 48))
    pygame.draw.ellipse(s, (140, 136, 130), (4, 32, 102, 44))
    pygame.draw.ellipse(s, (40, 36, 38), (14, 38, 82, 30))                 # seca y negra
    pygame.draw.rect(s, OUTLINE, (48, 6, 14, 40), border_radius=3)
    pygame.draw.rect(s, (150, 146, 140), (50, 8, 10, 36), border_radius=3)
    pygame.draw.lines(s, (60, 54, 52), False, [(54, 10), (57, 20), (53, 30), (56, 42)], 2)    # grieta
    return s


def void_crystal(variant=0):
    rng = random.Random(70 + variant)
    s = _surf(60, 80)
    _glow(s, (30, 56), 26, VOID, 70)
    for _ in range(4):
        x = rng.randint(14, 46)
        hgt = rng.randint(30, 66)
        wid = rng.randint(7, 12)
        pts = [(x - wid, 76), (x - wid // 2, 76 - hgt + 10), (x, 76 - hgt), (x + wid // 2, 76 - hgt + 10), (x + wid, 76)]
        pygame.draw.polygon(s, OUTLINE, pts)
        inner = [(x - wid + 2, 75), (x - wid // 2 + 1, 77 - hgt + 10), (x, 78 - hgt),
                 (x + wid // 2 - 1, 77 - hgt + 10), (x + wid - 2, 75)]
        pygame.draw.polygon(s, (130, 60, 190), inner)
        pygame.draw.line(s, VOID_LIGHT, (x, 76 - hgt + 3), (x - 2, 70), 2)
    return s


def void_portal():
    w, h = 300, 160
    s = _surf(w, h)
    c = (w // 2, h // 2)
    for r, a in ((80, 40), (66, 70), (52, 110)):
        _glow(s, c, r, (170, 80, 240), a)
    for i in range(6):
        rect = pygame.Rect(0, 0, 240 - i * 34, 120 - i * 17)
        rect.center = c
        pygame.draw.ellipse(s, (60 + i * 25, 20 + i * 10, 110 + i * 20), rect, 0 if i == 5 else 6)
    for i in range(10):
        a = i * math.tau / 10
        x, y = c[0] + math.cos(a) * 128, c[1] + math.sin(a) * 66
        pygame.draw.line(s, VOID_LIGHT, (x, y), (c[0] + math.cos(a + 0.4) * 104, c[1] + math.sin(a + 0.4) * 52), 2)
    pygame.draw.circle(s, (10, 0, 16), c, 18)
    return s


def haystack():
    s = _surf(60, 50)
    pygame.draw.ellipse(s, OUTLINE, (2, 6, 56, 44))
    pygame.draw.ellipse(s, (170, 140, 70), (4, 8, 52, 40))
    pygame.draw.ellipse(s, (50, 40, 30), (24, 10, 24, 18))                  # quemado
    for x in range(10, 50, 6):
        pygame.draw.line(s, (200, 170, 90), (x, 20), (x + 3, 44), 1)
    return s


def market_stall():
    s = _surf(90, 80)
    for x in (8, 80):
        pygame.draw.line(s, OUTLINE, (x, 78), (x, 18), 5)
        pygame.draw.line(s, (110, 76, 48), (x, 78), (x, 18), 3)
    pygame.draw.rect(s, OUTLINE, (4, 46, 82, 20))
    pygame.draw.rect(s, (130, 92, 56), (6, 48, 78, 16))
    for i, x in enumerate(range(2, 88, 14)):                                  # toldo rasgado
        col = (180, 50, 50) if i % 2 else (230, 210, 180)
        pygame.draw.polygon(s, col, [(x, 14), (x + 14, 14), (x + 14, 26 + (i % 3) * 4), (x, 22)])
    pygame.draw.line(s, OUTLINE, (2, 14), (88, 14), 3)
    for x in (18, 34, 54):
        pygame.draw.circle(s, (200, 170, 70), (x, 46), 4)
    return s


def forge():
    s = _surf(80, 86)
    pygame.draw.rect(s, OUTLINE, (6, 20, 68, 64), border_radius=6)
    pygame.draw.rect(s, (110, 70, 56), (8, 22, 64, 60), border_radius=6)
    for y in range(28, 80, 12):
        pygame.draw.line(s, (80, 50, 40), (8, y), (72, y), 1)
    pygame.draw.rect(s, OUTLINE, (22, 48, 36, 24), border_radius=10)
    pygame.draw.rect(s, (30, 14, 10), (24, 50, 32, 22), border_radius=10)
    _glow(s, (40, 62), 16, (255, 120, 40), 140)
    pygame.draw.rect(s, OUTLINE, (30, 0, 20, 24))                           # chimenea
    pygame.draw.rect(s, (90, 60, 50), (32, 2, 16, 22))
    return s


def crate():
    s = _surf(40, 40)
    pygame.draw.rect(s, OUTLINE, (2, 6, 36, 32))
    pygame.draw.rect(s, (140, 100, 60), (4, 8, 32, 28))
    pygame.draw.line(s, (100, 70, 40), (4, 8), (36, 36), 3)
    pygame.draw.line(s, (100, 70, 40), (36, 8), (4, 36), 3)
    pygame.draw.ellipse(s, (40, 30, 26), (18, 10, 14, 8))
    return s


def gravestone():
    s = _surf(32, 40)
    pygame.draw.rect(s, OUTLINE, (4, 4, 24, 34), border_top_left_radius=12, border_top_right_radius=12)
    pygame.draw.rect(s, (130, 128, 124), (6, 6, 20, 31), border_top_left_radius=10, border_top_right_radius=10)
    pygame.draw.line(s, (90, 88, 84), (16, 12), (16, 26), 2)
    pygame.draw.line(s, (90, 88, 84), (11, 17), (21, 17), 2)
    return s


# ---------------------------------------------------------------------------
# Bloques (muros / bloqueos) con volumen
# ---------------------------------------------------------------------------
def house_block(s, w, depth, height):
    """Pared de casa quemada: entramado de madera y yeso ennegrecido."""
    rng = random.Random(w * 11 + height)
    total = depth + height
    pygame.draw.rect(s, (70, 56, 46), (0, 0, w, depth))
    pygame.draw.rect(s, (150, 136, 112), (0, depth, w, height))
    for x in range(0, w, 34):
        pygame.draw.rect(s, (66, 46, 32), (x, depth, 6, height))
    pygame.draw.rect(s, (66, 46, 32), (0, depth + height // 2 - 3, w, 6))
    for _ in range(max(1, w // 30)):
        x = rng.randint(0, max(1, w - 20))
        pygame.draw.ellipse(s, (36, 30, 28), (x, depth + rng.randint(0, height // 2), rng.randint(14, 34),
                                                rng.randint(10, height)))
    if rng.random() < 0.6:
        x = rng.randint(0, max(1, w - 10))
        pygame.draw.polygon(s, (0, 0, 0, 0), [(x, 0), (x + 16, 0), (x + 8, depth + 10)])    # mordisco del fuego
    pygame.draw.rect(s, OUTLINE, (0, 0, w, total), 2)
    pygame.draw.line(s, OUTLINE, (0, depth), (w, depth), 2)


def fence_block(s, w, depth, height):
    total = depth + height
    for x in range(2, w, 12):
        pygame.draw.rect(s, OUTLINE, (x - 1, 0, 6, total))
        pygame.draw.rect(s, (130, 96, 60), (x, 1, 4, total - 2))
    for y in (depth + 4, total - 8):
        pygame.draw.rect(s, OUTLINE, (0, y - 1, w, 5))
        pygame.draw.rect(s, (150, 112, 70), (0, y, w, 3))


def fire_block(s, w, depth, height, frame=0):
    """Barricada en llamas: escombros con fuego encima (cierra un camino)."""
    rng = random.Random(w * 5 + height)
    total = depth + height
    for _ in range(max(4, w * total // 200)):
        x, y = rng.randint(0, w), rng.randint(total // 2, total)
        pygame.draw.circle(s, rng.choice([(40, 32, 30), (60, 46, 40), (30, 24, 22)]), (x, y), rng.randint(6, 12))
    for k in range(max(3, w // 10)):
        fx = 4 + k * 10 + (4 if frame else 0)
        if fx > w - 2:
            break
        hgt = rng.randint(total // 2, total)
        pygame.draw.polygon(s, (236, 96, 30), [(fx - 7, total - 4), (fx, total - hgt), (fx + 7, total - 4)])
        pygame.draw.polygon(s, (255, 200, 80), [(fx - 3, total - 4), (fx, total - hgt // 2), (fx + 3, total - 4)])


def void_block(s, w, depth, height):
    """Muralla de cristales del vacío."""
    rng = random.Random(w * 3 + height)
    total = depth + height
    for k in range(max(3, w // 12)):
        x = rng.randint(0, w)
        hgt = rng.randint(total // 2, total)
        wid = rng.randint(6, 12)
        pts = [(x - wid, total), (x, total - hgt), (x + wid, total)]
        pygame.draw.polygon(s, OUTLINE, pts)
        pygame.draw.polygon(s, (130, 60, 190), [(x - wid + 2, total - 1), (x, total - hgt + 4), (x + wid - 2, total - 1)])
        pygame.draw.line(s, VOID_LIGHT, (x, total - hgt + 6), (x - 2, total - 6), 1)


def make_block(key, w, depth, height):
    """Bloques de la aldea, o None si `key` no es de la aldea."""
    s = _surf(w, depth + height)
    if key == "wall_house":
        house_block(s, w, depth, height)
    elif key == "wall_fence":
        fence_block(s, w, depth, height)
    elif key.startswith("fireblock"):
        fire_block(s, w, depth, height, int(key[-1]))
    elif key.startswith("voidblock"):
        void_block(s, w, depth, height)
    else:
        return None
    return s


def make(key):
    """Sprite de la aldea para `key`, o None si no es de la aldea."""
    parts = key.split("_")
    if parts[0] == "villager" and len(parts) >= 2:
        return villager(parts[1], corrupted=key.endswith("_void"))
    if key.startswith("void_insect"):
        return void_insect({"void_insect": "main", "void_insect_brood": "brood",
                            "void_insect_rage": "rage"}.get(key, "main"))
    if parts[0] == "clock" and len(parts) == 3:
        return clock_activator(int(parts[2]), on=parts[1] == "on")
    if key.startswith("void_part"):
        return void_part(int(parts[-1]) if parts[-1].isdigit() else 0)
    if key.startswith("void_circle"):
        return void_circle(int(parts[-1]))
    if key.startswith("barrel"):
        return barrel({"barrel": "whole", "barrel_broken": "broken", "barrel_seeds": "seeds"}[key])
    if key.startswith("dead_tree"):
        return dead_tree(int(parts[-1]) if parts[-1].isdigit() else 0)
    if key.startswith("flames"):
        return flames(int(parts[-1]) if parts[-1].isdigit() else 0)
    if key.startswith("void_crystal"):
        return void_crystal(int(parts[-1]) if parts[-1].isdigit() else 0)
    simple = {"diary": diary, "plush_void": plush_void, "anvil": anvil, "void_barrier": void_barrier,
              "chicken": chicken, "chicken_humanoid": lambda: chicken(humanoid=True), "well": well,
              "fountain": fountain, "void_portal": void_portal, "haystack": haystack,
              "market_stall": market_stall, "forge": forge, "crate": crate, "gravestone": gravestone}
    if key in simple:
        return simple[key]()
    return None
