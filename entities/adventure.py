"""Objetos de AVENTURA: solo se pueden usar con el personaje adecuado.

Cada personaje jugable tiene una habilidad de aventura
(combate/game/characters.py: Character.adventure). Un objeto con
`requires_ability` solo muestra su indicador «E - ...» (y solo se puede usar)
si el personaje elegido en el menú de pausa tiene esa habilidad: no hay un
botón aparte para la habilidad. Lo filtra systems/interaction_system.py.

    LeafWall   "burn" (Blaze)   pared de hojas que cierra un paso; al quemarla desaparece
    JumpSpot   "jump" (Hero)    punto de salto: lleva al jugador de un salto a `target`

JSON:
    { "type": "leaf_wall", "id": "hojas_1", "rect": [x, y, w, h], "height": 70,
      "style": "leaves" | "roots" }     # roots: maraña de raíces secas (cuevas)
    { "type": "jump_spot", "id": "salto_1", "pos": [x, y], "target": [x, y], "verb": "Saltar arriba" }
"""
from entities.entity import RectEntity
from entities.interactable import Interactable
from game import settings

BURN_TIME = 0.9          # segundos que tarda en arder la pared


class LeafWall(Interactable, RectEntity):
    prompt_verb = "Quemar hojas"
    requires_ability = "burn"

    def __init__(self, rect, obj_id=None, name="Pared de hojas", height=70, style="leaves"):
        RectEntity.__init__(self, rect, height)
        self.style = style
        self._key = "rootwall" if style == "roots" else "leafwall"
        if style == "roots":
            self.prompt_verb = "Quemar raíces"
        self.id = obj_id
        self.name = name
        self.enabled = True
        self.interact_range = settings.INTERACT_RANGE
        self.secret_id = None
        self.burned = False
        self.burning = 0.0          # > 0 mientras arde

    @property
    def solid(self):
        return not self.burned

    def can_interact(self):
        return self.enabled and not self.burned and self.burning <= 0

    def interact(self, ctx):
        self.burning = BURN_TIME
        what = "las raíces" if self.style == "roots" else "las hojas"
        ctx.notify(f"{ctx.player_character_name} prende fuego a {what}...")

    def update(self, dt, ctx):
        if self.burning > 0:
            self.burning -= dt
            if self.burning <= 0:
                self.burned = True
                self.visible = False
                ctx.notify("El paso está libre.", "discovery")

    def get_image(self, assets):
        if self.burning > 0:
            frame = int(self.burning * 10) % 2
            return assets.get_block(f"{self._key}_burning{frame}", self.footprint.w, self.footprint.h, self.height)
        return assets.get_block(self._key, self.footprint.w, self.footprint.h, self.height)

    def get_state(self):
        return {"burned": self.burned or self.burning > 0}

    def set_state(self, state):
        self.burned = state.get("burned", False)
        self.visible = not self.burned

    @classmethod
    def from_data(cls, d):
        return cls(d["rect"], d.get("id"), d.get("name", "Pared de hojas"), d.get("height", 70),
                   d.get("style", "leaves"))


class JumpSpot(Interactable):
    prompt_verb = "Saltar"
    requires_ability = "jump"

    def __init__(self, x, y, obj_id=None, target=(0, 0), name="Punto de salto", verb=None):
        super().__init__(x, y, obj_id, name, "jump_spot", hitbox=(30, 14), solid=False)
        self.target = (float(target[0]), float(target[1]))
        if verb:
            self.prompt_verb = verb

    def interact(self, ctx):
        ctx.jump_to(self.target)

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d["target"], d.get("name", "Punto de salto"), d.get("verb"))
