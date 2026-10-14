"""Editor de mazos dentro de la exploración (menú de pausa -> Editar mazos).

Reutiliza el editor del combate (combate/game/deck_editor.py + ui/deck_screen.py)
a través de su App, igual que BattleScene: misma pantalla, mismos botones,
mismas teclas. Los cambios se guardan en combate/decks.json, así que valen
también para el duelo PvP (python combate/main.py).

Al pulsar VOLVER (ESC), `finished` pasa a True y `selected` es el mazo que
estaba abierto en el editor (o None si era uno nuevo sin guardar).
"""
import pygame

from combate.game.deck_editor import DeckEditor
from combate.game.game import App
from combate.ui import theme as T


class DeckEditScene(App):
    def __init__(self, screen, store, selected=None, locked=(), single=False):
        # No se llama a App.__init__: crearía otra ventana.
        self.screen = screen
        self.canvas = pygame.Surface((T.SCREEN_W, T.SCREEN_H))
        self.store = store
        self.menu = None
        self.running = True
        self.buttons = []
        self.hover = None
        self.ui_time = 0.0
        self._leave_pending = False
        self.editor = DeckEditor(store, selected=selected, locked=locked, single=single)
        self._editor = self.editor          # App pone editor = None al salir
        self.mode = "decks"
        self.finished = False

    @property
    def selected(self):
        return self._editor.selected

    def go_menu(self):
        """VOLVER: en el duelo vuelve a su menú; aquí, al menú de pausa."""
        self.store.apply()
        self.finished = True
