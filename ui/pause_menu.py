"""Menú de pausa de la exploración (TAB): cambiar de personaje y de mazo.

    W/S o flechas arriba/abajo   elegir fila (Personaje · Mazo · Editar mazos · Continuar)
    A/D o flechas izq./der.      cambiar el valor
    ENTER en Editar mazos        abre el editor de mazos (crear, duplicar, cambiar cartas...)
    TAB / ESC / ENTER en Continuar   volver al juego

La elección se guarda en GameState (flags "combat_character" y "combat_deck"),
que es lo que lee game/battle_scene.py al empezar cada combate. Solo salen los
personajes JUGABLES (los de los enemigos no) y los mazos del jugador
(de fábrica y los creados con el editor de combate/).
"""
import pygame

from combate.cards.card_database import CARDS, DECKS
from combate.game.characters import CHARACTERS, playable_characters
from combate.ui.theme import PROPERTY_COLORS
from game import settings
from ui import text as T

ROWS = ("character", "deck", "edit_decks", "resume")
UP = (pygame.K_w, pygame.K_UP)
DOWN = (pygame.K_s, pygame.K_DOWN)
LEFT = (pygame.K_a, pygame.K_LEFT)
RIGHT = (pygame.K_d, pygame.K_RIGHT)
CLOSE = (pygame.K_TAB, pygame.K_ESCAPE)
CONFIRM = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e, pygame.K_SPACE)


class PauseMenu:
    def __init__(self, state, deck_names, assets=None):
        self.state = state
        self.assets = assets         # para enseñar el avatar del personaje elegido
        self.deck_names = list(deck_names)
        self.characters = playable_characters()
        self.is_open = False
        self.row = 0
        self.request = None          # "edit_decks": el juego abre el editor de mazos

    # --- Estado -----------------------------------------------------------------
    @property
    def character(self):
        cid = self.state.get_flag("combat_character", settings.PLAYER_CHARACTER)
        return cid if cid in self.characters else self.characters[0]

    @property
    def deck(self):
        name = self.state.get_flag("combat_deck", settings.PLAYER_DECK)
        if name in self.deck_names or not self.deck_names:
            return name
        return self.deck_names[0]

    def open(self):
        self.is_open = True
        self.row = 0
        # Deja guardada la elección efectiva (por si settings apuntaba a algo que no existe)
        self.state.set_flag("combat_character", self.character)
        self.state.set_flag("combat_deck", self.deck)

    def close(self):
        self.is_open = False

    def refresh_decks(self, deck_names, prefer=None):
        """Tras editar: mazos nuevos o borrados. `prefer` pasa a ser el mazo elegido."""
        self.deck_names = list(deck_names)
        if prefer in self.deck_names:
            self.state.set_flag("combat_deck", prefer)
        self.state.set_flag("combat_deck", self.deck)

    def cycle(self, step):
        if ROWS[self.row] == "character":
            ids = self.characters
            self.state.set_flag("combat_character", ids[(ids.index(self.character) + step) % len(ids)])
        elif ROWS[self.row] == "deck":
            names = self.deck_names
            self.state.set_flag("combat_deck", names[(names.index(self.deck) + step) % len(names)])

    def handle_events(self, events):
        for ev in events:
            if ev.type != pygame.KEYDOWN or not self.is_open:
                continue
            if ev.key in CLOSE:
                self.close()
            elif ev.key in UP:
                self.row = (self.row - 1) % len(ROWS)
            elif ev.key in DOWN:
                self.row = (self.row + 1) % len(ROWS)
            elif ev.key in LEFT:
                self.cycle(-1)
            elif ev.key in RIGHT:
                self.cycle(1)
            elif ev.key in CONFIRM:
                if ROWS[self.row] == "resume":
                    self.close()
                elif ROWS[self.row] == "edit_decks":
                    self.request = "edit_decks"
                else:
                    self.cycle(1)

    # --- Dibujo -------------------------------------------------------------------
    def draw(self, surface):
        if not self.is_open:
            return
        w, h = surface.get_size()
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 165))
        surface.blit(veil, (0, 0))
        pw, ph = 820, 600
        x, y = (w - pw) // 2, (h - ph) // 2
        surface.blit(T.panel((pw, ph), border=settings.UI_ACCENT, alpha=240), (x, y))
        title = T.font(34, bold=True).render("PAUSA", True, settings.UI_ACCENT)
        surface.blit(title, title.get_rect(midtop=(w // 2, y + 18)))

        ch = CHARACTERS[self.character]
        pas = ch.make_passive()
        yy = y + 80
        self._row(surface, 0, x, yy, pw, "Personaje", ch.name)
        f = T.font(17)
        lines = [ch.description, f"Pasiva (combate) · {pas.name}: {pas.summary()}",
                 f"Aventura (mapa) · {ch.adventure_name}: {ch.adventure_desc}" if ch.adventure
                 else "Aventura (mapa) · ninguna por ahora"]
        ty = yy + 44
        text_w = pw - 80
        if self.assets:
            # Avatar del personaje (el sprite que se ve en el mapa), ampliado
            # hasta x2 sin salirse del recuadro (Jurgenoid es más alto)
            img = self.assets.get(f"{ch.avatar or 'player'}_down_0")
            box = pygame.Rect(x + pw - 40 - 120, ty - 2, 120, 150)
            k = min(2.0, (box.h - 14) / img.get_height(), (box.w - 8) / img.get_width())
            img = pygame.transform.scale(img, (round(img.get_width() * k), round(img.get_height() * k)))
            pygame.draw.rect(surface, (34, 38, 44), box, border_radius=10)
            pygame.draw.rect(surface, (70, 74, 80), box, 2, border_radius=10)
            surface.blit(img, img.get_rect(midbottom=(box.centerx, box.bottom - 8)))
            text_w -= 136
            avatar_bottom = box.bottom
        else:
            avatar_bottom = ty
        for line in lines:
            for part in T.wrap(line, f, text_w):
                surface.blit(f.render(part, True, settings.UI_TEXT_DIM), (x + 40, ty))
                ty += 22

        yy = max(ty, avatar_bottom) + 18
        self._row(surface, 1, x, yy, pw, "Mazo", self.deck)
        self._deck_cards(surface, x + 40, yy + 46, pw - 80)

        yy = y + ph - 142
        self._row(surface, 2, x, yy, pw, "Editar mazos", None, "ENTER: crear y personalizar mazos")
        self._row(surface, 3, x, yy + 46, pw, "Continuar", None)
        hint = T.font(15).render("W/S: elegir  ·  A/D: cambiar  ·  TAB / ESC: volver al juego", True,
                                 settings.UI_TEXT_DIM)
        surface.blit(hint, hint.get_rect(midbottom=(w // 2, y + ph - 14)))

    def _row(self, surface, index, x, y, pw, label, value, note=None):
        selected = self.row == index
        rect = pygame.Rect(x + 24, y, pw - 48, 38)
        if selected:
            pygame.draw.rect(surface, (60, 56, 40), rect, border_radius=8)
            pygame.draw.rect(surface, settings.UI_ACCENT, rect, 2, border_radius=8)
        color = settings.UI_ACCENT if selected else settings.UI_TEXT
        lab = T.font(21, bold=True).render(label, True, color)
        surface.blit(lab, lab.get_rect(midleft=(rect.x + 16, rect.centery)))
        if value is not None:
            val = T.font(21, bold=True).render(f"<  {value.upper()}  >", True, settings.UI_TEXT)
            surface.blit(val, val.get_rect(midright=(rect.right - 16, rect.centery)))
        elif note:
            img = T.font(16).render(note, True, settings.UI_TEXT_DIM)
            surface.blit(img, img.get_rect(midright=(rect.right - 16, rect.centery)))

    def _deck_cards(self, surface, x, y, width):
        counts = {}
        for cid in DECKS.get(self.deck, []):
            counts[cid] = counts.get(cid, 0) + 1
        f = T.font(16)
        cx, cy = x, y
        for cid, n in counts.items():
            data = CARDS[cid]
            label = f"{data['name']}" + (f" x{n}" if n > 1 else "")
            if data.get("element"):
                label += f" ({data['element']})"
            img = f.render(label, True, (20, 22, 26))
            chip = pygame.Rect(cx, cy, img.get_width() + 16, 26)
            if chip.right > x + width:
                cx, cy = x, cy + 32
                chip.topleft = (cx, cy)
            pygame.draw.rect(surface, PROPERTY_COLORS.get(data["card_type"], PROPERTY_COLORS[None]), chip,
                             border_radius=6)
            surface.blit(img, img.get_rect(center=chip.center))
            cx = chip.right + 8
