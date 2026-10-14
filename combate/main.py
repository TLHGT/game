"""Punto de entrada.

    python main.py                          # menú: elegir mazos, jugar o ver/editar mazos
    python main.py --deck starter           # el menú arranca con ese mazo para ambos
    python main.py --p1 starter --p2 laboratorio --seed 42
    python main.py --sin-menu               # directo a la partida (como antes)
    python main.py --pj1 hero --pj2 hero    # personajes (también se eligen en el menú)

Los mazos editados se guardan en decks.json (cards/deck_store.py).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from combate.cards.card_database import DECKS  # noqa: E402
from combate.cards.deck_store import DeckStore  # noqa: E402
from combate.game.characters import playable_characters  # noqa: E402
from combate.game.config import DEFAULT_DECKS  # noqa: E402


def main():
    store = DeckStore()
    store.apply()                            # mazos de fábrica + los guardados en decks.json
    parser = argparse.ArgumentParser(description="Prototipo de combate PvP de cartas")
    parser.add_argument("--deck", choices=sorted(DECKS), help="mazo para ambos jugadores")
    parser.add_argument("--p1", choices=sorted(DECKS), help="mazo del jugador 1")
    parser.add_argument("--p2", choices=sorted(DECKS), help="mazo del jugador 2")
    parser.add_argument("--pj1", choices=playable_characters(), default="blaze", help="personaje del jugador 1")
    parser.add_argument("--pj2", choices=playable_characters(), default="hero", help="personaje del jugador 2")
    parser.add_argument("--seed", type=int, help="semilla para barajar (partida reproducible)")
    parser.add_argument("--sin-menu", action="store_true", help="empezar la partida sin pasar por el menú")
    args = parser.parse_args()
    base = (args.deck, args.deck) if args.deck else DEFAULT_DECKS
    decks = (args.p1 or base[0], args.p2 or base[1])

    from combate.game.game import App
    App(decks=decks, seed=args.seed, menu=not args.sin_menu, store=store, characters=(args.pj1, args.pj2)).run()


if __name__ == "__main__":
    main()
