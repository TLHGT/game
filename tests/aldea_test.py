"""Juega automáticamente la Aldea del vacío de principio a fin.

    python tests/aldea_test.py            # solo comprobaciones
    python tests/aldea_test.py --shots    # además guarda capturas en tests/shots/

Recorrido: fase 1 (diarios y el reloj de la plaza, con un error que lo apaga) ->
fase 2 (almas a los círculos, con un alma equivocada) -> fase 3 (partes del
insecto, yunque, plataformas saltando con Hero, barrera) -> Void Insect -> fase 4.
Además prueba los easter eggs (peluches, pollo y semillas, pozo), que siempre se
puede llegar a ellos en todas las fases y que el sorteo cambia en cada partida.
Los combates se dan por ganados (el combate se prueba en combate/tests/test_aldea.py).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke_test import Bot  # noqa: E402  (configura SDL sin ventana)

from game import settings  # noqa: E402
from pathing import go, reachable  # noqa: E402

settings.use_village()
settings.DECKS_PATH = os.path.join(tempfile.mkdtemp(), "decks_aldea.json")   # no toca los mazos del usuario
settings.VILLAGE_SEED = 11

from entities.chest import CARD_PREFIX  # noqa: E402
from entities.enemy import Enemy  # noqa: E402
from systems import village_quest as Q  # noqa: E402
from systems.game_state import GameState  # noqa: E402


def front(b, obj_id, dy=24):
    """Va delante (debajo) de un objeto y lo mira."""
    it = b.g.world.get_interactable(obj_id)
    r = it.rect
    go(b, (r.centerx, r.bottom + dy))
    b.g.player.facing = "up"
    b.tick(2)
    return it


def use(b, obj_id, dy=24):
    front(b, obj_id, dy)
    b.check(b.target_id() == obj_id, f"Delante de «{obj_id}»" + ("" if b.target_id() == obj_id else
            f" (objetivo: {b.target_id()}, jugador en {round(b.g.player.x)}, {round(b.g.player.y)})"))
    b.press_e()
    text = dialogue_text(b.g)
    b.close_dialogue()
    return text


def dialogue_text(g):
    return " ".join(" ".join(lines) for lines in g.dialogue.pages)


def calm_enemies(b, seconds=9999):
    """Los aldeanos no molestan mientras se prueba otra cosa (los combates se fuerzan aparte)."""
    for it in b.g.world.all_interactables:
        if isinstance(it, Enemy):
            it.cooldown = seconds


def win_against(b, enemy):
    """Combate ganado contra `enemy` (lo revive antes si estaba vencido: como su respawn)."""
    enemy.defeated = False
    enemy._apply_defeated()
    enemy.visible = True
    b.g.start_battle(enemy)
    b.resolve_encounter("win")
    calm_enemies(b)


def park_villagers(b):
    """Quita a los aldeanos de en medio (vencidos y sin volver) para probar los easter eggs."""
    for it in b.g.world.all_interactables:
        if isinstance(it, Enemy):
            it.defeated = True
            it.respawn_left = 1e9
            it._apply_defeated()


def hold_still(b):
    """El pollo deja de pasear un rato (para que el bot pueda cogerlo)."""
    chicken = b.g.world.get_interactable("pollo")
    chicken._target, chicken._wait = None, 999


def point(b, obj_id):
    it = b.g.world.get_interactable(obj_id)
    return (it.rect.centerx, it.rect.bottom + 24)


def easter_eggs_reachable(b, phase):
    """Casas, barriles, pozos y gallinero se alcanzan andando desde la entrada."""
    w = b.g.world
    start = w.spawns["default"]
    targets = [f"barril_{n}" for n in range(1, Q.BARRELS + 1)] + [f"pozo_{n}" for n in range(1, Q.WELLS + 1)]
    targets += [f"casa{n}_peluche" for n in range(1, Q.HOUSES + 1)] + [f"casa{n}_diario" for n in range(1, Q.HOUSES + 1)]
    bad = [t for t in targets if not reachable(w, start, point(b, t))]
    bad += [] if reachable(w, start, (800, 2040)) else ["gallinero"]
    b.check(not bad, f"Fase {phase}: se llega a todos los easter eggs y casas {bad or ''}")


def main():
    b = Bot()
    g = b.g
    quest = g.village
    notes = []                              # todo lo que se notifica (la cola solo enseña uno a la vez)
    notify = g.notify
    g.notify = lambda text, style="info": (notes.append(text), notify(text, style))
    b.tick(60)
    calm_enemies(b)
    b.check(g.world.id == "aldea" and g.world.phase == Q.CLOCKS, "Empieza en la aldea, fase 1 (los relojes)")
    b.check(g.pause.deck == "aldea" and g.store.path.endswith("decks_aldea.json"),
            "La versión aldea tiene su propio mazo (decks_aldea.json)")
    b.check(g.world.ground.get("theme") == "ashes" and {e.kind for e in g.world.forest} == {"dead_tree"},
            "Aldea quemada: suelo de ceniza y árboles muertos")
    b.check("heal" not in g.locked_cards(), "La carta Heal está desbloqueada desde el principio")
    b.check(Q.VOID_CARD in g.locked_cards(), "Void Impact empieza bloqueada")
    b.shot("a01_entrada")

    # --- La estructura de la fase 1: llamas en los tres caminos --------------------
    w = g.world
    start = w.spawns["default"]
    for place, p in (("la granja", (320, 1300)), ("la herrería", (2400, 1300)), ("el mercado", (1400, 900))):
        b.check(not reachable(w, start, p), f"Fase 1: las llamas cierran el paso a {place}")
    b.check(not reachable(w, (1400, 900), (1400, 640)), "No hay rocas flotantes todavía")
    easter_eggs_reachable(b, 1)

    # --- Diarios ---------------------------------------------------------------------
    hours = quest.target_hours
    diaries = [it for it in w.all_interactables if getattr(it, "kind", None) == "diary"]
    for it in diaries:
        it.update(0, g)
    visible = [it for it in diaries if it.visible]
    b.check(len(visible) == 3 and len({it.house for it in visible}) == 3, "Hay 3 diarios en 3 casas distintas")
    read_hours = []
    for it in visible:
        text = use(b, it.id)
        label = next(lbl for lbl in quest.setup["hour_labels"] if lbl in text)
        h = int(label.split(":")[0])
        read_hours.append(12 if h % 12 == 0 else h % 12)
    b.check(sorted(read_hours) == sorted(hours), f"Los diarios dicen las horas {quest.setup['hour_labels']} -> {hours}")
    b.check(Q.hour_label(2, True) == "14:00" and Q.hour_label(9, False) == "9:00" and Q.hour_label(12, True) == "0:00",
            "14:00 es el 2, 9:00 es el 9, 0:00 es el 12")

    # --- El reloj: uno bien, uno mal (se apagan todos), luego los tres -------------
    wrong = next(h for h in range(1, 13) if h not in hours)
    use(b, f"reloj_{hours[0]}")
    b.check(quest.clock_progress == [hours[0]], "Primer activador correcto: 1/3")
    text = use(b, f"reloj_{wrong}")
    b.check(quest.clock_progress == [] and "apagan" in text, "Uno equivocado: se apagan todos")
    for h in reversed(hours):                                  # el orden da igual
        use(b, f"reloj_{h}")
    b.tick(3)
    b.check(quest.phase == Q.SOULS and g.world.phase == Q.SOULS, "Los tres correctos: fase 2 (las almas)")
    b.check(g.world.get_interactable("reloj_1") not in g.world.interactables and
            g.world.get_interactable("llamas_granja") not in g.world.interactables,
            "La plaza y los caminos cambian: sin activadores ni llamas")
    for place, p in (("la granja", (320, 1300)), ("la herrería", (2400, 1300)), ("el mercado", (1400, 900))):
        b.check(reachable(g.world, start, p), f"Fase 2: se puede ir a {place}")
    circles = [it.id for it in g.world.interactables if it.id and it.id.startswith("circulo_")]
    b.check(sorted(circles) == ["circulo_granjero", "circulo_herrero", "circulo_vendedor"],
            "Aparecen los círculos del vacío en la granja, la herrería y el mercado")
    easter_eggs_reachable(b, 2)
    b.shot("a02_almas")

    # --- Almas ----------------------------------------------------------------------
    def villager(trade):
        return next(it for it in g.world.all_interactables if isinstance(it, Enemy) and it.soul == trade)

    text = use(b, "circulo_herrero")
    b.check("0/3" in text and quest.circle_count("herrero") == 0, "Sin alma, el círculo solo espera")
    win_against(b, villager("herrero"))
    b.check(quest.soul == "herrero", "Vencer a un herrero da su alma")
    win_against(b, villager("granjero"))
    b.check(quest.soul == "herrero", "Solo se lleva un alma a la vez")
    use(b, "circulo_herrero")
    b.check(quest.circle_count("herrero") == 1 and quest.soul is None, "Alma de herrero al círculo de la herrería: 1/3")
    win_against(b, villager("vendedor"))
    text = use(b, "circulo_herrero")
    b.check(quest.circle_count("herrero") == 0 and "escapan" in text, "Un alma equivocada: escapan todas las del círculo")
    for trade in Q.TRADES:
        for _ in range(Q.SOULS_PER_CIRCLE):
            win_against(b, villager(trade))
            use(b, f"circulo_{trade}")
    b.tick(3)
    b.check(quest.phase == Q.PORTAL and g.world.phase == Q.PORTAL, "Tres círculos llenos: fase 3 (el portal)")
    b.check(reachable(g.world, (1400, 600), (1400, 640)) and not reachable(g.world, (1400, 900), (1400, 640)),
            "Aparecen rocas flotantes, pero solo se llega a ellas saltando")
    easter_eggs_reachable(b, 3)

    # --- Respawn de los aldeanos -----------------------------------------------------
    h = villager("herrero")
    h.on_defeated(g)
    b.check(h.defeated and h.respawn_left == 40, "Un aldeano vencido vuelve a los 40 s")
    h.respawn_left = 0.01
    g.player.x, g.player.y = start
    b.tick(3)
    b.check(not h.defeated and h.visible, "...y reaparece en su sitio si estás lejos")
    calm_enemies(b)

    # --- La barrera, las partes y el yunque ---------------------------------------------
    g.pause.state.set_flag("combat_character", "hero")
    go(b, (1400, 830))
    use(b, "salto_mercado", dy=10)
    b.tick(60)
    use(b, "salto_p1_p2", dy=10)
    b.tick(60)
    use(b, "salto_p2_p3", dy=10)
    b.tick(60)
    b.check(abs(g.player.y - 250) < 30, "Hero salta de roca en roca hasta el portal")
    insect = g.world.get_interactable("void_insect")
    b.check(not insect.can_interact(), "El insecto está tras la barrera: no se puede luchar")
    text = use(b, "barrera_insecto", dy=10)
    b.check("vacío" in text and g.world.get_interactable("barrera_insecto").visible,
            "Sin Void Impact, la barrera no cede")
    b.shot("a03_barrera")
    use(b, "salto_p3_p2", dy=10)
    b.tick(60)
    use(b, "salto_p2_p1", dy=10)
    b.tick(60)
    use(b, "salto_p1_bajar", dy=10)
    b.tick(60)
    b.check(g.player.y > 760, "Y vuelve a bajar al mercado")

    use(b, "yunque")
    b.check(Q.VOID_CARD in g.locked_cards(), "Sin las partes, el yunque no forja nada")
    parts = [it for it in g.world.interactables if getattr(it, "kind", None) == "part"]
    for it in parts:
        it.update(0, g)
    parts = [it for it in parts if it.visible]
    b.check(len(parts) == 3 and len({it.house for it in parts}) == 3, "Hay 3 partes del insecto en 3 casas")
    for it in parts:
        use(b, it.id)
    b.check(quest.parts_found(g.state.inventory) == 3, "Recoges la pata, el ala y el aguijón")
    use(b, "yunque")
    b.check(Q.VOID_CARD not in g.locked_cards() and quest.parts_found(g.state.inventory) == 0,
            "El yunque forja Void Impact (y gasta las partes): ya se puede usar")

    go(b, (1400, 830))
    for jid in ("salto_mercado", "salto_p1_p2", "salto_p2_p3"):
        use(b, jid, dy=10)
        b.tick(60)
    use(b, "barrera_insecto", dy=10)
    b.tick(3)
    b.check(g.secrets.is_unlocked(Q.BARRIER_SECRET) and not g.world.get_interactable("barrera_insecto").visible,
            "Con Void Impact la barrera estalla")
    b.check(insect.can_interact(), "Ya se puede luchar con el Void Insect")
    b.check(not insect.can_flee, "No se puede huir del Void Insect")
    b.g.start_battle(insect)
    b.resolve_encounter("win")
    b.tick(5)
    b.check(quest.phase == Q.END and g.world.phase == Q.END, "Vencido el insecto: fase 4, el portal se cierra")
    b.check(not any(o.kind in ("flames", "void_portal") for o in g.world.decorations), "Se apagan los fuegos")
    easter_eggs_reachable(b, 4)
    b.shot("a04_fin")
    use(b, "salto_p3_p2", dy=10)
    b.tick(60)
    use(b, "salto_p2_p1", dy=10)
    b.tick(60)
    use(b, "salto_p1_bajar", dy=10)
    b.tick(60)

    # --- Easter egg 1: los peluches ---------------------------------------------------
    park_villagers(b)
    plush = [it for it in g.world.interactables if getattr(it, "kind", None) == "plush"]
    for it in plush:
        it.update(0, g)
    plush = [it for it in plush if it.visible]
    b.check(len(plush) == 3, "3 peluches con aura del vacío en casas al azar")
    for it in plush:
        use(b, it.id)
    b.tick(2)
    b.check(any("Alguien te observa" in t for t in notes),
            "Tocar los tres: «Alguien te observa»")

    # --- Easter egg 2: el pollo y las semillas -----------------------------------------
    seeds = quest.setup["seed_barrels"]
    use(b, f"barril_{seeds[0]}")
    b.check(g.world.get_interactable(f"barril_{seeds[0]}").broken, "Los barriles se rompen")
    other = next(n for n in range(1, Q.BARRELS + 1) if n not in seeds)
    use(b, f"barril_{other}")
    hold_still(b)
    use(b, "pollo", dy=20)
    b.check(quest.chicken == "carried", "Coges al pollo del gallinero")
    use(b, f"barril_{seeds[0]}")
    b.check(quest.seeds_eaten == [seeds[0]], "El pollo se come las semillas (1/3)")
    foe = villager("granjero")
    foe.defeated = False
    foe._apply_defeated()
    foe.visible = True
    b.g.start_battle(foe)
    b.check(quest.chicken == "coop", "Si empieza un combate, el pollo huye al gallinero")
    b.resolve_encounter("win")
    park_villagers(b)
    chicken = g.world.get_interactable("pollo")
    b.check(chicken.home.distance_to((chicken.x, chicken.y)) <= chicken.radius + 2, "...y vuelve al gallinero")
    hold_still(b)
    use(b, "pollo", dy=20)
    for n in seeds[1:]:
        use(b, f"barril_{n}")         # romper
        use(b, f"barril_{n}")         # dar las semillas
    b.tick(5)
    b.check(quest.chicken == "mutated" and chicken.sprite_key == "chicken_humanoid",
            "Con las tres semillas el pollo muta en un pollo humanoide y huye")
    b.tick(400)
    b.check(not chicken.visible, "...y desaparece")

    # --- Easter egg 3: el pozo -----------------------------------------------------------
    special = quest.setup["special_well"]
    normal = next(n for n in range(1, Q.WELLS + 1) if n != special)
    for _ in range(3):
        use(b, f"pozo_{normal}")
    b.check(g._blackout is None, "Los otros pozos no hacen nada")
    for _ in range(3):
        use(b, f"pozo_{special}")
    b.tick(2)
    b.check(g._blackout is not None and g.fade == 1.0, "3 veces el pozo especial: pantalla negra")
    b.tick(200)
    b.check(abs(g.player.x - start[0]) < 2 and abs(g.player.y - start[1]) < 2, "Vuelves al principio de la aldea")
    b.check("Buen intento." in notes, "«Buen intento.»")

    # --- El sorteo cambia en cada partida -------------------------------------------------
    setups = [Q.VillageQuest(GameState()).setup for _ in range(20)]
    b.check(len({tuple(s["hours"]) for s in setups}) > 10 and len({tuple(s["part_houses"]) for s in setups}) > 10
            and len({tuple(s["seed_barrels"]) for s in setups}) > 10,
            "Horas, casas, barriles y pozo cambian en cada partida")
    print(f"\nAldea OK ({b.ok} comprobaciones).")


if __name__ == "__main__":
    main()
