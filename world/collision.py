"""Colisiones rectangulares.

- CollisionGrid: rejilla estática construida a partir de las zonas
  caminables del mapa. Todo lo que no es caminable (bosque denso, fuera
  del mapa) es sólido.
- move_and_collide: mueve una entidad eje por eje y la recoloca contra
  los sólidos. Separar ejes permite "deslizarse" por las paredes.
"""
import pygame


class CollisionGrid:
    def __init__(self, width, height, cell, walkable_rects):
        self.cell = cell
        self.cols = (width + cell - 1) // cell
        self.rows = (height + cell - 1) // cell
        self.solid = [[True] * self.cols for _ in range(self.rows)]
        for rect in walkable_rects:
            self._mark(rect, False)

    def _mark(self, rect, value):
        c0, r0 = max(0, rect.left // self.cell), max(0, rect.top // self.cell)
        c1 = min(self.cols, (rect.right + self.cell - 1) // self.cell)
        r1 = min(self.rows, (rect.bottom + self.cell - 1) // self.cell)
        for r in range(r0, r1):
            for c in range(c0, c1):
                self.solid[r][c] = value

    def is_solid_cell(self, c, r):
        if c < 0 or r < 0 or c >= self.cols or r >= self.rows:
            return True  # fuera del mapa = sólido
        return self.solid[r][c]

    def is_solid_point(self, x, y):
        return self.is_solid_cell(int(x // self.cell), int(y // self.cell))

    def rects_near(self, rect):
        """Rectángulos sólidos de las celdas que tocan `rect` (+1 de margen)."""
        out = []
        c0, r0 = rect.left // self.cell - 1, rect.top // self.cell - 1
        c1, r1 = rect.right // self.cell + 1, rect.bottom // self.cell + 1
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if self.is_solid_cell(c, r):
                    out.append(pygame.Rect(c * self.cell, r * self.cell, self.cell, self.cell))
        return out


def move_and_collide(entity, dx, dy, world):
    """Desplaza `entity` (dx, dy) resolviendo colisiones contra `world`."""
    w, h = entity.hitbox_w, entity.hitbox_h
    if dx:
        entity.x += dx
        r = entity.rect
        for solid in world.solids_near(r, exclude=entity):
            if r.colliderect(solid):
                if dx > 0:
                    entity.x = solid.left - w + w // 2   # rect.right == solid.left
                else:
                    entity.x = solid.right + w // 2      # rect.left == solid.right
                r = entity.rect
    if dy:
        entity.y += dy
        r = entity.rect
        for solid in world.solids_near(r, exclude=entity):
            if r.colliderect(solid):
                if dy > 0:
                    entity.y = solid.top                 # rect.bottom == solid.top
                else:
                    entity.y = solid.bottom + h          # rect.top == solid.bottom
                r = entity.rect
