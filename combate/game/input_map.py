"""Teclas -> acciones abstractas (jugador, tipo, índice). Cambiar controles aquí."""
import pygame

PLAYER_KEYS = [
    {   # Jugador 1
        "cards": [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5],
        "pass": [pygame.K_SPACE],
        "confirm": [pygame.K_RETURN, pygame.K_KP_ENTER],
        "ultimate": [pygame.K_6],        # definitiva de Estilo: recorre las categorías
    },
    {   # Jugador 2 (el documento no le asignaba confirmar: usamos SHIFT izquierdo)
        "cards": [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t],
        "pass": [pygame.K_TAB],
        "confirm": [pygame.K_LSHIFT],
        "ultimate": [pygame.K_y],
    },
]


def key_to_action(key):
    """Devuelve (player, kind, index) o None."""
    for player, keys in enumerate(PLAYER_KEYS):
        if key in keys["cards"]:
            return player, "card", keys["cards"].index(key)
        if key in keys["pass"]:
            return player, "pass", None
        if key in keys["confirm"]:
            return player, "confirm", None
        if key in keys["ultimate"]:
            return player, "ultimate", None
    return None
