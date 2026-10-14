"""Zonas que reaccionan cuando el jugador entra en ellas.

- MapTransition: salida hacia otro mapa (Forest -> Village...).
- TriggerZone: mensajes de zona / descubrimiento ("Área secreta descubierta.").

Ambas detectan el *flanco de entrada*: solo se activan al entrar, no en
cada frame que el jugador permanece dentro.
"""
import pygame


class _Zone:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self._inside = False

    def check_enter(self, player_rect):
        inside = self.rect.colliderect(player_rect)
        entered = inside and not self._inside
        self._inside = inside
        return entered


class MapTransition(_Zone):
    """Si `target_map` existe en maps/ el juego lo carga y coloca al jugador
    en `target_spawn`. Si no existe todavía, solo muestra `message`."""

    def __init__(self, rect, target_map=None, target_spawn="default", message=None):
        super().__init__(rect)
        self.target_map = target_map
        self.target_spawn = target_spawn
        self.message = message

    @classmethod
    def from_data(cls, d):
        return cls(d["rect"], d.get("target_map"), d.get("target_spawn", "default"),
                   d.get("message"))


class TriggerZone(_Zone):
    def __init__(self, rect, message, style="info", once=True, requires_secret=None, obj_id=None):
        super().__init__(rect)
        self.id = obj_id
        self.message = message
        self.style = style
        self.once = once
        self.requires_secret = requires_secret
        self.fired = False

    def try_fire(self, player_rect, ctx):
        if not self.check_enter(player_rect):
            return
        if self.once and self.fired:
            return
        if self.requires_secret and not ctx.secrets.is_unlocked(self.requires_secret):
            return
        self.fired = True
        ctx.notify(self.message, self.style)

    @classmethod
    def from_data(cls, d):
        return cls(d["rect"], d["message"], d.get("style", "info"), d.get("once", True),
                   d.get("requires_secret"), d.get("id"))


class HiddenArea:
    """Zona tapada que se revela.

    style "foliage": follaje que oculta un secreto hasta que el jugador entra.
    style "dark":    sala a oscuras (el jugador lleva un halo de luz) que se
                     ilumina cuando se desbloquea el secreto `secret`
                     (p. ej. un interruptor de la luz). `secret` puede ser una
                     lista: se ilumina cuando están todos.
    `reveal` va de 0 (tapado) a 1 (descubierto); el renderer lo usa como alpha."""

    def __init__(self, rect, style="foliage", secret=None):
        self.rect = pygame.Rect(rect)
        self.style = style
        self.secret = secret
        self.revealed = False
        self.reveal = 0.0

    def update(self, dt, player_rect, secrets=None):
        if not self.revealed:
            if self.secret:
                ids = self.secret if isinstance(self.secret, list) else [self.secret]
                self.revealed = secrets is not None and all(secrets.is_unlocked(s) for s in ids)
            elif self.rect.colliderect(player_rect):
                self.revealed = True
        if self.revealed and self.reveal < 1.0:
            self.reveal = min(1.0, self.reveal + dt * 1.6)
