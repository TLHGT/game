"""Punto de entrada de la versión «Dimensión del vacío».

    python main_vacio.py          # o doble clic en jugar_vacio.bat

Es el mismo juego que main.py (mismo código, mismas cartas y personajes), pero
empieza en la dimensión del vacío (maps/vacio.json): por ahora, un espacio
abierto para caminar y el Void Insect. Guarda su mazo en decks_vacio.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import settings  # noqa: E402


def main():
    settings.use_void()
    from game.game import Game
    Game().run()


if __name__ == "__main__":
    main()
