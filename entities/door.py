"""Puertas: bloqueadas, desbloqueables y puertas secretas.

    door.is_locked   -> bool
    door.unlock()    -> la abre y deja de ser sólida

Una puerta puede pedir una llave (`key_id`). Cuando exista un inventario
real bastará con que ctx.state.inventory.has(key_id) devuelva True.
"""
from entities.entity import RectEntity
from entities.interactable import Interactable
from game import settings


class Door(Interactable, RectEntity):
    prompt_verb = "Abrir"

    def __init__(self, rect, obj_id=None, name="Puerta", style="wood", height=64,
                 is_locked=True, key_id=None, locked_text=None):
        RectEntity.__init__(self, rect, height)
        self.id = obj_id
        self.name = name
        self.enabled = True
        self.interact_range = settings.INTERACT_RANGE
        self.secret_id = None
        self.style = style
        self.is_locked = is_locked
        self.is_open = not is_locked
        self.key_id = key_id
        self.locked_text = locked_text or ["Está cerrada."]

    @property
    def solid(self):
        return not self.is_open

    def can_interact(self):
        # Una puerta abierta ya no necesita indicador de interacción.
        return self.enabled and not self.is_open

    def unlock(self):
        self.is_locked = False
        self.is_open = True

    def lock(self):
        self.is_locked = True
        self.is_open = False

    def interact(self, ctx):
        if self.is_locked and self.key_id and ctx.state.inventory.has(self.key_id):
            self.unlock()
            ctx.notify(f"{self.name}: abierta.")
            return
        if self.is_locked:
            ctx.show_dialogue(self.locked_text)
        else:
            self.is_open = True

    def get_image(self, assets):
        state = "open" if self.is_open else "closed"
        return assets.get_block(f"door_{self.style}_{state}", self.footprint.w,
                                self.footprint.h, self.height)

    def get_state(self):
        return {"is_locked": self.is_locked, "is_open": self.is_open}

    def set_state(self, state):
        self.is_locked = state.get("is_locked", self.is_locked)
        self.is_open = state.get("is_open", self.is_open)

    @classmethod
    def from_data(cls, d):
        text = d.get("locked_text")
        if isinstance(text, str):
            text = [text]
        return cls(d["rect"], d.get("id"), d.get("name", "Puerta"), d.get("style", "wood"),
                   d.get("height", 64), d.get("locked", True), d.get("key"), text)


class SecretDoor(Door):
    """Puerta camuflada que se abre cuando se desbloquea un secreto."""
    prompt_verb = "Examinar"

    def __init__(self, rect, obj_id, secret_id, name="Muro", height=72, hidden_text=None,
                 style="secret"):
        super().__init__(rect, obj_id, name, style, height, is_locked=True,
                         locked_text=hidden_text)
        self.secret_id = secret_id
        self.secret_unlocked = False

    def on_secret_unlocked(self, ctx):
        self.secret_unlocked = True
        self.unlock()

    @classmethod
    def from_data(cls, d):
        text = d.get("hidden_text")
        if isinstance(text, str):
            text = [text]
        return cls(d["rect"], d.get("id"), d["secret"], d.get("name", "Muro"),
                   d.get("height", 72), text, d.get("style", "secret"))
