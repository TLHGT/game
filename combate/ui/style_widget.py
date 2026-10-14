"""Estilo en combate: rango, puntos, racha, progreso y definitiva.

    fila de Estilo     bajo la ficha del personaje: [B] 33 pts · racha 3 ▬▬▬▬▬░░ · DEF —
    selector           durante la elección, si la definitiva está disponible:
                       DEFINITIVA [ATK] [GRD] [BRK] [MAG] [SPC]
"""
import pygame

from combate.game.style import ULTIMATE_CATEGORIES, next_rank, rank_for, rank_progress
from combate.ui import theme as T
from combate.ui.player_hud import HUD_W, hud_anchor

ROW_W, ROW_H = 310, 30
RANK_COLORS = {"D": (150, 156, 176), "C": (110, 200, 140), "B": (90, 170, 255), "A": (200, 120, 255),
               "S": T.GOLD}
SHORT = {"ATTACK": "ATK", "GUARD": "GRD", "BREAK": "BRK", "MAGIC": "MAG", "SPECIAL": "SPC"}


def _row_x(index):
    x, _ = hud_anchor(index)
    return x if index == 0 else x + HUD_W - ROW_W


def draw_style_row(surface, engine, player, pulse=0.0):
    rules, st = engine.rules, player.style
    rect = pygame.Rect(_row_x(player.index), 164, ROW_W, ROW_H)
    code, name = rank_for(st.points, rules)
    color = RANK_COLORS.get(code, T.TEXT)
    border = T.GOLD if pulse > 0 else T.LINE
    pygame.draw.rect(surface, (24, 27, 38), rect, border_radius=7)
    pygame.draw.rect(surface, border, rect, 2, border_radius=7)
    badge = pygame.Rect(rect.x + 4, rect.y + 3, 24, 24)
    pygame.draw.rect(surface, color, badge, border_radius=5)
    T.text(surface, code, 18, T.BG, badge.center, "center")
    T.text(surface, f"{st.points} pts · racha {st.streak}", 13, T.TEXT, (badge.right + 8, rect.y + 8), "midleft")
    # progreso hacia el siguiente rango (en S: máximo, sin tope de puntos)
    bar = pygame.Rect(badge.right + 8, rect.y + 18, 128, 6)
    pygame.draw.rect(surface, (44, 48, 64), bar, border_radius=3)
    fill = bar.copy()
    fill.w = int(bar.w * rank_progress(st.points, rules))
    pygame.draw.rect(surface, color, fill, border_radius=3)
    nxt = next_rank(st.points, rules)
    T.text(surface, f"{nxt[0]} en {nxt[1]}" if nxt else "MÁX", 10, T.DIM, (bar.right + 6, bar.centery), "midleft",
           bold=False)
    # definitiva: disponible / usada / bloqueada
    if st.ultimate_used:
        label, lcolor = "DEF USADA", T.DIM
    elif engine.ultimate_available(player.index):
        label, lcolor = "DEF LISTA", T.GOLD
    else:
        label, lcolor = f"DEF ({rules.ULTIMATE_RANK})", (110, 116, 136)
    T.text(surface, label, 12, lcolor, (rect.right - 8, rect.centery), "midright")
    return rect


def draw_ultimate_picker(surface, engine, player, buttons, hover, key_label):
    """Botones de categoría de la definitiva. La elección queda oculta, como las cartas."""
    i = player.index
    options = engine.ultimate_options(i)
    if engine.confirmed[i] or not engine.ultimate_available(i):
        return None
    rect = pygame.Rect(_row_x(i), 198, ROW_W, 38)
    pygame.draw.rect(surface, (40, 34, 18), rect, border_radius=8)
    pygame.draw.rect(surface, T.GOLD, rect, 2, border_radius=8)
    T.text(surface, "DEFINITIVA", 13, T.GOLD, (rect.x + 8, rect.y + 11), "midleft")
    T.text(surface, f"[{key_label}]", 10, T.DIM, (rect.x + 8, rect.y + 27), "midleft", bold=False)
    x = rect.x + 86
    for category in ULTIMATE_CATEGORIES:
        b = pygame.Rect(x, rect.y + 6, 42, 26)
        enabled = category in options
        hot = enabled and hover is not None and b.collidepoint(hover)
        base = T.PROPERTY_COLORS.get(category, T.GOLD) if enabled else (60, 64, 80)
        pygame.draw.rect(surface, T.mix(base, (255, 255, 255), 0.25) if hot else base, b, border_radius=6)
        T.text(surface, SHORT[category], 12, T.BG if enabled else T.DIM, b.center, "center")
        if enabled:
            buttons.append((b, (i, "ultimate", category)))
        x += 44
    return rect
