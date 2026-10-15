"""Registro del combate: todo lo que ha pasado, turno a turno.

BattleLog guarda las entradas (sin Pygame) y draw_battle_log las dibuja como
un panel con scroll encima de la pantalla de combate.

    ("turn", n)                         cabecera de turno
    ("result", InteractionResult)       una interacción: cartas, por qué ganó y qué pasó
    ("note", jugador, texto)            lo que pasa fuera de una interacción
                                        (BURN al empezar el turno, POISON, Alerta...)

Las listas de cada InteractionResult se leen al dibujar: así el Mega Combo,
que se añade después de la resolución, también aparece.

Al pasar el ratón por el nombre de una carta jugada en esa interacción (o
por su tipo, en las básicas), se muestra la carta en grande.
"""
import re

import pygame

from combate.game.status import BREAK_ICE
from combate.ui import theme as T
from combate.ui.battle_screen import _consequence_color
from combate.ui.card_widget import draw_card

PANEL = pygame.Rect(140, 60, 1000, 600)
LINE_H = 20


class BattleLog:
    def __init__(self):
        self.entries = []
        self._last_result = None

    def observe(self, engine, events):
        """Llamar con los eventos del motor ANTES de consumirlos."""
        for ev in events:
            if ev.kind == "turn":
                self.entries.append(("turn", ev.data["turn"]))
            elif ev.kind == "message" and ev.data.get("status"):
                r = engine.result
                if r is None or ev.data["text"] not in r.consequences:   # ya sale en la interacción
                    self.entries.append(("note", ev.player, ev.data["text"]))
        r = engine.result
        if r is not None and r is not self._last_result:
            self._last_result = r
            self.entries.append(("result", r))

    # --- Texto ------------------------------------------------------------------------
    @staticmethod
    def _play(engine, r, i):
        p = engine.players[i]
        action = r.status_actions[i] if r.status_actions else None
        card = r.cards[i]
        main = ("BREAK ICE" if action == BREAK_ICE else "WAIT") if action else (card.name if card else "PASS")
        special = r.specials[i] if r.specials else None
        return f"{p.name}: {main}" + (f" + {special.name}" if special is not None else "")

    def lines(self, engine, width):
        """[(texto, tamaño, color, sangría, cartas)] ya partidas al ancho. `cartas`
        son las cartas de esa interacción (para mostrarlas al pasar el ratón)."""
        out = []
        for entry in self.entries:
            if entry[0] == "turn":
                out.append(("", 8, T.TEXT, 0, ()))
                out.append((f"— TURNO {entry[1]} —", 18, T.GOLD, 0, ()))
            elif entry[0] == "note":
                _, player, text = entry
                color = T.PLAYER_COLORS[player] if player is not None else T.DIM
                out.append((f"· {text}", 14, T.mix(color, T.TEXT, 0.4), 16, ()))
            else:
                r = entry[1]
                cards = _cards_of(r)
                n = getattr(r, "interaction_number", "?")
                head = f"Interacción {n}:  {self._play(engine, r, 0)}   vs   {self._play(engine, r, 1)}"
                out.append((head, 15, T.TEXT, 8, cards))
                for line in r.lines[:4]:
                    color = T.PLAYER_COLORS[r.winner] if "WINS" in line and r.winner is not None else \
                        (T.GOLD if line == "DRAW" else (200, 204, 218))
                    out.append((line, 14, color, 24, cards))
                for c in r.consequences:
                    out.append((f"• {c}", 13, _consequence_color(c), 32, cards))
        wrapped = []
        for text, size, color, indent, cards in out:
            parts = T.wrap(text, size, width - indent) if text else [""]
            for k, part in enumerate(parts):
                wrapped.append((part, size, color, indent + (12 if k else 0), cards))
        return wrapped


def _cards_of(r):
    """Cartas jugadas en la interacción (y sus SPECIAL), sin repetir nombre."""
    seen, out = set(), []
    for card in tuple(r.cards or ()) + tuple(r.specials or ()):
        if card is not None and card.name.upper() not in seen:
            seen.add(card.name.upper())
            out.append(card)
    return tuple(out)


def card_spans(text, cards):
    """[(inicio, fin, carta)] de los nombres de carta que aparecen en `text`
    (sin distinguir mayúsculas; los nombres largos primero, sin solaparse)."""
    spans, upper = [], text.upper()
    for card in sorted(cards, key=lambda c: -len(c.name)):
        for m in re.finditer(r"(?<!\w)" + re.escape(card.name.upper()) + r"(?!\w)", upper):
            if all(m.end() <= a or m.start() >= b for a, b, _ in spans):
                spans.append((m.start(), m.end(), card))
    return spans


def _card_at(text, size, cards, x, y, mouse):
    """Carta cuyo nombre está bajo el ratón en una línea dibujada en (x, y)."""
    if not cards or mouse is None or not y <= mouse[1] < y + LINE_H:
        return None
    f = T.font(size, size >= 15)
    for a, b, card in card_spans(text, cards):
        if x + f.size(text[:a])[0] <= mouse[0] < x + f.size(text[:b])[0]:
            return card
    return None


def draw_battle_log(surface, log, engine, scroll, mouse=None):
    """Panel del registro. `scroll` = líneas desplazadas hacia arriba desde el final;
    `mouse` = posición del ratón (muestra la carta cuyo nombre está debajo).
    Devuelve el scroll máximo (para limitarlo desde fuera)."""
    veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    veil.fill((4, 6, 10, 200))
    surface.blit(veil, (0, 0))
    T.panel(surface, PANEL, color=(20, 23, 34), border=T.GOLD, alpha=250)
    T.text(surface, "REGISTRO DEL COMBATE", 24, T.GOLD, (PANEL.x + 20, PANEL.y + 14))
    T.text(surface, "TAB / ESC: cerrar  ·  W/S, flechas o rueda: desplazar  ·  combate en pausa", 13, T.DIM,
           (PANEL.right - 20, PANEL.y + 22), "topright", bold=False)
    body = pygame.Rect(PANEL.x + 20, PANEL.y + 54, PANEL.w - 40, PANEL.h - 70)
    lines = log.lines(engine, body.w - 16)
    visible = body.h // LINE_H
    max_scroll = max(0, len(lines) - visible)
    scroll = max(0, min(scroll, max_scroll))
    start = max(0, len(lines) - visible - scroll)
    clip = surface.get_clip()
    surface.set_clip(body)
    y = body.y
    if not lines:
        T.text(surface, "Aún no ha pasado nada.", 15, T.DIM, (body.x, y), bold=False)
    hovered = None
    inside = mouse is not None and body.collidepoint(mouse)
    for text, size, color, indent, cards in lines[start:start + visible]:
        x = body.x + indent
        T.text(surface, text, size, color, (x, y), bold=size >= 15)
        card = _card_at(text, size, cards, x, y, mouse) if inside else None
        if card is not None:
            hovered = card
            f = T.font(size, size >= 15)
            for a, b, c in card_spans(text, cards):
                if c is card:                         # subraya el nombre señalado
                    x0, x1 = x + f.size(text[:a])[0], x + f.size(text[:b])[0]
                    pygame.draw.line(surface, T.GOLD, (x0, y + size + 2), (x1, y + size + 2), 1)
        y += LINE_H
    surface.set_clip(clip)
    if max_scroll:                                    # barra de scroll
        track = pygame.Rect(body.right - 6, body.y, 4, body.h)
        pygame.draw.rect(surface, (50, 54, 70), track, border_radius=2)
        h = max(24, int(body.h * visible / len(lines)))
        pos = int((body.h - h) * (1 - scroll / max_scroll))
        pygame.draw.rect(surface, T.GOLD, (track.x, body.y + pos, 4, h), border_radius=2)
    if hovered is not None:
        _draw_card_detail(surface, hovered, mouse)
    return max_scroll


def _draw_card_detail(surface, card, mouse):
    """La carta en grande debajo del ratón y, al lado, su descripción completa."""
    desc = T.wrap(card.description, 14, 236) if card.description else []
    big = pygame.Rect(0, 0, 176, 236)
    box = pygame.Rect(0, 0, 260, 20 + LINE_H * len(desc)) if desc else pygame.Rect(0, 0, 0, 0)
    both = pygame.Rect(0, 0, big.w + (box.w + 8 if desc else 0), big.h)
    both.topleft = (mouse[0] + 16, mouse[1] + 16)
    if both.right > surface.get_width() - 8:
        both.right = mouse[0] - 16
    both.clamp_ip(surface.get_rect().inflate(-8, -8))
    big.topleft = both.topleft
    draw_card(surface, card, big, big=True)
    if desc:
        box.topleft = (big.right + 8, big.y)
        T.panel(surface, box, color=(28, 32, 46), border=T.GOLD, alpha=250)
        for k, line in enumerate(desc):
            T.text(surface, line, 14, T.TEXT, (box.x + 10, box.y + 10 + LINE_H * k), bold=False)
