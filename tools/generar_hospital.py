"""Genera los mapas del hospital (maps/hospital_lobby.json y hospital_piso1..4.json)
y maps/elevators.json.

    python tools/generar_hospital.py

Los mapas son JSON normales: se pueden retocar a mano después, pero si se vuelve
a ejecutar este script se sobrescriben. Para cambios de diseño (qué pasos están
bloqueados, dónde está cada cosa) es más cómodo cambiar este archivo.

Todas las plantas comparten la misma planta: una rejilla de 3 x 3 zonas

        WN | CN | EN          W / C / E = oeste / centro / este
        ---+----+---          N / M / S = norte / medio / sur
        WM | CM | EM          CM es el vestíbulo del ascensor (centro del piso)
        ---+----+---
        WS | CS | ES

y cada frontera entre zonas vecinas es una puerta, un muro, un derrumbe
(paso bloqueado) o una puerta especial (con llave / que abre un secreto).
Las escaleras van pegadas a la pared norte de una zona.

Recorrido previsto (A/B = partes de un piso que no se comunican entre sí):

    Lobby A (entrada) --escalera S1--> Piso 1 A --S2--> Lobby B (energía del lobby,
    palanca que abre el portón hacia Lobby A) --S2b--> Piso 1 B (energía, Ice Shard,
    Quick Revive) --S3--> Piso 2 A (sin la energía) --S4--> Piso 3 A (rellano)
    --S5--> Piso 2 B (energía, Fire Bolt, Juggernog) --S6--> Piso 3 B (energía,
    Speed Cola). Con las cuatro energías, el ascensor llega al Piso 4 (Elemental
    Wolf, Double Tap y, detrás del lobo, la llave del cuarto secreto del lobby).
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPS = os.path.join(ROOT, "maps")

SIZE = [2400, 1800]
COLS = {"W": (240, 960), "C": (1000, 1400), "E": (1440, 2160)}
ROWS = {"N": (240, 660), "M": (700, 1100), "S": (1140, 1560)}
INNER = [240, 240, 1920, 1320]
ELEVATOR = [1160, 700, 80, 40]
ELEVATOR_SPAWN = [1200, 800]
POWERS = ["energia_lobby", "energia_p1", "energia_p2", "energia_p3"]

FLOORS = [
    {"map": "hospital_lobby", "name": "Lobby", "requires": ["energia_lobby"]},
    {"map": "hospital_piso1", "name": "Piso 1", "requires": ["energia_p1"]},
    {"map": "hospital_piso2", "name": "Piso 2", "requires": ["energia_p2"]},
    {"map": "hospital_piso3", "name": "Piso 3", "requires": ["energia_p3"]},
    {"map": "hospital_piso4", "name": "Piso 4", "requires": POWERS,
     "unlock_message": "Todas las fuentes de energía están activas: el ascensor ya llega al Piso 4.",
     "no_power_text": ["El ascensor no responde."]},
]


def zone(z):
    (x0, x1), (y0, y1) = COLS[z[0]], ROWS[z[1]]
    return x0, y0, x1, y1


def at(z, fx, fy):
    """Punto dentro de la zona `z` (fx, fy de 0 a 1)."""
    x0, y0, x1, y1 = zone(z)
    return [round(x0 + (x1 - x0) * fx), round(y0 + (y1 - y0) * fy)]


# --- Fronteras -------------------------------------------------------------------
H_DOOR_X = {"W": 600, "C": 1200, "E": 1800}      # puertas entre filas (centradas en la columna)
V_DOOR_Y = {"N": 450, "M": 900, "S": 1350}       # puertas entre columnas (centradas en la fila)


def boundary_geometry(a, b):
    """Rectángulo del muro entre las zonas vecinas a y b, y del hueco de su puerta."""
    if a[0] == b[0]:                                     # misma columna: muro horizontal
        col = a[0]
        top = min(ROWS[a[1]][1], ROWS[b[1]][1])
        # los muros horizontales cubren también los cruces con los verticales
        x0, x1 = {"W": (240, 1000), "C": (1000, 1400), "E": (1400, 2160)}[col]
        cx = H_DOOR_X[col]
        if col == "C" and "N" in (a[1], b[1]) and "M" in (a[1], b[1]):
            cx = 1080                                    # el ascensor ocupa el centro de CM
        wall = [x0, top, x1 - x0, 40]
        gap = [cx - 40, top, 80, 40]
    else:                                                # misma fila: muro vertical
        row = a[1]
        left = min(COLS[a[0]][1], COLS[b[0]][1])
        y0, y1 = ROWS[row]
        cy = V_DOOR_Y[row]
        wall = [left, y0, 40, y1 - y0]
        gap = [left, cy - 40, 40, 80]
    return wall, gap


def split(wall, gap):
    x, y, w, h = wall
    gx, gy, gw, gh = gap
    if h == 40:      # horizontal
        return [[x, y, gx - x, h], [gx + gw, y, x + w - gx - gw, h]]
    return [[x, y, w, gy - y], [x, gy + gh, w, y + h - gy - gh]]


ALL_BOUNDARIES = [("WN", "WM"), ("WM", "WS"), ("CN", "CM"), ("CM", "CS"), ("EN", "EM"), ("EM", "ES"),
                  ("WN", "CN"), ("CN", "EN"), ("WM", "CM"), ("CM", "EM"), ("WS", "CS"), ("CS", "ES")]


class Floor:
    def __init__(self, map_id, name, description, dark_secret=None, lit=False):
        self.d = {"id": map_id, "name": name, "description": description, "size": SIZE,
                  "spawns": {"default": ELEVATOR_SPAWN, "elevator": ELEVATOR_SPAWN}, "walkable": [INNER[:]],
                  "ground": {"seed": len(map_id), "background": "void",
                             "areas": [{"type": "tiles", "rect": INNER[:]}]},
                  "walls": [
                      {"rect": [200, 200, 2000, 40], "style": "hospital", "height": 80},
                      {"rect": [200, 240, 40, 1360], "style": "hospital", "height": 80},
                      {"rect": [2160, 240, 40, 1360], "style": "hospital", "height": 80},
                  ],
                  "obstacles": [], "interactables": [], "secrets": [], "hidden_areas": [],
                  "triggers": [], "exits": []}
        self.map_id = map_id
        self.bottom_gap = None
        if dark_secret:
            self.d["hidden_areas"].append({"rect": INNER[:], "style": "dark", "secret": dark_secret})
        self.d["interactables"].append({"type": "elevator", "id": "ascensor", "rect": ELEVATOR, "height": 90,
                                        "group": "hospital", "floor": map_id,
                                        "note": "Ascensor: necesita la energía de este piso (maps/elevators.json)."})

    # --- Estructura -------------------------------------------------------------
    def boundaries(self, spec):
        """spec: {("WN", "CN"): "rubble" | "wall" | {"type": "door", ...}}; el resto, puerta abierta."""
        for a, b in ALL_BOUNDARIES:
            kind = spec.get((a, b), spec.get((b, a), "door"))
            wall, gap = boundary_geometry(a, b)
            if kind == "wall":
                self.d["walls"].append({"rect": wall, "style": "hospital", "height": 70})
                continue
            for part in split(wall, gap):
                self.d["walls"].append({"rect": part, "style": "hospital", "height": 70})
            if kind == "rubble":
                self.d["walls"].append({"rect": gap, "style": "rubble", "height": 60,
                                        "note": f"Derrumbe: paso bloqueado entre {a} y {b}."})
            elif isinstance(kind, dict):
                self.d["interactables"].append(dict(kind, rect=gap))

    def entrance(self):
        """Hueco de la puerta principal en la fachada sur (solo el lobby)."""
        self.bottom_gap = [1160, 1560, 80, 40]

    def finish_outer(self):
        if self.bottom_gap:
            self.d["walls"].append({"rect": [200, 1560, 960, 40], "style": "hospital", "height": 80})
            self.d["walls"].append({"rect": [1240, 1560, 960, 40], "style": "hospital", "height": 80})
        else:
            self.d["walls"].append({"rect": [200, 1560, 2000, 40], "style": "hospital", "height": 80})

    # --- Contenido ----------------------------------------------------------------
    def stairs(self, z, slot, sid, target, label):
        """Escalera pegada a la pared norte de la zona. `sid` es también el nombre del
        punto de aparición (en ambos pisos la misma escalera se llama igual)."""
        x0, y0, x1, y1 = zone(z)
        sx = x0 + 40 if slot == "L" else x1 - 160
        self.d["ground"]["areas"].append({"type": "stairs", "rect": [sx, y0, 120, 90]})
        self.d["exits"].append({"rect": [sx, y0, 120, 24], "target_map": target, "target_spawn": sid,
                                "note": label})
        self.d["spawns"][sid] = [sx + 60, y0 + 140]
        # Cartel al lado (en la columna central, a la izquierda: a la derecha está la puerta)
        if slot == "L":
            sign_x = sx - 22 if z[0] == "C" else sx + 150
        else:
            sign_x = sx - 30
        self.d["interactables"].append({"type": "sign", "id": f"cartel_{sid}", "name": "Escalera",
                                        "pos": [sign_x, y0 + 50], "text": [label]})

    def power(self, z, fx, fy, secret, floor_name, lights=True):
        self.d["interactables"].append({
            "type": "secret_object", "id": f"energia_{self.map_id}", "name": "Activador de energía",
            "pos": at(z, fx, fy), "sprite": "generator_off", "verb": "Activar",
            "stage_sprites": {"0": "generator_off", "1": "generator_on"},
            "stages": [f"Un cuadro eléctrico con una palanca enorme: «{floor_name.upper()}». La bajas con todas tus fuerzas..."],
            "idle_text": "El cuadro zumba. Este piso tiene corriente.",
            "unlocks_secret": secret, "unlock_stage": 1})
        self.d["secrets"].append({"id": secret, "name": f"Energía · {floor_name}",
                                  "unlock_message": f"¡Corriente en el {floor_name}! "
                                                    + ("Se encienden las luces y el ascensor funciona." if lights
                                                       else "El ascensor funciona.")})

    def chest(self, cid, z, fx, fy, **kw):
        self.d["interactables"].append(dict({"type": "chest", "id": cid, "pos": at(z, fx, fy)}, **kw))

    def perk(self, z, fx, fy, perk, name, floor):
        self.d["interactables"].append({"type": "perk_machine", "id": f"perk_{floor}", "perk": perk,
                                        "name": name, "floor": floor, "pos": at(z, fx, fy),
                                        "note": "Máquina de ventajas: se encienden en el orden del cuarto secreto del lobby."})

    def enemy(self, eid, kind, z, fx, fy, **kw):
        base = ENEMIES[kind]
        self.d["interactables"].append(dict(dict(base, id=eid, pos=at(z, fx, fy)), **kw))

    def props(self, *items):
        for kind, z, fx, fy in items:
            self.d["obstacles"].append({"type": kind, "pos": at(z, fx, fy)})

    def add(self, key, value):
        self.d[key].append(value)

    def save(self):
        self.finish_outer()
        if self.bottom_gap:
            self.d["walkable"].append([1160, 1560, 80, 40])
            self.d["ground"]["areas"].append({"type": "tiles", "rect": [1160, 1560, 80, 80]})
        write(os.path.join(MAPS, f"{self.map_id}.json"), self.d)


ROBOT = {"type": "enemy", "name": "Dron de seguridad", "sprite": "npc_droid",
         "deck": "security_droid", "character": "security_droid",
         "hp": 60, "aggression": -0.2, "behavior": "wander", "radius": 140, "aggro": 140, "speed": 60,
         "intro": ["BZZT. ZONA RESTRINGIDA. IDENTIFÍQUESE.",
                   "...IDENTIFICACIÓN NO ENCONTRADA. ACTIVANDO PROTOCOLO DE DEFENSA."],
         "victory": ["BZZT... QUE TENGA... UN BUEN... DÍA."]}
ENEMIES = {
    "robot": ROBOT,
    "fire_wolf": {"type": "enemy", "name": "Fire Wolf", "sprite": "wolf_fire",
                  "deck": "fire_wolf", "character": "fire_wolf", "behavior": "wander", "radius": 120,
                  "aggro": 170, "speed": 80, "can_flee": True},
    "ice_wolf": {"type": "enemy", "name": "Ice Wolf", "sprite": "wolf_ice",
                 "deck": "ice_wolf", "character": "ice_wolf", "behavior": "wander", "radius": 120,
                 "aggro": 170, "speed": 80, "can_flee": True},
}


# ===================================================================================
def lobby():
    f = Floor("hospital_lobby", "Hospital · Lobby",
              "Planta de entrada, con luz y drones. Parte A: entrada, vestíbulo del ascensor y ala oeste "
              "(escalera al Piso 1). Parte B (ala este): energía del lobby y la palanca del portón; se "
              "llega bajando desde el Piso 1. Cuarto secreto (WN): se abre con la llave del Piso 4.")
    f.entrance()
    f.d["spawns"].update({"default": [1200, 1500], "from_exterior": [1200, 1500]})
    f.d["exits"].append({"rect": [1160, 1588, 80, 12], "target_map": "hospital_exterior",
                         "target_spawn": "from_hospital", "note": "Puerta principal: a la caverna."})
    f.boundaries({
        ("WN", "WM"): {"type": "door", "id": "puerta_secreta", "name": "Sala del personal", "style": "metal",
                       "height": 70, "key": "llave_acceso",
                       "locked_text": ["SALA DEL PERSONAL. Acceso restringido.",
                                       "Hay un lector de tarjetas junto a la puerta."]},
        ("WN", "CN"): "wall", ("CN", "EN"): "wall", ("CS", "ES"): "wall",
        ("CM", "EM"): {"type": "secret_door", "id": "porton_lobby", "name": "Portón", "style": "gate",
                       "secret": "porton_lobby", "height": 60,
                       "hidden_text": ["Un portón de rejas cerrado con cadena.",
                                       "Al otro lado se ve una palanca. Habrá que llegar por otro camino."]},
    })
    f.stairs("WM", "L", "s1", "hospital_piso1", "Escalera: sube al Piso 1.")
    f.stairs("EN", "R", "s2", "hospital_piso1", "Escalera: sube al Piso 1 (ala oeste).")
    f.stairs("ES", "R", "s2b", "hospital_piso1", "Escalera: sube al Piso 1 (ala este).")
    f.power("EN", 0.3, 0.75, "energia_lobby", "Lobby", lights=False)
    f.add("interactables", {
        "type": "secret_object", "id": "palanca_porton", "name": "Palanca del portón", "pos": [1520, 960],
        "sprite": "switch_off", "stage_sprites": {"0": "switch_off", "1": "switch_on"}, "verb": "Tirar",
        "stages": ["Una palanca oxidada con un cartel: «PORTÓN». Tiras de ella..."],
        "idle_text": "El portón ya está abierto.", "unlocks_secret": "porton_lobby", "unlock_stage": 1})
    f.add("secrets", {"id": "porton_lobby", "name": "Portón del lobby",
                      "unlock_message": "El portón se abre con un chirrido: atajo hacia la entrada."})
    f.add("interactables", {"type": "sign", "id": "directorio", "name": "Directorio", "pos": [1300, 1250],
                            "text": ["LOBBY · Ascensor en el centro. Escaleras en las alas oeste y este.",
                                     "Cada planta tiene su propio activador de energía para el ascensor.",
                                     "PISO 4: acceso solo con todas las plantas en marcha."]})
    # Cuarto secreto
    f.add("interactables", {"type": "perk_code", "id": "ordenador", "name": "Ordenador", "sprite": "monitor",
                            "verb": "Mirar", "pos": [420, 300],
                            "text": ["La pantalla se enciende con un zumbido. Letras verdes sobre fondo negro:",
                                     "SECUENCIA DE ARRANQUE DE LAS MÁQUINAS (PISOS): {code}",
                                     "ADVERTENCIA: UN ARRANQUE FUERA DE ORDEN REINICIA TODAS LAS MÁQUINAS.",
                                     "(La secuencia cambia en cada partida.)"],
                            "note": "La secuencia es aleatoria en cada partida (systems/perk_puzzle.py)."})
    f.add("interactables", {"type": "pack_a_punch", "id": "pack_a_punch", "pos": [760, 330],
                            "item": "pack_a_punch", "item_name": "una Lata de Pack-a-Punch",
                            "note": "Recompensa del puzle de las máquinas de ventajas (pendiente: darle un uso)."})
    f.add("interactables", {"type": "sign", "id": "nota_personal", "name": "Nota", "pos": [560, 560],
                            "text": ["«Máquinas instaladas: una por planta, del 1 al 4.»",
                                     "«La grande solo arranca si las encendemos en el orden que marca el ordenador.»"]})
    f.add("secrets", {"id": "perks_completas", "name": "Máquinas de ventajas",
                      "unlock_message": "Se oye una melodía lejana: la máquina del cuarto secreto del lobby se ha encendido."})
    f.enemy("dron_lobby_1", "robot", "CS", 0.25, 0.3, behavior="patrol", patrol=[[1080, 1200], [1320, 1200]])
    f.enemy("dron_lobby_2", "robot", "WS", 0.5, 0.6)
    f.enemy("dron_lobby_3", "robot", "ES", 0.4, 0.7)
    f.props(("pillar", "CM", 0.15, 0.55), ("pillar", "CM", 0.85, 0.55), ("pillar", "CS", 0.12, 0.3),
            ("pillar", "CS", 0.88, 0.3), ("cabinet", "WS", 0.1, 0.9), ("bed", "WS", 0.9, 0.85),
            ("cabinet", "EM", 0.9, 0.9), ("cabinet", "WN", 0.1, 0.9), ("rubble", "EN", 0.85, 0.9),
            ("cabinet", "WM", 0.9, 0.92), ("bed", "ES", 0.1, 0.85))
    f.add("triggers", {"id": "entrada_lobby", "rect": [1080, 1440, 240, 30], "style": "info",
                       "message": "El lobby huele a desinfectante viejo. Las luces todavía funcionan."})
    f.save()


def piso1():
    f = Floor("hospital_piso1", "Hospital · Piso 1",
              "A oscuras, con drones. Parte A (ala oeste): llegas desde el lobby y bajas al ala este del "
              "lobby. Parte B (centro y este): energía, ascensor, Quick Revive y, al fondo, la carta Ice Shard.",
              dark_secret="energia_p1")
    f.boundaries({("WN", "CN"): "rubble", ("WM", "CM"): "rubble", ("WS", "CS"): "rubble",
                  ("CN", "EN"): "wall", ("CS", "ES"): "wall"})
    f.stairs("WM", "L", "s1", "hospital_lobby", "Escalera: baja al Lobby.")
    f.stairs("WN", "L", "s2", "hospital_lobby", "Escalera: baja al Lobby (ala este).")
    f.stairs("ES", "R", "s2b", "hospital_lobby", "Escalera: baja al Lobby (ala este).")
    f.stairs("CS", "L", "s3", "hospital_piso2", "Escalera: sube al Piso 2.")
    f.power("CN", 0.75, 0.6, "energia_p1", "Piso 1")
    f.chest("cofre_ice_shard", "EN", 0.9, 0.25, card="ice_shard")
    f.perk("EM", 0.85, 0.35, "quick_revive", "Quick Revive", 1)
    f.enemy("dron_p1_1", "robot", "WS", 0.6, 0.55)
    f.enemy("dron_p1_2", "robot", "WN", 0.75, 0.6)
    f.enemy("dron_p1_3", "robot", "EM", 0.4, 0.6)
    f.enemy("dron_p1_4", "robot", "EN", 0.3, 0.6, behavior="patrol", patrol=[[1560, 520], [1960, 520]])
    f.props(("bed", "WS", 0.1, 0.85), ("bed", "WS", 0.9, 0.85), ("cabinet", "WM", 0.9, 0.92),
            ("rubble", "WN", 0.9, 0.9), ("bed", "CN", 0.15, 0.85), ("cabinet", "ES", 0.1, 0.9),
            ("bed", "EM", 0.1, 0.85), ("rubble", "CS", 0.9, 0.85), ("cabinet", "EN", 0.1, 0.92))
    f.add("interactables", {"type": "sign", "id": "nota_p1", "name": "Nota arrugada", "pos": at("CM", 0.2, 0.85),
                            "text": ["«Si se va la luz, el ascensor se queda en la planta.»",
                                     "«Cada planta tiene su cuadro eléctrico. Búscalo a tientas.»"]})
    f.save()


def piso2():
    f = Floor("hospital_piso2", "Hospital · Piso 2",
              "A oscuras, con Fire Wolves. Parte A (suroeste): llegas desde el Piso 1, pero la energía no "
              "está aquí: hay que subir al Piso 3 y bajar por otra escalera. Parte B: energía, ascensor, "
              "Juggernog y, al fondo, la carta Fire Bolt.", dark_secret="energia_p2")
    f.boundaries({("CS", "CM"): "rubble", ("CS", "ES"): "rubble", ("WM", "CM"): "rubble",
                  ("WN", "WM"): "rubble", ("CM", "CS"): "rubble"})
    f.stairs("CS", "L", "s3", "hospital_piso1", "Escalera: baja al Piso 1.")
    f.stairs("WM", "L", "s4", "hospital_piso3", "Escalera: sube al Piso 3.")
    f.stairs("EN", "R", "s5", "hospital_piso3", "Escalera: sube al Piso 3 (rellano oeste).")
    f.stairs("WN", "L", "s6", "hospital_piso3", "Escalera: sube al Piso 3 (ala norte).")
    f.power("CN", 0.75, 0.6, "energia_p2", "Piso 2")
    f.chest("cofre_fire_bolt", "ES", 0.9, 0.8, card="fire_bolt")
    f.perk("EM", 0.85, 0.35, "juggernog", "Juggernog", 2)
    f.enemy("lobo_fuego_1", "fire_wolf", "WS", 0.6, 0.6)
    f.enemy("lobo_fuego_2", "fire_wolf", "WM", 0.75, 0.7)
    f.enemy("lobo_fuego_3", "fire_wolf", "CM", 0.15, 0.85)
    f.enemy("lobo_fuego_4", "fire_wolf", "ES", 0.4, 0.5)
    f.props(("bed", "WS", 0.1, 0.85), ("rubble", "CS", 0.85, 0.3), ("rubble", "WM", 0.9, 0.9),
            ("bed", "WN", 0.9, 0.85), ("cabinet", "CN", 0.15, 0.9), ("bed", "EN", 0.1, 0.85),
            ("cabinet", "EM", 0.1, 0.9), ("rubble", "ES", 0.1, 0.9))
    f.add("interactables", {"type": "sign", "id": "aviso_p2", "name": "Cartel chamuscado", "pos": at("CS", 0.7, 0.85),
                            "text": ["«PELIGRO: animales sueltos en la planta 2.»",
                                     "Las marcas de garras están calientes al tacto."]})
    f.save()


def piso3():
    f = Floor("hospital_piso3", "Hospital · Piso 3",
              "A oscuras, con Ice Wolves. Parte A: un rellano al oeste con dos escaleras (a las dos partes "
              "del Piso 2). Parte B: se llega desde el Piso 2 B; energía, ascensor y Speed Cola.",
              dark_secret="energia_p3")
    f.boundaries({("WM", "WN"): "rubble", ("WM", "WS"): "rubble", ("WM", "CM"): "rubble"})
    f.stairs("WM", "L", "s4", "hospital_piso2", "Escalera: baja al Piso 2.")
    f.stairs("WM", "R", "s5", "hospital_piso2", "Escalera: baja al Piso 2 (ala este).")
    f.stairs("WN", "L", "s6", "hospital_piso2", "Escalera: baja al Piso 2 (ala norte).")
    f.power("ES", 0.85, 0.7, "energia_p3", "Piso 3")
    f.perk("WS", 0.2, 0.4, "speed_cola", "Speed Cola", 3)
    f.enemy("lobo_hielo_1", "ice_wolf", "WM", 0.5, 0.85, behavior="guard", aggro=110,
            note="Vigila el rellano: si pasas pegado a las escaleras no te ve.")
    f.enemy("lobo_hielo_2", "ice_wolf", "CN", 0.5, 0.6)
    f.enemy("lobo_hielo_3", "ice_wolf", "EM", 0.5, 0.6)
    f.enemy("lobo_hielo_4", "ice_wolf", "CS", 0.5, 0.6)
    f.chest("cofre_p3", "EN", 0.9, 0.25, item="ether", item_name="un Éter")
    f.props(("rubble", "WM", 0.1, 0.92), ("bed", "WN", 0.9, 0.85), ("cabinet", "CN", 0.1, 0.9),
            ("bed", "EN", 0.1, 0.85), ("cabinet", "EM", 0.9, 0.9), ("bed", "ES", 0.1, 0.85),
            ("rubble", "WS", 0.9, 0.85))
    f.save()


def piso4():
    f = Floor("hospital_piso4", "Hospital · Piso 4",
              "Solo se llega en ascensor, con las cuatro energías activas (entonces también hay luz). "
              "Elemental Wolf en la sala norte; detrás de su verja, la llave de acceso al cuarto secreto "
              "del lobby. Double Tap en la sala oeste.", dark_secret=None)
    f.d["hidden_areas"].append({"rect": INNER[:], "style": "dark", "secret": POWERS})
    walls = {b: "wall" for b in ALL_BOUNDARIES}
    walls.update({("CN", "CM"): "door", ("WM", "CM"): "door",
                  ("CN", "EN"): {"type": "secret_door", "id": "verja_tesoro", "name": "Verja", "style": "gate",
                                 "secret": "lobo_vencido", "height": 60,
                                 "hidden_text": ["Una verja sellada con escarcha. Está helada al tacto."]}})
    f.boundaries(walls)
    f.add("interactables", {
        "type": "enemy", "id": "elemental_wolf", "name": "Elemental Wolf", "pos": [1200, 430],
        "sprite": "wolf_ghost", "verb": "Enfrentarse", "deck": "elemental_wolf", "character": "elemental_wolf",
        "aggression": 0.3, "randomness": 0.35, "behavior": "guard", "aggro": 0, "can_flee": False,
        "intro": ["Un lobo espectral te cierra el paso. Medio cuerpo le arde; el otro medio está cubierto de escarcha.",
                  "Ruge. El aire se congela a tu alrededor... y un instante después quema."],
        "victory": ["No retrocedes. El lobo te sostiene la mirada durante una eternidad...",
                    "...y se deshace en una nube de chispas y nieve."],
        "unlocks_secret": "lobo_vencido"})
    f.add("secrets", {"id": "lobo_vencido", "name": "El lobo fantasma",
                      "unlock_message": "El lobo fantasma ha desaparecido. La escarcha de la verja se derrite."})
    f.chest("cofre_llave", "EN", 0.85, 0.4, item="llave_acceso", item_name="la Llave de acceso",
            note="Abre la Sala del personal del lobby (el cuarto secreto).")
    f.chest("cofre_p4", "EN", 0.6, 0.4, item="gold_medal", item_name="una Medalla de oro")
    f.perk("WM", 0.2, 0.4, "double_tap", "Double Tap", 4)
    f.add("interactables", {"type": "sign", "id": "nota_p4", "name": "Diario", "verb": "Leer",
                            "pos": at("EN", 0.3, 0.75),
                            "text": ["«La llave del personal está aquí arriba, con el lobo.»",
                                     "«Abajo, en la sala del personal, dejé apuntado el orden de las máquinas.»"]})
    f.add("triggers", {"id": "aviso_lobo", "rect": [1040, 640, 80, 40], "style": "discovery",
                       "message": "Algo te observa desde la sala del norte..."})
    f.props(("pillar", "CN", 0.12, 0.3), ("pillar", "CN", 0.88, 0.3), ("rubble", "CM", 0.88, 0.85),
            ("cabinet", "WM", 0.9, 0.9), ("rubble", "WN", 0.5, 0.5), ("rubble", "ES", 0.5, 0.5))
    f.save()


# ===================================================================================
def write(path, data):
    """JSON legible: una línea por elemento de cada lista."""
    lines = ["{"]
    keys = list(data)
    for i, k in enumerate(keys):
        v = data[k]
        comma = "," if i < len(keys) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], (dict, list)) and k != "size":
            lines.append(f'  "{k}": [')
            for j, item in enumerate(v):
                lines.append("    " + json.dumps(item, ensure_ascii=False) + ("," if j < len(v) - 1 else ""))
            lines.append("  ]" + comma)
        elif isinstance(v, dict) and k in ("ground", "spawns"):
            lines.append(f'  "{k}": {{')
            sub = list(v)
            for j, sk in enumerate(sub):
                sv = v[sk]
                c2 = "," if j < len(sub) - 1 else ""
                if isinstance(sv, list) and sv and isinstance(sv[0], dict):
                    lines.append(f'    "{sk}": [')
                    for n, item in enumerate(sv):
                        lines.append("      " + json.dumps(item, ensure_ascii=False) + ("," if n < len(sv) - 1 else ""))
                    lines.append("    ]" + c2)
                else:
                    lines.append(f'    "{sk}": {json.dumps(sv, ensure_ascii=False)}{c2}')
            lines.append("  }" + comma)
        else:
            lines.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}{comma}')
    lines.append("}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    lobby()
    piso1()
    piso2()
    piso3()
    piso4()
    write(os.path.join(MAPS, "elevators.json"), {"hospital": FLOORS})
    print("Mapas del hospital generados en", MAPS)


if __name__ == "__main__":
    main()
