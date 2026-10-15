"""Objetos de la Aldea del vacío (misión y easter eggs: systems/village_quest.py).

    PhaseBlock      llamas / cristales del vacío que cierran un paso (con "phases")
    ClockActivator  uno de los 12 activadores de la plaza (hora 1-12)
    VillageItem     lo que se esconde en las casas: diario, peluche o parte del insecto
                    (el sorteo de la partida decide en qué casas hay de cada uno)
    VoidCircle      círculo del vacío de un oficio: recibe almas
    Anvil           yunque de la herrería: forja Void Impact con las tres partes
    VoidBarrier     barrera del Void Insect: solo la rompe quien tenga Void Impact
    Barrel          se rompe; en tres (al azar) hay semillas del vacío para el pollo
    Chicken         el pollo del gallinero: se lleva en brazos y muta con 3 semillas
    Well            pozo; uno (al azar) te devuelve al principio a la 3ª vez

Todos leen y cambian la misión con ctx.village (VillageQuest). JSON en
tools/generar_aldea.py, que genera maps/aldea.json.
"""
import math
import random

import pygame

from entities.chest import CARD_PREFIX
from entities.entity import RectEntity
from entities.interactable import Interactable
from game import settings
from systems import village_quest as Q


class PhaseBlock(Interactable, RectEntity):
    """Bloque que cierra un paso mientras exista (sus "phases" del JSON). No se
    puede quitar: lo quita la misión al cambiar de fase."""
    prompt_verb = "Examinar"

    def __init__(self, rect, obj_id=None, name="Llamas", style="fire", height=70, text=None):
        RectEntity.__init__(self, rect, height)
        self.id = obj_id
        self.name = name
        self.style = style
        self.enabled = True
        self.interact_range = settings.INTERACT_RANGE
        self.secret_id = None
        self.solid = True
        self.text = text or ["Las llamas cierran el paso."]
        self._t = random.uniform(0, 3)

    def update(self, dt, ctx):
        self._t += dt

    def interact(self, ctx):
        ctx.show_dialogue(self.text)

    def get_image(self, assets):
        frame = int(self._t * 6) % 2 if self.style == "fire" else 0
        return assets.get_block(f"{self.style}block_{frame}", self.footprint.w, self.footprint.h, self.height)

    @classmethod
    def from_data(cls, d):
        return cls(d["rect"], d.get("id"), d.get("name", "Llamas"), d.get("style", "fire"),
                   d.get("height", 70), d.get("text"))


class ClockActivator(Interactable):
    def __init__(self, x, y, obj_id, hour):
        super().__init__(x, y, obj_id, f"Activador · {hour}", f"clock_off_{hour}", hitbox=(26, 14),
                         shadow=(30, 10))
        self.hour = hour
        self.prompt_verb = f"Activar ({hour})"

    def update(self, dt, ctx):
        on = self.hour in ctx.village.clock_progress or ctx.village.phase != Q.CLOCKS
        self.sprite_key = f"clock_{'on' if on else 'off'}_{self.hour}"

    def interact(self, ctx):
        result = ctx.village.press_clock(self.hour)
        name = f"La piedra de las {self.hour}"
        if result == "already":
            ctx.show_dialogue([f"{name} ya brilla con luz morada."])
        elif result == "wrong":
            ctx.show_dialogue([f"{name} se enciende un instante... y se apaga con un chasquido.",
                               "Todas las piedras del reloj se apagan a la vez."])
        elif result == "on":
            done = len(ctx.village.clock_progress)
            ctx.show_dialogue([f"{name} se enciende con un zumbido grave. ({done}/3)"])
        elif result == "done":
            ctx.show_dialogue([f"{name} se enciende. Las tres piedras laten a la vez...",
                               "Un temblor recorre la aldea. Las llamas que cerraban los caminos se apagan "
                               "de golpe y algo se abre en la granja, la herrería y el mercado."])
        else:
            ctx.show_dialogue(["La piedra está fría. El reloj ya ha hecho su trabajo."])

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), int(d["hour"]))


class VillageItem(Interactable):
    """Diario, peluche o parte del insecto en la casa `house`. Solo existe si el
    sorteo de la partida puso uno de ese tipo en esa casa (las partes, además,
    desde la fase del portal y hasta que se recogen)."""
    KINDS = {"diary": ("Diario", "diary", "Leer"), "plush": ("Peluche", "plush_void", "Tocar"),
             "part": ("Algo que brilla", "void_part", "Coger")}

    def __init__(self, x, y, obj_id, kind, house):
        name, sprite, verb = self.KINDS[kind]
        super().__init__(x, y, obj_id, name, sprite, hitbox=(24, 14), solid=False, shadow=(26, 8))
        self.kind = kind
        self.house = house
        self.prompt_verb = verb
        self.visible = False

    def present(self, ctx):
        quest = ctx.village
        if self.kind == "diary":
            return quest.diary(self.house) is not None
        if self.kind == "plush":
            return quest.has_plush(self.house)
        part = quest.part_in_house(self.house)
        return part is not None and quest.phase >= Q.PORTAL and not quest.part_taken(part[0])

    def update(self, dt, ctx):
        self.visible = self.present(ctx)
        if self.kind == "part" and self.visible:
            self.sprite_key = f"void_part_{Q.PARTS.index(ctx.village.part_in_house(self.house))}"

    def interact(self, ctx):
        quest = ctx.village
        if self.kind == "diary":
            title, pages = quest.diary(self.house)
            ctx.show_dialogue(pages, speaker=title)
        elif self.kind == "plush":
            n = quest.touch_plush(self.house)
            pages = ["Un peluche de trapo. Está frío, y un aura morada le sale de las costuras."]
            if n >= 3:
                pages.append("Al tocarlo, sientes un escalofrío en la nuca...")
                ctx.show_dialogue(pages, on_close=lambda: ctx.notify("Alguien te observa.", "discovery"))
                return
            ctx.show_dialogue(pages)
        else:
            pid, pname = quest.part_in_house(self.house)
            if quest.part_taken(pid):
                return
            quest.take_part(pid)
            ctx.state.inventory.add(pid)
            found = quest.parts_found(ctx.state.inventory)
            pages = [f"Has encontrado {pname}. Todavía se mueve un poco. ({found}/3)"]
            if found == 3:
                pages.append("Con las tres partes, quizá se pueda forjar algo en el yunque de la herrería.")
            ctx.show_dialogue(pages)

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d["kind"], int(d["house"]))


class VoidCircle(Interactable):
    prompt_verb = "Ofrecer alma" if Q.SOULS_REQUIRED else "Activar"

    def __init__(self, x, y, obj_id, trade):
        super().__init__(x, y, obj_id, f"Círculo del vacío ({Q.TRADE_NAMES[trade]})", "void_circle_0",
                         hitbox=(70, 26), solid=False)
        self.trade = trade
        self._t = 0.0

    def update(self, dt, ctx):
        self._t += dt
        # El dibujo tiene 4 estados (0-3 almas): se escala a las que pida el círculo
        count = min(Q.SOULS_PER_CIRCLE, ctx.village.circle_count(self.trade))
        self.sprite_key = f"void_circle_{3 * count // Q.SOULS_PER_CIRCLE}"
        self.sprite_offset = (0, 0)

    @property
    def sort_y(self):
        return self.y - 40              # se dibuja como suelo: debajo del jugador

    def interact(self, ctx):
        quest = ctx.village
        trade = Q.TRADE_NAMES[self.trade]
        result = quest.offer_soul(self.trade)
        count, need = quest.circle_count(self.trade), Q.SOULS_PER_CIRCLE
        sinks = (f"El alma se hunde en el círculo. ({count}/{need})" if Q.SOULS_REQUIRED
                 else "Las runas se encienden en cuanto lo pisas.")
        if result == "empty":
            wants = (f"el alma de un {trade} de la aldea." if need == 1
                     else f"las almas de los {trade}s de la aldea.")
            ctx.show_dialogue([f"Un círculo de runas moradas grabado a fuego en el suelo. ({count}/{need})",
                               f"Parece que espera algo... {wants}"])
        elif result == "complete":
            ctx.show_dialogue(["El círculo está lleno. " + ("El alma gira dentro, en silencio." if need == 1
                                                             else "Las almas giran dentro, en silencio.")])
        elif result == "wrong":
            ctx.show_dialogue(["El alma no es de este oficio. El círculo se agita...",
                               f"¡El alma escapa chillando hacia el cielo, y con ella las que guardaba! (0/{need})"])
        elif result == "ok":
            ctx.show_dialogue([f"El alma se hunde en el círculo. ({count}/{need})"])
        elif result == "filled":
            ctx.show_dialogue([sinks,
                               f"El círculo de {Q.CIRCLE_PLACES[self.trade]} se cierra con un destello."])
        else:   # "all"
            ctx.show_dialogue([sinks,
                               "Los tres círculos se encienden a la vez. Un rayo morado sube hasta el portal...",
                               "Sobre el mercado aparecen rocas flotando en el aire, una tras otra, como "
                               "escalones hacia el cielo."])

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d["trade"])


class Anvil(Interactable):
    prompt_verb = "Usar yunque"

    def __init__(self, x, y, obj_id=None):
        super().__init__(x, y, obj_id, "Yunque", "anvil", hitbox=(44, 16), shadow=(50, 12))

    def interact(self, ctx):
        inv = ctx.state.inventory
        if inv.has(CARD_PREFIX + Q.VOID_CARD):
            ctx.show_dialogue(["El yunque aún está caliente. Ya forjaste aquí el Void Impact."])
            return
        found = ctx.village.parts_found(inv)
        if found < 3:
            pages = ["Un yunque enorme. El martillo sigue encima, como si el herrero fuera a volver."]
            if ctx.village.phase >= Q.PORTAL:
                pages.append(f"Con las partes del insecto del vacío se podría forjar algo. ({found}/3)")
            ctx.show_dialogue(pages)
            return
        for pid, _ in Q.PARTS:
            inv.remove(pid)
        inv.add(CARD_PREFIX + Q.VOID_CARD)
        ctx.on_card_unlocked(Q.VOID_CARD)
        ctx.show_dialogue(["Pones la pata, el ala y el aguijón sobre el yunque y golpeas con el martillo...",
                           "Cada golpe suena dentro de tu cabeza. Al final queda una carta que vibra.",
                           "Has conseguido la carta «Void Impact».",
                           "Ya puedes ponerla en tu mazo (TAB > Editar mazos). Con ella podrás romper "
                           "la barrera del insecto."])

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"))


class VoidBarrier(Interactable):
    """Cúpula alrededor del Void Insect. Mientras existe, no se le puede tocar."""
    prompt_verb = "Examinar barrera"

    def __init__(self, x, y, obj_id=None, secret=Q.BARRIER_SECRET):
        super().__init__(x, y, obj_id, "Barrera del vacío", "void_barrier", hitbox=(150, 70))
        self.secret_id = secret
        self.broken = False

    def on_secret_unlocked(self, ctx):
        self._break()

    def _break(self):
        self.broken = True
        self.visible = False
        self.solid = False
        self.enabled = False

    def interact(self, ctx):
        if not ctx.state.inventory.has(CARD_PREFIX + Q.VOID_CARD):
            ctx.show_dialogue(["Una cúpula de energía morada envuelve al insecto. Al tocarla te tiembla todo el cuerpo.",
                               "Nada de este mundo la atraviesa. Haría falta algo hecho del mismo vacío...",
                               "Quizá con partes del propio insecto, forjadas en la herrería."])
            return
        ctx.show_dialogue(["Sacas la carta Void Impact. La barrera la reconoce y se resquebraja...",
                           "¡La cúpula estalla en mil pedazos! El insecto se gira hacia ti."],
                          on_close=lambda: ctx.unlock_secret(self.secret_id))

    def get_state(self):
        return {"broken": self.broken}

    def set_state(self, state):
        if state.get("broken"):
            self._break()

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("secret", Q.BARRIER_SECRET))


class Barrel(Interactable):
    def __init__(self, x, y, obj_id, number):
        super().__init__(x, y, obj_id, "Barril", "barrel", hitbox=(26, 14), shadow=(30, 10))
        self.number = number
        self.broken = False

    def update(self, dt, ctx):
        if not self.broken:
            self.sprite_key = "barrel"
            self.prompt_verb = "Romper"
            return
        quest = ctx.village
        seeds = quest.barrel_has_seeds(self.number) and self.number not in quest.seeds_eaten
        self.sprite_key = "barrel_seeds" if seeds else "barrel_broken"
        self.prompt_verb = "Dar las semillas al pollo" if seeds and quest.chicken == "carried" else "Examinar"

    def interact(self, ctx):
        quest = ctx.village
        if not self.broken:
            self.broken = True
            self.solid = False
            if quest.barrel_has_seeds(self.number):
                ctx.show_dialogue(["Rompes el barril de una patada. Entre las duelas hay un puñado de semillas...",
                                   "Brillan con un aura morada. A alguien con pico le encantarían."])
            else:
                ctx.notify("Rompes el barril. Solo había ceniza.")
            return
        if not quest.barrel_has_seeds(self.number):
            ctx.show_dialogue(["Astillas y ceniza."])
        elif self.number in quest.seeds_eaten:
            ctx.show_dialogue(["Aquí había semillas del vacío. El pollo no dejó ni una."])
        elif quest.chicken == "carried":
            n = quest.feed_chicken(self.number)
            pages = [f"El pollo se lanza a picotear las semillas. Sus ojos brillan un instante. ({n}/3)"]
            if n >= 3:
                pages += ["El pollo se retuerce, crece, se estira... ¡y se pone de pie sobre dos patas humanas!",
                          "El pollo humanoide te mira, cacarea con voz grave y sale corriendo hacia el bosque."]
                ctx.show_dialogue(pages, on_close=lambda: ctx.chicken_mutates())
                return
            ctx.show_dialogue(pages)
        else:
            ctx.show_dialogue(["Semillas con un aura morada. Tú no te las comerías... pero algún animal sí."])

    def get_state(self):
        return {"broken": self.broken}

    def set_state(self, state):
        self.broken = state.get("broken", False)
        self.solid = not self.broken

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), int(d["number"]))


class Chicken(Interactable):
    """El único pollo superviviente. En el gallinero pasea; si lo coges, te sigue
    en brazos (ctx.village.chicken == "carried")."""
    prompt_verb = "Coger el pollo"

    def __init__(self, x, y, obj_id="pollo", radius=50):
        super().__init__(x, y, obj_id, "Pollo", "chicken", hitbox=(18, 10), solid=False, shadow=(18, 6))
        self.home = pygame.Vector2(x, y)
        self.radius = radius
        self._target = None
        self._wait = 1.0
        self._t = random.uniform(0, 6)
        self.facing_left = False
        self._run = None            # hacia dónde huye el pollo humanoide

    def can_interact(self):
        return self.visible and self.enabled and self._quest_state == "coop"

    _quest_state = "coop"

    def update(self, dt, ctx):
        self._t += dt
        state = self._quest_state = ctx.village.chicken
        if state == "mutated":
            self._update_run(dt)
            return
        if state == "carried":
            p = ctx.player
            side = -1 if p.facing in ("right", "down") else 1
            self.x, self.y = p.x + side * 16, p.y + 2
            self.facing_left = side > 0
            self.sprite_offset = (0, -26 + round(math.sin(self._t * 6)))
            self.sprite_key = "chicken"
            return
        self.sprite_offset = (0, 0)
        self._wander(dt)

    def _wander(self, dt):
        if self._target is None:
            self._wait -= dt
            if self._wait > 0:
                return
            a = random.uniform(0, math.tau)
            self._target = self.home + pygame.Vector2(math.cos(a), math.sin(a) * 0.6) * random.uniform(8, self.radius)
        d = self._target - pygame.Vector2(self.x, self.y)
        if d.length() < 3:
            self._target, self._wait = None, random.uniform(0.6, 2.0)
            return
        step = d.normalize() * min(40 * dt, d.length())
        self.x += step.x
        self.y += step.y
        self.facing_left = step.x < 0
        self.sprite_offset = (0, -abs(round(math.sin(self._t * 14) * 2)))

    def _update_run(self, dt):
        if self._run is None:
            self.visible = False
            return
        self.sprite_key = "chicken_humanoid"
        d = self._run - pygame.Vector2(self.x, self.y)
        if d.length() < 8:
            self._run = None
            self.visible = False
            return
        step = d.normalize() * min(260 * dt, d.length())
        self.x += step.x
        self.y += step.y
        self.facing_left = step.x < 0
        self.sprite_offset = (0, -abs(round(math.sin(self._t * 16) * 3)))

    def interact(self, ctx):
        ctx.village.set_chicken("carried")
        ctx.show_dialogue(["Coges al pollo. Se revuelve un poco y luego se acurruca contra ti.",
                           "(Si te ve pelear, se escapará al gallinero.)"])

    def run_away(self, target):
        """Muta: corre hacia `target` y desaparece."""
        self._run = pygame.Vector2(target)
        self.visible = True

    def return_home(self):
        self.x, self.y = self.home.x, self.home.y
        self._target = None
        self.sprite_offset = (0, 0)

    def get_image(self, assets):
        img = super().get_image(assets)
        if img is not None and self.facing_left:
            img = pygame.transform.flip(img, True, False)
        return img

    def set_state(self, state):
        pass

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id", "pollo"), d.get("radius", 50))


class Well(Interactable):
    prompt_verb = "Asomarse"

    def __init__(self, x, y, obj_id, number):
        super().__init__(x, y, obj_id, "Pozo", "well", hitbox=(46, 22), shadow=(54, 14))
        self.number = number

    def interact(self, ctx):
        if ctx.village.use_well(self.number):
            ctx.show_dialogue(["Te asomas otra vez. Del fondo sube un susurro que dice tu nombre..."],
                              on_close=lambda: ctx.blackout_to_start("Buen intento."))
        else:
            ctx.show_dialogue([random.choice(["Un pozo de piedra. El fondo está demasiado oscuro para verlo.",
                                              "Tiras una piedrecita. No se oye el agua.",
                                              "Huele a humedad... y a algo dulce, como fruta podrida."])])

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), int(d["number"]))
