"""AssetManager: imágenes por clave, con PNG opcional y placeholder automático.

    assets.get("chest_open")
        1. busca assets/chest_open.png
        2. si no existe, prueba quitando sufijos: assets/chest.png
        3. si no hay ningún PNG, genera un placeholder (render/placeholders.py)

Así, para sustituir un placeholder por arte real basta con soltar el PNG en
assets/ con el nombre adecuado. Ver assets/README.md para la lista de claves.
"""
import os

import pygame

from render import placeholders


class AssetManager:
    def __init__(self, asset_dir):
        self.asset_dir = asset_dir
        self._cache = {}

    def _find_png(self, key):
        parts = key.split("_")
        while parts:
            path = os.path.join(self.asset_dir, "_".join(parts) + ".png")
            if os.path.isfile(path):
                return path
            parts.pop()
        return None

    def has_png(self, key):
        return self._find_png(key) is not None

    def _load(self, path):
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as exc:
            print(f"[assets] No se pudo cargar {path}: {exc}")
            return None

    @staticmethod
    def _optimize(img):
        """Formato de pantalla + RLE: los blits con transparencia son mucho
        más rápidos (hay cientos de árboles en pantalla)."""
        img = img.convert_alpha()
        img.set_alpha(255, pygame.RLEACCEL)
        return img

    def get(self, key):
        """Imagen de tamaño fijo (personajes, árboles, objetos)."""
        if key not in self._cache:
            path = self._find_png(key)
            img = self._load(path) if path else None
            self._cache[key] = self._optimize(img or placeholders.make(key))
        return self._cache[key]

    def get_block(self, key, width, depth, height):
        """Imagen dimensionada para muros/puertas: huella (width x depth)
        más `height` píxeles de altura visual."""
        cache_key = (key, width, depth, height)
        if cache_key not in self._cache:
            path = self._find_png(key)
            img = self._load(path) if path else None
            if img:
                img = pygame.transform.smoothscale(img, (width, depth + height))
            self._cache[cache_key] = self._optimize(
                img or placeholders.make_block(key, width, depth, height))
        return self._cache[cache_key]

    def get_tile(self, key):
        """Textura repetible para el suelo, solo si existe un PNG (si no, None
        y el suelo se pinta proceduralmente)."""
        path = os.path.join(self.asset_dir, key + ".png")
        return self._load(path) if os.path.isfile(path) else None
