"""Detecta con qué objeto puede interactuar el jugador ahora mismo.

Criterio: el objeto cuya zona de interacción toca los pies del jugador y
que esté más cerca de un punto ligeramente adelantado en la dirección en
la que mira (así, con dos objetos cerca, gana el que tienes delante).
"""
import pygame


class InteractionSystem:
    def __init__(self):
        self.target = None

    def update(self, player, interactables, ability=None):
        """`ability`: habilidad de aventura del personaje elegido. Los objetos que
        piden otra (o cualquiera, si no hay) ni se señalan ni se pueden usar."""
        probe = pygame.Vector2(player.x, player.y - 6) + player.facing_vector * 14
        player_rect = player.rect
        best, best_dist = None, float("inf")
        for it in interactables:
            if not it.can_interact():
                continue
            needed = getattr(it, "requires_ability", None)
            if needed is not None and needed != ability:
                continue
            if not it.interaction_rect.colliderect(player_rect):
                continue
            center = pygame.Vector2(it.rect.center)
            dist = probe.distance_squared_to(center)
            if dist < best_dist:
                best, best_dist = it, dist
        self.target = best
        return best

    def interact(self, ctx):
        if self.target is not None:
            self.target.interact(ctx)
            return True
        return False
