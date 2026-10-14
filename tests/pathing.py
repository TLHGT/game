"""Búsqueda de caminos para las pruebas automáticas.

Sirve para dos cosas:
    reachable(world, a, b)   ¿se puede ir andando de a a b? (comprueba el diseño:
                             p. ej. que un derrumbe bloquea de verdad un paso)
    go(bot, (x, y))          lleva al jugador hasta (x, y) por el camino más corto

Rejilla de CELL px: una celda es transitable si los pies del jugador caben en su
centro sin chocar con nada sólido (muros, zonas no caminables, puertas cerradas,
objetos) ni pisar una salida a otro mapa. Los enemigos no son sólidos.
"""
import heapq

import pygame

from game import settings

CELL = 20
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


class Grid:
    def __init__(self, world):
        self.world = world
        self.cols = world.width // CELL
        self.rows = world.height // CELL
        self._free = {}

    def center(self, c):
        return (c[0] * CELL + CELL // 2, c[1] * CELL + CELL // 2)

    def cell(self, p):
        return (int(p[0]) // CELL, int(p[1]) // CELL)

    def free(self, c):
        if c not in self._free:
            x, y = self.center(c)
            ok = 0 <= c[0] < self.cols and 0 <= c[1] < self.rows
            if ok:
                r = pygame.Rect(0, 0, *settings.PLAYER_HITBOX)
                r.midbottom = (x, y)
                ok = r.collidelist(self.world.solids_near(r)) == -1
                # pisar una salida (escalera, puerta) cambiaría de mapa a mitad de camino
                ok = ok and r.inflate(8, 8).collidelist([ex.rect for ex in self.world.exits]) == -1
            self._free[c] = ok
        return self._free[c]

    def nearest_free(self, p):
        c = self.cell(p)
        if self.free(c):
            return c
        for radius in range(1, 4):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    n = (c[0] + dx, c[1] + dy)
                    if self.free(n):
                        return n
        return c

    def path(self, a, b):
        start, goal = self.nearest_free(a), self.nearest_free(b)
        if not self.free(start) or not self.free(goal):
            return None
        frontier = [(0, start)]
        came = {start: None}
        cost = {start: 0}
        while frontier:
            _, cur = heapq.heappop(frontier)
            if cur == goal:
                break
            for dx, dy in DIRS:
                n = (cur[0] + dx, cur[1] + dy)
                if not self.free(n):
                    continue
                if dx and dy and not (self.free((cur[0] + dx, cur[1])) and self.free((cur[0], cur[1] + dy))):
                    continue                     # sin cortar esquinas
                step = 14 if dx and dy else 10
                new = cost[cur] + step
                if new < cost.get(n, 1 << 30):
                    cost[n] = new
                    came[n] = cur
                    h = 10 * max(abs(goal[0] - n[0]), abs(goal[1] - n[1]))
                    heapq.heappush(frontier, (new + h, n))
        if goal not in came:
            return None
        cells = []
        c = goal
        while c is not None:
            cells.append(c)
            c = came[c]
        cells.reverse()
        return [self.center(c) for c in simplify(cells)]


def simplify(cells):
    """Quita los puntos intermedios de los tramos rectos."""
    if len(cells) < 3:
        return cells
    out = [cells[0]]
    for prev, cur, nxt in zip(cells, cells[1:], cells[2:]):
        if (cur[0] - prev[0], cur[1] - prev[1]) != (nxt[0] - cur[0], nxt[1] - cur[1]):
            out.append(cur)
    out.append(cells[-1])
    return out


def reachable(world, a, b):
    return Grid(world).path(a, b) is not None


def go(bot, target):
    """Camina hasta `target` por el camino más corto (resuelve los combates por el camino)."""
    p = bot.g.player
    route = Grid(bot.g.world).path((p.x, p.y), target)
    if route is None:
        raise SystemExit(f"[FALLO] No hay camino de {(round(p.x), round(p.y))} a {target} en {bot.g.world.id}")
    bot.walk(*(route[1:] + [tuple(target)]))
