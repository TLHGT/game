"""Colores, fuentes y utilidades de dibujo compartidas por la UI."""
import pygame

SCREEN_W, SCREEN_H = 1280, 720

BG = (16, 18, 26)
BG2 = (24, 28, 40)
PANEL = (32, 36, 50)
LINE = (58, 64, 84)
TEXT = (236, 236, 240)
DIM = (140, 146, 164)
GOLD = (250, 206, 92)

PLAYER_COLORS = [(80, 200, 255), (255, 112, 150)]   # P1 cian, P2 rosa
STABLE_COLOR = (90, 220, 130)
UNSTABLE_COLOR = (255, 84, 72)
MANA_COLOR = (90, 150, 255)
HP_COLOR = (110, 230, 120)

PROPERTY_COLORS = {
    "ATTACK": (235, 84, 72),
    "MAGIC": (64, 196, 196),     # ofensiva a distancia: se enfrenta como ATTACK
    "GUARD": (72, 140, 240),
    "BREAK": (245, 178, 52),
    "SPECIAL": (176, 110, 240),  # cartas SPECIAL (acompañan a la acción principal)
    None: (166, 104, 232),
}

# Status Effects: el color ayuda, pero cada estado tiene además su icono y su abreviatura
STATUS_COLORS = {
    "BURN": (255, 128, 48),
    "POISON": (170, 100, 230),
    "PARALYZE": (250, 226, 70),
    "FREEZE": (130, 220, 255),
    "SLEEP": (150, 160, 255),
}
ICE_COLOR = STATUS_COLORS["FREEZE"]

_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.SysFont("bahnschrift,segoeui,arial", size, bold=bold)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size + 6)
    return _fonts[key]


def text(surface, s, size, color, pos, anchor="topleft", bold=True, alpha=255, shadow=False):
    img = font(size, bold).render(str(s), True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        sh = font(size, bold).render(str(s), True, (0, 0, 0))
        sh.set_alpha(min(alpha, 160))
        surface.blit(sh, rect.move(2, 3))
    if alpha < 255:
        img.set_alpha(alpha)
    surface.blit(img, rect)
    return rect


def wrap(s, size, max_w, bold=False):
    f = font(size, bold)
    words, lines, line = s.split(), [], ""
    for w in words:
        cand = f"{line} {w}".strip()
        if f.size(cand)[0] <= max_w or not line:
            line = cand
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def panel(surface, rect, color=PANEL, radius=12, border=LINE, alpha=255, width=2):
    if alpha < 255:
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
        if border:
            pygame.draw.rect(s, (*border, alpha), s.get_rect(), width, border_radius=radius)
        surface.blit(s, rect)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(surface, border, rect, width, border_radius=radius)


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
