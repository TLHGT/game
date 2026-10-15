"""Elementos de escenario: árboles, rocas, muros...

Los tipos se definen como datos en PROP_TYPES. Añadir un nuevo objeto
decorativo = añadir una entrada aquí (y opcionalmente su PNG en assets/).
"""
from entities.entity import Entity, RectEntity

# sprite: clave de imagen ({v} se sustituye por la variante)
# hitbox: rectángulo sólido de los pies (no todo el sprite es sólido)
PROP_TYPES = {
    "tree":          dict(sprite="tree_{v}", variants=4, hitbox=(22, 14), shadow=(64, 20), solid=True, fade=True),
    "pine":          dict(sprite="pine_{v}", variants=2, hitbox=(20, 14), shadow=(54, 18), solid=True, fade=True),
    "rock":          dict(sprite="rock", hitbox=(38, 18), shadow=(46, 14), solid=True),
    "stump":         dict(sprite="stump", hitbox=(28, 14), shadow=(34, 10), solid=True),
    "log":           dict(sprite="log", hitbox=(74, 18), shadow=(80, 14), solid=True),
    "bush":          dict(sprite="bush", hitbox=(34, 14), shadow=(44, 12), solid=True),
    "pillar":        dict(sprite="pillar", hitbox=(32, 20), shadow=(40, 14), solid=True, fade=True),
    "pillar_broken": dict(sprite="pillar_broken", hitbox=(32, 20), shadow=(40, 14), solid=True),
    "bed":           dict(sprite="bed", hitbox=(40, 60), shadow=(48, 14), solid=True),
    "cabinet":       dict(sprite="cabinet", hitbox=(44, 18), shadow=(48, 10), solid=True, fade=True),
    "rubble":        dict(sprite="rubble", hitbox=(40, 16), shadow=None, solid=True),
    "tall_grass":    dict(sprite="tall_grass", hitbox=(0, 0), shadow=None, solid=False),
    # Cueva
    "stalagmite":    dict(sprite="stalagmite_{v}", variants=3, hitbox=(24, 14), shadow=(44, 14), solid=True, fade=True),
    "cave_rock":     dict(sprite="cave_rock_{v}", variants=2, hitbox=(36, 16), shadow=(48, 14), solid=True),
    "crystal":       dict(sprite="crystal_{v}", variants=2, hitbox=(26, 12), shadow=(30, 10), solid=True),
    "glowshroom":    dict(sprite="glowshroom", hitbox=(0, 0), shadow=None, solid=False),
    # Aldea del vacío (render/village_sprites.py)
    "dead_tree":     dict(sprite="dead_tree_{v}", variants=3, hitbox=(20, 12), shadow=(44, 14), solid=True, fade=True),
    "flames":        dict(sprite="flames_{v}", variants=3, hitbox=(0, 0), shadow=None, solid=False),
    "fountain":      dict(sprite="fountain", hitbox=(96, 30), shadow=None, solid=True),
    "void_crystal":  dict(sprite="void_crystal_{v}", variants=3, hitbox=(40, 16), shadow=None, solid=True),
    "void_crystal_deco": dict(sprite="void_crystal_{v}", variants=3, hitbox=(0, 0), shadow=None, solid=False),
    "void_portal":   dict(sprite="void_portal", hitbox=(0, 0), shadow=None, solid=False),
    "haystack":      dict(sprite="haystack", hitbox=(50, 18), shadow=(56, 14), solid=True),
    "market_stall":  dict(sprite="market_stall", hitbox=(84, 18), shadow=(88, 14), solid=True, fade=True),
    "forge":         dict(sprite="forge", hitbox=(68, 20), shadow=(74, 14), solid=True, fade=True),
    "crate":         dict(sprite="crate", hitbox=(34, 14), shadow=(38, 10), solid=True),
    "gravestone":    dict(sprite="gravestone", hitbox=(24, 10), shadow=(28, 8), solid=True),
}


class Prop(Entity):
    def __init__(self, kind, x, y, variant=0):
        cfg = PROP_TYPES[kind]
        key = cfg["sprite"].format(v=variant % cfg.get("variants", 1))
        super().__init__(x, y, key, hitbox=cfg["hitbox"], shadow=cfg["shadow"])
        self.kind = kind
        self.solid = cfg["solid"]
        self.fade_when_occluding = cfg.get("fade", False)

    @classmethod
    def from_data(cls, data):
        x, y = data["pos"]
        return cls(data["type"], x, y, data.get("variant", 0))


class Wall(RectEntity):
    """Muro con volumen 2.5D. style='invisible' solo colisiona."""
    solid = True

    def __init__(self, rect, style="stone", height=64):
        super().__init__(rect, height)
        self.style = style
        self.fade_when_occluding = False

    def get_image(self, assets):
        if self.style == "invisible":
            return None
        return assets.get_block(f"wall_{self.style}", self.footprint.w, self.footprint.h, self.height)

    @classmethod
    def from_data(cls, data):
        return cls(data["rect"], data.get("style", "stone"), data.get("height", 64))
