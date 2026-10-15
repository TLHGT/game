"""Enemigo del mapa: se mueve por el mundo y, al tocar al jugador (o al pulsar
E delante de él), empieza un combate de cartas (combate/).

Encuentros "visibles", como en muchos RPG: el enemigo deambula, patrulla o
espera quieto; si ve al jugador cerca, lo persigue. Si el jugador huye o
pierde, el enemigo tarda unos segundos en volver a atacar.

JSON (lista `interactables` del mapa):
    {
      "type": "enemy", "id": "lobo_1", "name": "Lobo gris", "sprite": "wolf_grey",
      "pos": [x, y],
      "deck": ["attack", "break", ...]   o el nombre de un mazo: "duelo",
      "character": "hero",               (opcional: pasiva de combate/game/characters.py)
      "hp": 60,                          (opcional, máx. el MAX_HP del combate)
      "aggression": 0.3, "randomness": 0.6,     (personalidad de la IA)
      "behavior": "wander" | "patrol" | "guard",
      "radius": 120,                     (wander: distancia máx. a su posición inicial)
      "patrol": [[x, y], [x, y]],        (patrol: puntos que recorre en bucle)
      "aggro": 170, "speed": 80,
      "intro": ["Texto antes del combate"],
      "victory": ["Texto al vencerlo"],
      "unlocks_secret": "id_secreto",    (opcional: se desbloquea al vencerlo)
      "reward": {"item": "potion", "name": "Poción"},
      "can_flee": true, "vanish": true,
      "respawn": 40,                     (opcional: segundos hasta que vuelve tras vencerlo)
      "soul": "herrero",                 (opcional: alma que suelta en la Aldea del vacío)
      "requires_secret": "id_secreto"    (opcional: no hay combate hasta desbloquearlo)
    }
"""
import math
import random

import pygame

from entities.interactable import SPRITE_HITBOX, Interactable
from world.collision import move_and_collide

CONTACT_MARGIN = 6       # px alrededor de la hitbox para considerar que te ha tocado
REENGAGE_DELAY = 3.0     # segundos sin atacar tras huir / perder
RESPAWN_DISTANCE = 360   # un enemigo con "respawn" no reaparece si el jugador está más cerca


class Enemy(Interactable):
    prompt_verb = "Luchar"

    def __init__(self, x, y, obj_id, name, sprite="wolf_grey", deck="duelo", character=None,
                 hp=None, aggression=0.0, randomness=0.6, behavior="wander", radius=120,
                 patrol=None, aggro=170, speed=80, intro=None, victory=None,
                 unlocks_secret=None, reward=None, can_flee=True, vanish=True, respawn=None, soul=None,
                 requires_secret=None):
        hb = SPRITE_HITBOX.get(sprite, (30, 14))
        super().__init__(x, y, obj_id, name, sprite, hitbox=hb, solid=False, shadow=(hb[0] + 8, 12))
        self.home = pygame.Vector2(x, y)
        self.deck = deck
        self.character = character
        self.hp = hp
        self.aggression = aggression
        self.randomness = randomness
        self.behavior = behavior
        self.radius = radius
        self.patrol = [pygame.Vector2(p) for p in (patrol or [])]
        self.aggro = aggro
        self.speed = speed
        self.intro = intro
        self.victory = victory
        self.unlocks_secret = unlocks_secret
        self.reward = reward
        self.can_flee = can_flee
        self.vanish = vanish
        self.respawn = respawn
        self.soul = soul
        self.requires_secret = requires_secret

        self.defeated = False
        self.respawn_left = 0.0
        self._secret_ok = requires_secret is None
        self.cooldown = 0.0
        self.chasing = False
        self.facing_left = False
        self._target = None
        self._wait = random.uniform(0.3, 1.5)
        self._patrol_i = 0
        self._t = random.uniform(0, 6)
        self._flipped = {}

    # --- Interacción ------------------------------------------------------
    def can_interact(self):
        return super().can_interact() and not self.defeated and self._secret_ok

    def interact(self, ctx):
        ctx.start_battle(self)

    def on_defeated(self, ctx):
        """Lo llama el juego al ganar el combate."""
        self.defeated = True
        self._apply_defeated()
        if self.reward and self.reward.get("item"):
            ctx.state.inventory.add(self.reward["item"])
            ctx.notify(f"Obtienes: {self.reward.get('name', self.reward['item'])}", "discovery")
        if self.unlocks_secret:
            ctx.unlock_secret(self.unlocks_secret)
        if self.soul:
            ctx.on_soul_dropped(self.soul)
        if self.respawn:
            self.respawn_left = float(self.respawn)

    def on_escaped(self):
        """El jugador huyó o perdió: un respiro antes de volver a atacar."""
        self.cooldown = REENGAGE_DELAY
        self.chasing = False
        self._target = None

    def _apply_defeated(self):
        if self.defeated and self.vanish:
            self.visible = False
        self.enabled = not self.defeated

    # --- Movimiento ---------------------------------------------------------
    def update(self, dt, ctx):
        self._t += dt
        if self.requires_secret:
            self._secret_ok = ctx.secrets.is_unlocked(self.requires_secret)
        if self.defeated:
            if self.respawn:
                self._update_respawn(dt, ctx)
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        moving = False
        if not ctx.busy and self._secret_ok:
            moving = self._think(dt, ctx)
            if self.cooldown <= 0 and self.rect.inflate(CONTACT_MARGIN * 2, CONTACT_MARGIN * 2) \
                    .colliderect(ctx.player.rect):
                ctx.start_battle(self)
                return
        bob = math.sin(self._t * (9 if moving else 2.5)) * (2 if moving else 1)
        self.sprite_offset = (0, round(bob))

    def _update_respawn(self, dt, ctx):
        """Vuelve a su sitio cuando pasa su tiempo y el jugador no está cerca."""
        self.respawn_left = max(0.0, self.respawn_left - dt)
        far = self.home.distance_to((ctx.player.x, ctx.player.y)) > RESPAWN_DISTANCE
        if self.respawn_left <= 0 and far and not ctx.busy:
            self.defeated = False
            self.x, self.y = self.home.x, self.home.y
            self.chasing = False
            self._target = None
            self.cooldown = REENGAGE_DELAY
            self._apply_defeated()
            self.visible = True

    def _think(self, dt, ctx):
        pos = pygame.Vector2(self.x, self.y)
        player = pygame.Vector2(ctx.player.x, ctx.player.y)
        leash = self.radius + 260
        sees = self.cooldown <= 0 and self.aggro > 0 and pos.distance_to(player) < self.aggro
        if sees and self.home.distance_to(player) < leash:
            self.chasing = True
            return self._move_towards(player, self.speed * 1.5, dt, ctx)
        if self.chasing:                       # lo ha perdido: vuelve a casa
            self.chasing = False
            self._target = self.home if self.behavior != "patrol" else None
        if self.behavior == "guard":
            return self._move_towards(self.home, self.speed, dt, ctx) if pos.distance_to(self.home) > 4 else False
        if self.behavior == "patrol" and self.patrol:
            target = self.patrol[self._patrol_i % len(self.patrol)]
            if pos.distance_to(target) < 6 or not self._move_towards(target, self.speed, dt, ctx):
                self._patrol_i += 1            # llegó (o algo le corta el paso): siguiente punto
                return False
            return True
        # wander
        if self._target is None:
            self._wait -= dt
            if self._wait > 0:
                return False
            angle = random.uniform(0, math.tau)
            dist = random.uniform(0.3, 1.0) * self.radius
            self._target = self.home + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
        if pos.distance_to(self._target) < 6 or not self._move_towards(self._target, self.speed, dt, ctx):
            self._target = None
            self._wait = random.uniform(0.8, 2.5)
            return False
        return True

    def _move_towards(self, target, speed, dt, ctx):
        """Devuelve False si no ha podido avanzar (choca con algo)."""
        d = pygame.Vector2(target) - pygame.Vector2(self.x, self.y)
        if d.length() < 1:
            return False
        step = d.normalize() * min(speed * dt, d.length())
        before = (self.x, self.y)
        move_and_collide(self, step.x, step.y, ctx.world)
        if abs(step.x) > 0.05:
            self.facing_left = step.x < 0
        return (self.x, self.y) != before

    # --- Visual ---------------------------------------------------------------
    def get_image(self, assets):
        img = super().get_image(assets)
        if img is None or not self.facing_left:
            return img
        if self.sprite_key not in self._flipped:
            self._flipped[self.sprite_key] = pygame.transform.flip(img, True, False)
        return self._flipped[self.sprite_key]

    # --- Estado (sobrevive al cambiar de mapa) ---------------------------------
    def get_state(self):
        return {"defeated": self.defeated, "respawn_left": self.respawn_left}

    def set_state(self, state):
        self.defeated = state.get("defeated", False)
        self.respawn_left = state.get("respawn_left", 0.0)
        self._apply_defeated()

    @classmethod
    def from_data(cls, d):
        obj = cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("name", "Enemigo"),
                  d.get("sprite", "wolf_grey"), d.get("deck", "duelo"), d.get("character"),
                  d.get("hp"), d.get("aggression", 0.0), d.get("randomness", 0.6),
                  d.get("behavior", "wander"), d.get("radius", 120), d.get("patrol"),
                  d.get("aggro", 170), d.get("speed", 80), d.get("intro"), d.get("victory"),
                  d.get("unlocks_secret"), d.get("reward"), d.get("can_flee", True),
                  d.get("vanish", True), d.get("respawn"), d.get("soul"), d.get("requires_secret"))
        if d.get("verb"):
            obj.prompt_verb = d["verb"]
        return obj
