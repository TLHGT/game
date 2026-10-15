"""Punto de entrada de la versión «Aldea del vacío».

    python main_aldea.py          # o doble clic en jugar_aldea.bat

Es el mismo juego que main.py (mismo código, mismas cartas y personajes), pero
empieza en la aldea (maps/aldea.json) y guarda su mazo en decks_aldea.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import settings  # noqa: E402


def main():
    settings.use_village()
    from game.game import Game
    Game().run()


if __name__ == "__main__":
    main()
