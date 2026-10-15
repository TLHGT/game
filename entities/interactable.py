"""Clase base de todo objeto con el que el jugador puede interactuar (tecla E).

Para crear un interactuable nuevo:
    1. Hereda de Interactable.
    2. Implementa interact(self, ctx).
    3. (Opcional) cambia prompt_verb, get_image, on_secret_unlocked...
    4. Regístralo en world/map_loader.py (INTERACTABLE_TYPES) para poder
       colocarlo desde el JSON del mapa.

`ctx` es el contexto del juego (la instancia de Game) y ofrece:
    ctx.show_dialogue(pages, speaker=None, on_close=None)
    ctx.notify(text, style="info")
    ctx.unlock_secret(secret_id)
    ctx.secrets   -> SecretSystem
    ctx.state     -> GameState (flags, inventario provisional)
    ctx.world     -> GameMap actual
    ctx.player    -> Player
"""
from entities.entity import Entity
from game import settings

# Hitbox (ancho, alto) para sprites grandes; el resto usa la del tipo.
SPRITE_HITBOX = {
    "operating_table": (70, 22),
    "monitor": (44, 16),
    "shrine": (56, 20),
    "switch_off": (22, 10),
    "wolf_ghost": (64, 22),
    "wolf_grey": (40, 14),
    "shroom": (24, 12),
    "npc_droid": (26, 12),
    "wolf_fire": (40, 14),
    "wolf_ice": (40, 14),
    "generator_off": (34, 14),
    # Aldea del vacío
    "villager_herrero": (26, 12),
    "villager_granjero": (26, 12),
    "villager_vendedor": (26, 12),
    "void_insect": (64, 22),
}


class Interactable(Entity):
    prompt_verb = "Interactuar"
    # Habilidad de aventura necesaria ("burn", "jump"...; ver entities/adventure.py).
    # Sin ella, el objeto no muestra indicador ni se puede usar.
    requires_ability = None

    def __init__(self, x, y, obj_id=None, name="", sprite_key=None,
                 hitbox=(32, 20), solid=True, shadow=None):
        super().__init__(x, y, sprite_key, hitbox=hitbox, shadow=shadow)
        self.id = obj_id
        self.name = name
        self.solid = solid
        self.enabled = True
        self.interact_range = settings.INTERACT_RANGE
        self.secret_id = None   # si se fija, recibe on_secret_unlocked

    # --- Detección -----------------------------------------------------
    @property
    def interaction_rect(self):
        return self.rect.inflate(self.interact_range * 2, self.interact_range * 2)

    def can_interact(self):
        return self.enabled and self.visible

    def get_prompt(self):
        return f"E - {self.prompt_verb}"

    # --- Comportamiento --------------------------------------------------
    def interact(self, ctx):
        raise NotImplementedError

    def on_secret_unlocked(self, ctx):
        """Se llama cuando se desbloquea el secreto `self.secret_id`."""

    # --- Guardado futuro -------------------------------------------------
    def get_state(self):
        """Estado serializable (para un futuro sistema de guardado)."""
        return {}

    def set_state(self, state):
        pass

    @classmethod
    def from_data(cls, data):
        raise NotImplementedError
