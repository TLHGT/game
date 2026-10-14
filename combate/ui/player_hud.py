"""Panel superior de cada jugador: HP, Mana, Stability, hits, cambios."""
import math

import pygame

from combate.ui import theme as T

HUD_W = 440


def hud_anchor(index):
    """Esquina superior izquierda del HUD de cada jugador."""
    return (20, 14) if index == 0 else (T.SCREEN_W - 20 - HUD_W, 14)


def mana_pip_pos(index, pip, rules):
    x, y = hud_anchor(index)
    return x + 92 + pip * 30, y + 82


def draw_hud(surface, player, rules, hp_shown, time, show_redraws=False, pulse=None, mana_shown=None):
    """pulse: dict con timers de realce {"mana": t, "stability": t, "hits": t}."""
    pulse = pulse or {}
    i = player.index
    mana = player.mana if mana_shown is None else mana_shown
    color = T.PLAYER_COLORS[i]
    x, y = hud_anchor(i)
    rect = pygame.Rect(x, y, HUD_W, 118)
    T.panel(surface, rect, color=(26, 30, 42), border=T.mix(T.LINE, color, 0.5))

    # Nombre + Stability
    T.text(surface, player.name, 22, color, (x + 14, y + 8))
    st_color = T.STABLE_COLOR if player.stable else T.UNSTABLE_COLOR
    badge = pygame.Rect(0, 0, 132, 28)
    badge.topright = (rect.right - 12, y + 8)
    grow = 1 + 0.12 * math.sin(min(1, pulse.get("stability", 0) * 3) * math.pi)
    b = badge.inflate(int(badge.w * (grow - 1)), int(badge.h * (grow - 1)))
    if not player.stable:   # parpadeo suave para que se note la desventaja
        alpha = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(time * 5))
        st_color = T.mix((60, 20, 20), st_color, alpha)
    pygame.draw.rect(surface, st_color, b, border_radius=8)
    T.text(surface, player.stability_label, 18, T.BG, b.center, "center")

    # HP
    T.text(surface, "HP", 18, T.DIM, (x + 14, y + 44))
    bar = pygame.Rect(x + 52, y + 46, 300, 18)
    pygame.draw.rect(surface, (50, 20, 24), bar, border_radius=6)
    ghost = bar.copy(); ghost.w = int(bar.w * max(0, hp_shown) / rules.MAX_HP)
    pygame.draw.rect(surface, (240, 220, 120), ghost, border_radius=6)
    cur = bar.copy(); cur.w = int(bar.w * max(0, player.hp) / rules.MAX_HP)
    hp_col = T.HP_COLOR if player.hp > rules.MAX_HP * 0.3 else T.UNSTABLE_COLOR
    pygame.draw.rect(surface, hp_col, cur, border_radius=6)
    T.text(surface, f"{player.hp}", 20, T.TEXT, (bar.right + 12, bar.centery), "midleft")

    # Mana
    T.text(surface, "MANA", 18, T.DIM, (x + 14, y + 72))
    for k in range(rules.MAX_MANA):
        c = mana_pip_pos(i, k, rules)
        full = k < mana
        pygame.draw.circle(surface, (40, 48, 80), c, 11)
        if full:
            pygame.draw.circle(surface, T.MANA_COLOR, c, 10)
            pygame.draw.circle(surface, (190, 215, 255), (c[0] - 3, c[1] - 3), 3)
        if pulse.get("mana", 0) > 0:
            pygame.draw.circle(surface, T.TEXT, c, int(12 + 6 * pulse["mana"]), 2)
    T.text(surface, f"{mana} / {rules.MAX_MANA}", 18, T.TEXT,
           (mana_pip_pos(i, rules.MAX_MANA - 1, rules)[0] + 22, y + 72))

    # Hits del combo
    hx = rect.right - 14 - rules.MAX_COMBO_HITS * 26
    T.text(surface, "COMBO", 15, T.DIM, (hx - 56, y + 76))
    for k in range(rules.MAX_COMBO_HITS):
        r = pygame.Rect(hx + k * 26, y + 74, 20, 20)
        on = k < player.combo_hits
        pygame.draw.rect(surface, T.GOLD if on else (50, 54, 70), r, border_radius=4)
        if on and pulse.get("hits", 0) > 0:
            pygame.draw.rect(surface, T.TEXT, r.inflate(8, 8), 2, border_radius=6)

    # Pie: mazo, descarte y cambios
    info = f"MAZO {len(player.deck)}  ·  DESCARTE {len(player.deck.discard_pile)}"
    T.text(surface, info, 14, T.DIM, (x + 14, y + 98), bold=False)
    if show_redraws:
        T.text(surface, f"CAMBIOS: {player.redraws_left}", 16, T.GOLD, (rect.right - 14, y + 97), "topright")
