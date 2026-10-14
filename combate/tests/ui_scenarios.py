"""Reproduce por la UI (teclas reales) los ejemplos del documento de diseño y
comprueba lo que se ve y lo que pasa después.

    python tests/ui_scenarios.py            # comprobaciones
    python tests/ui_scenarios.py --shots    # + capturas en tests/shots/
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))

import pygame  # noqa: E402

from combate.cards.card_database import make_card  # noqa: E402
from combate.game.game import AUTO_DELAYS, App  # noqa: E402
from combate.game.input_map import PLAYER_KEYS  # noqa: E402
from combate.game.state_machine import Phase  # noqa: E402

SHOTS = "--shots" in sys.argv
SHOT_DIR = os.path.join(ROOT, "tests", "shots")
DT = 1 / 60


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def run_until(app, cond, limit=600):
    for _ in range(limit):
        if cond():
            return True
        app.step(DT, [])
    return cond()


def scenario(name, hand1, hand2, pick1, pick2, stable=(True, True), combo=(0, 0)):
    """pick: índice de carta o "PASS". Devuelve (app, resultado, fase siguiente)."""
    app = App(seed=1)
    e = app.engine
    run_until(app, lambda: e.phase == Phase.REDRAW)
    for p, ids in zip(e.players, (hand1, hand2)):
        p.hand = [make_card(c) for c in ids]
    e.players[0].stable, e.players[1].stable = stable
    e.players[0].combo_hits, e.players[1].combo_hits = combo
    app.step(DT, [key(PLAYER_KEYS[0]["confirm"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION)
    for i, pick in enumerate((pick1, pick2)):
        k = PLAYER_KEYS[i]["pass"][0] if pick == "PASS" else PLAYER_KEYS[i]["cards"][pick]
        app.step(DT, [key(k), key(PLAYER_KEYS[i]["confirm"][0])])
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    result = e.result
    if SHOTS:
        os.makedirs(SHOT_DIR, exist_ok=True)
        app.draw()
        pygame.image.save(app.screen, os.path.join(SHOT_DIR, f"caso_{name}.png"))
    stab_after = [p.stable for p in e.players]
    scenario.hp_at_resolution = [p.hp for p in e.players]
    scenario.combo_at_resolution = [p.combo_hits for p in e.players]
    if result.mega_combo is not None:          # captura aparte del Mega Combo
        run_until(app, lambda: e.phase == Phase.MEGA_COMBO and app.view.phase_time > 0.6, limit=200)
        scenario.hp_at_mega = [p.hp for p in e.players]
        scenario.combo_at_mega = [p.combo_hits for p in e.players]
        if SHOTS:
            app.draw()
            pygame.image.save(app.screen, os.path.join(SHOT_DIR, f"caso_{name}_b_mega.png"))
    run_until(app, lambda: e.phase not in (Phase.CARD_RESOLUTION, Phase.MEGA_COMBO),
              limit=int((AUTO_DELAYS[Phase.CARD_RESOLUTION] + AUTO_DELAYS[Phase.MEGA_COMBO]) * 60) + 30)
    run_until(app, lambda: e.phase not in (Phase.INTERACTION_START,), limit=60)
    return app, result, stab_after, e.phase


def check(cond, label):
    print(f"[{'OK ' if cond else 'FALLO'}] {label}")
    if not cond:
        raise SystemExit(1)


def main():
    # Ejemplo 1: ATTACK vs GUARD
    app, r, st, nxt = scenario("1_attack_vs_guard", ["attack", "guard"], ["guard", "guard"], 0, 0)
    check(r.winner == 1 and r.lines[0] == "GUARD > ATTACK", "Guard vence a Attack")
    check(st[0] is True, "Guard normal NO desestabiliza (J1 sigue STABLE)")
    check(r.hit_generated == 0, "Guard no genera hit")
    check(nxt == Phase.CARD_SELECTION, "Attack tenía iniciativa: vuelve a elegir carta sin preguntar")

    # Ejemplo 2: ATTACK vs PERFECT GUARD
    app, r, st, nxt = scenario("2_attack_vs_perfect_guard", ["attack", "guard"], ["perfect_guard", "guard"], 0, 0)
    check(r.winner == 1 and st[0] is False, "Perfect Guard gana y desestabiliza (J1 -> UNSTABLE)")
    check(any(c.startswith("PLAYER 1 -> UNSTABLE") for c in r.consequences), "La UI lo explica: PLAYER 1 -> UNSTABLE")
    check(nxt == Phase.CARD_SELECTION, "Sigue (por la iniciativa de Attack)")

    # Ejemplo 3: BREAK vs UNBREAKABLE GUARD
    app, r, st, nxt = scenario("3_break_vs_unbreakable", ["break", "guard"], ["unbreakable_guard", "guard"], 0, 0)
    check(r.winner == 1 and r.lines[0] == "UNBREAKABLE GUARD > BREAK", "Unbreakable Guard vence a Break")
    check(st[0] is True and r.hit_generated == 0, "Sin desestabilizar y sin hit")

    # Ejemplo 4: ATTACK vs ATTACK, ambos STABLE
    app, r, st, nxt = scenario("4_attack_vs_attack_draw", ["attack", "guard"], ["attack", "guard"], 0, 0)
    check(r.outcome == "draw" and nxt == Phase.CARD_SELECTION, "Empate y nueva interacción")

    # Ejemplo 5: ATTACK vs ATTACK, J1 STABLE / J2 UNSTABLE
    app, r, st, nxt = scenario("5_attack_vs_attack_stability", ["attack", "guard"], ["attack", "guard"], 0, 0,
                               stable=(True, False))
    check(r.winner == 0 and r.decided_by == "stability" and r.hit_generated == 1, "Gana J1 por Stability con hit")
    check(nxt == Phase.CARD_SELECTION, "Ambos con iniciativa: sigue")

    # Ejemplo 6: GUARD vs PASS
    app, r, st, nxt = scenario("6_guard_vs_pass", ["guard", "attack"], ["attack", "guard"], 0, "PASS")
    check(r.continues is False, "Guard + Pass: nadie tiene iniciativa")
    check(nxt in (Phase.TURN_END, Phase.TURN_START, Phase.DRAW, Phase.REDRAW), "El turno termina")

    # Guard + Guard
    app, r, st, nxt = scenario("7_guard_vs_guard", ["guard", "attack"], ["perfect_guard", "attack"], 0, 0)
    check(r.continues is False and nxt != Phase.CARD_SELECTION, "Guard + Perfect Guard: fin del turno")

    # Daño normal al resolver
    app, r, st, nxt = scenario("8_attack_vs_break_damage", ["attack", "guard"], ["break", "guard"], 0, 0)
    check(scenario.hp_at_resolution[1] == 90, "ATTACK > BREAK: J2 -10 HP ya visible en la resolución")
    check(scenario.combo_at_resolution[0] == 1, "J1 +1 hit de combo")

    # Tercer hit: daño normal + Mega Combo como dos momentos distintos
    app, r, st, nxt = scenario("9_tercer_hit", ["attack", "guard"], ["break", "guard"], 0, 0, combo=(2, 0))
    check(scenario.hp_at_resolution[1] == 90 and scenario.combo_at_resolution[0] == 3,
          "Resolución: -10 HP y combo 3/3")
    check(scenario.hp_at_mega[1] == 70 and scenario.combo_at_mega[0] == 0,
          "Fase MEGA COMBO aparte: -20 HP adicionales y combo 0")
    check([d.kind for d in r.damage_events] == ["interaction", "mega_combo"], "Dos eventos de daño separados")
    check(nxt == Phase.CARD_SELECTION, "Después sigue por iniciativa")

    # Stability definitiva
    app, r, st, nxt = scenario("10_unstable_sin_hit_recupera", ["attack", "guard"], ["guard", "guard"], 0, 0,
                               stable=(False, True))
    check(st == [True, True], "J1 UNSTABLE no recibe hit (Guard gana) -> recupera STABLE")
    app, r, st, nxt = scenario("11_unstable_recibe_hit", ["attack", "guard"], ["break", "guard"], 0, 0,
                               stable=(True, False))
    check(st == [True, False], "J2 UNSTABLE recibe hit -> sigue UNSTABLE")
    app, r, st, nxt = scenario("12_guard_guard_empate", ["guard", "attack"], ["guard", "attack"], 0, 0,
                               stable=(True, False))
    check(r.outcome == "draw" and st == [True, True], "GUARD = GUARD (STABLE vs UNSTABLE): empate, ambos STABLE")
    app, r, st, nxt = scenario("13_unstable_unstable_empate", ["attack", "guard"], ["attack", "guard"], 0, 0,
                               stable=(False, False))
    check(r.outcome == "draw" and st == [True, True], "ATTACK = ATTACK ambos UNSTABLE: empate, ambos STABLE")

    # Mana: 1ª interacción gratis, 2ª cuesta 1, PASS gratis, sin delatar antes del REVEAL
    for m0, name in ((3, "14_mana_segunda_interaccion"), (0, "15_mana_cero")):
        app = App(seed=1)
        e = app.engine
        run_until(app, lambda: e.phase == Phase.REDRAW)
        e.players[0].hand = [make_card(c) for c in ("attack", "attack", "guard", "break")]
        e.players[1].hand = [make_card(c) for c in ("attack", "attack", "guard", "break")]
        app.step(DT, [key(PLAYER_KEYS[0]["confirm"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
        run_until(app, lambda: e.phase == Phase.CARD_SELECTION)
        e.players[0].mana = m0
        if SHOTS and m0 == 3:
            os.makedirs(SHOT_DIR, exist_ok=True)
            app.draw()
            pygame.image.save(app.screen, os.path.join(SHOT_DIR, "caso_14a_mana_primera_gratis.png"))
        for i in range(2):                          # 1ª: ATTACK vs ATTACK (gratis, empate, sigue)
            app.step(DT, [key(PLAYER_KEYS[i]["cards"][0]), key(PLAYER_KEYS[i]["confirm"][0])])
        check([p.mana for p in e.players] == [m0, 3], f"Interacción 1 gratis (J1 con {m0} Mana)")
        run_until(app, lambda: e.phase == Phase.CARD_SELECTION and e.interaction_number == 2, limit=400)
        if SHOTS:
            app.draw()
            pygame.image.save(app.screen, os.path.join(SHOT_DIR, f"caso_{name}.png"))
        if m0 == 3:
            app.step(DT, [key(PLAYER_KEYS[0]["cards"][1]), key(PLAYER_KEYS[0]["confirm"][0])])
            check(e.players[0].mana == 2 and e.displayed_mana(0) == 3,
                  "Interacción 2: J1 paga 1 al confirmar, pero el HUD no lo delata")
            app.step(DT, [key(PLAYER_KEYS[1]["pass"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
            check(e.displayed_mana(0) == 2 and e.players[1].mana == 3, "REVEAL: se ve el -1 de J1; el PASS de J2 es gratis")
        else:
            check(e.selection[0] == "PASS" and e.confirmed[0], "Con 0 Mana: PASS automático")

    # SPECIAL: RECOVER + ATTACK con J1 UNSTABLE contra ATTACK -> se resuelve STABLE vs STABLE
    app = App(seed=1)
    e = app.engine
    run_until(app, lambda: e.phase == Phase.REDRAW)
    e.players[0].hand = [make_card(c) for c in ("attack", "recover", "guard")]
    e.players[1].hand = [make_card(c) for c in ("attack", "guard", "break")]
    e.players[0].stable = False
    app.step(DT, [key(PLAYER_KEYS[0]["confirm"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION)
    app.step(DT, [key(PLAYER_KEYS[0]["cards"][1])])        # tecla 2: RECOVER como SPECIAL
    app.step(DT, [key(PLAYER_KEYS[0]["cards"][0])])        # tecla 1: ATTACK como acción principal
    if SHOTS:
        app.draw()
        pygame.image.save(app.screen, os.path.join(SHOT_DIR, "caso_16a_recover_seleccion.png"))
    check(e.special_selection[0] is not None and e.selection[0].id == "attack", "Teclas: SPECIAL + acción principal")
    app.step(DT, [key(PLAYER_KEYS[0]["confirm"][0])])
    app.step(DT, [key(PLAYER_KEYS[1]["cards"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
    check(e.players[0].stable, "RECOVER se aplica al revelar, antes del enfrentamiento")
    run_until(app, lambda: e.phase == Phase.CARD_REVEAL and app.view.phase_time > 0.5)
    if SHOTS:
        app.draw()
        pygame.image.save(app.screen, os.path.join(SHOT_DIR, "caso_16b_recover_reveal.png"))
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    if SHOTS:
        app.draw()
        pygame.image.save(app.screen, os.path.join(SHOT_DIR, "caso_16c_recover_resolucion.png"))
    check(e.result.outcome == "draw", "ATTACK = ATTACK con ambos STABLE: empate")
    check(e.result.mana_paid[0] == 1, "RECOVER cuesta 1 aunque ATTACK sea gratis en la 1ª")

    status_scenarios()
    magic_scenarios()
    style_scenarios()

    print("\nTodos los escenarios OK. Nunca aparece una pregunta de continuar.")
    pygame.quit()


def shot(app, name):
    if SHOTS:
        os.makedirs(SHOT_DIR, exist_ok=True)
        app.draw()
        pygame.image.save(app.screen, os.path.join(SHOT_DIR, f"estado_{name}.png"))


def status_app(hand1, hand2, mana=(5, 5)):
    app = App(seed=1)
    e = app.engine
    run_until(app, lambda: e.phase == Phase.REDRAW)
    for p, ids in zip(e.players, (hand1, hand2)):
        p.hand = [make_card(c) for c in ids]
    for p, m in zip(e.players, mana):
        p.mana = m
    app.step(DT, [key(PLAYER_KEYS[0]["confirm"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION)
    return app, e


def press(app, i, kind, index=None):
    k = PLAYER_KEYS[i][kind][index] if index is not None else PLAYER_KEYS[i][kind][0]
    app.step(DT, [key(k)])


def status_scenarios():
    from combate.game.status import BREAK_ICE, StatusId

    # FREEZE: Frost Guard vence a ATTACK -> J1 en un ICE CUBE
    app, e = status_app(["attack", "attack", "recover"], ["frost_guard", "attack", "attack"])
    press(app, 0, "cards", 0); press(app, 0, "confirm")
    press(app, 1, "cards", 0); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    shot(app, "1_freeze_aplicado")
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION, limit=400)
    check(e.players[0].has_status(StatusId.FREEZE) and e.players[0].status.cube_hp == 30, "FREEZE: ICE CUBE 30/30")
    app.step(DT, [])
    shot(app, "2_freeze_seleccion")
    app.draw()                                      # los botones se crean al dibujar
    buttons = [a for _, a in app.buttons if a[1] == "status"]
    check(buttons == [(0, "status", "BREAK_ICE"), (0, "status", "WAIT")], "La UI ofrece BREAK ICE y WAIT")
    press(app, 0, "cards", 2)                       # tecla 3: no hay tercera opción
    check(e.selection[0] is None, "Las teclas de carta no eligen cartas estando congelado")
    press(app, 0, "cards", 0); press(app, 0, "confirm")
    check(e.selection[0] == BREAK_ICE and e.confirmed[0], "Tecla 1: BREAK ICE")
    press(app, 1, "cards", 0); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    shot(app, "3_freeze_break_ice")
    check(e.players[0].hp == 100 and e.players[0].status.cube_hp == 5, "ATTACK -10 y BREAK ICE -15 al cubo; HP intacto")

    # PARALYZE: Stun Guard vence a ATTACK -> J1 PASS obligatorio
    app, e = status_app(["attack", "attack", "recover"], ["stun_guard", "attack", "guard"])
    press(app, 0, "cards", 0); press(app, 0, "confirm")
    press(app, 1, "cards", 0); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION, limit=400)
    app.step(DT, [])
    shot(app, "4_paralyze_pass_obligatorio")
    check(e.confirmed[0] and e.selection[0] == "PASS", "PARALYZED: PASS automático")
    press(app, 0, "cards", 0)
    check(e.selection[0] == "PASS", "Las teclas no cambian el PASS obligatorio")
    press(app, 1, "cards", 1); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    shot(app, "5_paralyze_resolucion")
    check(e.players[0].status is None, "PARALYZE termina tras la interacción")

    # BURN, POISON y SLEEP: paneles, inicio de turno y daño periódico
    app, e = status_app(["guard"], ["guard"])
    e.apply_status(0, StatusId.BURN)
    e.apply_status(1, StatusId.POISON)
    press(app, 0, "pass"); press(app, 0, "confirm")
    press(app, 1, "pass"); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.DRAW and app.view.phase_time > 0.3, limit=600)
    shot(app, "6_burn_inicio_turno")
    check(e.players[0].hp == 95, "BURN: -5 HP al empezar el turno")
    run_until(app, lambda: e.phase == Phase.REDRAW, limit=600)
    app.step(DT, [key(PLAYER_KEYS[0]["confirm"][0]), key(PLAYER_KEYS[1]["confirm"][0])])
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION, limit=600)
    check(e.players[1].hp == 97, "POISON: -3 HP al empezar la interacción")
    e.apply_status(0, StatusId.SLEEP)
    app.step(DT, [])
    shot(app, "7_sleep_y_poison")
    check(e.players[0].has_status(StatusId.SLEEP), "BURN -> SLEEP (reemplazo)")



def magic_scenarios():
    from combate.game.status import StatusId

    # FLAME + FIRE BOLT (MAGIC) vence a BREAK: daño mágico y BURN por el efecto de FLAME
    app, e = status_app(["fire_bolt", "flame", "magic"], ["break", "guard", "attack"])
    app.step(DT, [])
    shot(app, "8_magic_mano")
    press(app, 0, "cards", 1)                       # tecla 2: FLAME como SPECIAL
    press(app, 0, "cards", 0); press(app, 0, "confirm")
    press(app, 1, "cards", 0); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    shot(app, "9_magic_flame_resolucion")
    r = e.result
    check(r.lines[0] == "FIRE BOLT > BREAK" and r.winner == 0, "MAGIC vence a BREAK")
    check("PLAYER 2 -10 HP (MAGIC · FIRE)" in r.consequences, "La UI distingue el daño mágico")
    check(e.players[1].has_status(StatusId.BURN), "FLAME + MAGIC ganadora: BURN")

    # GUARD vence a MAGIC
    app, e = status_app(["magic", "guard"], ["guard", "guard"])
    press(app, 0, "cards", 0); press(app, 0, "confirm")
    press(app, 1, "cards", 0); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    check(e.result.lines[0] == "GUARD > MAGIC" and e.result.winner == 1, "GUARD vence a MAGIC")


def style_scenarios():
    # J1 en rango S usa su DEFINITIVA (ATTACK) con la tecla 6; J2 juega BREAK
    app, e = status_app(["guard", "guard"], ["break", "guard"])
    e.players[0].style.points, e.players[1].style.points = 320, 30
    app.step(DT, [])
    app.draw()
    check(any(a == (0, "ultimate", "ATTACK") for _, a in app.buttons), "J1 en S ve el selector de DEFINITIVA")
    check(not any(a[:2] == (1, "ultimate") for _, a in app.buttons), "J2 (rango B) no lo ve")
    shot(app, "10_definitiva_seleccion")
    press(app, 0, "ultimate")
    check(e.ultimate_pick[0] == "ATTACK" and e.selection[0].is_ultimate, "Tecla 6: definitiva ATTACK")
    press(app, 0, "confirm")
    press(app, 1, "cards", 0); press(app, 1, "confirm")
    run_until(app, lambda: e.phase == Phase.CARD_RESOLUTION and app.view.phase_time > 0.6)
    shot(app, "11_definitiva_resolucion")
    r = e.result
    check(r.ultimates == ("ATTACK", None) and r.winner == 0, "La definitiva ATTACK vence a BREAK como un ATTACK normal")
    check(e.players[0].style.ultimate_used and len(e.players[0].hand) == 2, "Usada; no gasta cartas de la mano")
    check([c.delta for c in r.style_changes] == [3, -30], "Estilo: J1 +3 (1ª victoria), J2 -30 (derrota en B)")
    run_until(app, lambda: e.phase == Phase.CARD_SELECTION, limit=400)
    app.step(DT, [])
    app.draw()
    check(not any(a[:2] == (0, "ultimate") for _, a in app.buttons), "Ya usada: el selector desaparece")
    shot(app, "12_definitiva_usada")


if __name__ == "__main__":
    main()
