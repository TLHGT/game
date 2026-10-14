"""Overlay de depuración (F3): texto informativo + cajas de colisión."""
import pygame

from ui import text as T


class DebugOverlay:
    def __init__(self):
        self.enabled = False
        self.font = T.font(15)

    def toggle(self):
        self.enabled = not self.enabled

    def draw_text(self, surface, game):
        p, cam, world = game.player, game.camera, game.world
        secrets = game.secrets.status()
        lines = [
            f"FPS: {game.clock.get_fps():.0f}",
            f"Mapa: {world.name} ({world.id})",
            f"Jugador: x={p.x:.1f}  y={p.y:.1f}  mira={p.facing}",
            f"Cámara: x={cam.camera_x:.1f}  y={cam.camera_y:.1f}",
            f"Interactuables: {len(world.interactables)}  (objetivo: "
            f"{game.interaction.target.name if game.interaction.target else '-'})",
            f"Entidades estáticas: {len(world.static_entities())}",
            "Secretos: " + (", ".join(f"{k}={'SÍ' if v else 'no'}" for k, v in secrets.items()) or "-"),
            f"Inventario: {', '.join(game.state.inventory.items) or '-'}",
        ]
        rendered = [self.font.render(l, True, (235, 235, 235)) for l in lines]
        w = max(r.get_width() for r in rendered) + 20
        h = sum(r.get_height() + 2 for r in rendered) + 14
        surface.blit(T.panel((w, h), color=(0, 0, 0), alpha=170, radius=6), (8, 8))
        y = 15
        for r in rendered:
            surface.blit(r, (18, y))
            y += r.get_height() + 2

    def draw_world(self, surface, game):
        """Colisiones (rojo), zonas de interacción (amarillo), triggers (cian),
        salidas (magenta)."""
        cam, world = game.camera, game.world
        ox, oy = cam.offset
        view = cam.view_rect

        def box(rect, color, width=1):
            r = pygame.Rect(rect).move(-ox, -oy)
            pygame.draw.rect(surface, color, r, width)

        for r in world.collision.rects_near(view):
            if r.colliderect(view):
                box(r, (150, 40, 40))
        for e in world.static_near(view):
            if e.solid:
                box(e.rect, (255, 80, 80))
        for it in world.interactables:
            if it.solid:
                box(it.rect, (255, 80, 80))
            box(it.interaction_rect, (240, 220, 60))
        for t in world.triggers:
            box(t.rect, (60, 220, 240))
        for ex in world.exits:
            box(ex.rect, (230, 60, 230), 2)
        box(game.player.rect, (80, 255, 120), 2)
