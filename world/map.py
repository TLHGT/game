"""GameMap: contenedor de todo lo que forma una zona del mundo.

    GameMap
    ├── walkable       zonas por las que se puede andar (el resto es bosque)
    ├── walls          muros con volumen
    ├── obstacles      árboles, rocas... sueltos y sólidos
    ├── decorations    elementos no sólidos (hierba alta...)
    ├── forest         árboles generados del bosque denso
    ├── interactables  NPCs, cofres, puertas, carteles, objetos secretos
    ├── triggers       zonas de mensaje
    ├── exits          MapTransition
    ├── hidden_areas   follaje que oculta zonas secretas
    └── secrets        definiciones de secretos de esta zona

El mapa solo contiene *datos y lógica*; cómo se dibuja lo decide el renderer.

FASES (mapas que cambian con una misión, p. ej. la aldea del vacío): si el JSON
declara "phase_flag", la fase actual es ctx.state.get_flag(phase_flag, 1) y
cualquier zona caminable, muro, obstáculo, decoración, interactuable, trigger o
área del suelo puede llevar "phases": [1, 2] para existir solo en esas fases.
Las listas normales (walkable, walls, interactables...) tienen solo lo de la
fase actual; las all_* lo tienen todo (el estado de los objetos se guarda de
all_interactables). apply_phase() reconstruye colisión e índice.
"""
from collections import defaultdict

import pygame

from game import settings
from world.collision import CollisionGrid

CHUNK = 256


def in_phase(obj_phases, phase):
    """¿Existe en `phase` algo con fases `obj_phases` (None = siempre)?"""
    return obj_phases is None or phase is None or phase in obj_phases


class GameMap:
    def __init__(self, map_id, name, width, height):
        self.id = map_id
        self.name = name
        self.width = width
        self.height = height
        self.walkable = []
        self.walls = []
        self.obstacles = []
        self.decorations = []
        self.forest = []
        self.interactables = []
        self.triggers = []
        self.exits = []
        self.hidden_areas = []
        self.secrets = []          # [{"id":..., "name":..., "unlock_message":...}]
        self.spawns = {}
        self.ground = {}           # datos visuales del suelo (los interpreta el renderer)
        self.collision = None      # CollisionGrid
        self._chunks = defaultdict(list)
        # Fases (ver arriba). Sin "phase_flag" todo existe siempre.
        self.phase_flag = None
        self.phase = None
        self.all_walkable = []     # [(Rect, phases)]
        self.all_walls = []
        self.all_obstacles = []
        self.all_decorations = []
        self.all_interactables = []
        self.all_triggers = []

    # --- Fases --------------------------------------------------------------
    def current_phase(self, state):
        return state.get_flag(self.phase_flag, 1) if self.phase_flag else None

    def apply_phase(self, phase, force=False):
        """Deja activas solo las cosas de `phase`. Devuelve True si algo cambió."""
        if phase == self.phase and self.collision is not None and not force:
            return False
        self.phase = phase

        def keep(items):
            return [e for e in items if in_phase(getattr(e, "phases", None), phase)]
        self.walkable = [r for r, ph in self.all_walkable if in_phase(ph, phase)]
        self.collision = CollisionGrid(self.width, self.height, settings.COLLISION_CELL, self.walkable)
        self.walls = keep(self.all_walls)
        self.obstacles = keep(self.all_obstacles)
        self.decorations = keep(self.all_decorations)
        self.interactables = keep(self.all_interactables)
        self.triggers = keep(self.all_triggers)
        self.build_index()
        return True

    def all_walkable_rects(self):
        return [r for r, _ in self.all_walkable]

    # --- Construcción -----------------------------------------------------
    def build_index(self):
        """Indexa por trozos los objetos estáticos para no recorrer cientos
        de árboles en cada frame."""
        self._chunks.clear()
        for e in self.static_entities():
            # Un muro largo ocupa varios trozos: se apunta en todos los que toca
            # (si solo contara su punto base, lejos de él no chocaría).
            r = e.rect
            cx0, cx1 = min(int(e.x), r.left) // CHUNK, max(int(e.x), r.right) // CHUNK
            cy0, cy1 = min(int(e.y), r.top) // CHUNK, max(int(e.y), r.bottom) // CHUNK
            for cy in range(cy0, cy1 + 1):
                for cx in range(cx0, cx1 + 1):
                    self._chunks[(cx, cy)].append(e)

    def static_entities(self):
        return self.walls + self.obstacles + self.decorations + self.forest

    # --- Consultas ----------------------------------------------------------
    def static_near(self, rect, margin=0):
        c0 = (rect.left - margin) // CHUNK
        c1 = (rect.right + margin) // CHUNK
        r0 = (rect.top - margin) // CHUNK
        r1 = (rect.bottom + margin) // CHUNK
        seen = set()
        for cy in range(r0, r1 + 1):
            for cx in range(c0, c1 + 1):
                for e in self._chunks.get((cx, cy), ()):
                    if id(e) not in seen:
                        seen.add(id(e))
                        yield e

    def solids_near(self, rect, exclude=None):
        solids = self.collision.rects_near(rect)
        for e in self.static_near(rect, margin=CHUNK):
            if e.solid and e is not exclude:
                solids.append(e.rect)
        for e in self.interactables:
            if e.solid and e is not exclude:
                solids.append(e.rect)
        return solids

    def visible_entities(self, view_rect):
        """Entidades que pueden aparecer en pantalla (margen por sprites altos)."""
        yield from self.static_near(view_rect, margin=160)
        yield from self.interactables

    def get_interactable(self, obj_id):
        for it in self.all_interactables:
            if it.id == obj_id:
                return it
        return None

    def secret_ids(self):
        return [s["id"] for s in self.secrets]

    # --- Eventos ------------------------------------------------------------
    def on_secret_unlocked(self, secret_id, ctx):
        """Los secretos modifican el mapa: avisa a quien dependa de él (en cualquier fase)."""
        for e in self.all_interactables + self.all_walls:
            if getattr(e, "secret_id", None) == secret_id:
                e.on_secret_unlocked(ctx)

    def update(self, dt, ctx):
        if self.phase_flag and self.apply_phase(self.current_phase(ctx.state)):
            ctx.on_phase_changed(self)
        for it in self.interactables:
            it.update(dt, ctx)
        player_rect = ctx.player.rect
        for area in self.hidden_areas:
            area.update(dt, player_rect, ctx.secrets)
        for trig in self.triggers:
            trig.try_fire(player_rect, ctx)
