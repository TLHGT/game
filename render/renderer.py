"""Dibuja el mundo: suelo, sombras, entidades ordenadas por Y y follaje.

Es la única parte que sabe *cómo* se ve el mundo. La lógica (entidades,
mapa) solo expone posiciones y claves de sprite.
"""
import pygame

from render import placeholders
from render.ground import build_ground


class Renderer:
    def __init__(self, assets, screen_size):
        self.assets = assets
        self.ground = None
        self._shadows = {}
        self._faded = {}
        self._covers = {}
        self._dark_surfs = {}
        self._vignettes = {"default": self._make_vignette(screen_size),
                           "cave": self._make_vignette(screen_size, start=0.3, alpha=190, color=(0, 0, 0))}
        self.vignette = self._vignettes["default"]

    def prepare(self, world):
        """Llamar al cargar un mapa: pre-renderiza el suelo."""
        self.ground = build_ground(world, self.assets)
        self._covers.clear()
        # Las cuevas se ven más cerradas y oscuras hacia los bordes.
        theme = world.ground.get("theme", "default")
        self.vignette = self._vignettes.get(theme, self._vignettes["default"])

    # ------------------------------------------------------------------
    def _shadow(self, size):
        if size not in self._shadows:
            s = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.ellipse(s, (0, 0, 0, 70), s.get_rect())
            self._shadows[size] = s
        return self._shadows[size]

    def _fade(self, img):
        key = id(img)
        if key not in self._faded:
            faded = img.copy()
            faded.set_alpha(125)
            self._faded[key] = faded
        return self._faded[key]

    def _cover(self, area):
        key = (tuple(area.rect), area.style)
        if key not in self._covers:
            if area.style == "dark":
                self._covers[key] = placeholders.darkness(area.rect.w, area.rect.h)
            else:
                self._covers[key] = placeholders.cover(area.rect.w, area.rect.h, seed=area.rect.x)
        return self._covers[key]

    def _darkness(self, size):
        """Oscuridad del tamaño pedido, lista para restarle el halo (se reutiliza)."""
        surf = self._dark_surfs.get(size)
        if surf is None:
            surf = self._dark_surfs[size] = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((4, 6, 10, 238))
        return surf

    def _light(self, radius=110):
        if not hasattr(self, "_light_surf"):
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for r in range(radius, 0, -2):
                a = int(235 * (1 - (r / radius) ** 2))
                pygame.draw.circle(s, (0, 0, 0, a), (radius, radius), r)
            self._light_surf = s
        return self._light_surf

    @staticmethod
    def _make_vignette(size, start=0.55, alpha=110, color=(0, 8, 4)):
        w, h = size
        small = pygame.Surface((64, 36), pygame.SRCALPHA)
        for y in range(36):
            for x in range(64):
                dx, dy = (x - 31.5) / 32, (y - 17.5) / 18
                d = min(1.0, (dx * dx + dy * dy) ** 0.5)
                a = int(max(0.0, d - start) / (1 - start) * alpha)
                small.set_at((x, y), (*color, a))
        return pygame.transform.smoothscale(small, (w, h))

    # ------------------------------------------------------------------
    def draw_world(self, surface, world, player, camera):
        ox, oy = camera.offset
        view = camera.view_rect
        surface.blit(self.ground, (-ox, -oy))

        # Recolectar lo visible
        drawables = []
        for e in list(world.visible_entities(view)) + [player]:
            if not e.visible:
                continue
            img = e.get_image(self.assets)
            if img is None:
                continue
            sx, sy = e.sprite_offset
            rect = img.get_rect(midbottom=(round(e.x) + sx, round(e.y) + sy))
            if rect.colliderect(view):
                drawables.append((e, img, rect))

        # Profundidad 2.5D: lo que está más abajo en pantalla se dibuja después
        drawables.sort(key=lambda d: d[0].sort_y)

        # Sombras primero, para que nunca tapen a otros sprites
        for e, img, rect in drawables:
            if e.shadow:
                sh = self._shadow(e.shadow)
                surface.blit(sh, sh.get_rect(center=(round(e.x) - ox, round(e.y) - oy - 2)))

        player_rect = next((r for e, _, r in drawables if e is player), None)
        for e, img, rect in drawables:
            if (e.fade_when_occluding and player_rect is not None and e.sort_y > player.y
                    and rect.colliderect(player_rect.inflate(-10, -10))):
                img = self._fade(img)
            surface.blit(img, rect.move(-ox, -oy))

        # Follaje que oculta zonas secretas / salas a oscuras
        for area in world.hidden_areas:
            if area.reveal >= 1.0:
                continue
            if area.style == "dark":
                # Solo la parte visible (las plantas enteras a oscuras son enormes),
                # con un halo de luz "restado" alrededor del jugador.
                part = area.rect.clip(view)
                if not part.w or not part.h:
                    continue
                cover = self._darkness(part.size)
                light = self._light()
                cover.blit(light, light.get_rect(center=(round(player.x) - part.x,
                                                         round(player.y) - 24 - part.y)),
                           special_flags=pygame.BLEND_RGBA_SUB)
                cover.set_alpha(int(255 * (1.0 - area.reveal)))
                surface.blit(cover, part.move(-ox, -oy))
                continue
            cover = self._cover(area)
            cover.set_alpha(int(255 * (1.0 - area.reveal)))
            surface.blit(cover, area.rect.move(-ox, -oy))

        surface.blit(self.vignette, (0, 0))
