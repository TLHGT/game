"""Genera maps/aldea.json: la Aldea del vacío (Velmora en llamas).

    python tools/generar_aldea.py

Como generar_hospital.py: el JSON se puede retocar a mano, pero se sobrescribe
al volver a ejecutar este script. La misión y los easter eggs están en
systems/village_quest.py; los objetos, en entities/village.py.

Plano (y crece hacia arriba: el cielo está al norte):

                       [ PORTAL ]  plataformas flotantes (fase 3, saltando con Hero)
                    [   MERCADO   ]
                          ||  (llamas en la fase 1)
    [GRANJA] == [ casas  PLAZA  casas ] == [HERRERÍA]
                [ casas         casas ]
                [ gallinero  pozos    ]
                          ||
                       entrada

Las fases (FASE n) cambian el mapa:
    1 RELOJES  llamas en los tres caminos; 12 activadores y la fuente en la plaza.
    2 ALMAS    sin llamas; círculos del vacío en granja, herrería y mercado; grietas en la plaza.
    3 PORTAL   cristales del vacío donde estaban los círculos; plataformas flotantes y saltos
               hasta el Void Insect (tras su barrera); partes del insecto en las casas.
    4 FIN      el portal se cierra; se apagan los fuegos.
Las casas, el gallinero, los barriles y los pozos (los easter eggs) no se
cierran nunca, en ninguna fase.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from systems.village_quest import BARRIER_SECRET, BOSS_SECRET, HOUSES, PHASE_FLAG, WELLS  # noqa: E402
from tools.generar_hospital import write  # noqa: E402

MAPS = os.path.join(ROOT, "maps")
CLOCKS, SOULS, PORTAL, END = 1, 2, 3, 4
BEFORE_END = [CLOCKS, SOULS, PORTAL]

SIZE = [2800, 2400]
# Zonas caminables (múltiplos de 40, como la rejilla de colisión)
CORE = [600, 1080, 1600, 1160]            # el pueblo: x 600-2200, y 1080-2240
SOUTH_ROAD = [1360, 2240, 80, 160]        # entrada
FARM_ROAD = [520, 1440, 80, 80]
FARM = [120, 1120, 400, 720]
SMITHY_ROAD = [2200, 1440, 80, 80]
SMITHY = [2280, 1200, 400, 560]
MARKET_ROAD = [1360, 1040, 80, 40]
MARKET = [1000, 760, 800, 280]
SKY = [0, 0, 2800, 760]
PLATFORMS = [[1320, 560, 160, 120], [1040, 360, 200, 120], [1240, 120, 320, 160]]
PLAZA = [1200, 1280, 400, 400]
PLAZA_CENTER = (1400, 1480)

# Casas: esquina superior izquierda (240 x 200) y lado de la puerta
HOUSE_SPOTS = [((640, 1120), "S"), ((920, 1120), "S"), ((1680, 1120), "S"), ((1960, 1120), "S"),
               ((640, 1600), "N"), ((920, 1600), "N"), ((1680, 1600), "N"), ((1960, 1600), "N")]
assert len(HOUSE_SPOTS) == HOUSES

BARREL_SPOTS = [(980, 1400), (1140, 1380), (1660, 1390), (1880, 1400), (2140, 1380), (680, 1400),
                (1220, 1860), (1560, 1880), (1880, 1880), (2120, 2080), (980, 2160), (1240, 2140),
                (1640, 2100), (620, 1560)]
WELL_SPOTS = [(1120, 2000), (1820, 2000), (1560, 1800)]
assert len(WELL_SPOTS) == WELLS

VILLAGER = {"type": "enemy", "aggression": 0.0, "randomness": 0.6, "behavior": "wander", "radius": 130,
            "aggro": 170, "speed": 70, "can_flee": True, "respawn": 40}
VILLAGER_NAMES = {"herrero": "Herrero", "granjero": "Granjero", "vendedor": "Vendedor"}


def villager(eid, trade, pos, **kw):
    d = dict(VILLAGER, id=eid, name=VILLAGER_NAMES[trade], sprite=f"villager_{trade}", pos=list(pos),
             deck=trade, character=trade, soul=trade,
             note="Aldeano hueco (pasiva Corrupted). En la fase de las almas suelta la suya al vencerlo; "
                  "vuelve a aparecer a los 40 s (respawn).")
    d.update(kw)
    return d


def house(n, corner, door):
    """Casa sin tejado (se quemó): cuatro muros, puerta, suelo de tablas y los tres
    sitios donde el sorteo puede poner un diario, un peluche o una parte del insecto."""
    x, y = corner
    walls = [{"rect": [x, y, 240, 20], "style": "house", "height": 50}] if door != "N" else \
        [{"rect": [x, y, 80, 20], "style": "house", "height": 50},
         {"rect": [x + 160, y, 80, 20], "style": "house", "height": 50}]
    walls += [{"rect": [x, y + 180, 240, 20], "style": "house", "height": 50}] if door != "S" else \
        [{"rect": [x, y + 180, 80, 20], "style": "house", "height": 50},
         {"rect": [x + 160, y + 180, 80, 20], "style": "house", "height": 50}]
    walls += [{"rect": [x, y + 20, 20, 160], "style": "house", "height": 50},
              {"rect": [x + 220, y + 20, 20, 160], "style": "house", "height": 50}]
    walls[0]["note"] = f"Casa {n}"
    items = [
        {"type": "village_item", "id": f"casa{n}_diario", "kind": "diary", "house": n, "pos": [x + 56, y + 76],
         "note": f"Casa {n}: diario (si el sorteo pone uno aquí)."},
        {"type": "village_item", "id": f"casa{n}_peluche", "kind": "plush", "house": n, "pos": [x + 184, y + 80],
         "note": f"Casa {n}: peluche del vacío (easter egg, si el sorteo pone uno aquí)."},
        {"type": "village_item", "id": f"casa{n}_parte", "kind": "part", "house": n, "pos": [x + 120, y + 130],
         "phases": [PORTAL, END], "note": f"Casa {n}: parte del insecto (fase del portal)."},
    ]
    area = {"type": "planks", "rect": [x + 20, y + 20, 200, 160]}
    door_area = {"type": "planks", "rect": [x + 80, y + (180 if door == "S" else 0), 80, 20]}
    return walls, items, [area, door_area]


def main():
    d = {"id": "aldea", "name": "Aldea de Velmora",
         "description": "Aldea destruida en medio de las llamas. Un insecto del vacío ha vaciado a sus "
                        "habitantes (los aldeanos huecos) e intenta abrir un portal en el cielo. "
                        "Misión por fases (systems/village_quest.py); generado por tools/generar_aldea.py.",
         "size": SIZE, "phase_flag": PHASE_FLAG,
         "spawns": {"default": [1400, 2340]},
         "walkable": [CORE, SOUTH_ROAD, FARM_ROAD, FARM, SMITHY_ROAD, SMITHY, MARKET_ROAD, MARKET]
                     + [{"rect": p, "phases": [PORTAL, END]} for p in PLATFORMS],
         "forest": {"style": "burnt", "seed": 7, "spacing": 60, "exclude": [SKY]},
         "ground": {"seed": 21, "theme": "ashes", "areas": [], "paths": [], "details": []},
         "walls": [], "obstacles": [], "decorations": [], "interactables": [], "secrets": [],
         "triggers": [], "hidden_areas": [], "exits": []}
    g = d["ground"]
    add = lambda key, *items: d[key].extend(items)   # noqa: E731

    # --- Suelo -----------------------------------------------------------------------
    g["areas"] += [{"type": "void_sky", "rect": SKY, "phases": BEFORE_END},
                   {"type": "void_sky", "rect": SKY, "calm": True, "phases": [END]}]
    g["areas"] += [{"type": "platform", "rect": p, "phases": [PORTAL, END]} for p in PLATFORMS]
    g["areas"].append({"type": "stone", "rect": PLAZA})
    g["areas"].append({"type": "field", "rect": [160, 1160, 320, 220]})
    g["areas"].append({"type": "field", "rect": [160, 1580, 320, 220]})
    g["areas"].append({"type": "stone", "rect": [2300, 1240, 360, 200]})
    g["paths"] += [
        {"style": "ash", "width": 90, "points": [[1400, 2400], [1400, 1080]]},
        {"style": "ash", "width": 80, "points": [[520, 1480], [2280, 1480]]},
        {"style": "ash", "width": 70, "points": [[1400, 1100], [1400, 900]]},
        {"style": "ash", "width": 60, "points": [[480, 1480], [300, 1480]]},
    ]
    g["details"] += [
        {"type": "ash", "rect": CORE, "count": 70},
        {"type": "embers", "rect": CORE, "count": 120, "phases": BEFORE_END},
        {"type": "embers", "rect": FARM, "count": 40, "phases": BEFORE_END},
        {"type": "embers", "rect": SMITHY, "count": 40, "phases": BEFORE_END},
        {"type": "void_cracks", "rect": [1260, 1380, 280, 200], "count": 9, "phases": [SOULS, PORTAL]},
        {"type": "void_cracks", "rect": [1080, 800, 640, 200], "count": 6, "phases": [PORTAL]},
    ]

    # --- Casas -------------------------------------------------------------------------
    for n, (corner, door) in enumerate(HOUSE_SPOTS, start=1):
        walls, items, areas = house(n, corner, door)
        add("walls", *walls)
        add("interactables", *items)
        g["areas"] += areas

    # --- Plaza: el reloj de piedra (fase 1) -------------------------------------------
    cx, cy = PLAZA_CENTER
    for hour in range(1, 13):
        a = hour * math.tau / 12
        pos = [round(cx + math.sin(a) * 160), round(cy - math.cos(a) * 140) + 20]
        add("interactables", {"type": "clock_activator", "id": f"reloj_{hour}", "hour": hour, "pos": pos,
                              "phases": [CLOCKS],
                              "note": f"Activador de las {hour} (el reloj de la plaza)."})
    add("obstacles", {"type": "fountain", "pos": [cx, cy + 30], "phases": [CLOCKS],
                      "note": "Fuente seca del centro del reloj (solo en la fase 1)."})
    add("decorations", *[{"type": "void_crystal_deco", "pos": p, "variant": i, "phases": [SOULS, PORTAL]}
                         for i, p in enumerate([(cx - 30, cy + 20), (cx + 40, cy + 40), (cx + 4, cy - 10)])])
    add("interactables", {"type": "sign", "id": "inscripcion_reloj", "name": "Inscripción", "verb": "Leer",
                          "pos": [1460, 1720],
                          "text": ["Grabado en la piedra, alrededor del reloj de la plaza:",
                                   "«Doce piedras marcan las horas de Velmora.»",
                                   "«Quien vio llegar al vacío escribió su hora. Solo tres horas lo despiertan; "
                                   "una hora falsa lo duerme de nuevo.»"]})
    add("interactables", {"type": "sign", "id": "cartel_entrada", "name": "Cartel quemado", "pos": [1480, 2200],
                          "text": ["VELMORA", "Alguien ha tachado el nombre y ha escrito debajo, con ceniza: «HUID»."]})

    # --- Bloqueos de los caminos ----------------------------------------------------------
    fire_text = ["Una barricada de escombros arde con llamas moradas en el centro.",
                 "No hay forma de pasar. El fuego parece salir del reloj de la plaza..."]
    for bid, rect in (("llamas_granja", [520, 1440, 40, 80]), ("llamas_herreria", [2240, 1440, 40, 80]),
                      ("llamas_mercado", [1360, 1040, 80, 40])):
        add("interactables", {"type": "phase_block", "id": bid, "name": "Llamas", "style": "fire",
                              "rect": rect, "height": 60, "phases": [CLOCKS], "text": fire_text})
    add("walls", {"rect": [1340, 2380, 120, 20], "style": "rubble", "height": 50,
                  "note": "La entrada se derrumbó detrás de ti."})
    add("triggers", {"id": "entrada", "rect": [1360, 2280, 80, 20], "style": "discovery",
                     "message": "Velmora arde. Los aldeanos siguen ahí... pero están huecos."},
        {"id": "sin_salida", "rect": [1360, 2340, 80, 20], "style": "info", "once": False,
         "message": "Los escombros tapan el camino de vuelta."})

    # --- Granja (oeste) ------------------------------------------------------------------
    add("interactables", {"type": "void_circle", "id": "circulo_granjero", "trade": "granjero",
                          "pos": [320, 1500], "phases": [SOULS],
                          "note": "Círculo del vacío de la granja: 3 almas de granjero."})
    add("decorations", *[{"type": "void_crystal_deco", "pos": p, "variant": i, "phases": [PORTAL]}
                         for i, p in enumerate([(300, 1480), (346, 1500)])])
    add("obstacles", {"type": "haystack", "pos": [200, 1440]}, {"type": "haystack", "pos": [460, 1440]},
        {"type": "crate", "pos": [440, 1820]}, {"type": "gravestone", "pos": [180, 1820]})
    add("interactables", villager("granjero_g1", "granjero", (300, 1260)),
        villager("granjero_g2", "granjero", (320, 1700)))

    # --- Herrería (este) -------------------------------------------------------------------
    add("interactables", {"type": "void_circle", "id": "circulo_herrero", "trade": "herrero",
                          "pos": [2480, 1620], "phases": [SOULS],
                          "note": "Círculo del vacío de la herrería: 3 almas de herrero."})
    add("decorations", *[{"type": "void_crystal_deco", "pos": p, "variant": i, "phases": [PORTAL]}
                         for i, p in enumerate([(2460, 1600), (2506, 1620)])])
    add("obstacles", {"type": "forge", "pos": [2600, 1320]}, {"type": "crate", "pos": [2320, 1700]})
    add("interactables", {"type": "anvil", "id": "yunque", "pos": [2460, 1360],
                          "note": "Forja Void Impact con las tres partes del insecto."})
    add("interactables", villager("herrero_h1", "herrero", (2420, 1500)),
        villager("herrero_h2", "herrero", (2560, 1700)))

    # --- Mercado (norte) --------------------------------------------------------------------
    add("interactables", {"type": "void_circle", "id": "circulo_vendedor", "trade": "vendedor",
                          "pos": [1600, 940], "phases": [SOULS],
                          "note": "Círculo del vacío del mercado: 3 almas de vendedor."})
    add("decorations", *[{"type": "void_crystal_deco", "pos": p, "variant": i, "phases": [PORTAL]}
                         for i, p in enumerate([(1580, 920), (1626, 940)])])
    add("obstacles", {"type": "market_stall", "pos": [1100, 860]}, {"type": "market_stall", "pos": [1240, 1000]},
        {"type": "market_stall", "pos": [1700, 860]}, {"type": "crate", "pos": [1560, 1010]})
    add("interactables", villager("vendedor_m1", "vendedor", (1200, 920)),
        villager("vendedor_m2", "vendedor", (1720, 980)))

    # --- Calles del pueblo: aldeanos huecos de los tres oficios --------------------------
    add("interactables", villager("herrero_c1", "herrero", (1960, 1440)),
        villager("granjero_c1", "granjero", (840, 1460)),
        villager("vendedor_c1", "vendedor", (1700, 2020)),
        villager("herrero_c2", "herrero", (1100, 2080)),
        villager("granjero_c2", "granjero", (2000, 2160)),
        villager("vendedor_c2", "vendedor", (800, 1520)))

    # --- Plataformas flotantes y el portal (fase 3) ----------------------------------------
    jumps = [
        ("salto_mercado", (1400, 800), (1400, 640), "Saltar a la roca flotante", [PORTAL, END]),
        ("salto_p1_bajar", (1450, 600), (1460, 820), "Saltar abajo", [PORTAL, END]),
        ("salto_p1_p2", (1350, 600), (1140, 450), "Saltar a la siguiente roca", [PORTAL, END]),
        ("salto_p2_p1", (1200, 400), (1400, 640), "Saltar a la roca de abajo", [PORTAL, END]),
        ("salto_p2_p3", (1080, 400), (1300, 250), "Saltar hacia el portal", [PORTAL, END]),
        ("salto_p3_p2", (1280, 160), (1100, 450), "Saltar a la roca de abajo", [PORTAL, END]),
    ]
    for jid, pos, target, verb, phases in jumps:
        add("interactables", {"type": "jump_spot", "id": jid, "pos": list(pos), "target": list(target),
                              "verb": verb, "phases": phases,
                              "note": "Habilidad de aventura de HERO: saltar entre las rocas flotantes."})
    add("decorations", {"type": "void_portal", "pos": [1400, 150], "phases": BEFORE_END,
                        "note": "El portal del cielo (se cierra al vencer al Void Insect)."})
    add("interactables", {"type": "sign", "id": "aviso_portal", "name": "Roca grabada", "verb": "Mirar",
                          "pos": [1360, 640], "phases": [PORTAL, END],
                          "text": ["Alguien grabó con las uñas en la roca flotante:",
                                   "«Solo un salto valiente llega hasta la mosca.»"]})
    add("interactables", {
        "type": "enemy", "id": "void_insect", "name": "Void Insect", "sprite": "void_insect",
        "pos": [1460, 200], "verb": "Enfrentarse", "deck": "void_insect", "character": "void_insect",
        "hp": 100, "aggression": 0.2, "randomness": 0.5, "behavior": "guard", "aggro": 0,
        "can_flee": False, "requires_secret": BARRIER_SECRET, "unlocks_secret": BOSS_SECRET,
        "phases": [PORTAL],
        "intro": ["La mosca gira la cabeza hacia ti. Cientos de ojos te reflejan a la vez.",
                  "El zumbido te llena la cabeza: el portal late a su espalda."],
        "victory": ["El insecto se encoge, se retuerce... y el portal lo absorbe con un chasquido.",
                    "Sobre Velmora, el cielo se cierra."],
        "note": "Jefe: no hay combate hasta romper su barrera con la carta Void Impact."})
    add("interactables", {"type": "void_barrier", "id": "barrera_insecto", "pos": [1460, 226],
                          "secret": BARRIER_SECRET, "phases": [PORTAL],
                          "note": "La rompe quien tenga Void Impact (se forja en el yunque)."})
    add("secrets", {"id": BARRIER_SECRET, "name": "La barrera del vacío",
                    "unlock_message": "La barrera del insecto ha caído."},
        {"id": BOSS_SECRET, "name": "El Void Insect",
         "unlock_message": "El portal se ha cerrado. El fuego de Velmora empieza a apagarse."})
    add("interactables", {"type": "sign", "id": "final", "name": "Silencio", "verb": "Escuchar",
                          "pos": [1400, 220], "phases": [END],
                          "text": ["Ya no se oye el zumbido. Solo el viento y la ceniza que cae.",
                                   "Velmora está en paz."]})

    # --- Easter eggs (siempre disponibles) ---------------------------------------------------
    for n, pos in enumerate(BARREL_SPOTS, start=1):
        add("interactables", {"type": "barrel", "id": f"barril_{n}", "number": n, "pos": list(pos)})
    for n, pos in enumerate(WELL_SPOTS, start=1):
        add("interactables", {"type": "well", "id": f"pozo_{n}", "number": n, "pos": list(pos),
                              "note": "Uno de los pozos (al azar) te devuelve al principio a la 3ª vez."})
    # Gallinero (cercado) con el único pollo superviviente
    add("walls", {"rect": [680, 1920, 240, 12], "style": "fence", "height": 26},
        {"rect": [680, 2068, 80, 12], "style": "fence", "height": 26},
        {"rect": [840, 2068, 80, 12], "style": "fence", "height": 26},
        {"rect": [680, 1932, 12, 136], "style": "fence", "height": 26},
        {"rect": [908, 1932, 12, 136], "style": "fence", "height": 26, "note": "Gallinero"})
    add("interactables", {"type": "chicken", "id": "pollo", "pos": [800, 2000], "radius": 60,
                          "note": "Easter egg: llévalo a las 3 semillas del vacío (barriles al azar)."})
    add("interactables", {"type": "sign", "id": "cartel_gallinero", "name": "Gallinero", "pos": [940, 2060],
                          "text": ["«GALLINERO». Solo queda un pollo. Te mira con desconfianza."]})

    # --- Fuegos y decorado ------------------------------------------------------------------
    fires = [(900, 1140), (1940, 1130), (1180, 1700), (1640, 1700), (900, 1840), (2180, 1360),
             (1000, 2220), (1800, 2220), (640, 2160), (2150, 2000), (260, 1160), (2620, 1220), (1100, 780)]
    add("decorations", *[{"type": "flames", "pos": list(p), "variant": i % 3, "phases": BEFORE_END}
                         for i, p in enumerate(fires)])
    add("obstacles", {"type": "crate", "pos": [1300, 2100]}, {"type": "crate", "pos": [2000, 1940]},
        {"type": "gravestone", "pos": [2060, 2200]}, {"type": "gravestone", "pos": [2120, 2210]})

    write(os.path.join(MAPS, "aldea.json"), d)
    print("Aldea generada en", os.path.join(MAPS, "aldea.json"))


if __name__ == "__main__":
    main()
