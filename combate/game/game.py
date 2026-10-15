"""Aplicación Pygame: conecta input, motor de combate, animaciones y pantalla.

Modos (solo con menu=True; sin menú, la partida empieza directamente, como en los tests):
    "menu"    elegir mazos · JUGAR · VER / EDITAR MAZOS     (ui/menu_screen.py)
    "decks"   editor de mazos                               (ui/deck_screen.py)
    "battle"  la partida                                    (ui/battle_screen.py)
"""
import pygame

from combate.game.combat import PASS, CombatEngine
from combate.game.deck_editor import DeckEditor, MenuState
from combate.game.input_map import key_to_action
from combate.game.state_machine import Phase
from combate.game.status import LOCK_FREEZE
from combate.ui import theme as T
from combate.ui.animations import Animations
from combate.ui.battle_screen import View, draw_battle, side_pos
from combate.ui.deck_screen import draw_deck_editor
from combate.ui.menu_screen import draw_menu
from combate.ui.player_hud import hud_anchor, mana_pip_pos

# Cuánto se muestra cada fase automática antes de avanzar (segundos)
AUTO_DELAYS = {
    Phase.TURN_START: 1.0,
    Phase.DRAW: 0.45,
    Phase.INTERACTION_START: 0.15,   # se vuelve a elegir casi al instante
    Phase.CARD_REVEAL: 0.7,
    Phase.CARD_RESOLUTION: 1.7,      # por qué ganó + daño normal + combo
    Phase.MEGA_COMBO: 1.6,           # momento aparte: daño adicional y reset del combo
    Phase.TURN_END: 0.6,
}

MESSAGE_COLORS = {
    "UNSTABLE!": T.UNSTABLE_COLOR, "STABLE!": T.STABLE_COLOR, "ADVANTAGE!": T.GOLD,
    "COUNTER!": T.PROPERTY_COLORS["GUARD"], "BLOCK!": T.PROPERTY_COLORS["GUARD"],
    "BREAK!": T.PROPERTY_COLORS["BREAK"], "COMBO ROTO": T.UNSTABLE_COLOR,
    "RECOVER!": T.PROPERTY_COLORS["SPECIAL"],
}


class App:
    def __init__(self, decks=("starter", "starter"), seed=None, menu=False, store=None, characters=None):
        pygame.init()
        pygame.display.set_caption("Combate de cartas - prototipo PvP")
        self.screen = pygame.display.set_mode((T.SCREEN_W, T.SCREEN_H))
        self.canvas = pygame.Surface((T.SCREEN_W, T.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.decks, self.seed = decks, seed
        self.characters = tuple(characters) if characters else (None, None)   # sin personaje: sin pasiva
        self.running = True
        self.buttons = []
        self.hover = None
        self.ui_time = 0.0
        self.menu = None                 # MenuState (solo con menú)
        self.editor = None               # DeckEditor mientras se editan mazos
        self._leave_pending = False      # VOLVER con cambios sin guardar: pide repetirlo
        if menu:
            from combate.cards.deck_store import DeckStore
            self.store = store or DeckStore()
            self.store.apply()           # el motor lee DECKS: con los mazos editados
            self.menu = MenuState(self.store, decks, characters)
            self.mode = "menu"
        else:
            self.mode = "battle"
            self.new_game()

    def new_game(self):
        self.engine = CombatEngine(decks=self.decks, seed=self.seed, characters=self.characters)
        self.view = View(self.engine.rules)
        self.view.menu_available = self.menu is not None
        self.anim = Animations()
        self.buttons = []
        self._last_phase = None
        self.mode = "battle"

    # --- Menú y editor de mazos ---------------------------------------------------
    def go_menu(self):
        self.menu.refresh()
        self.mode = "menu"
        self.buttons = []

    def open_decks(self):
        self.editor = DeckEditor(self.store, selected=self.menu.choice[0])
        self.mode = "decks"
        self._leave_pending = False
        self.buttons = []

    def play(self):
        self.store.apply()
        self.decks = tuple(self.menu.choice)
        self.characters = tuple(self.menu.character)
        self.new_game()

    def menu_action(self, verb, arg=None):
        if verb == "cycle":
            self.menu.cycle(*arg)
        elif verb == "character":
            self.menu.cycle_character(*arg)
        elif verb == "play":
            self.play()
        elif verb == "decks":
            self.open_decks()
        elif verb == "quit":
            self.running = False

    def deck_action(self, verb, arg=None, right_click=False):
        ed = self.editor
        if verb != "back":
            self._leave_pending = False
        if verb != "rename":
            ed.stop_editing_name()
        if verb == "catalog":
            if right_click:
                ed.remove(arg)
            else:
                ed.add(arg)
        elif verb in ("add", "remove", "select"):
            getattr(ed, verb)(arg)
        elif verb in ("new", "duplicate", "save", "discard", "restore", "delete", "clear"):
            getattr(ed, "new_deck" if verb == "new" else verb)()
            self.store.apply()
        elif verb == "rename":
            ed.start_editing_name()
        elif verb == "back":
            if ed.dirty and not self._leave_pending:
                self._leave_pending = True
                ed.message = "Hay cambios sin guardar: pulsa VOLVER otra vez para descartarlos"
                return
            self.editor = None
            self.go_menu()

    def _ui_event(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self.hover = ev.pos
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3):
            right = ev.button == 3
            for rect, (screen, verb, arg) in reversed(self.buttons):
                if not rect.collidepoint(ev.pos):
                    continue
                if screen == "menu" and not right:
                    self.menu_action(verb, arg)
                elif screen == "deck" and (not right or verb in ("catalog", "add", "remove")):
                    self.deck_action("remove" if right and verb == "add" else verb, arg, right_click=right)
                break
        elif ev.type == pygame.KEYDOWN:
            if self.mode == "menu":
                keys = {pygame.K_RETURN: ("play", None), pygame.K_KP_ENTER: ("play", None),
                        pygame.K_m: ("decks", None), pygame.K_ESCAPE: ("quit", None),
                        pygame.K_a: ("cycle", (0, -1)), pygame.K_d: ("cycle", (0, 1)),
                        pygame.K_LEFT: ("cycle", (1, -1)), pygame.K_RIGHT: ("cycle", (1, 1)),
                        pygame.K_w: ("character", (0, -1)), pygame.K_s: ("character", (0, 1)),
                        pygame.K_UP: ("character", (1, -1)), pygame.K_DOWN: ("character", (1, 1))}
                if ev.key in keys:
                    self.menu_action(*keys[ev.key])
            elif self.editor.editing_name:
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    self.editor.stop_editing_name()
                elif ev.key == pygame.K_BACKSPACE:
                    self.editor.backspace()
                else:
                    self.editor.type_char(getattr(ev, "unicode", ""))
            else:
                keys = {pygame.K_ESCAPE: "back", pygame.K_RETURN: "save", pygame.K_KP_ENTER: "save",
                        pygame.K_DELETE: "discard"}
                if ev.key in keys:
                    self.deck_action(keys[ev.key])

    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.step(dt, pygame.event.get())
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def step(self, dt, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.running = False
            elif self.mode != "battle":
                self._ui_event(ev)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.menu is not None:       # con menú: ESC vuelve al menú
                        self.go_menu()
                    else:
                        self.running = False
                elif ev.key == pygame.K_r and self.engine.phase == Phase.GAME_OVER:
                    self.new_game()
                elif ev.key == pygame.K_m and self.menu is not None and self.engine.phase == Phase.GAME_OVER:
                    self.go_menu()
                else:
                    action = key_to_action(ev.key)
                    if action:
                        self.handle_action(*action)
            elif ev.type == pygame.MOUSEMOTION:
                self.view.hover = ev.pos
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(ev.pos):
                        self.handle_action(*action)
                        break
        if self.mode != "battle":
            self.ui_time += dt
            return
        self.update(dt)

    # ------------------------------------------------------------------
    def handle_action(self, player, kind, index=None):
        e = self.engine
        phase = e.phase
        if kind == "menu" and self.menu is not None:
            self.go_menu()
            return
        if kind == "restart" or (phase == Phase.GAME_OVER and kind == "confirm"):
            if phase == Phase.GAME_OVER:
                self.new_game()
            return
        if e.sm.is_auto:
            # Confirmar durante una animación la acelera
            if kind == "confirm":
                self.view.phase_time = max(self.view.phase_time, AUTO_DELAYS.get(phase, 0))
            return
        if phase == Phase.REDRAW:
            if kind == "card":
                e.redraw(player, index)
            else:
                e.finish_redraw(player)
        elif phase == Phase.CARD_SELECTION:
            if kind == "status":                       # botón BREAK ICE / WAIT
                e.select(player, index)
            elif kind == "card" and e.status_lock(player) == LOCK_FREEZE:
                choices = e.status_choices(player)     # tecla 1 / Q: BREAK ICE · 2 / W: WAIT
                if index < len(choices):
                    e.select(player, choices[index])
            elif kind == "card":
                e.select(player, index)
            elif kind == "ultimate":
                if index is None:                      # tecla: siguiente categoría (y al final, ninguna)
                    options = e.ultimate_options(player)
                    current = e.ultimate_pick[player]
                    if current in options and options.index(current) == len(options) - 1:
                        e.select_ultimate(player, current)          # quitarla
                    elif options:
                        nxt = options[options.index(current) + 1] if current in options else options[0]
                        e.select_ultimate(player, nxt)
                else:
                    e.select_ultimate(player, index)
            elif kind == "pass":
                e.select(player, PASS)
            elif kind == "confirm":
                e.confirm(player)

    # ------------------------------------------------------------------
    def update(self, dt):
        v, e = self.view, self.engine
        v.time += dt
        v.phase_time += dt
        if e.sm.is_auto and v.phase_time >= AUTO_DELAYS.get(e.phase, 0.3):
            e.advance()
        # Reiniciar el reloj de fase DESPUÉS de avanzar: si no, la fase nueva
        # arrancaría un frame con el tiempo de la anterior.
        if e.phase != self._last_phase:
            self._last_phase = e.phase
            v.phase_time = 0.0
        self._consume_events()
        self.anim.update(dt)
        for p in e.players:              # la barra "fantasma" de HP baja poco a poco
            shown = v.hp_shown[p.index]
            v.hp_shown[p.index] = p.hp if shown < p.hp else max(p.hp, shown - 40 * dt)
            for k in list(v.pulse[p.index]):
                v.pulse[p.index][k] = max(0.0, v.pulse[p.index][k] - dt)

    def _consume_events(self):
        for ev in self.engine.pop_events():
            p, d = ev.player, ev.data
            if ev.kind == "turn":
                self.anim.popup(f"TURNO {d['turn']}", (T.SCREEN_W // 2, 300), T.GOLD, 60)
            elif ev.kind == "mana":
                amount = d["amount"]
                pos = mana_pip_pos(p, max(0, self.engine.displayed_mana(p) - (1 if amount < 0 else 0)), self.engine.rules)
                self.anim.float_text(f"{'+' if amount > 0 else ''}{amount} MANA", (pos[0], pos[1] + 42),
                                     T.MANA_COLOR if amount > 0 else (170, 190, 255))
                self.view.pulse[p]["mana"] = 0.5
            elif ev.kind == "hp" and d["amount"] > 0:   # curación (p. ej. Elemental Wolf absorbe su elemento)
                x, y = hud_anchor(p)
                self.anim.float_text(f"+{d['amount']} HP", (x + 200, y + 40), T.HP_COLOR)
                self.anim.popup(f"+{d['amount']}", (side_pos(p)[0], side_pos(p)[1] - 70), T.HP_COLOR, 50)
            elif ev.kind == "affinity":                 # cambio de afinidad elemental
                color = (255, 130, 60) if d["element"] == "FIRE" else T.ICE_COLOR
                self.anim.flash.add(color, 0.35)
                self.view.pulse[p]["passive"] = 0.8
            elif ev.kind == "hp":
                x, y = hud_anchor(p)
                mega = d.get("damage_type") == "mega_combo"
                status_color = T.STATUS_COLORS.get(str(d.get("damage_type", "")).upper())
                self.anim.float_text(f"{d['amount']} HP", (x + 200, y + 40),
                                     status_color or (T.GOLD if mega else T.UNSTABLE_COLOR))
                sx, sy = side_pos(p)
                if status_color:  # daño periódico (BURN / POISON): sin hit, sin sacudida fuerte
                    self.anim.popup(f"{d['amount']}", (sx, sy - 110), status_color, 44)
                    self.anim.shake.add(3, 0.15)
                elif mega:          # daño del Mega Combo: grande, dorado y más abajo
                    self.anim.popup(f"{d['amount']}", (sx, sy + 70), T.GOLD, 72)
                    self.anim.shake.add(16, 0.45)
                else:             # daño normal de la interacción
                    self.anim.popup(f"{d['amount']}", (sx, sy - 70), T.UNSTABLE_COLOR, 50)
                    self.anim.shake.add(6, 0.2)
            elif ev.kind == "ice":
                sx, sy = side_pos(p)
                self.anim.popup(f"ICE {d['amount']}", (sx, sy - 70), T.ICE_COLOR, 44)
                self.anim.shake.add(4, 0.15)
            elif ev.kind == "status":
                self.view.pulse[p]["status"] = 0.6
            elif ev.kind == "style":                # una vez por interacción y jugador
                if d["delta"] == 0 and not d["streak_reset"]:
                    continue                        # p. ej. PASS sin recibir HIT: nada que contar
                self.view.pulse[p]["style"] = 0.8
                text = f"{'+' if d['delta'] >= 0 else ''}{d['delta']} ESTILO"
                if d["streak_reset"]:
                    text += " · RACHA 0"
                self.anim.popup(text, (side_pos(p)[0], 385), T.GOLD if d["delta"] > 0 else (255, 140, 120), 24)
            elif ev.kind == "passive":              # la pasiva del personaje aumenta un daño
                self.view.pulse[p]["passive"] = 0.8
                self.anim.popup(f"+{d['pct']}%", (side_pos(p)[0], 250), T.GOLD, 30)
            elif ev.kind == "stability":
                self.view.pulse[p]["stability"] = 0.4
            elif ev.kind == "transform":            # Corrupted / Void Insect: otro luchador
                if d.get("sprite"):
                    self.view.fighter_keys[p] = d["sprite"]
                self.view.hp_shown[p] = d["hp"]
                self.view.pulse[p]["passive"] = 1.0
                self.anim.flash.add((150, 70, 210), 0.5)
                self.anim.shake.add(10, 0.4)
            elif ev.kind in ("max_mana", "max_hp"):  # Corrupted / Void consumption
                self.view.pulse[p]["mana" if ev.kind == "max_mana" else "passive"] = 0.8
                self.anim.flash.add((150, 70, 210), 0.25)
            elif ev.kind == "hit":
                self.view.pulse[p]["hits"] = 0.6
                self.anim.popup(f"HIT {d['hits']}", side_pos(p), T.PLAYER_COLORS[p], 40)
            elif ev.kind == "message" and d.get("status"):
                # Mensajes de estados: el panel de estado los conserva; aquí, aviso breve
                color = next((c for n, c in T.STATUS_COLORS.items() if n in d["text"]), T.ICE_COLOR
                             if "ICE" in d["text"] else T.TEXT)
                self.anim.popup(d["text"], (side_pos(p)[0], 310), color, 22)
            elif ev.kind == "message":
                color = MESSAGE_COLORS.get(d["text"], T.TEXT)
                big = d["text"].endswith("COMBO!")
                self.anim.popup(d["text"], side_pos(p) if not big else (T.SCREEN_W // 2, 300),
                                T.GOLD if big else color, 60 if big else 40)
            elif ev.kind == "reveal":
                self.anim.shake.add(3, 0.15)
            elif ev.kind == "win":
                self.anim.shake.add(7, 0.25)
                self.anim.flash.add(T.PLAYER_COLORS[p], 0.22)
            elif ev.kind == "mega_combo":
                self.anim.flash.add(T.GOLD, 0.4)
                self.anim.popup(f"{d['hits']} HIT COMBO!", (T.SCREEN_W // 2, 250), T.PLAYER_COLORS[p], 40)
                self.anim.popup("MEGA COMBO!", (T.SCREEN_W // 2, 300), T.GOLD, 76)
            elif ev.kind == "combo_reset":
                self.view.pulse[p]["hits"] = 0.8
            elif ev.kind == "game_over":
                self.anim.shake.add(18, 0.6)

    # ------------------------------------------------------------------
    def draw(self):
        if self.mode == "menu":
            self.buttons = draw_menu(self.canvas, self.menu, self.ui_time, self.hover)
            self.screen.blit(self.canvas, (0, 0))
            return
        if self.mode == "decks":
            self.buttons = draw_deck_editor(self.canvas, self.editor, self.ui_time, self.hover)
            self.screen.blit(self.canvas, (0, 0))
            return
        self.buttons = draw_battle(self.canvas, self.engine, self.view)
        self.anim.draw(self.canvas)
        ox, oy = self.anim.shake.offset
        self.screen.fill(T.BG)
        self.screen.blit(self.canvas, (round(ox), round(oy)))
