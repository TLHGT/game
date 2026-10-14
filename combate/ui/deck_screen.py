"""Editor de mazos: ver y modificar los mazos.

    izquierda   lista de mazos (fábrica / modificado / propio) + NUEVO, DUPLICAR, RESTAURAR, BORRAR
    centro      el mazo que se edita: nombre, N/10 cartas, copias con [-] [+]
    derecha     catálogo con todas las cartas: clic izquierdo añade, clic derecho quita;
                al pasar el ratón se ve la carta en grande

Solo dibuja el estado (game/deck_editor.py: DeckEditor) y devuelve zonas
clicables como (rect, ("deck", acción, argumento)).
"""
import os

import pygame

from combate.cards.card_database import CARDS, make_card
from combate.game.deck_editor import CATALOG
from combate.ui import theme as T
from combate.ui.battle_screen import _button
from combate.ui.card_widget import draw_card

LIST = pygame.Rect(16, 70, 236, 560)
DECK = pygame.Rect(264, 70, 340, 560)
CATALOG_RECT = pygame.Rect(616, 70, 648, 560)
MINI_W, MINI_H, GAP_X, GAP_Y, COLS = 80, 107, 92, 120, 7

_cards = {}


def card_obj(cid):
    if cid not in _cards:
        _cards[cid] = make_card(cid)
    return _cards[cid]


def catalog_rect(k):
    return pygame.Rect(CATALOG_RECT.x + 12 + (k % COLS) * GAP_X, CATALOG_RECT.y + 40 + (k // COLS) * GAP_Y,
                       MINI_W, MINI_H)


def _small_button(surface, rect, label, color, buttons, action, enabled=True, hover=None):
    rect = pygame.Rect(rect)
    hot = enabled and hover is not None and rect.collidepoint(hover)
    base = color if enabled else (60, 64, 80)
    pygame.draw.rect(surface, T.mix(base, (255, 255, 255), 0.2) if hot else base, rect, border_radius=6)
    T.text(surface, label, 16, T.BG if enabled else T.DIM, rect.center, "center")
    if enabled:
        buttons.append((rect, action))


def draw_deck_editor(surface, ed, view_time, hover):
    buttons = []
    surface.fill(T.BG)
    T.text(surface, "MAZOS", 30, T.GOLD, (16, 16))
    T.text(surface, "Clic en el catálogo: añadir · clic derecho: quitar · los cambios se guardan en "
           + os.path.basename(ed.store.path), 14, T.DIM, (130, 28), bold=False)
    _draw_list(surface, ed, buttons, hover)
    _draw_deck(surface, ed, buttons, hover, view_time)
    preview = _draw_catalog(surface, ed, buttons, hover)

    by = 646
    _button(surface, (DECK.x, by, 160, 50), "GUARDAR", "ENTER", T.STABLE_COLOR, buttons, ("deck", "save", None),
            enabled=ed.dirty, hover=hover)
    _button(surface, (DECK.x + 170, by, 170, 50), "DESCARTAR", "SUPR", (150, 156, 176), buttons,
            ("deck", "discard", None), enabled=ed.dirty, hover=hover)
    _button(surface, (LIST.x, by, 236, 50), "VOLVER AL MENÚ", "ESC", (140, 200, 255), buttons,
            ("deck", "back", None), hover=hover)
    if ed.message:
        color = T.UNSTABLE_COLOR if ed.message.startswith(("No se", "Hay cambios", "El mazo ya", "Los mazos")) \
            else T.STABLE_COLOR
        T.text(surface, ed.message, 16, color, (CATALOG_RECT.x, by + 25), "midleft")
    if preview is not None:                   # carta en grande al pasar el ratón
        cid, rect = preview
        big = pygame.Rect(0, 0, 176, 236)
        big.midright = (rect.left - 10, rect.centery)
        if big.left < DECK.x:
            big.midleft = (rect.right + 10, rect.centery)
        big.clamp_ip(surface.get_rect().inflate(-8, -8))
        draw_card(surface, card_obj(cid), big, big=True)
    return buttons


def _draw_list(surface, ed, buttons, hover):
    T.panel(surface, LIST, color=(24, 27, 38))
    T.text(surface, "MAZOS", 15, T.DIM, (LIST.x + 12, LIST.y + 10))
    store = ed.store
    names = store.names()
    rows = 10 - (1 if ed.is_new else 0)
    start = 0                                  # desplaza la lista para que el seleccionado se vea
    if ed.selected in names:
        start = max(0, min(names.index(ed.selected) - rows + 1, len(names) - rows))
    start = max(0, start)
    if start:
        T.text(surface, f"^ {start} más", 11, T.DIM, (LIST.right - 12, LIST.y + 12), "topright")
    y = LIST.y + 34
    for name in names[start:start + rows]:
        row = pygame.Rect(LIST.x + 8, y, LIST.w - 16, 32)
        sel = name == ed.selected
        hot = hover is not None and row.collidepoint(hover)
        pygame.draw.rect(surface, (52, 60, 86) if sel else ((36, 40, 56) if hot else (28, 32, 44)), row,
                         border_radius=6)
        if sel:
            pygame.draw.rect(surface, T.GOLD, row, 2, border_radius=6)
        T.text(surface, name, 17, T.TEXT, (row.x + 10, row.centery), "midleft")
        kind = store.kind(name)
        tag = {"fábrica": "FÁBRICA", "modificado": "MODIF.", "propio": "PROPIO"}[kind]
        T.text(surface, tag, 11, T.GOLD if kind == "modificado" else T.DIM, (row.right - 8, row.centery),
               "midright")
        buttons.append((row, ("deck", "select", name)))
        y += 36
    if ed.is_new:
        row = pygame.Rect(LIST.x + 8, y, LIST.w - 16, 32)
        pygame.draw.rect(surface, (52, 60, 86), row, border_radius=6)
        pygame.draw.rect(surface, T.GOLD, row, 2, border_radius=6)
        T.text(surface, f"{ed.name} *", 17, T.TEXT, (row.x + 10, row.centery), "midleft")
        T.text(surface, "SIN GUARDAR", 11, T.GOLD, (row.right - 8, row.centery), "midright")
    by = LIST.bottom - 112
    _small_button(surface, (LIST.x + 10, by, 104, 32), "NUEVO", (140, 200, 255), buttons, ("deck", "new", None),
                  enabled=not ed.single, hover=hover)
    _small_button(surface, (LIST.x + 122, by, 104, 32), "DUPLICAR", (140, 200, 255), buttons,
                  ("deck", "duplicate", None), enabled=not ed.is_new and not ed.single, hover=hover)
    _small_button(surface, (LIST.x + 10, by + 40, 104, 32), "RESTAURAR", T.GOLD, buttons, ("deck", "restore", None),
                  enabled=ed.can_restore(), hover=hover)
    _small_button(surface, (LIST.x + 122, by + 40, 104, 32), "BORRAR", T.UNSTABLE_COLOR, buttons,
                  ("deck", "delete", None), enabled=ed.can_delete(), hover=hover)
    note = "Un solo mazo · sin cartas repetidas" if ed.single else "Fábrica: restaurar. Propios: borrar."
    T.text(surface, note, 12, T.DIM, (LIST.centerx, by + 86), "midtop", bold=False)


def _draw_deck(surface, ed, buttons, hover, view_time):
    T.panel(surface, DECK, color=(24, 27, 38))
    # Nombre (editable en mazos nuevos y propios)
    field = pygame.Rect(DECK.x + 12, DECK.y + 10, DECK.w - 24, 40)
    pygame.draw.rect(surface, (34, 38, 54), field, border_radius=8)
    pygame.draw.rect(surface, T.GOLD if ed.editing_name else T.LINE, field, 2, border_radius=8)
    cursor = "|" if ed.editing_name and int(view_time * 2) % 2 == 0 else ""
    T.text(surface, (ed.name or " ") + cursor, 22, T.TEXT, (field.x + 12, field.centery), "midleft")
    hint = "escribe · ENTER" if ed.editing_name else "clic para renombrar"
    T.text(surface, hint, 11, T.DIM, (field.right - 10, field.centery), "midright")
    buttons.append((field, ("deck", "rename", None)))

    n, size = len(ed.cards), ed.size
    ok = n == size
    T.text(surface, f"{n} / {size} CARTAS", 20, T.STABLE_COLOR if ok else T.UNSTABLE_COLOR,
           (DECK.x + 14, DECK.y + 62))
    _small_button(surface, (DECK.right - 92, DECK.y + 58, 80, 28), "VACIAR", (150, 156, 176), buttons,
                  ("deck", "clear", None), enabled=bool(ed.cards), hover=hover)
    y = DECK.y + 98
    for cid, count in ed.counts():
        data = CARDS[cid]
        color = T.PROPERTY_COLORS.get(data["card_type"], T.PROPERTY_COLORS[None])
        row = pygame.Rect(DECK.x + 10, y, DECK.w - 20, 34)
        pygame.draw.rect(surface, (30, 34, 48), row, border_radius=6)
        pygame.draw.rect(surface, color, (row.x, row.y, 6, row.h), border_radius=3)
        T.text(surface, f"{count}×", 18, T.GOLD, (row.x + 16, row.centery), "midleft")
        T.text(surface, data["name"], 17, T.TEXT, (row.x + 50, row.centery), "midleft")
        T.text(surface, data["card_type"], 11, color, (row.right - 76, row.centery), "midright")
        _small_button(surface, (row.right - 68, row.y + 4, 28, 26), "-", (220, 120, 110), buttons,
                      ("deck", "remove", cid), hover=hover)
        _small_button(surface, (row.right - 34, row.y + 4, 28, 26), "+", T.STABLE_COLOR, buttons,
                      ("deck", "add", cid), enabled=n < size and not ed.store.unique, hover=hover)
        y += 38
        if y > DECK.bottom - 40:
            break
    if not ed.cards:
        T.text(surface, "Mazo vacío: añade cartas desde el catálogo", 15, T.DIM, (DECK.centerx, DECK.y + 130),
               "center", bold=False)
    errors = [e for e in ed.errors() if "debe tener" not in e]
    if errors:
        T.text(surface, errors[0], 13, T.UNSTABLE_COLOR, (DECK.centerx, DECK.bottom - 18), "center", bold=False)


def _draw_catalog(surface, ed, buttons, hover):
    T.panel(surface, CATALOG_RECT, color=(24, 27, 38))
    T.text(surface, f"CATÁLOGO · {len(CATALOG)} cartas", 15, T.DIM, (CATALOG_RECT.x + 12, CATALOG_RECT.y + 10))
    full = len(ed.cards) >= ed.size
    preview = None
    for k, cid in enumerate(CATALOG):
        rect = catalog_rect(k)
        count = ed.count(cid)
        hot = hover is not None and rect.collidepoint(hover)
        locked = cid in ed.locked
        taken = ed.store.unique and count > 0            # sin repetidas: ya está en el mazo
        draw_card(surface, card_obj(cid), rect.move(0, -4 if hot else 0), dim=locked or taken or (full and not count),
                  glow=T.GOLD if count else None)
        if locked:
            tag = pygame.Rect(0, 0, rect.w, 20)
            tag.center = rect.center
            pygame.draw.rect(surface, (20, 20, 26), tag)
            T.text(surface, "BLOQUEADA", 12, T.DIM, tag.center, "center")
        if count:
            badge = pygame.Rect(0, 0, 30, 20)
            badge.topright = (rect.right + 4, rect.y - 6)
            pygame.draw.rect(surface, T.GOLD, badge, border_radius=6)
            T.text(surface, f"×{count}", 13, T.BG, badge.center, "center")
        buttons.append((rect, ("deck", "catalog", cid)))
        if hot:
            preview = (cid, rect)
    return preview
