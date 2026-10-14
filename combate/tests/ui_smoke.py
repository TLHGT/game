"""Juega una partida completa a través de la UI (teclas simuladas, sin ventana).

    python tests/ui_smoke.py            # comprueba que no hay errores
    python tests/ui_smoke.py --shots    # guarda capturas en tests/shots/
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))

import pygame  # noqa: E402

from combate.game.game import App  # noqa: E402
from combate.game.input_map import PLAYER_KEYS  # noqa: E402
from combate.game.state_machine import Phase  # noqa: E402

SHOTS = "--shots" in sys.argv
SHOT_DIR = os.path.join(ROOT, "tests", "shots")
DT = 1 / 60


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def main():
    app = App(seed=11)
    taken, seen = set(), set()
    frames = 0
    interactions = 0
    turn_ends_checked = 0
    megas = 0

    def shot(name):
        if SHOTS and name not in taken:
            taken.add(name)
            os.makedirs(SHOT_DIR, exist_ok=True)
            app.draw()
            pygame.image.save(app.screen, os.path.join(SHOT_DIR, f"smoke_{len(taken):02d}_{name}.png"))

    def tick(events=()):
        nonlocal frames
        app.step(DT, list(events))
        frames += 1

    last_result = None
    while app.engine.phase != Phase.GAME_OVER and frames < 60 * 60 * 30:
        e = app.engine
        phase = e.phase
        seen.add(phase)
        if e.result is not None and e.result is not last_result and phase == Phase.CARD_RESOLUTION:
            last_result = e.result
            interactions += 1
        if phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.5:
            shot(f"resolucion_{e.result.decided_by}")
        if phase == Phase.MEGA_COMBO and app.view.phase_time > 0.5:
            shot("mega_combo")
        if e.sm.is_auto:
            before = e.phase
            tick()
            # Tras resolver: Mega Combo si alguien llegó a 3; luego la regla de iniciativa
            r = last_result
            alive = all(p.alive for p in e.players)
            if before == Phase.CARD_RESOLUTION and e.phase != before and alive:
                if r.mega_combo is not None:
                    assert e.phase == Phase.MEGA_COMBO, e.phase
                    assert all(p.combo_hits == 0 for p in e.players), "Combo a 0 tras el Mega Combo"
                    megas += 1
                elif r.continues:
                    assert e.phase in (Phase.INTERACTION_START, Phase.CARD_SELECTION), e.phase
                else:
                    assert e.phase == Phase.TURN_END, e.phase
                    turn_ends_checked += 1
            if before == Phase.MEGA_COMBO and e.phase != before and alive:
                expected = (Phase.INTERACTION_START, Phase.CARD_SELECTION) if r.continues else (Phase.TURN_END,)
                assert e.phase in expected, e.phase
            continue
        evs = []
        if phase == Phase.REDRAW:
            shot("cambios")
            if e.turn == 1 and e.players[0].redraws_left == 2:
                evs.append(key(PLAYER_KEYS[0]["cards"][0]))
            else:
                evs += [key(PLAYER_KEYS[0]["confirm"][0]), key(PLAYER_KEYS[1]["confirm"][0])]
        elif phase == Phase.CARD_SELECTION:
            for i, p in enumerate(e.players):
                if e.confirmed[i]:
                    continue
                order = ["ATTACK", "GUARD", "BREAK"] if i == 0 else ["BREAK", "GUARD", "ATTACK"]
                shift = (e.turn + e.interaction_number) % 3
                order = order[shift:] + order[:shift]
                playable = [k for k, c in enumerate(p.hand) if not c.is_special and e.can_play(i, c)]
                pick = next((k for t in order for k in playable if p.hand[k].card_type == t), None)
                if pick is None or (i == 1 and e.turn % 4 == 0 and e.interaction_number == 1):
                    tick([key(PLAYER_KEYS[i]["pass"][0])])
                else:
                    tick([key(PLAYER_KEYS[i]["cards"][pick])])
                if i == 0:
                    shot("seleccion_oculta")
                tick([key(PLAYER_KEYS[i]["confirm"][0])])
            continue
        tick(evs)

    shot("game_over")
    e = app.engine
    assert e.phase == Phase.GAME_OVER, f"La partida no terminó (fase {e.phase})"
    expected = {Phase.REDRAW, Phase.CARD_SELECTION, Phase.CARD_REVEAL, Phase.CARD_RESOLUTION,
                Phase.MEGA_COMBO, Phase.TURN_END}
    print(f"Partida terminada en el turno {e.turn} tras {interactions} interacciones: "
          f"gana {e.players[e.winner].name} ({e.players[0].hp} - {e.players[1].hp} HP), {frames / 60:.0f} s simulados")
    print("Fases no vistas:", [p.value for p in expected - seen] or "ninguna")
    print(f"Fines de turno por falta de iniciativa comprobados: {turn_ends_checked} · Mega Combos: {megas}")
    tick([key(pygame.K_r)])
    assert app.engine.phase != Phase.GAME_OVER and app.engine.turn == 1, "R reinicia la partida"
    print("Revancha OK")
    pygame.quit()


if __name__ == "__main__":
    main()
