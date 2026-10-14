"""Objetos del hospital: ascensor, máquinas de ventajas y el cuarto secreto.

    Elevator     ascensor del centro de cada piso. Solo funciona si su piso tiene
                 corriente (los secretos de `requires` de ese piso, en
                 maps/elevators.json). Abre un menú con los pisos: solo se puede
                 ir a los que también tienen corriente.
    PerkMachine  máquina de ventajas de un piso (1-4). Se encienden en el orden de
                 la secuencia del ordenador del cuarto secreto (systems/perk_puzzle.py),
                 que es aleatoria en cada partida.
    PerkCode     el ordenador del cuarto secreto, que muestra la secuencia.
    PackAPunch   recompensa del puzle: funciona cuando las cuatro máquinas están
                 encendidas en orden.

JSON:
    { "type": "elevator", "id": "ascensor", "rect": [x, y, w, h], "height": 80,
      "group": "hospital", "floor": "hospital_piso1" }
    { "type": "perk_machine", "id": "perk_p2", "perk": "juggernog", "name": "Juggernog",
      "floor": 2, "pos": [x, y] }
    { "type": "perk_code", "id": "ordenador", "name": "Ordenador", "sprite": "monitor", "pos": [x, y],
      "text": ["... {code} ..."] }                       # {code} = la secuencia (p. ej. 2413)
    { "type": "pack_a_punch", "id": "pap", "pos": [x, y], "item": "...", "item_name": "..." }
"""
import json
import os

from entities.entity import RectEntity
from entities.interactable import Interactable
from entities.sign import Sign
from game import settings
from systems.perk_puzzle import SECRET_ID

_GROUPS = {}


def elevator_floors(group):
    """Pisos de un grupo de ascensores (maps/elevators.json), en orden."""
    if group not in _GROUPS:
        path = os.path.join(settings.MAP_DIR, "elevators.json")
        try:
            with open(path, encoding="utf-8") as f:
                _GROUPS.update(json.load(f))
        except OSError:
            pass
    return _GROUPS.get(group, [])


def power_messages(secret_id, secrets):
    """Mensajes de pisos que necesitan VARIAS energías y que `secret_id` acaba de
    completar (p. ej. el Piso 4 del hospital, que pide las de los demás pisos)."""
    elevator_floors("hospital")          # carga maps/elevators.json
    out = []
    for floors in _GROUPS.values():
        for f in floors:
            req = f.get("requires", [])
            if f.get("unlock_message") and secret_id in req and all(secrets.is_unlocked(s) for s in req):
                out.append(f["unlock_message"])
    return out


def has_power(floor, secrets):
    return all(secrets.is_unlocked(s) for s in floor.get("requires", []))


class Elevator(Interactable, RectEntity):
    prompt_verb = "Usar ascensor"

    def __init__(self, rect, obj_id="ascensor", group="hospital", floor=None, height=80, name="Ascensor"):
        RectEntity.__init__(self, rect, height)
        self.id = obj_id
        self.name = name
        self.enabled = True
        self.interact_range = settings.INTERACT_RANGE
        self.secret_id = None
        self.group = group
        self.floor = floor
        self.powered = False
        self.solid = True

    @property
    def floors(self):
        return elevator_floors(self.group)

    def here(self):
        return next((f for f in self.floors if f["map"] == self.floor), {})

    def update(self, dt, ctx):
        self.powered = has_power(self.here(), ctx.secrets)

    def interact(self, ctx):
        if not has_power(self.here(), ctx.secrets):
            ctx.show_dialogue(self.here().get("no_power_text") or
                              ["El ascensor no tiene corriente.",
                               "Busca el activador de energía de este piso."])
            return
        options = []
        for f in self.floors:
            if f["map"] == self.floor:
                options.append((f"{f['name']}  (aquí)", False, None))
            elif has_power(f, ctx.secrets):
                options.append((f["name"], True, f))
            else:
                options.append((f"{f['name']}  (sin corriente)", False, None))
        ctx.open_choice("Ascensor", options,
                        lambda f: ctx.travel(f["map"], f.get("spawn", "elevator"),
                                             f"El ascensor sube... {f['name']}."))

    def get_image(self, assets):
        state = "open" if self.powered else "closed"
        return assets.get_block(f"door_metal_{state}", self.footprint.w, self.footprint.h, self.height)

    @classmethod
    def from_data(cls, d):
        return cls(d["rect"], d.get("id", "ascensor"), d.get("group", "hospital"), d.get("floor"),
                   d.get("height", 80), d.get("name", "Ascensor"))


class PerkMachine(Interactable):
    prompt_verb = "Encender"

    def __init__(self, x, y, obj_id, perk, name, floor):
        super().__init__(x, y, obj_id, name, f"perk_{perk}_off", hitbox=(40, 16), shadow=(46, 12))
        self.perk = perk
        self.floor = floor

    def update(self, dt, ctx):
        on = ctx.perks.is_on(self.floor) or ctx.perks.complete
        self.sprite_key = f"perk_{self.perk}_{'on' if on else 'off'}"
        self.prompt_verb = "Examinar" if on else "Encender"

    def interact(self, ctx):
        result = ctx.perks.press(self.floor)
        if result == "already":
            ctx.show_dialogue([f"{self.name} zumba encendida. Huele a refresco caliente."], speaker=self.name)
        elif result == "wrong":
            ctx.show_dialogue([f"{self.name} chisporrotea y se apaga de golpe...",
                               "En todo el hospital se oye cómo las máquinas se apagan una tras otra."],
                              speaker=self.name)
        elif result == "done":
            ctx.show_dialogue([f"{self.name} se enciende con una melodía pegadiza.",
                               "Las cuatro máquinas suenan a la vez. Algo se ha encendido en el lobby."],
                              speaker=self.name, on_close=lambda: ctx.unlock_secret(SECRET_ID))
        else:
            done = len(ctx.perks.progress)
            ctx.show_dialogue([f"{self.name} se enciende con una melodía pegadiza. ({done}/4)"],
                              speaker=self.name)

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("perk", "juggernog"),
                   d.get("name", "Máquina"), int(d.get("floor", 1)))


class PerkCode(Sign):
    """Texto con la secuencia del puzle: "{code}" se sustituye al leerlo."""
    def interact(self, ctx):
        ctx.show_dialogue([p.format(code=ctx.perks.code) for p in self.pages], speaker=self.name or None)


class PackAPunch(Interactable):
    def __init__(self, x, y, obj_id, item_id, item_name, name="Pack-a-Punch"):
        super().__init__(x, y, obj_id, name, "perk_pack_a_punch_off", hitbox=(40, 16), shadow=(46, 12))
        self.item_id = item_id
        self.item_name = item_name
        self.given = False

    @property
    def prompt_verb(self):
        return "Examinar" if self.given else "Usar"

    def update(self, dt, ctx):
        on = ctx.secrets.is_unlocked(SECRET_ID)
        self.sprite_key = f"perk_pack_a_punch_{'on' if on else 'off'}"

    def interact(self, ctx):
        if self.given:
            ctx.show_dialogue(["La máquina ronronea satisfecha. Ya no tiene nada más para ti."], speaker=self.name)
        elif not ctx.secrets.is_unlocked(SECRET_ID):
            ctx.show_dialogue(["Una máquina enorme, apagada. Tiene cuatro pilotos sin luz.",
                               "Quizá se encienda si las máquinas de los pisos funcionan... en el orden correcto."],
                              speaker=self.name)
        else:
            self.given = True
            ctx.state.inventory.add(self.item_id)
            ctx.show_dialogue(["La máquina traga aire, tiembla y escupe algo con un destello.",
                               f"Has conseguido {self.item_name}."], speaker=self.name)

    def get_state(self):
        return {"given": self.given}

    def set_state(self, state):
        self.given = state.get("given", False)

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("item", "pack_a_punch"),
                   d.get("item_name", "una Lata de Pack-a-Punch"), d.get("name", "Pack-a-Punch"))
