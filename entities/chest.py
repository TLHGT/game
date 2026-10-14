"""Cofre: se abre una vez, cambia de sprite y entrega un objeto.

Con "card": "<id>" en el JSON entrega una CARTA bloqueada (las que no están en
settings.AVAILABLE_CARDS): desde ese momento se puede usar en el mazo."""
from entities.interactable import Interactable

CARD_PREFIX = "card_"     # objeto "card_ice_shard" = la carta Ice Shard desbloqueada


class Chest(Interactable):
    def __init__(self, x, y, obj_id, item_id, item_name, empty_text="El cofre está vacío."):
        super().__init__(x, y, obj_id, "Cofre", "chest_closed", hitbox=(40, 22), shadow=(48, 12))
        self.item_id = item_id
        self.item_name = item_name
        self.empty_text = empty_text
        self.opened = False

    @property
    def prompt_verb(self):
        return "Examinar" if self.opened else "Abrir"

    def interact(self, ctx):
        if self.opened:
            ctx.show_dialogue([self.empty_text])
            return
        self.opened = True
        self.sprite_key = "chest_open"
        # Inventario provisional: solo registra el objeto.
        ctx.state.inventory.add(self.item_id)
        # item_name incluye el artículo: "una Poción", "el Amuleto de Arken"...
        pages = [f"Has encontrado {self.item_name}."]
        if self.item_id.startswith(CARD_PREFIX):
            # Carta bloqueada: desde ahora se puede usar
            ctx.on_card_unlocked(self.item_id[len(CARD_PREFIX):])
            pages.append("Ya puedes ponerla en tu mazo (TAB > Editar mazos).")
        ctx.show_dialogue(pages)

    def get_state(self):
        return {"opened": self.opened}

    def set_state(self, state):
        self.opened = state.get("opened", False)
        self.sprite_key = "chest_open" if self.opened else "chest_closed"

    @classmethod
    def from_data(cls, d):
        if d.get("card"):
            # { "type": "chest", "card": "ice_shard" }: desbloquea esa carta
            from combate.cards.card_database import CARDS
            name = CARDS[d["card"]]["name"]
            return cls(d["pos"][0], d["pos"][1], d.get("id"), CARD_PREFIX + d["card"],
                       d.get("item_name", f"la carta «{name}»"))
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("item", "item"),
                   d.get("item_name", "objeto"))
