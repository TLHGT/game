"""Menú inicial: elegir el personaje y el mazo de cada jugador, jugar o abrir el editor de mazos.

Solo dibuja el estado (game/deck_editor.py: MenuState) y devuelve zonas
clicables como (rect, ("menu", acción, argumento)).
"""
import pygame

from combate.cards.card_database import CARDS
from combate.game.characters import CHARACTERS
from combate.ui import theme as T
from combate.ui.battle_screen import _button

PANELS = [pygame.Rect(120, 140, 480, 452), pygame.Rect(680, 140, 480, 452)]
CYCLE_KEYS = [("A", "D"), ("IZQ", "DER")]          # mazo (la fuente no tiene flechas)
CHAR_KEYS = [("W", "S"), ("ARR", "ABA")]           # personaje


def deck_summary(ids):
    """[(nombre, tipo, copias)] en el orden en que aparecen en el mazo."""
    seen = {}
    for cid in ids:
        seen[cid] = seen.get(cid, 0) + 1
    return [(CARDS[cid]["name"], CARDS[cid]["card_type"], n) for cid, n in seen.items()]


def draw_deck_list(surface, ids, x, y, width, rows=7):
    """Lista compacta "2× Attack" en dos columnas, con el color de su tipo."""
    items = deck_summary(ids)
    col_w = width // 2
    for k, (name, ctype, n) in enumerate(items):
        cx, cy = x + (k // rows) * col_w, y + (k % rows) * 23
        color = T.PROPERTY_COLORS.get(ctype, T.PROPERTY_COLORS[None])
        pygame.draw.rect(surface, color, (cx, cy + 3, 13, 13), border_radius=3)
        T.text(surface, f"{n}× {name}", 15, T.TEXT, (cx + 20, cy + 1), bold=False)


def _selector(surface, rect, label, sub, keys, actions, buttons, hover):
    _button(surface, (rect.x, rect.y, 50, rect.h), "<", keys[0], (150, 156, 176), buttons, actions[0], hover=hover)
    _button(surface, (rect.right - 50, rect.y, 50, rect.h), ">", keys[1], (150, 156, 176), buttons, actions[1],
            hover=hover)
    T.text(surface, label, 24, T.TEXT, (rect.centerx, rect.y + 13), "center")
    T.text(surface, sub, 12, T.DIM, (rect.centerx, rect.y + 33), "center")


def draw_menu(surface, menu, view_time, hover):
    buttons = []
    surface.fill(T.BG)
    T.text(surface, "COMBATE DE CARTAS", 52, T.GOLD, (T.SCREEN_W // 2, 62), "center", shadow=True)
    T.text(surface, "Elige el personaje y el mazo de cada jugador", 18, T.DIM, (T.SCREEN_W // 2, 106), "center")
    store = menu.store
    for i, rect in enumerate(PANELS):
        color = T.PLAYER_COLORS[i]
        T.panel(surface, rect, color=(26, 30, 42), border=T.mix(T.LINE, color, 0.6))
        T.text(surface, f"PLAYER {i + 1}", 24, color, (rect.x + 20, rect.y + 12))
        x, w = rect.x + 20, rect.w - 40

        # --- Personaje y pasiva -------------------------------------------------
        T.text(surface, "PERSONAJE", 12, T.DIM, (rect.right - 20, rect.y + 18), "topright")
        ch = CHARACTERS[menu.character[i]]
        _selector(surface, pygame.Rect(x, rect.y + 46, w, 42), ch.name.upper(), ch.description, CHAR_KEYS[i],
                  [("menu", "character", (i, -1)), ("menu", "character", (i, 1))], buttons, hover)
        pas = ch.make_passive()
        T.text(surface, f"PASIVA · {pas.name}", 16, T.GOLD, (x, rect.y + 96))
        for k, line in enumerate(T.wrap(pas.summary(), 14, w)[:2]):
            T.text(surface, line, 14, (200, 204, 218), (x, rect.y + 118 + k * 17), bold=False)

        # --- Mazo -------------------------------------------------------------
        pygame.draw.line(surface, T.LINE, (x, rect.y + 158), (x + w, rect.y + 158))
        name = menu.choice[i]
        ids = store.get(name)
        _selector(surface, pygame.Rect(x, rect.y + 170, w, 42), name,
                  f"MAZO · {store.kind(name).upper()} · {len(ids)} cartas", CYCLE_KEYS[i],
                  [("menu", "cycle", (i, -1)), ("menu", "cycle", (i, 1))], buttons, hover)
        draw_deck_list(surface, ids, x, rect.y + 226, w)

    by = 612
    _button(surface, (T.SCREEN_W // 2 - 290, by, 200, 52), "JUGAR", "ENTER", T.GOLD, buttons, ("menu", "play", None),
            hover=hover)
    _button(surface, (T.SCREEN_W // 2 - 70, by, 200, 52), "VER / EDITAR MAZOS", "M", (140, 200, 255), buttons,
            ("menu", "decks", None), hover=hover)
    _button(surface, (T.SCREEN_W // 2 + 150, by, 140, 52), "SALIR", "ESC", (150, 156, 176), buttons,
            ("menu", "quit", None), hover=hover)
    for k, warning in enumerate(store.warnings[:2]):        # entradas de decks.json no válidas
        T.text(surface, warning, 13, T.UNSTABLE_COLOR, (T.SCREEN_W // 2, 678 + 16 * k), "center", bold=False)
    return buttons
