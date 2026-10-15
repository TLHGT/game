"""Escena de combate dentro de la exploración.

Reutiliza la aplicación del combate de cartas (combate/game/game.py: App)
sin abrir otra ventana: el motor, las animaciones y la pantalla son los
mismos. Cambia solo lo necesario para jugar contra un enemigo del mapa:

    - el jugador 2 lo controla la IA (combate/game/ai.py) y su mano va boca abajo;
    - solo se aceptan las teclas y clics del jugador 1;
    - ESC huye (si el enemigo lo permite) y, al terminar, CONTINUAR vuelve al mapa;
    - TAB abre el registro del combate (combate/ui/battle_log.py) y lo pausa.

Al acabar, `finished` pasa a True y `result` vale "win", "lose", "draw" o "flee".
"""
import pygame

from combate.cards.card_database import make_card, make_deck_cards
from combate.game.ai import CardAI
from combate.game.combat import CombatEngine
from combate.game.config import RULES
from combate.game.game import App
from combate.game.input_map import key_to_action
from combate.game.state_machine import Phase
from combate.ui import theme as T
from combate.ui.animations import Animations
from combate.ui.battle_log import BattleLog, draw_battle_log
from combate.ui.battle_screen import View

AI_THINK_TIME = 0.7      # segundos que "piensa" la IA antes de cada decisión
PLAYER, ENEMY = 0, 1


def enemy_cards(deck):
    """`deck` puede ser el nombre de un mazo o una lista de ids de carta."""
    if isinstance(deck, str):
        return make_deck_cards(deck)
    return [make_card(cid) for cid in deck]


class BattleScene(App):
    def __init__(self, screen, enemy, player_deck, player_character=None, player_name="TÚ", seed=None):
        # No se llama a App.__init__: crearía otra ventana y el menú de mazos.
        self.screen = screen
        self.canvas = pygame.Surface((T.SCREEN_W, T.SCREEN_H))
        self.enemy = enemy
        self.player_deck = player_deck
        self.player_name = player_name
        self.characters = (player_character, enemy.character)
        self.seed = seed
        self.menu = None
        self.editor = None
        self.running = True
        self.buttons = []
        self.hover = None
        self.ui_time = 0.0
        self.finished = False
        self.result = None
        self.ai = CardAI(ENEMY, aggression=enemy.aggression, randomness=enemy.randomness, seed=seed)
        self._ai_timer = 0.0
        self.log = BattleLog()
        self.log_open = False
        self.log_scroll = 0
        self._log_max_scroll = 0
        self.new_game()

    def new_game(self):
        cards = (make_deck_cards(self.player_deck), enemy_cards(self.enemy.deck))
        self.engine = CombatEngine(card_lists=cards, seed=self.seed, characters=self.characters,
                                   names=(self.player_name, self.enemy.name.upper()))
        self.view = View(self.engine.rules)
        self.view.ai_players = {ENEMY}
        self.view.exit_label = "CONTINUAR"
        self.view.fighter_keys[ENEMY] = self.enemy.sprite_key     # el mismo aspecto que en el mapa
        if self.enemy.hp:
            foe = self.engine.players[ENEMY]
            foe.hp = foe.max_hp = max(1, min(RULES.MAX_HP, self.enemy.hp))
            self.view.hp_shown[ENEMY] = foe.hp
        self.anim = Animations()
        self.buttons = []
        self._last_phase = None
        self.mode = "battle"

    # ------------------------------------------------------------------
    def finish(self, result):
        self.finished = True
        self.result = result

    def _log_event(self, ev):
        """Con el registro abierto solo se cierra o se desplaza (el combate está en pausa)."""
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_TAB, pygame.K_ESCAPE):
                self.log_open = False
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.log_scroll += 1
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.log_scroll -= 1
            elif ev.key == pygame.K_PAGEUP:
                self.log_scroll += 10
            elif ev.key == pygame.K_PAGEDOWN:
                self.log_scroll -= 10
        elif ev.type == pygame.MOUSEWHEEL:
            self.log_scroll += ev.y * 3
        self.log_scroll = max(0, min(self.log_scroll, self._log_max_scroll))

    def step(self, dt, events):
        over = self.engine.phase == Phase.GAME_OVER
        for ev in events:
            if ev.type == pygame.QUIT:
                self.running = False
            elif self.log_open:
                self._log_event(ev)
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_TAB:
                self.log_open = True
                self.log_scroll = 0
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if over:
                        self._finish_game()
                    elif self.enemy.can_flee:
                        self.finish("flee")
                elif over and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e, pygame.K_SPACE):
                    self._finish_game()
                else:
                    action = key_to_action(ev.key)
                    if action and action[0] == PLAYER:
                        self.handle_action(*action)
            elif ev.type == pygame.MOUSEMOTION:
                self.view.hover = ev.pos
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(ev.pos) and action[0] in (PLAYER, None):
                        self.handle_action(*action)
                        break
        if self.finished or self.log_open:
            return
        self._run_ai(dt)
        self.update(dt)

    def _consume_events(self):
        self.log.observe(self.engine, self.engine.events)
        super()._consume_events()

    def handle_action(self, player, kind, index=None):
        if self.engine.phase == Phase.GAME_OVER:
            if kind in ("exit", "confirm", "restart", "menu"):
                self._finish_game()
            return
        super().handle_action(player, kind, index)

    def _finish_game(self):
        w = self.engine.winner
        self.finish("draw" if w is None else "win" if w == PLAYER else "lose")

    def _run_ai(self, dt):
        self.ai.observe(self.engine)
        if not self.ai.needs_input(self.engine):
            self._ai_timer = 0.0
            return
        self._ai_timer += dt
        if self._ai_timer >= AI_THINK_TIME:
            self._ai_timer = 0.0
            self.ai.act(self.engine)

    # ------------------------------------------------------------------
    def draw(self):
        super().draw()
        if self.engine.phase != Phase.GAME_OVER:
            hint = "ESC: huir del combate" if self.enemy.can_flee else "¡No puedes huir de este combate!"
            T.text(self.screen, f"{hint}  ·  TAB: registro", 14, T.DIM, (24, 476), "midleft", bold=False)
        if self.log_open:
            self._log_max_scroll = draw_battle_log(self.screen, self.log, self.engine, self.log_scroll)

