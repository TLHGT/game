"""Prueba la Dimensión del vacío (tercera versión: main_vacio.py).

    python tests/vacio_test.py            # solo comprobaciones
    python tests/vacio_test.py --shots    # además guarda capturas en tests/shots/

Por ahora la dimensión es una isla abierta flotando en el vacío con el Void
Insect: se comprueba que se puede andar por ella, que no se sale al vacío y que
el insecto se puede retar directamente (sin barrera) y no deja huir.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke_test import Bot  # noqa: E402  (configura SDL sin ventana)

from game import settings  # noqa: E402
from pathing import go, reachable  # noqa: E402

settings.use_void()
settings.DECKS_PATH = os.path.join(tempfile.mkdtemp(), "decks_vacio.json")   # no toca los mazos del usuario

from entities.enemy import Enemy  # noqa: E402


def main():
    b = Bot()
    g = b.g
    b.tick(60)
    w = g.world
    start = w.spawns["default"]
    b.check(w.id == "vacio" and w.name == "Dimensión del vacío", "Empieza en la dimensión del vacío")
    b.check(g.pause.deck == "vacio" and g.store.path.endswith("decks_vacio.json"),
            "La versión del vacío tiene su propio mazo (decks_vacio.json)")
    b.check(w.ground.get("theme") == "void" and not w.forest, "Suelo del vacío y sin árboles")
    enemies = [it for it in w.all_interactables if isinstance(it, Enemy)]
    b.check([e.id for e in enemies] == ["void_insect"] and len(w.all_interactables) == 1,
            "No hay nada más que el Void Insect")
    b.shot("v01_entrada")

    # --- Un espacio abierto para caminar ---------------------------------------------
    corners = [(460, 460), (1940, 460), (460, 1540), (1940, 1540)]
    b.check(all(reachable(w, start, c) for c in corners), "Se puede andar por toda la isla")
    b.check(not reachable(w, start, (200, 1000)) and not reachable(w, start, (1200, 1800)),
            "No se puede caminar fuera de la isla, al vacío")
    go(b, (1900, 1500))
    b.check(abs(g.player.x - 1900) < 30 and abs(g.player.y - 1500) < 30, "El jugador camina libremente")
    g.input.move_override = (1, 0)                  # sigue andando hacia el borde
    b.tick(120)
    g.input.move_override = None
    b.check(g.player.x < 2010, "El borde de la isla no deja caer al vacío")

    # --- El Void Insect ---------------------------------------------------------------
    insect = w.get_interactable("void_insect")
    b.check(reachable(w, start, (insect.rect.centerx, insect.rect.bottom + 24)), "Se llega hasta el Void Insect")
    b.check(insect.can_interact() and not insect.can_flee, "Se le puede retar directamente (y no deja huir)")
    g.start_battle(insect)
    b.tick(2)
    b.check(g.dialogue.is_open, "Antes del combate habla (presentación)")
    b.resolve_encounter("win")
    b.check(insect.defeated and not insect.visible, "Vencido el insecto, desaparece")
    print(f"\nDimensión del vacío OK ({b.ok} comprobaciones).")


if __name__ == "__main__":
    main()
