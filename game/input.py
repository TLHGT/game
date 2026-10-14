"""Traducción de teclado/gamepad a *acciones* abstractas.

El resto del juego nunca pregunta por teclas concretas: pregunta por
acciones ("interact", "confirm", "debug"...). Así cambiar controles o añadir
otro dispositivo solo afecta a este archivo.
"""
import pygame

KEY_BINDINGS = {
    "up": (pygame.K_w, pygame.K_UP),
    "down": (pygame.K_s, pygame.K_DOWN),
    "left": (pygame.K_a, pygame.K_LEFT),
    "right": (pygame.K_d, pygame.K_RIGHT),
    "interact": (pygame.K_e,),
    "confirm": (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER),
    "debug": (pygame.K_F3,),
    "pause": (pygame.K_TAB,),
    "quit": (pygame.K_ESCAPE,),
}

# Botones estilo Xbox: 0 = A, 1 = B, 6 = Back/Select
PAD_BINDINGS = {
    "interact": (0,),
    "confirm": (0, 1),
    "debug": (6,),
    "pause": (7,),          # Start
}

STICK_DEADZONE = 0.3


class InputHandler:
    def __init__(self):
        self._pressed = set()        # acciones pulsadas en ESTE frame
        self.quit_requested = False
        # Permite que tests o futuras cinemáticas muevan al jugador.
        self.move_override = None
        self.joysticks = {}
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            self._add_joystick(i)

    # ------------------------------------------------------------------
    def _add_joystick(self, index):
        try:
            joy = pygame.joystick.Joystick(index)
            joy.init()
            self.joysticks[joy.get_instance_id()] = joy
        except pygame.error:
            pass

    def process_events(self, events):
        """Llamar una vez por frame con la lista de eventos de pygame."""
        self._pressed.clear()
        for event in events:
            if event.type == pygame.QUIT:
                self.quit_requested = True
            elif event.type == pygame.KEYDOWN:
                for action, keys in KEY_BINDINGS.items():
                    if event.key in keys:
                        self._pressed.add(action)
            elif event.type == pygame.JOYBUTTONDOWN:
                for action, buttons in PAD_BINDINGS.items():
                    if event.button in buttons:
                        self._pressed.add(action)
            elif event.type == pygame.JOYDEVICEADDED:
                self._add_joystick(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self.joysticks.pop(event.instance_id, None)
        if "quit" in self._pressed:
            self.quit_requested = True

    def pressed(self, action):
        """True solo en el frame en que se pulsó la acción."""
        return action in self._pressed

    def move_vector(self):
        """Dirección de movimiento con longitud <= 1 (diagonal normalizada)."""
        if self.move_override is not None:
            vec = pygame.Vector2(self.move_override)
        else:
            keys = pygame.key.get_pressed()

            def held(action):
                return any(keys[k] for k in KEY_BINDINGS[action])

            vec = pygame.Vector2(held("right") - held("left"), held("down") - held("up"))
            for joy in self.joysticks.values():
                ax = joy.get_axis(0) if joy.get_numaxes() > 0 else 0.0
                ay = joy.get_axis(1) if joy.get_numaxes() > 1 else 0.0
                if abs(ax) > STICK_DEADZONE:
                    vec.x += ax
                if abs(ay) > STICK_DEADZONE:
                    vec.y += ay
                if joy.get_numhats() > 0:
                    hx, hy = joy.get_hat(0)
                    vec.x += hx
                    vec.y -= hy
        if vec.length_squared() > 1.0:
            vec.scale_to_length(1.0)
        return vec
