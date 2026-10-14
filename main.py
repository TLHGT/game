"""Punto de entrada: exploración del mapa con el combate de cartas.

    python main.py                       # empieza en la caverna del hospital
    python main.py ruta/a/mi_mapa.json   # prueba un mapa (p. ej. del diseñador)

El duelo de cartas PvP original sigue disponible con `python combate/main.py`.

Con un mapa propio, las salidas buscan sus mapas destino en la misma carpeta.
"""
import os
import sys

# Permite ejecutar desde cualquier directorio.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import settings  # noqa: E402


def main():
    if len(sys.argv) > 1:
        path = os.path.abspath(sys.argv[1])
        if not os.path.isfile(path):
            sys.exit(f"No existe el mapa: {path}")
        settings.MAP_DIR = os.path.dirname(path)
        settings.START_MAP = os.path.splitext(os.path.basename(path))[0]
    from game.game import Game
    Game().run()


if __name__ == "__main__":
    main()
