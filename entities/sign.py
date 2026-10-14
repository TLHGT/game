"""Carteles, inscripciones, altares... cualquier cosa que solo se 'lee'."""
from entities.interactable import SPRITE_HITBOX, Interactable


class Sign(Interactable):
    prompt_verb = "Leer"

    def __init__(self, x, y, obj_id, name, pages, sprite="sign", verb=None):
        hb = SPRITE_HITBOX.get(sprite, (30, 14))
        super().__init__(x, y, obj_id, name, sprite, hitbox=hb, shadow=(hb[0] + 6, 10))
        self.pages = pages
        if verb:
            self.prompt_verb = verb

    def interact(self, ctx):
        ctx.show_dialogue(self.pages, speaker=self.name or None)

    @classmethod
    def from_data(cls, d):
        pages = d.get("text", [])
        if isinstance(pages, str):
            pages = [pages]
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("name", ""), pages,
                   d.get("sprite", "sign"), d.get("verb"))
