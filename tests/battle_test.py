"""Prueba automática de la unión exploración + combate de cartas (sin ventana).

    python tests/battle_test.py            # solo comprobaciones
    python tests/battle_test.py --shots    # además guarda capturas en tests/shots/

Juega combates de verdad: el jugador 1 lo maneja un bot que pulsa las mismas
teclas que una persona (1-5, ESPACIO, ENTER) y el enemigo, la IA del juego.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke_test import DT, Bot, key_event  # noqa: E402  (configura SDL sin ventana)

import pygame  # noqa: E402

from combate.game.state_machine import Phase  # noqa: E402
from game import settings  # noqa: E402

settings.START_MAP = "forest"               # los enemigos de esta prueba están en el bosque

CARD_KEYS = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]


def teleport(b, x, y):
    b.g.player.x, b.g.player.y = float(x), float(y)
    b.g.camera.snap_to(x, y)


def next_to(b, enemy):
    """Justo encima o debajo del enemigo (sin cofres ni árboles en medio)."""
    teleport(b, enemy.x, enemy.y + (-28 if enemy.y > 1500 else 28))


def wait_battle(b, frames=240):
    for _ in range(frames):
        if b.g.battle is not None:
            return True
        if b.g.dialogue.is_open:
            b.close_dialogue()
        b.tick()
    return b.g.battle is not None


def approach(b, enemy):
    """Camina hacia el enemigo hasta que empieza el combate."""
    g = b.g
    for _ in range(900):
        if g.battle is not None or g._pending_battle is not None or g.dialogue.is_open:
            break
        d = pygame.Vector2(enemy.x - g.player.x, enemy.y - g.player.y)
        g.input.move_override = d.normalize() if d.length() > 1 else (0, 0)
        b.tick()
    g.input.move_override = None
    return wait_battle(b)


def play_battle(b, max_frames=40000):
    """El jugador 1 juega con el teclado, como una persona: primera carta jugable
    (tecla 1-5) o PASS (ESPACIO), y ENTER para confirmar."""
    g = b.g
    e = g.battle.engine
    for _ in range(max_frames):
        if g.battle is None or e.phase == Phase.GAME_OVER:
            break
        events = []
        if e.phase == Phase.REDRAW and not e.redraw_done[0]:
            events = [key_event(pygame.K_RETURN)]          # sin cambios
        elif e.phase == Phase.CARD_SELECTION and not e.confirmed[0]:
            if e.selection[0] is None:
                if e.status_choices(0):                     # FREEZE: 1 = BREAK ICE
                    events = [key_event(pygame.K_1)]
                else:
                    playable = e.playable_cards(0)
                    hand = e.players[0].hand
                    events = [key_event(CARD_KEYS[hand.index(playable[0])]) if playable
                              else key_event(pygame.K_SPACE)]
            else:
                events = [key_event(pygame.K_RETURN)]
        g.step(DT * 3, events)
    g.draw()
    return e


def main():
    b = Bot()
    g = b.g
    b.tick(60)
    lobo = g.world.get_interactable("lobo_camino")
    b.check(lobo is not None and lobo.can_interact(), "Hay un lobo en el camino del bosque")
    lobo_home = (lobo.x, lobo.y)
    b.tick(180)
    b.check((lobo.x, lobo.y) != lobo_home, "El lobo deambula por su cuenta")

    # --- 1. Encuentro al tocarlo ----------------------------------------------
    teleport(b, lobo.x - 120, lobo.y)
    b.check(approach(b, lobo), "Tocar al enemigo abre el combate de cartas")
    scene = g.battle
    e = scene.engine
    b.check(e.players[1].name == "LOBO GRIS" and e.players[1].hp == 50, "El enemigo usa sus datos del mapa (nombre, 50 HP)")
    b.check(e.players[0].character is not None and e.players[0].character.id == "hero", "El jugador lleva su personaje (Hero)")
    b.tick(60)
    b.shot("b01_combate_inicio")

    # La mano del enemigo no responde a las teclas del jugador 2
    for _ in range(400):
        if e.phase == Phase.CARD_SELECTION:
            break
        g.step(DT, [key_event(pygame.K_RETURN)] if e.phase == Phase.REDRAW and not e.redraw_done[0] else [])
    b.check(e.phase == Phase.CARD_SELECTION, "Se llega a la selección de cartas")
    scene._ai_timer = -999                      # la IA espera mientras probamos
    before = (e.selection[1], e.confirmed[1])
    g.step(DT, [key_event(pygame.K_q), key_event(pygame.K_w), key_event(pygame.K_LSHIFT)])
    b.check((e.selection[1], e.confirmed[1]) == before, "Las teclas del jugador 2 no controlan al enemigo")
    g.step(DT, [key_event(pygame.K_TAB)])
    phase, t = e.phase, scene.view.phase_time
    for _ in range(90):
        g.step(DT, [key_event(CARD_KEYS[0])])
    b.check(scene.log_open and e.phase == phase and scene.view.phase_time == t and e.selection[0] is None,
            "TAB abre el registro y el combate queda en pausa (las cartas no responden)")
    g.draw()
    b.shot("b02b_registro")
    g.step(DT, [key_event(pygame.K_ESCAPE)])
    b.check(not scene.log_open and g.battle is scene, "ESC cierra el registro (sin huir)")
    scene._ai_timer = 0.0
    first = e.players[0].hand.index(e.playable_cards(0)[0])
    g.step(DT, [key_event(CARD_KEYS[first])])
    b.check(e.selection[0] is not None, f"La tecla {first + 1} elige carta para el jugador")
    b.shot("b02_seleccion")

    # --- 2. Partida completa -----------------------------------------------------
    e = play_battle(b)
    b.check(e.phase == Phase.GAME_OVER, f"El combate termina (turnos: {e.turn}, ganador: {e.winner})")
    b.shot("b03_fin_combate")
    winner = e.winner
    b.tick(1, [key_event(pygame.K_RETURN)])
    b.tick(2)
    b.check(g.battle is None, "CONTINUAR vuelve al mapa")
    if winner == 0:
        b.close_dialogue()
        b.check(lobo.defeated and not lobo.visible, "Victoria: el lobo desaparece del mapa")
    elif winner == 1:
        b.check(not lobo.defeated and g.world.get_interactable("lobo_camino") is not lobo,
                "Derrota: vuelves a la entrada y el lobo sigue ahí")
    else:
        b.check(not lobo.defeated, "Empate: el lobo sigue ahí")
    b.tick(60)
    b.shot("b04_vuelta_al_mapa")

    # --- 3. Huir con ESC ---------------------------------------------------------
    seta = g.world.get_interactable("seta_desvio")
    teleport(b, 1300, 1530)
    b.check(approach(b, seta), "Encuentro con la seta venenosa")
    b.tick(30)
    b.tick(1, [key_event(pygame.K_ESCAPE)])
    b.tick(2)
    b.check(g.battle is None and g.running and not seta.defeated, "ESC huye del combate (el juego sigue)")
    b.check(seta.cooldown > 0, "Tras huir, el enemigo tarda en volver a atacar")
    x0 = g.player.x
    g.input.move_override = (-1, 0)
    b.tick(30)
    g.input.move_override = None
    b.check(g.player.x < x0, "Puedes moverte nada más huir")

    # --- 4. Derrota --------------------------------------------------------------
    b.tick(int(3.2 / DT))                       # se acaba el respiro
    next_to(b, seta)
    b.check(approach(b, seta), "La seta vuelve a atacar")
    g.battle.finish("lose")
    b.tick(3)
    spawn = g.world.spawns["default"]
    b.check(g.battle is None and abs(g.player.x - spawn[0]) < 2 and abs(g.player.y - spawn[1]) < 2,
            "Derrota: reapareces en la entrada de la zona")

    # --- 5. Victoria y persistencia -----------------------------------------------
    seta = g.world.get_interactable("seta_desvio")
    b.tick(int(3.2 / DT))
    next_to(b, seta)
    b.check(approach(b, seta), "Otro encuentro con la seta")
    g.battle.finish("win")
    b.tick(3)
    b.close_dialogue()
    b.check(seta.defeated and not seta.visible, "Victoria: la seta desaparece")
    alfa = g.world.get_interactable("lobo_este")
    teleport(b, alfa.x - 260 if alfa.x > 2600 else alfa.x + 260, alfa.y + 60)
    b.check(approach(b, alfa), "El lobo alfa patrulla y te persigue")
    g.battle.finish("win")
    b.tick(3)
    b.close_dialogue()
    b.check(g.state.inventory.has("colmillo"), "El lobo alfa deja su recompensa (colmillo)")
    g.load_map("forest")                        # salir y volver: se recuerda
    b.check(g.world.get_interactable("seta_desvio").defeated, "Los enemigos vencidos siguen vencidos al volver")

    # --- 6. Hablar con E también inicia el combate (con presentación) -------------------
    ancestral = g.world.get_interactable("seta_ancestral") or g.world.get_interactable("seta_ruinas")
    teleport(b, ancestral.x, ancestral.y - 30)
    ancestral.cooldown = 99                     # que no ataque solo: se usa E
    b.tick(2)
    b.check(b.target_id() == "seta_ruinas" and ancestral.get_prompt() == "E - Luchar", "Indicador «E - Luchar»")
    b.press_e()
    b.check(g.dialogue.is_open and g.battle is None, "Primero habla (presentación)")
    b.check(wait_battle(b), "...y después empieza el combate")
    b.shot("b05_combate_seta")
    g.battle.finish("flee")
    b.tick(3)

    print(f"\nCombate integrado OK ({b.ok} comprobaciones).")


if __name__ == "__main__":
    main()
