"""Objeto con comportamiento por etapas: base para easter eggs y puzzles.

Cada interacción avanza una etapa y muestra su texto. Al alcanzar
`unlock_stage` desbloquea un secreto del mapa.

Para convertirlo en un puzzle complejo basta con heredar y sobrescribir
`on_stage_reached` (p. ej. exigir una hora concreta, una secuencia de
objetos, que el jugador lleve cierto objeto, etc.).

JSON:
    {
      "type": "secret_object", "id": "old_radio", "name": "Radio vieja",
      "pos": [x, y], "sprite": "radio",
      "stage_sprites": {"0": "radio_off", "2": "radio_static", "4": "radio_on"},
      "stages": ["texto 1", "texto 2", ...],
      "idle_text": "Texto cuando ya no quedan etapas",
      "unlocks_secret": "arken_shrine", "unlock_stage": 4
    }
"""
import random

from entities.interactable import SPRITE_HITBOX, Interactable


class SecretObject(Interactable):
    def __init__(self, x, y, obj_id, name, stages, idle_text=None, sprite="radio",
                 stage_sprites=None, unlocks_secret=None, unlock_stage=None, vanish=False):
        hb = SPRITE_HITBOX.get(sprite, (34, 16))
        super().__init__(x, y, obj_id, name, sprite, hitbox=hb, shadow=(hb[0] + 6, 12))
        self.stages = stages
        self.idle_text = idle_text or stages[-1]
        self.base_sprite = sprite
        self.stage_sprites = {int(k): v for k, v in (stage_sprites or {}).items()}
        self.unlocks_secret = unlocks_secret
        self.unlock_stage = unlock_stage if unlock_stage is not None else len(stages)
        self.vanish = vanish    # desaparece al desbloquear (p. ej. un jefe derrotado)
        self.stage = 0          # nº de interacciones realizadas
        self._flicker = 0.0
        self._show_alt = False

    def interact(self, ctx):
        if self.stage < len(self.stages):
            text = self.stages[self.stage]
        else:
            text = self.idle_text
        self.stage += 1
        reached = self.stage
        ctx.show_dialogue([text], speaker=None,
                          on_close=lambda: self.on_stage_reached(reached, ctx))

    def on_stage_reached(self, stage, ctx):
        """Se ejecuta al cerrar el diálogo de cada etapa."""
        if self.unlocks_secret and stage == self.unlock_stage:
            ctx.unlock_secret(self.unlocks_secret)
        self._apply_vanish()

    def _apply_vanish(self):
        if self.vanish and self.stage >= self.unlock_stage:
            self.visible = False
            self.solid = False

    # --- Visual -----------------------------------------------------------
    def _sprite_for_stage(self):
        key = self.base_sprite
        for threshold in sorted(self.stage_sprites):
            if self.stage >= threshold:
                key = self.stage_sprites[threshold]
        return key

    def update(self, dt, ctx):
        key = self._sprite_for_stage()
        # Parpadeo aleatorio entre el sprite actual y el anterior: da vida.
        self._flicker -= dt
        if self._flicker <= 0:
            self._flicker = random.uniform(0.08, 0.5)
            self._show_alt = random.random() < 0.3
        if self.stage_sprites and self._show_alt and self.stage >= 2:
            lower = [t for t in self.stage_sprites if t <= self.stage]
            if len(lower) >= 2:
                key = self.stage_sprites[sorted(lower)[-2]]
        self.sprite_key = key

    def get_state(self):
        return {"stage": self.stage}

    def set_state(self, state):
        self.stage = state.get("stage", 0)
        self._apply_vanish()

    @classmethod
    def from_data(cls, d):
        obj = cls._from_data(d)
        if d.get("verb"):
            obj.prompt_verb = d["verb"]
        return obj

    @classmethod
    def _from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("name", ""),
                   d.get("stages", ["..."]), d.get("idle_text"), d.get("sprite", "radio"),
                   d.get("stage_sprites"), d.get("unlocks_secret"), d.get("unlock_stage"),
                   d.get("vanish", False))
