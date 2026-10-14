"""Utilidades de texto compartidas por la UI."""
import pygame

from game import settings

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.SysFont(settings.FONT_NAMES, size, bold=bold)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size + 6)
    return _fonts[key]


def wrap(text, fnt, max_width):
    """Parte `text` en líneas que caben en `max_width` píxeles."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if fnt.size(candidate)[0] <= max_width or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def panel(size, color=settings.UI_PANEL, alpha=225, radius=10, border=None):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, surf.get_rect(), width=2, border_radius=radius)
    return surf
