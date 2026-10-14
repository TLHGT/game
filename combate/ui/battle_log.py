"""Registro del combate: todo lo que ha pasado, turno a turno.

BattleLog guarda las entradas (sin Pygame) y draw_battle_log las dibuja como
un panel con scroll encima de la pantalla de combate.

    ("turn", n)                         cabecera de turno
    ("result", InteractionResult)       una interacción: cartas, por qué ganó y qué pasó
    ("note", jugador, texto)            lo que pasa fuera de una interacción
                                        (BURN al empezar el turno, POISON, Alerta...)

Las listas de cada InteractionResult se leen al dibujar: así el Mega Combo,
que se añade después de la resolución, también aparece.
"""
import pygame

from combate.game.status import BREAK_ICE
from combate.ui import theme as T
from combate.ui.battle_screen import _consequence_color

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
        """[(texto, tamaño, color, sangría)] ya partidas al ancho."""
        out = []
        for entry in self.entries:
            if entry[0] == "turn":
                out.append(("", 8, T.TEXT, 0))
                out.append((f"— TURNO {entry[1]} —", 18, T.GOLD, 0))
            elif entry[0] == "note":
                _, player, text = entry
                color = T.PLAYER_COLORS[player] if player is not None else T.DIM
                out.append((f"· {text}", 14, T.mix(color, T.TEXT, 0.4), 16))
            else:
                r = entry[1]
                n = getattr(r, "interaction_number", "?")
                head = f"Interacción {n}:  {self._play(engine, r, 0)}   vs   {self._play(engine, r, 1)}"
                out.append((head, 15, T.TEXT, 8))
                for line in r.lines[:4]:
                    color = T.PLAYER_COLORS[r.winner] if "WINS" in line and r.winner is not None else \
                        (T.GOLD if line == "DRAW" else (200, 204, 218))
                    out.append((line, 14, color, 24))
                for c in r.consequences:
                    out.append((f"• {c}", 13, _consequence_color(c), 32))
        wrapped = []
        for text, size, color, indent in out:
            parts = T.wrap(text, size, width - indent) if text else [""]
            for k, part in enumerate(parts):
                wrapped.append((part, size, color, indent + (12 if k else 0)))
        return wrapped


def draw_battle_log(surface, log, engine, scroll):
    """Panel del registro. `scroll` = líneas desplazadas hacia arriba desde el final.
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
    for text, size, color, indent in lines[start:start + visible]:
        T.text(surface, text, size, color, (body.x + indent, y), bold=size >= 15)
        y += LINE_H
    surface.set_clip(clip)
    if max_scroll:                                    # barra de scroll
        track = pygame.Rect(body.right - 6, body.y, 4, body.h)
        pygame.draw.rect(surface, (50, 54, 70), track, border_radius=2)
        h = max(24, int(body.h * visible / len(lines)))
        pos = int((body.h - h) * (1 - scroll / max_scroll))
        pygame.draw.rect(surface, T.GOLD, (track.x, body.y + pos, 4, h), border_radius=2)
    return max_scroll
