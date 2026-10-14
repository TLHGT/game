"""Dibujo de cartas con formas simples.

Cada concepto se ve por separado:
    color + icono + cabecera  -> TIPO (ATTACK / GUARD / BREAK)
    chips INI · HIT · DES/REC -> iniciativa y qué pasa si gana
    descripción               -> efectos especiales
"""
import pygame

from combate.game.status import STATUS_DEFS, StatusId
from combate.ui import theme as T

CHIP_COLORS = {"INI": (250, 206, 92), "HIT": (235, 110, 96), "DES": (255, 140, 60), "REC": (90, 220, 130),
               "DMG": (255, 255, 255)}


# Chip de estado alterado (BRN, PSN...): la abreviatura lo identifica sin depender del color
STATUS_CHIPS = {d.short: T.STATUS_COLORS[sid.value] for sid, d in STATUS_DEFS.items()}


def chip_color(chip):
    return CHIP_COLORS.get(chip) or STATUS_CHIPS.get(chip) or CHIP_COLORS["DMG"]   # los números son daño


def card_chips(card):
    chips = []
    if card.damage:
        chips.append(str(card.damage))
    if card.has_initiative:
        chips.append("INI")
    if card.generates_hit:
        chips.append("HIT")
    if card.causes_instability or card.has_effect("CAUSE_INSTABILITY"):
        chips.append("DES")
    if card.recovers_stability or card.has_effect("RECOVER_STABILITY"):
        chips.append("REC")
    for data in card.effects:
        if data["type"] == "APPLY_STATUS":
            chips.append(STATUS_DEFS[StatusId(data["status"])].short)
    return chips


def draw_icon(surface, card_type, center, size, color):
    cx, cy = center
    s = size
    if card_type == "ATTACK":          # espada
        pygame.draw.line(surface, color, (cx - s * 0.55, cy + s * 0.55), (cx + s * 0.55, cy - s * 0.55), max(3, int(s * 0.18)))
        pygame.draw.line(surface, color, (cx - s * 0.5, cy + s * 0.1), (cx - s * 0.1, cy + s * 0.5), max(3, int(s * 0.16)))
        pygame.draw.circle(surface, color, (cx - s * 0.62, cy + s * 0.62), max(2, int(s * 0.14)))
    elif card_type == "MAGIC":         # orbe con órbita (a distancia)
        pygame.draw.circle(surface, color, (int(cx), int(cy)), max(3, int(s * 0.32)))
        pygame.draw.ellipse(surface, color, pygame.Rect(cx - s * 0.75, cy - s * 0.3, s * 1.5, s * 0.6),
                            max(2, int(s * 0.1)))
        for dx, dy in ((0.55, -0.55), (-0.6, 0.5)):
            pygame.draw.circle(surface, color, (int(cx + s * dx), int(cy + s * dy)), max(2, int(s * 0.1)))
    elif card_type == "GUARD":         # escudo
        pts = [(cx - s * 0.55, cy - s * 0.55), (cx + s * 0.55, cy - s * 0.55), (cx + s * 0.5, cy + s * 0.1),
               (cx, cy + s * 0.65), (cx - s * 0.5, cy + s * 0.1)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, T.BG, [(cx, cy - s * 0.4), (cx + s * 0.3, cy - s * 0.4), (cx + s * 0.27, cy + s * 0.05),
                                           (cx, cy + s * 0.4)])
    elif card_type == "SPECIAL":       # destello de 4 puntas
        pts = [(cx, cy - s * 0.7), (cx + s * 0.18, cy - s * 0.18), (cx + s * 0.7, cy), (cx + s * 0.18, cy + s * 0.18),
               (cx, cy + s * 0.7), (cx - s * 0.18, cy + s * 0.18), (cx - s * 0.7, cy), (cx - s * 0.18, cy - s * 0.18)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.circle(surface, T.BG, (cx, cy), max(2, int(s * 0.14)))
    elif card_type == "BREAK":         # rayo
        pts = [(cx + s * 0.15, cy - s * 0.7), (cx - s * 0.45, cy + s * 0.08), (cx - s * 0.02, cy + s * 0.08),
               (cx - s * 0.2, cy + s * 0.7), (cx + s * 0.45, cy - s * 0.12), (cx + s * 0.02, cy - s * 0.12)]
        pygame.draw.polygon(surface, color, pts)


def draw_card(surface, card, rect, key_label=None, dim=False, glow=None, big=False):
    """Carta boca arriba. `glow`: color del brillo (carta ganadora)."""
    rect = pygame.Rect(rect)
    color = T.PROPERTY_COLORS.get(card.card_type, T.PROPERTY_COLORS[None])
    scale = rect.w / 112
    if glow:
        g = pygame.Surface((rect.w + 24, rect.h + 24), pygame.SRCALPHA)
        for i in range(6):
            pygame.draw.rect(g, (*glow, 40), g.get_rect().inflate(-i * 4, -i * 4), border_radius=16)
        surface.blit(g, rect.move(-12, -12))
    pygame.draw.rect(surface, (34, 38, 52), rect, border_radius=int(10 * scale))
    pygame.draw.rect(surface, color, rect, max(2, int(3 * scale)), border_radius=int(10 * scale))
    head = pygame.Rect(rect.x, rect.y, rect.w, int(22 * scale))
    pygame.draw.rect(surface, color, head, border_top_left_radius=int(10 * scale), border_top_right_radius=int(10 * scale))
    T.text(surface, card.card_type or "?", int(13 * scale), T.BG, head.center, "center")

    # Nombre (se encoge si no cabe). El coste NO es de la carta: lo pinta la mano.
    max_name_w = rect.w - 12 * scale
    name_size = int(15 * scale)
    while name_size > 9 and T.font(name_size).size(card.name)[0] > max_name_w:
        name_size -= 1
    T.text(surface, card.name, name_size, T.TEXT, (rect.centerx, head.bottom + 4 * scale), "midtop")

    draw_icon(surface, card.card_type, (rect.centerx, int(rect.y + 60 * scale)), 20 * scale, color)
    if card.priority:
        T.text(surface, f"P{card.priority}", int(12 * scale), T.GOLD, (rect.x + 8 * scale, rect.y + 52 * scale))
    if card.element:                   # el elemento es informativo: no aplica estados
        T.text(surface, card.element, int(10 * scale), T.TEXT, (rect.right - 7 * scale, rect.y + 52 * scale),
               "topright")

    # Chips: iniciativa y consecuencias de ganar
    chips = card_chips(card)
    if chips:
        cw, ch, gap = int(23 * scale), int(14 * scale), int(2 * scale)
        x = rect.centerx - (len(chips) * cw + (len(chips) - 1) * gap) // 2
        y = int(rect.y + 82 * scale)
        for chip in chips:
            r = pygame.Rect(x, y, cw, ch)
            pygame.draw.rect(surface, chip_color(chip), r, border_radius=4)
            T.text(surface, chip, int(10 * scale), T.BG, r.center, "center")
            x += cw + gap

    # Descripción (especiales siempre; básicas solo en grande)
    if card.category != "basic" or big:
        max_lines = 3
        lines = T.wrap(card.description, int(11 * scale), rect.w - 12 * scale, bold=False)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(".,") + "…"
        y = rect.y + 100 * scale
        for line in lines:
            T.text(surface, line, int(11 * scale), (200, 204, 218), (rect.centerx, y), "midtop", bold=False)
            y += 12 * scale

    if key_label:
        badge = pygame.Rect(0, 0, int(24 * scale), int(20 * scale))
        badge.midbottom = (rect.centerx, rect.bottom + int(10 * scale))
        pygame.draw.rect(surface, T.TEXT, badge, border_radius=5)
        T.text(surface, key_label, int(13 * scale), T.BG, badge.center, "center")

    if card.is_ultimate:               # definitiva de Estilo: misma carta, marcada en dorado
        pygame.draw.rect(surface, T.GOLD, rect.inflate(6, 6), max(2, int(3 * scale)), border_radius=int(12 * scale))
        ribbon = pygame.Rect(0, 0, int(rect.w * 0.9), int(16 * scale))
        ribbon.midtop = (rect.centerx, rect.bottom - int(20 * scale))
        pygame.draw.rect(surface, T.GOLD, ribbon, border_radius=4)
        T.text(surface, "DEFINITIVA", max(8, int(11 * scale)), T.BG, ribbon.center, "center")

    if dim:
        veil = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(veil, (8, 10, 16, 165), veil.get_rect(), border_radius=int(10 * scale))
        surface.blit(veil, rect)


COST_STYLES = {
    "SPECIAL · 1 MANA": ((176, 110, 240), (250, 245, 255)),
    "FREE": ((90, 220, 130), (16, 18, 26)),
    "1 MANA": ((90, 150, 255), (245, 245, 250)),
    "UNAVAILABLE": ((150, 50, 50), (255, 220, 220)),
}


def draw_cost_tag(surface, rect, label):
    """Etiqueta de coste sobre la esquina superior de una carta de la mano."""
    bg, fg = COST_STYLES.get(label, ((90, 150, 255), (245, 245, 250)))
    f = T.font(11)
    w = f.size(label)[0] + 12
    tag = pygame.Rect(0, 0, w, 16)
    tag.midbottom = (rect.centerx, rect.top - 2)     # encima de la carta, sin tapar el tipo
    pygame.draw.rect(surface, T.BG, tag.inflate(4, 4), border_radius=6)
    pygame.draw.rect(surface, bg, tag, border_radius=5)
    T.text(surface, label, 11, fg, tag.center, "center")


def draw_card_back(surface, rect, color, label="?", ready=False):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, (26, 30, 46), rect, border_radius=12)
    pygame.draw.rect(surface, color, rect, 3, border_radius=12)
    inner = rect.inflate(-18, -18)
    for i in range(0, inner.w + inner.h, 14):     # patrón de rayas
        a = (inner.x + i, inner.y)
        b = (inner.x + i - inner.h, inner.bottom)
        pygame.draw.line(surface, T.mix((26, 30, 46), color, 0.25), a, b, 2)
    pygame.draw.rect(surface, (26, 30, 46), rect.inflate(-6, -6), 6, border_radius=10)
    T.text(surface, label, int(rect.h * 0.3), color, rect.center, "center")
    if ready:
        T.text(surface, "LISTO", 18, T.STABLE_COLOR, (rect.centerx, rect.bottom - 22), "center")


def draw_empty_slot(surface, rect, color, label):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y in range(0, rect.h, 12):
        pygame.draw.line(s, (*color, 60), (0, y), (6, y), 2)
        pygame.draw.line(s, (*color, 60), (rect.w - 6, y), (rect.w, y), 2)
    for x in range(0, rect.w, 12):
        pygame.draw.line(s, (*color, 60), (x, 0), (x, 6), 2)
        pygame.draw.line(s, (*color, 60), (x, rect.h - 6), (x, rect.h), 2)
    surface.blit(s, rect)
    T.text(surface, label, 16, T.DIM, rect.center, "center")
