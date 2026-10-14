"""Dibujo de los Status Effects: insignia junto al nombre, ficha de detalle y acciones de FREEZE.

    insignia   en el HUD, al lado del nombre del jugador: [icono] BURN · 2 turnos
    ficha      al pasar el ratón por la insignia: efecto, contador y últimos mensajes

Cada estado se distingue por TRES cosas, no solo por el color:
    icono (forma)   BURN llama · POISON gota · PARALYZE rayo · FREEZE cubo · SLEEP "Zz"
    abreviatura     BRN · PSN · PRZ · FRZ · SLP
    nombre completo y contador
"""
import math

import pygame

from combate.game.status import StatusId
from combate.ui import theme as T

PANEL_W, PANEL_H = 310, 142


def status_panel_rect(index):
    """Ficha de detalle: justo debajo del HUD de cada jugador."""
    x = 20 if index == 0 else T.SCREEN_W - 20 - PANEL_W
    return pygame.Rect(x, 166, PANEL_W, PANEL_H)      # bajo la ficha del personaje


def status_description(status, rules):
    sid = status.id
    if sid == StatusId.BURN:
        return f"-{rules.BURN_DAMAGE} HP al empezar cada turno"
    if sid == StatusId.POISON:
        return f"-{rules.POISON_DAMAGE} HP al empezar cada interacción"
    if sid == StatusId.PARALYZE:
        return "PASS obligatorio en la siguiente interacción"
    if sid == StatusId.SLEEP:
        return "PASS obligatorio · despierta con un HIT"
    if sid == StatusId.FREEZE:
        return "El ICE CUBE absorbe el daño · BREAK ICE o WAIT"
    return status.definition.description


def draw_status_icon(surface, status_id, center, size, color=None):
    sid = StatusId(status_id)
    color = color or T.STATUS_COLORS[sid.value]
    cx, cy = center
    s = size
    if sid == StatusId.BURN:            # llama
        pts = [(cx, cy - s), (cx + s * 0.55, cy - s * 0.05), (cx + s * 0.45, cy + s * 0.6),
               (cx, cy + s * 0.85), (cx - s * 0.45, cy + s * 0.6), (cx - s * 0.55, cy - s * 0.05)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.circle(surface, T.BG, (int(cx), int(cy + s * 0.35)), max(2, int(s * 0.25)))
    elif sid == StatusId.POISON:        # gota con burbuja
        pygame.draw.circle(surface, color, (int(cx), int(cy + s * 0.25)), int(s * 0.6))
        pygame.draw.polygon(surface, color, [(cx, cy - s), (cx + s * 0.52, cy), (cx - s * 0.52, cy)])
        pygame.draw.circle(surface, T.BG, (int(cx - s * 0.2), int(cy + s * 0.2)), max(2, int(s * 0.16)))
    elif sid == StatusId.PARALYZE:      # rayo en zigzag
        pts = [(cx - s * 0.7, cy - s * 0.6), (cx - s * 0.1, cy - s * 0.15), (cx - s * 0.35, cy + s * 0.1),
               (cx + s * 0.7, cy + s * 0.75), (cx + s * 0.1, cy + s * 0.1), (cx + s * 0.35, cy - s * 0.1)]
        pygame.draw.lines(surface, color, False, pts, max(3, int(s * 0.28)))
    elif sid == StatusId.FREEZE:        # cubo
        r = pygame.Rect(0, 0, int(s * 1.4), int(s * 1.4))
        r.center = (int(cx), int(cy))
        pygame.draw.rect(surface, color, r, max(2, int(s * 0.22)), border_radius=3)
        pygame.draw.line(surface, color, r.topleft, r.bottomright, max(1, int(s * 0.12)))
    elif sid == StatusId.SLEEP:         # Zz
        T.text(surface, "Zz", max(10, int(s * 1.5)), color, (cx, cy), "center")


def badge_label(status):
    """Texto de la insignia: nombre y contador compacto."""
    sid = status.id
    if sid == StatusId.FREEZE:
        counter = f"{status.cube_hp}/{status.cube_max}"
    elif sid in (StatusId.BURN, StatusId.POISON):
        counter = f"{status.turns_left} turno{'s' if status.turns_left != 1 else ''}"
    else:
        counter = f"{status.interactions_left} int."
    return f"{status.name} · {counter}"


def draw_status_badge(surface, status, pos, max_w, time=0.0, pulse=0.0):
    """Insignia junto al nombre del jugador: [icono] NOMBRE · contador. El texto
    se encoge si no cabe en `max_w`. Devuelve su rect (para la ficha al pasar el ratón)."""
    color = T.STATUS_COLORS[status.id.value]
    label = badge_label(status)
    size = 15
    while size > 10 and T.font(size).size(label)[0] + 34 > max_w:
        size -= 1
    rect = pygame.Rect(pos[0], pos[1], min(max_w, T.font(size).size(label)[0] + 34), 26)
    grow = int(4 * math.sin(min(1.0, pulse * 2) * math.pi)) if pulse else 0
    box = rect.inflate(grow, grow)
    pygame.draw.rect(surface, (20, 22, 32), box, border_radius=8)
    pygame.draw.rect(surface, color, box, 2, border_radius=8)
    draw_status_icon(surface, status.id, (rect.x + 14, rect.centery), 7, color)
    T.text(surface, label, size, color, (rect.x + 26, rect.centery), "midleft")
    return rect


def draw_status_panel(surface, engine, player_index, time):
    """Estado activo, su efecto, su contador y los últimos mensajes del jugador."""
    p = engine.players[player_index]
    rules = engine.rules
    rect = status_panel_rect(player_index)
    st = p.status
    color = T.STATUS_COLORS[st.id.value] if st else T.LINE
    T.panel(surface, rect, color=(22, 25, 36), border=color, alpha=245)
    x, y = rect.x + 12, rect.y + 8
    T.text(surface, "ESTADO", 13, T.DIM, (x, y))
    if st is None:
        T.text(surface, "SIN ESTADO ALTERADO", 16, (120, 126, 146), (x, y + 20))
        y += 46
    else:
        pulse = 1 + 0.08 * math.sin(time * 5)
        draw_status_icon(surface, st.id, (x + 14, y + 34), 13 * pulse, color)
        T.text(surface, f"{st.name}", 22, color, (x + 36, y + 20))
        T.text(surface, f"[{st.definition.short}]", 13, color, (rect.right - 12, y + 2), "topright")
        counter = st.counter_text()
        if st.id == StatusId.FREEZE:
            bar = pygame.Rect(x + 36, y + 48, rect.w - 60, 12)
            pygame.draw.rect(surface, (30, 50, 70), bar, border_radius=4)
            fill = bar.copy()
            fill.w = int(bar.w * st.cube_hp / max(1, st.cube_max))
            pygame.draw.rect(surface, T.ICE_COLOR, fill, border_radius=4)
            T.text(surface, f"ICE CUBE {st.cube_hp}/{st.cube_max} HP", 13, T.TEXT, (bar.centerx, bar.centery),
                   "center")
            counter = ""
        elif counter:
            T.text(surface, f"Quedan: {counter}", 14, T.TEXT, (x + 36, y + 46))
        lines = T.wrap(status_description(st, rules), 12, rect.w - 24)
        yy = y + 64
        for line in lines[:2]:
            T.text(surface, line, 12, (200, 204, 218), (x, yy), bold=False)
            yy += 14
        if st.fresh and st.definition.lock:
            T.text(surface, "Bloquea desde la próxima interacción", 12, T.DIM, (x, yy), bold=False)
        y = rect.y + 102
    # Últimos mensajes de estados de este jugador
    recent = [t for i, t in engine.status_log if i == player_index][-2:]
    for t in recent:
        line = f"· {t}"
        while T.font(12, bold=False).size(line)[0] > rect.w - 24 and len(line) > 4:
            line = line[:-2]
        T.text(surface, line, 12, (170, 176, 196), (x, y), bold=False)
        y += 15


def draw_freeze_actions(surface, engine, player_index, x0, y0, buttons, hover, key_labels, pass_key):
    """Sustituye la mano del jugador congelado: BREAK ICE o WAIT (sin coste)."""
    st = engine.players[player_index].status
    rules = engine.rules
    T.text(surface, f"FREEZE · ICE CUBE {st.cube_hp}/{st.cube_max} HP · sin cartas ni SPECIAL", 15,
           T.ICE_COLOR, (x0, y0 - 2), "bottomleft")
    options = [("BREAK_ICE", "BREAK ICE", f"{rules.BREAK_ICE_DAMAGE} de daño al cubo", f"{key_labels[0]}"),
               ("WAIT", "WAIT", "No atacar el cubo", f"{key_labels[1]} / {pass_key}")]
    confirmed = engine.confirmed[player_index]
    for k, (action, title, sub, key) in enumerate(options):
        rect = pygame.Rect(x0 + k * 300, y0 + 6, 290, 128)
        hot = not confirmed and hover is not None and rect.collidepoint(hover)
        base = (28, 44, 60) if not confirmed else (36, 40, 52)
        pygame.draw.rect(surface, T.mix(base, (255, 255, 255), 0.08) if hot else base, rect, border_radius=12)
        pygame.draw.rect(surface, T.ICE_COLOR if not confirmed else T.LINE, rect, 3, border_radius=12)
        if action == "BREAK_ICE":
            draw_status_icon(surface, StatusId.FREEZE, (rect.x + 34, rect.y + 40), 16)
            pygame.draw.line(surface, T.TEXT, (rect.x + 20, rect.y + 58), (rect.x + 48, rect.y + 22), 3)
        else:
            T.text(surface, "...", 26, T.ICE_COLOR, (rect.x + 34, rect.y + 36), "center")
        T.text(surface, title, 24, T.TEXT, (rect.x + 64, rect.y + 22))
        T.text(surface, sub, 15, (200, 220, 235), (rect.x + 64, rect.y + 54), bold=False)
        T.text(surface, "Sin Mana · sin HIT · sin iniciativa", 12, T.DIM, (rect.x + 64, rect.y + 76), bold=False)
        T.text(surface, f"[{key}]", 14, T.GOLD, (rect.centerx, rect.bottom - 18), "center")
        if not confirmed:
            buttons.append((rect, (player_index, "status", action)))

