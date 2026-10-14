"""Menú y editor de mazos por la UI (clics y teclas simulados, decks.json temporal).

    python tests/ui_decks.py            # comprobaciones
    python tests/ui_decks.py --shots    # + capturas en tests/shots/
"""
import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))

import pygame  # noqa: E402

from combate.cards.deck_store import BUILTIN_DECKS, DeckStore  # noqa: E402
from combate.game.game import App  # noqa: E402
from combate.game.state_machine import Phase  # noqa: E402

SHOTS = "--shots" in sys.argv
SHOT_DIR = os.path.join(ROOT, "tests", "shots")
DT = 1 / 60


def check(cond, label):
    print(f"[{'OK ' if cond else 'FALLO'}] {label}")
    if not cond:
        raise SystemExit(1)


def shot(app, name):
    if SHOTS:
        os.makedirs(SHOT_DIR, exist_ok=True)
        app.draw()
        pygame.image.save(app.screen, os.path.join(SHOT_DIR, f"mazos_{name}.png"))


def key(k, uni=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni, scancode=0)


def click(app, action, button=1):
    """Clic en el centro del botón cuya acción es `action` (busca en lo último dibujado)."""
    app.draw()
    rect = next((r for r, a in app.buttons if a == action), None)
    assert rect is not None, f"No hay botón {action}"
    app.step(DT, [pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center, rel=(0, 0), buttons=(0, 0, 0)),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=button)])


def main():
    tmp = tempfile.mkdtemp()
    try:
        run(DeckStore(os.path.join(tmp, "decks.json")), tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pygame.quit()
    print("\nMenú y editor de mazos OK.")


def run(store, tmp):
    app = App(decks=("duelo", "duelo"), seed=1, menu=True, store=store)
    check(app.mode == "menu", "Con menú, la app arranca en el menú")
    check(app.menu.character == ["blaze", "hero"], "Personajes por defecto: Blaze y Hero")
    app.step(DT, [key(pygame.K_s), key(pygame.K_UP)])
    check(app.menu.character == ["hero", "blaze"], "W/S cambian el personaje de J1; flechas arriba/abajo, el de J2")
    click(app, ("menu", "character", (1, 1)))
    check(app.menu.character == ["hero", "hero"], "Botón > del personaje; ambos pueden elegir el mismo")
    shot(app, "1_menu")
    app.step(DT, [key(pygame.K_d), key(pygame.K_LEFT)])
    check(app.menu.choice == ["starter", store.names()[-1]], "A/D cambian el mazo de J1; flechas, el de J2")
    click(app, ("menu", "cycle", (0, -1)))
    check(app.menu.choice[0] == "duelo", "Botón < del menú")

    # --- Editor: ver y modificar un mazo de fábrica ---------------------------------
    click(app, ("menu", "decks", None))
    ed = app.editor
    check(app.mode == "decks" and ed.selected == "duelo", "VER / EDITAR MAZOS abre el editor con el mazo de J1")
    shot(app, "2_editor")
    click(app, ("deck", "catalog", "magic"))
    check("ya tiene 10" in ed.message, "Mazo lleno: el catálogo avisa en vez de añadir")
    click(app, ("deck", "remove", "recover"))
    click(app, ("deck", "catalog", "magic"))
    check(ed.count("magic") == 1 and len(ed.cards) == 10, "[-] quita una copia; clic en el catálogo añade")
    click(app, ("deck", "catalog", "attack"), button=3)
    check(ed.count("attack") == 1, "Clic derecho en el catálogo quita una copia")
    app.step(DT, [pygame.event.Event(pygame.MOUSEMOTION, pos=(700, 160), rel=(0, 0), buttons=(0, 0, 0))])
    shot(app, "3_editando_con_vista_previa")
    click(app, ("deck", "back", None))
    check(app.mode == "decks" and "otra vez" in ed.message, "VOLVER con cambios sin guardar pide confirmación")
    app.step(DT, [key(pygame.K_RETURN)])
    check(ed.dirty and "No se puede guardar" in ed.message, "ENTER no guarda un mazo incompleto (9/10)")
    click(app, ("deck", "add", "magic"))
    app.step(DT, [key(pygame.K_RETURN)])
    check(not ed.dirty and store.kind("duelo") == "modificado", "ENTER guarda: 'duelo' queda MODIFICADO")
    check(DeckStore(store.path).get("duelo").count("magic") == 2, "Guardado en decks.json")

    # --- Mazo nuevo con nombre escrito ----------------------------------------------------
    click(app, ("deck", "new", None))
    click(app, ("deck", "rename", None))
    app.step(DT, [key(pygame.K_BACKSPACE)] * 10 + [key(0, ch) for ch in "Arcano 2"] + [key(pygame.K_RETURN)])
    check(ed.name == "arcano_2" and not ed.editing_name, "El nombre se escribe con el teclado")
    for cid in ["magic"] * 4 + ["fire_bolt", "flame", "flame", "guard", "guard", "break"]:
        click(app, ("deck", "catalog", cid))
    shot(app, "4_mazo_nuevo")
    click(app, ("deck", "save", None))
    check(store.kind("arcano_2") == "propio" and not ed.dirty, "GUARDAR crea un mazo propio")
    click(app, ("deck", "select", "duelo"))
    click(app, ("deck", "restore", None))
    check(store.get("duelo") == BUILTIN_DECKS["duelo"], "RESTAURAR devuelve el mazo de fábrica")

    # --- Volver y jugar con el mazo nuevo --------------------------------------------------
    app.step(DT, [key(pygame.K_ESCAPE)])
    check(app.mode == "menu", "ESC vuelve al menú")
    while app.menu.choice[0] != "arcano_2":
        app.menu.cycle(0, 1)
    shot(app, "5_menu_con_mazo_propio")
    app.step(DT, [key(pygame.K_RETURN)])
    e = app.engine
    check(app.mode == "battle" and e.players[0].deck is not None, "ENTER empieza la partida")
    check([p.character.id for p in e.players] == ["hero", "hero"], "La partida usa los personajes elegidos")
    for _ in range(200):
        app.step(DT, [])
        if e.phase == Phase.REDRAW:
            break
    ids = {c.id for c in e.players[0].hand} | {c.id for c in e.players[0].deck.draw_pile}
    check(ids <= {"magic", "fire_bolt", "flame", "guard", "break"}, "J1 juega con su mazo editado")
    shot(app, "6_partida_con_mazo_propio")
    app.draw()
    chip = pygame.Rect(20, 136, 310, 24)
    app.step(DT, [pygame.event.Event(pygame.MOUSEMOTION, pos=chip.center, rel=(0, 0), buttons=(0, 0, 0))])
    shot(app, "6b_ficha_de_personaje")
    e.players[1].hp = 0
    e.sm.phase = Phase.TURN_END
    e.advance()
    app.step(DT, [])
    check(e.phase == Phase.GAME_OVER, "Fin de partida")
    shot(app, "7_fin_con_boton_menu")
    click(app, (None, "menu"))
    check(app.mode == "menu", "Botón MENÚ / MAZOS al terminar la partida")
    check(app.menu.character == ["hero", "hero"], "El menú recuerda los personajes elegidos")
    app.step(DT, [key(pygame.K_ESCAPE)])
    check(not app.running, "ESC en el menú sale del juego")


if __name__ == "__main__":
    main()
