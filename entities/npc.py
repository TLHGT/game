"""NPC reutilizable con diálogo lineal por páginas.

Formato en el JSON del mapa:
    {
      "type": "npc", "id": "brann", "name": "Brann", "look": "woodcutter",
      "pos": [x, y],
      "dialogue": ["Página 1", "Página 2"],
      "repeat_dialogue": ["Lo que dice a partir de la 2ª vez"],
      "conditional_dialogue": [
          {"requires_secret": "arken_shrine", "pages": ["..."]}
      ]
    }
"""
import math

from entities.interactable import Interactable


class NPC(Interactable):
    prompt_verb = "Hablar"

    def __init__(self, x, y, obj_id, name, look="default", dialogue=None,
                 repeat_dialogue=None, conditional_dialogue=None):
        super().__init__(x, y, obj_id, name, f"npc_{look}", hitbox=(24, 14), shadow=(30, 10))
        self.look = look
        self.dialogue = dialogue or ["..."]
        self.repeat_dialogue = repeat_dialogue
        self.conditional_dialogue = conditional_dialogue or []
        self.talk_count = 0
        self._t = 0.0
        # Punto de extensión: aquí podría ir un dialogue_id para un sistema
        # de diálogos ramificados, una quest asociada, una tienda...

    def pick_pages(self, ctx):
        # Los diálogos condicionados por secretos tienen prioridad.
        for entry in self.conditional_dialogue:
            if ctx.secrets.is_unlocked(entry["requires_secret"]):
                return entry["pages"]
        if self.talk_count > 0 and self.repeat_dialogue:
            return self.repeat_dialogue
        return self.dialogue

    def interact(self, ctx):
        ctx.show_dialogue(self.pick_pages(ctx), speaker=self.name)
        self.talk_count += 1

    def update(self, dt, ctx):
        # Pequeña "respiración" para que el NPC no parezca una estatua.
        self._t += dt
        self.sprite_offset = (0, round(math.sin(self._t * 2.2) * 1.2))

    def get_state(self):
        return {"talk_count": self.talk_count}

    def set_state(self, state):
        self.talk_count = state.get("talk_count", 0)

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("name", ""),
                   d.get("look", "default"), d.get("dialogue"),
                   d.get("repeat_dialogue"), d.get("conditional_dialogue"))
