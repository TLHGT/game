"""Misión principal de la Aldea del vacío (maps/aldea.json) y sus easter eggs.

El mapa cambia con cada paso (FASE, flag "aldea_fase"; ver world/map.py):

    1 RELOJES   En la plaza hay 12 activadores del vacío, uno por cada hora del
                reloj. En tres casas hay un diario con una hora (14:00 -> el 2,
                9:00 -> el 9). Hay que activar esas tres, en cualquier orden; uno
                equivocado los apaga todos. Las llamas cierran la granja, la
                herrería y el mercado.
    2 ALMAS     Se apagan las llamas y aparecen tres círculos del vacío (granja,
                herrería, mercado). Cada aldeano hueco vencido deja su alma (solo
                se lleva una a la vez). Cada círculo pide SOULS_PER_CIRCLE almas (1) de su oficio; un
                alma equivocada hace escapar todas las de ese círculo.
    3 PORTAL    Aparecen plataformas flotantes hasta el portal (se suben saltando
                con Hero). El Void Insect está tras una barrera que solo rompe la
                carta Void Impact, que se forja en el yunque de la herrería con
                tres partes del insecto escondidas en las casas.
    4 FIN       Vencido el insecto, el portal se cierra y el fuego se apaga.

Easter eggs (siempre disponibles, en cualquier fase):
    - 3 peluches con aura del vacío en casas al azar: tocar los tres -> «Alguien te observa».
    - El pollo del gallinero: llévalo a las semillas del vacío de 3 barriles al azar
      (hay que romperlos) y muta en un pollo humanoide que huye. Si empieza un
      combate mientras lo llevas, huye de vuelta al gallinero.
    - Uno de los pozos (al azar): interactuar 3 veces -> pantalla negra y vuelves
      al principio: «Buen intento».

Todo lo aleatorio se sortea una vez por partida (settings.VILLAGE_SEED lo fija
para las pruebas) y vive en GameState: sobrevive al cambiar de mapa.
"""
import random

PHASE_FLAG = "aldea_fase"
CLOCKS, SOULS, PORTAL, END = 1, 2, 3, 4
PHASE_NAMES = {CLOCKS: "Los relojes del vacío", SOULS: "Las almas huecas",
               PORTAL: "El portal del cielo", END: "El cielo se cierra"}

HOUSES = 8                      # casas 1..8 (tools/generar_aldea.py las coloca)
BARRELS = 14                    # barriles barril_1..barril_14
WELLS = 3                       # pozos pozo_1..pozo_3
TRADES = ("herrero", "granjero", "vendedor")
TRADE_NAMES = {"herrero": "herrero", "granjero": "granjero", "vendedor": "vendedor"}
CIRCLE_PLACES = {"herrero": "la herrería", "granjero": "la granja", "vendedor": "el mercado"}
SOULS_PER_CIRCLE = 1             # almas de su oficio que pide cada círculo
SOULS_REQUIRED = True            # False: los círculos se encienden al tocarlos, sin almas
PARTS = (("parte_pata", "una Pata del vacío"), ("parte_ala", "un Ala del vacío"),
         ("parte_aguijon", "un Aguijón del vacío"))
VOID_CARD = "void_impact"
BARRIER_SECRET = "barrera_vacio"
BOSS_SECRET = "insecto_vencido"
WELL_USES = 3

# Quién escribió cada diario (el texto se completa con la hora sorteada)
DIARIES = [
    ("Diario de Tomasa, la panadera",
     ["«El horno aún estaba encendido cuando empezó el zumbido.»",
      "«A las {hour}, el cielo se rajó encima de la plaza y una de las piedras del reloj se puso a brillar.»"]),
    ("Cuaderno del viejo Anselmo",
     ["«Llevo cuarenta años mirando el reloj de piedra de la plaza.»",
      "«Hoy, a las {hour}, una de sus piedras se volvió morada. Juraría que respiraba.»"]),
    ("Diario de la pequeña Iria",
     ["«Mamá dice que no salga. Pero a las {hour} vi una mosca enorme encima de la plaza.»",
      "«La piedra de esa hora del reloj se encendió cuando pasó por encima.»"]),
]


def hour_label(hour, pm):
    """Cómo se escribe la hora en un diario: 14:00 (pm) o 2:00; las 12, 12:00 o 0:00."""
    if hour == 12:
        return "0:00" if pm else "12:00"
    return f"{hour + 12 if pm else hour}:00"


class VillageQuest:
    def __init__(self, state, seed=None):
        self.state = state
        if not state.get_flag("aldea_setup"):
            self._setup(random.Random(seed))

    # --- Sorteo de la partida ----------------------------------------------------
    def _setup(self, rng):
        hours = rng.sample(range(1, 13), 3)
        houses = list(range(1, HOUSES + 1))
        self.state.set_flag("aldea_setup", {
            "hours": hours,
            "hour_labels": [hour_label(h, rng.random() < 0.5) for h in hours],
            "diary_houses": rng.sample(houses, 3),
            "plush_houses": rng.sample(houses, 3),
            "part_houses": rng.sample(houses, 3),
            "seed_barrels": sorted(rng.sample(range(1, BARRELS + 1), 3)),
            "special_well": rng.randint(1, WELLS),
        })
        self.state.set_flag(PHASE_FLAG, CLOCKS)

    @property
    def setup(self):
        return self.state.get_flag("aldea_setup")

    def _get(self, key, default):
        value = self.state.get_flag("aldea_" + key, None)
        return default if value is None else value

    def _set(self, key, value):
        self.state.set_flag("aldea_" + key, value)

    @property
    def phase(self):
        return self.state.get_flag(PHASE_FLAG, CLOCKS)

    def set_phase(self, phase):
        self.state.set_flag(PHASE_FLAG, phase)

    # --- Fase 1: los relojes --------------------------------------------------------
    @property
    def target_hours(self):
        return list(self.setup["hours"])

    @property
    def clock_progress(self):
        return list(self._get("clock", []))

    def diary(self, house):
        """(título, páginas) del diario de esa casa, o None si no hay."""
        houses = self.setup["diary_houses"]
        if house not in houses:
            return None
        k = houses.index(house)
        title, pages = DIARIES[k]
        label = self.setup["hour_labels"][k]
        return title, [p.format(hour=label) for p in pages]

    def press_clock(self, hour):
        """"already" | "on" | "done" (tercero correcto: fase 2) | "wrong" (se apagan todos)
        | "dormant" (la fase de los relojes ya pasó)."""
        if self.phase != CLOCKS:
            return "dormant"
        progress = self.clock_progress
        if hour in progress:
            return "already"
        if hour not in self.target_hours:
            self._set("clock", [])
            return "wrong"
        progress.append(hour)
        self._set("clock", progress)
        if len(progress) == len(self.target_hours):
            self.set_phase(SOULS)
            return "done"
        return "on"

    # --- Fase 2: las almas ----------------------------------------------------------
    @property
    def soul(self):
        """Oficio del alma que lleva el jugador (o None)."""
        return self._get("soul", None)

    def circle_count(self, trade):
        return self._get("circles", {}).get(trade, 0)

    def circle_done(self, trade):
        return self.circle_count(trade) >= SOULS_PER_CIRCLE

    def grant_soul(self, trade):
        """Un aldeano hueco vencido suelta su alma: "got" | "full" (ya lleva una) | "none"."""
        if self.phase != SOULS or trade not in TRADES:
            return "none"
        if self.soul:
            return "full"
        self._set("soul", trade)
        return "got"

    def offer_soul(self, circle):
        """El jugador entrega su alma al círculo `circle`. Devuelve:
        "empty" (no lleva alma), "complete" (el círculo ya está lleno), "ok",
        "filled" (este círculo se completa), "all" (los tres: fase 3) o
        "wrong" (alma de otro oficio: escapan las del círculo)."""
        if self.circle_done(circle):
            return "complete"
        if not SOULS_REQUIRED:          # momentáneo: tocar el círculo lo llena
            circles = dict(self._get("circles", {}))
            circles[circle] = SOULS_PER_CIRCLE
            self._set("circles", circles)
            if not all(self.circle_done(t) for t in TRADES):
                return "filled"
            self.set_phase(PORTAL)
            return "all"
        soul = self.soul
        if not soul:
            return "empty"
        circles = dict(self._get("circles", {}))
        self._set("soul", None)
        if soul != circle:
            circles[circle] = 0
            self._set("circles", circles)
            return "wrong"
        circles[circle] = circles.get(circle, 0) + 1
        self._set("circles", circles)
        if not all(self.circle_done(t) for t in TRADES):
            return "filled" if self.circle_done(circle) else "ok"
        self.set_phase(PORTAL)
        return "all"

    # --- Fase 3: el portal ------------------------------------------------------------
    def part_in_house(self, house):
        """(id, nombre) de la parte del insecto escondida en esa casa, o None."""
        houses = self.setup["part_houses"]
        return PARTS[houses.index(house)] if house in houses else None

    def parts_found(self, inventory):
        return sum(1 for pid, _ in PARTS if inventory.has(pid))

    def part_taken(self, pid):
        """True si esa parte ya se recogió en esta partida (no vuelve a aparecer,
        aunque el yunque la gaste al forjar Void Impact)."""
        return pid in self._get("parts_taken", [])

    def take_part(self, pid):
        taken = list(self._get("parts_taken", []))
        if pid not in taken:
            self._set("parts_taken", taken + [pid])

    # --- Easter eggs ---------------------------------------------------------------
    def has_plush(self, house):
        return house in self.setup["plush_houses"]

    def touch_plush(self, house):
        """Devuelve cuántos peluches distintos se han tocado (3 = «Alguien te observa»)."""
        touched = set(self._get("plush", []))
        touched.add(house)
        self._set("plush", sorted(touched))
        return len(touched)

    def barrel_has_seeds(self, number):
        return number in self.setup["seed_barrels"]

    @property
    def seeds_eaten(self):
        return list(self._get("seeds", []))

    def feed_chicken(self, number):
        """El pollo come las semillas del barril `number`. Devuelve cuántas lleva."""
        eaten = self.seeds_eaten
        if number not in eaten:
            eaten.append(number)
            self._set("seeds", eaten)
        return len(eaten)

    @property
    def chicken(self):
        """"coop" (en el gallinero) | "carried" (lo llevas) | "mutated" (huyó)."""
        return self._get("chicken", "coop")

    def set_chicken(self, value):
        self._set("chicken", value)

    def use_well(self, number):
        """Suma un uso al pozo. True si es el pozo especial y llega a WELL_USES (y reinicia)."""
        uses = dict(self._get("wells", {}))
        key = str(number)
        uses[key] = uses.get(key, 0) + 1
        special = number == self.setup["special_well"] and uses[key] >= WELL_USES
        if special:
            uses[key] = 0
        self._set("wells", uses)
        return special
