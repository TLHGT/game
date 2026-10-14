"""Estado de partida compartido entre mapas.

Es deliberadamente mínimo: sirve de punto de enganche para inventario,
quests, guardado/carga... sin implementarlos todavía.
"""


class Inventory:
    """Inventario provisional: solo recuerda qué objetos se han recogido."""

    def __init__(self):
        self.items = []

    def add(self, item_id):
        self.items.append(item_id)

    def has(self, item_id):
        return item_id in self.items

    def remove(self, item_id):
        if item_id in self.items:
            self.items.remove(item_id)


class GameState:
    def __init__(self):
        self.flags = {}            # banderas genéricas: "habló_con_brann": True...
        self.inventory = Inventory()
        self.map_states = {}       # map_id -> {objeto_id: estado} (cofres abiertos...)

    def set_flag(self, key, value=True):
        self.flags[key] = value

    def get_flag(self, key, default=False):
        return self.flags.get(key, default)

    def to_dict(self):
        """Base para un futuro sistema de guardado."""
        return {"flags": dict(self.flags), "inventory": list(self.inventory.items),
                "map_states": self.map_states}
