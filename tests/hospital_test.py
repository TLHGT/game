"""Juega automáticamente el nivel del hospital abandonado de principio a fin.

    python tests/hospital_test.py            # solo comprobaciones
    python tests/hospital_test.py --shots    # además guarda capturas en tests/shots/

Recorrido: caverna (habilidades de aventura) -> lobby -> piso 1 A -> lobby B ->
piso 1 B -> piso 2 A -> piso 3 A -> piso 2 B -> piso 3 B -> (ascensor) piso 4 ->
puzle de las máquinas de ventajas -> cuarto secreto del lobby. Además comprueba
con un buscador de caminos (tests/pathing.py) que los pasos bloqueados lo están.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke_test import Bot, key_event  # noqa: E402  (configura SDL sin ventana)

import pygame  # noqa: E402

from combate.game.deck_editor import CATALOG  # noqa: E402
from game import settings  # noqa: E402
from pathing import go, reachable  # noqa: E402

settings.START_MAP = "hospital_exterior"
settings.PERK_SEQUENCE = (2, 4, 1, 3)          # secuencia fija para poder probar el puzle


def change_map(b, direction, expected):
    """Camina en `direction` hasta que el fundido cargue el mapa `expected`."""
    b.g.input.move_override = direction
    for _ in range(240):
        b.tick()
        if b.g.world.id == expected and b.g.fade < 0.05:
            break
    b.g.input.move_override = None
    b.check(b.g.world.id == expected, f"Cambio de mapa a {expected}")


def wait_map(b, expected):
    for _ in range(240):
        b.tick()
        if b.g.world.id == expected and b.g.fade < 0.05:
            break
    b.check(b.g.world.id == expected, f"Llegada a {expected}")


def use(b, expected_id):
    b.check(b.target_id() == expected_id, f"Delante de «{expected_id}»")
    b.press_e()
    b.close_dialogue()


def front(b, obj_id, dy=24):
    """Va delante (debajo) de un objeto y lo mira."""
    it = b.g.world.get_interactable(obj_id)
    r = it.rect
    go(b, (r.centerx, r.bottom + dy))
    b.g.player.facing = "up"
    b.tick(2)
    return it


def use_obj(b, obj_id, dy=24):
    front(b, obj_id, dy)
    use(b, obj_id)


def stairs(b, sid, target):
    """Sube / baja por la escalera `sid` (su punto de aparición está justo delante)."""
    go(b, b.g.world.spawns[sid])
    change_map(b, (0, -1), target)
    spawn = b.g.world.spawns[sid]
    b.check(abs(b.g.player.x - spawn[0]) < 40 and b.g.player.y - spawn[1] < 60,
            f"Apareces junto a la escalera {sid} de {target}")


def dialogue_text(g):
    return " ".join(" ".join(lines) for lines in g.dialogue.pages)


def elevator(b, floor_name, target):
    """Usa el ascensor del piso actual para ir a `floor_name`."""
    g = b.g
    front(b, "ascensor", dy=30)
    b.check(b.target_id() == "ascensor", "Delante del ascensor")
    b.press_e()
    b.check(g.choice.is_open, "El ascensor abre el menú de pisos")
    names = [label for label, _, _ in g.choice.options]
    i = next(k for k, (label, _, _) in enumerate(g.choice.options) if label.startswith(floor_name))
    b.check(g.choice.choose(i), f"Ascensor: {floor_name} ({' · '.join(names)})")
    wait_map(b, target)


def edit_deck(b, remove=(), add=()):
    """Cambia cartas del mazo desde la pausa (TAB > Editar mazos) y guarda."""
    g = b.g
    g.store.path = os.path.join(tempfile.mkdtemp(), "decks_hospital.json")
    b.tick(1, [key_event(pygame.K_TAB)])
    g.pause.row = 2
    b.tick(1, [key_event(pygame.K_RETURN)])
    ed = g.deck_scene.editor
    for cid in remove:
        ed.remove(cid)
    for cid in add:
        b.check(ed.add(cid), f"Editor: {cid} ya se puede añadir")
    g.deck_scene.deck_action("save")
    b.tick(1, [key_event(pygame.K_ESCAPE)])
    b.tick(1, [key_event(pygame.K_ESCAPE)])
    b.check(set(add) <= set(g.store.get("hospital")) and not g.pause.is_open, "Mazo guardado")


def perk_rng_check(b):
    """Sin secuencia fija, cada partida sortea un orden distinto."""
    from systems.game_state import GameState
    from systems.perk_puzzle import PerkPuzzle
    codes = {PerkPuzzle(GameState()).code for _ in range(30)}
    b.check(len(codes) > 5 and all(sorted(c) == ["1", "2", "3", "4"] for c in codes),
            f"La secuencia de las máquinas es aleatoria en cada partida ({len(codes)} órdenes distintos en 30)")


def can_reach(b, a, z):
    """¿Se puede ir andando del punto/objeto a al z en el mapa actual?"""
    w = b.g.world

    def point(p):
        if isinstance(p, str):
            if p in w.spawns:
                return w.spawns[p]
            it = w.get_interactable(p)
            return (it.rect.centerx, it.rect.bottom + 24)
        return p
    return reachable(w, point(a), point(z))


def main():
    b = Bot()
    g = b.g
    b.tick(90)
    b.check(g.world.id == "hospital_exterior", "Empieza fuera del hospital (nivel principal)")
    b.check(g.world.ground.get("theme") == "cave", "El exterior es una cueva")
    kinds = {e.kind for e in g.world.forest}
    b.check(kinds and kinds <= {"stalagmite", "cave_rock"},
            f"El relleno de la cueva son estalagmitas y rocas, no árboles ({sorted(kinds)})")
    b.check(not any(o.kind in ("tree", "pine", "bush", "stump") for o in g.world.obstacles),
            "Sin árboles ni arbustos en la cueva")
    b.check(g.renderer.vignette is g.renderer._vignettes["cave"], "La cueva usa la viñeta oscura")
    b.check(len(g.world.exits) == 1 and g.world.exits[0].target_map == "hospital_lobby",
            "La cueva no tiene salida hacia atrás: solo la puerta del hospital")
    b.walk((670, 1720))
    b.check(g.world.id == "hospital_exterior" and g.player.y < 1740,
            "Al fondo del túnel hay un derrumbe: no se puede salir")
    b.shot("h01_exterior")

    # --- Menú de pausa (TAB): personaje y mazo ------------------------------
    b.tick(1, [key_event(pygame.K_TAB)])
    b.check(g.pause.is_open and g.busy, "TAB abre el menú de pausa")
    b.check(g.pause.characters == ["blaze", "hero", "jurgenoid"],
            "Solo personajes jugables (Blaze, Hero y Jurgenoid; los enemigos no)")
    x0 = g.player.x
    g.input.move_override = (1, 0)
    b.tick(20)
    g.input.move_override = None
    b.check(g.player.x == x0, "En pausa el mundo está congelado")
    before = g.pause.character
    b.tick(1, [key_event(pygame.K_d)])            # fila Personaje: siguiente
    b.check(g.pause.character != before, f"Cambia de personaje ({before} -> {g.pause.character})")
    while g.pause.character != "blaze":
        b.tick(1, [key_event(pygame.K_d)])
    b.check(g.pause.deck_names == ["hospital"] and g.pause.deck == "hospital",
            "En el hospital solo hay un mazo")
    deck = g.store.get("hospital")
    b.check(sorted(settings.HOSPITAL_DECK) == sorted(deck) and len(set(deck)) == 10,
            "El mazo: Attack, Guard, Break, Magic, Perfect Guard, Recover, Taunt, Stun Guard, Revenge, Overdrive")
    b.tick(1, [key_event(pygame.K_s)])            # fila Mazo
    b.tick(1, [key_event(pygame.K_d)])
    b.check(g.pause.deck == "hospital", "No hay otro mazo al que cambiar")
    b.shot("h00_pausa")

    # --- Editar mazos desde la pausa (decks.json temporal: no toca los del usuario) ---
    tmp = tempfile.mkdtemp()
    g.store.path = os.path.join(tmp, "decks_hospital.json")
    b.tick(1, [key_event(pygame.K_s)])            # fila Editar mazos
    b.tick(1, [key_event(pygame.K_RETURN)])
    scene = g.deck_scene
    b.check(scene is not None and scene.editor.name == "hospital", "ENTER en «Editar mazos» abre el editor con tu mazo")
    b.check(not ({"flame_fang", "infernal_shift"} & set(CATALOG)),
            "El catálogo no ofrece cartas exclusivas de enemigos")
    ed = scene.editor
    available = set(settings.AVAILABLE_CARDS)
    b.check(ed.locked and not (ed.locked & available) and set(CATALOG) - ed.locked == available,
            f"Solo hay 12 cartas disponibles; el resto ({len(ed.locked)}) salen bloqueadas")
    scene.deck_action("duplicate")
    scene.deck_action("new")
    b.check(scene.editor.name == "hospital" and not scene.editor.is_new, "No se pueden crear ni duplicar mazos")
    ed = scene.editor
    ed.remove("taunt")
    b.check(not ed.add("guard") and "repetir" in ed.message, "No se pueden repetir cartas en el mazo")
    b.check(not ed.add("ice_shard") and "bloqueada" in ed.message, "No se puede añadir una carta bloqueada")
    b.check(ed.add("heavy_blow"), "Heavy Blow (disponible) sí entra")
    scene.deck_action("save")
    b.check(ed.selected == "hospital" and "heavy_blow" in g.store.get("hospital"), "Mazo guardado con Heavy Blow")
    b.shot("h00b_editor")
    b.tick(1, [key_event(pygame.K_ESCAPE)])       # VOLVER
    b.check(g.deck_scene is None and g.pause.is_open, "VOLVER regresa al menú de pausa")
    b.check(g.pause.deck_names == ["hospital"], "Sigue habiendo un solo mazo")
    b.check(os.path.exists(g.store.path), "Se guarda en decks_hospital.json")
    shutil.rmtree(tmp, ignore_errors=True)
    b.tick(1, [key_event(pygame.K_ESCAPE)])
    b.check(not g.pause.is_open and g.running, "ESC cierra la pausa (sin salir del juego)")

    # --- Habilidades de aventura ---------------------------------------------
    b.check(g.pause.character == "blaze" and g.ability == "burn", "Con Blaze la habilidad de aventura es Quemar")
    b.walk((670, 1580), (1000, 1580), (1000, 1436), (1400, 1436), (1400, 1262), (1404, 1262))
    b.check(g.player.sprite_key.startswith("avatar_blaze_"), f"Blaze se ve con su avatar ({g.player.sprite_key})")
    wall = g.world.get_interactable("hojas_patio")
    b.check(wall.solid, "La maraña de raíces cierra el paso")
    b.check(b.target_id() == "hojas_patio" and wall.get_prompt() == "E - Quemar raíces",
            "Con Blaze, al acercarte aparece «E - Quemar raíces»")
    b.shot("h01b_pared_hojas")
    b.press_e()
    b.tick(70)
    b.check(wall.burned and not wall.solid and not wall.visible, "Blaze quema las raíces: el paso queda libre")
    b.walk((1500, 1262))
    use(b, "cofre_hojas")
    b.check(g.state.inventory.has("ether"), "Cofre de detrás de la pared")
    b.walk((1400, 1262), (1400, 1436), (1240, 1436), (1240, 1416))
    b.check(b.target_id() != "salto_plataforma", "Con Blaze, el punto de salto no ofrece nada")

    b.tick(1, [key_event(pygame.K_TAB)])          # cambiar a Hero en la pausa
    b.tick(1, [key_event(pygame.K_d)])
    b.tick(1, [key_event(pygame.K_ESCAPE)])
    b.tick(3)
    b.check(g.pause.character == "hero" and g.ability == "jump", "Cambio a Hero: habilidad Saltar")
    b.check(g.player.sprite_key.startswith("player_"), "Hero aún no tiene avatar propio: usa el de por defecto")
    b.check(b.target_id() == "salto_plataforma"
            and g.world.get_interactable("salto_plataforma").get_prompt() == "E - Saltar arriba",
            "Con Hero aparece «E - Saltar arriba»")
    b.press_e()
    b.tick(10)
    b.shot("h01c_salto")
    b.tick(40)
    b.check(1270 < g.player.y < 1340 and 1160 < g.player.x < 1320, f"Hero salta a la plataforma alta ({g.player.x:.0f}, {g.player.y:.0f})")
    b.walk((1226, 1316))
    use(b, "cofre_plataforma")
    b.check(g.state.inventory.has("hero_badge"), "Cofre de la plataforma")
    b.walk((1290, 1326))
    b.check(b.target_id() == "salto_bajar", "Punto para bajar")
    b.press_e()
    b.tick(50)
    b.check(g.player.y > 1380, "Hero baja de un salto")
    b.walk((1290, 1436), (1000, 1436))
    b.tick(1, [key_event(pygame.K_TAB)])          # Jurgenoid: sin habilidad de aventura
    b.tick(1, [key_event(pygame.K_d)])
    b.tick(1, [key_event(pygame.K_ESCAPE)])
    b.check(g.pause.character == "jurgenoid" and g.ability is None, "Jurgenoid no tiene habilidad de aventura")
    b.tick(2)
    b.check(g.player.sprite_key.startswith("avatar_jurgenoid_"), "Jurgenoid se ve con su avatar")
    b.shot("h01d_avatar_jurgenoid")
    b.walk((1240, 1436), (1240, 1416))
    b.check(b.target_id() != "salto_plataforma", "Con Jurgenoid, el punto de salto no ofrece nada")
    b.walk((1240, 1436), (1000, 1436))
    b.tick(1, [key_event(pygame.K_TAB)])          # de vuelta a Blaze para el resto de la prueba
    while g.pause.character != "blaze":
        b.tick(1, [key_event(pygame.K_d)])
    b.tick(1, [key_event(pygame.K_ESCAPE)])

    # --- Caverna -> lobby (escenas distintas) ---------------------------------
    b.walk((1000, 1230), (725, 1165))
    use(b, "cofre_patio")
    b.walk((1000, 1200), (1000, 960))
    change_map(b, (0, -1), "hospital_lobby")
    b.walk((1200, 1530))
    change_map(b, (0, 1), "hospital_exterior")
    b.check(abs(g.player.x - 1000) < 30 and 990 < g.player.y < 1200,
            f"Al salir apareces delante de la puerta ({g.player.x:.0f}, {g.player.y:.0f})")
    b.check(g.world.get_interactable("cofre_patio").opened, "La caverna recuerda el cofre abierto")
    change_map(b, (0, -1), "hospital_lobby")

    # --- Lobby (parte A) ---------------------------------------------------------
    b.check(not g.world.hidden_areas, "El lobby tiene luz")
    enemies = [it for it in g.world.interactables if it.__class__.__name__ == "Enemy"]
    b.check(enemies and all(e.character == "security_droid" for e in enemies), "En el lobby solo hay drones")
    b.check(not can_reach(b, "from_exterior", "energia_hospital_lobby"),
            "Desde la entrada no se llega a la energía del lobby (portón cerrado)")
    b.check(not can_reach(b, "from_exterior", "ordenador"), "El cuarto secreto está cerrado")
    use_obj(b, "ascensor", dy=30)
    b.check(not g.choice.is_open, "Sin energía, el ascensor del lobby no funciona")
    door = front(b, "puerta_secreta")
    use(b, "puerta_secreta")
    b.check(door.is_locked, "La Sala del personal pide una llave de acceso")
    b.shot("h02_lobby")
    stairs(b, "s1", "hospital_piso1")

    # --- Piso 1 (parte A) --------------------------------------------------------
    b.check(g.world.hidden_areas and g.world.hidden_areas[0].style == "dark", "El piso 1 está a oscuras")
    enemies = [it for it in g.world.interactables if it.__class__.__name__ == "Enemy"]
    b.check(enemies and all(e.character == "security_droid" for e in enemies), "En el piso 1 solo hay drones")
    b.check(not can_reach(b, "s1", "energia_hospital_piso1") and not can_reach(b, "s1", "ascensor"),
            "Desde la escalera del lobby, la energía y el ascensor del piso 1 están tras un derrumbe")
    b.shot("h03_piso1_oscuro")
    stairs(b, "s2", "hospital_lobby")

    # --- Lobby (parte B) ---------------------------------------------------------
    use_obj(b, "energia_hospital_lobby")
    b.check(g.secrets.is_unlocked("energia_lobby"), "Energía del lobby activada")
    use_obj(b, "palanca_porton")
    gate = g.world.get_interactable("porton_lobby")
    b.check(gate.is_open and can_reach(b, "s2", "from_exterior"), "La palanca abre el portón: atajo a la entrada")
    stairs(b, "s2b", "hospital_piso1")

    # --- Piso 1 (parte B) --------------------------------------------------------
    use_obj(b, "energia_hospital_piso1")
    b.check(g.secrets.is_unlocked("energia_p1"), "Energía del piso 1 activada")
    b.tick(90)
    b.check(g.world.hidden_areas[0].reveal >= 1.0, "Se encienden las luces del piso 1")
    use_obj(b, "cofre_ice_shard")
    b.check("ice_shard" not in g.locked_cards(), "Cofre del final del piso 1: carta Ice Shard desbloqueada")
    b.check("fire_bolt" in g.locked_cards(), "Fire Bolt sigue bloqueada")
    stairs(b, "s3", "hospital_piso2")

    # --- Piso 2 (parte A) --------------------------------------------------------
    enemies = [it for it in g.world.interactables if it.__class__.__name__ == "Enemy"]
    b.check(enemies and all(e.character == "fire_wolf" for e in enemies), "En el piso 2 hay Fire Wolves")
    b.check(not can_reach(b, "s3", "energia_hospital_piso2"),
            "Al llegar al piso 2 no hay forma de llegar a su energía")
    stairs(b, "s4", "hospital_piso3")

    # --- Piso 3 (rellano) ----------------------------------------------------------
    b.check(not can_reach(b, "s4", "energia_hospital_piso3") and can_reach(b, "s4", "s5"),
            "Rellano del piso 3: solo la otra escalera de bajada")
    stairs(b, "s5", "hospital_piso2")

    # --- Piso 2 (parte B) --------------------------------------------------------
    use_obj(b, "energia_hospital_piso2")
    b.check(g.secrets.is_unlocked("energia_p2"), "Energía del piso 2 activada (bajando desde el 3)")
    use_obj(b, "cofre_fire_bolt")
    b.check("fire_bolt" not in g.locked_cards(), "Cofre del final del piso 2: carta Fire Bolt desbloqueada")
    edit_deck(b, remove=("heavy_blow", "overdrive"), add=("fire_bolt", "ice_shard"))
    stairs(b, "s6", "hospital_piso3")

    # --- Piso 3 (parte B) --------------------------------------------------------
    enemies = [it for it in g.world.interactables if it.__class__.__name__ == "Enemy"]
    b.check(enemies and all(e.character == "ice_wolf" for e in enemies), "En el piso 3 hay Ice Wolves")
    use_obj(b, "energia_hospital_piso3")
    b.check(g.secrets.is_unlocked("energia_p3"), "Energía del piso 3 activada")
    b.check(any("Piso 4" in n.text for n in g.notifications.queue), "Aviso: el ascensor ya llega al piso 4")
    b.shot("h04_piso3")
    elevator(b, "Piso 4", "hospital_piso4")

    # --- Piso 4: Elemental Wolf ------------------------------------------------------
    b.check(not can_reach(b, "elevator", "cofre_llave"), "La llave está tras la verja del lobo")
    b.check(all(a.revealed for a in g.world.hidden_areas) or g.world.hidden_areas[0].reveal > 0,
            "Con todas las energías, el piso 4 tiene luz")
    wolf = front(b, "elemental_wolf", dy=40)
    b.check(b.target_id() == "elemental_wolf" and wolf.get_prompt() == "E - Enfrentarse", "Indicador «E - Enfrentarse»")
    b.press_e()
    b.close_dialogue()
    b.tick(30)
    b.check(g.battle is not None and not g.battle.enemy.can_flee, "Empieza el combate contra el jefe (sin huida)")
    foe = g.battle.engine.players[1]
    me = g.battle.engine.players[0]
    mine = [c.id for c in me.deck.draw_pile + me.deck.discard_pile + me.hand]
    b.check(foe.character.id == "elemental_wolf" and g.battle.player_deck == "hospital"
            and {"fire_bolt", "ice_shard"} <= set(mine), "Elemental Wolf, y tú con tu mazo (ya con Fire Bolt e Ice Shard)")
    b.tick(120)
    b.shot("h05_combate_jefe")
    b.resolve_encounter("win")
    b.check(g.world.get_interactable("verja_tesoro").is_open, "Al vencer al lobo se abre la verja")
    use_obj(b, "cofre_llave")
    b.check(g.state.inventory.has("llave_acceso"), "Llave de acceso conseguida")

    # --- Puzle de las máquinas de ventajas (secuencia de prueba 2-4-1-3) ----------
    use_obj(b, "perk_4")
    b.check(g.perks.progress == [], "Encender la del piso 4 primero (fuera de orden) apaga todas")
    elevator(b, "Piso 2", "hospital_piso2")
    use_obj(b, "perk_2")
    b.check(g.perks.progress == [2], "1ª máquina: piso 2")
    elevator(b, "Piso 4", "hospital_piso4")
    use_obj(b, "perk_4")
    elevator(b, "Piso 1", "hospital_piso1")
    use_obj(b, "perk_1")
    elevator(b, "Piso 3", "hospital_piso3")
    use_obj(b, "perk_3")
    b.check(g.perks.complete and g.secrets.is_unlocked("perks_completas"), "Las cuatro máquinas, en orden")
    b.shot("h06_perk")

    # --- Cuarto secreto del lobby --------------------------------------------------
    elevator(b, "Lobby", "hospital_lobby")
    door = front(b, "puerta_secreta")
    use(b, "puerta_secreta")
    b.check(not door.is_locked and not door.solid, "La llave de acceso abre la Sala del personal")
    front(b, "ordenador")
    b.press_e()
    for _ in range(4):                            # pasa a la página de la secuencia
        b.tick(60)
        if "2413" in dialogue_text(g):
            break
        b.press_e()
    b.check("2413" in dialogue_text(g), "El ordenador muestra la secuencia (2413)")
    b.close_dialogue()
    use_obj(b, "pack_a_punch")
    b.check(g.state.inventory.has("pack_a_punch"), "El Pack-a-Punch funciona y da su recompensa")
    b.shot("h07_cuarto_secreto")

    perk_rng_check(b)
    print(f"\nHospital completado ({b.ok} comprobaciones). Inventario: {g.state.inventory.items}")


if __name__ == "__main__":
    main()
