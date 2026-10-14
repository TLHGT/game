"""Fases del combate y transiciones permitidas.

Las fases AUTO avanzan solas (la UI llama a engine.advance() cuando termina
su animación). Solo dos fases esperan a los jugadores: REDRAW (cambios) y
CARD_SELECTION (elegir carta o PASS).
"""
from enum import Enum


class Phase(str, Enum):
    TURN_START = "TURN_START"
    DRAW = "DRAW"
    REDRAW = "REDRAW"
    INTERACTION_START = "INTERACTION_START"
    CARD_SELECTION = "CARD_SELECTION"
    CARD_REVEAL = "CARD_REVEAL"
    CARD_RESOLUTION = "CARD_RESOLUTION"
    MEGA_COMBO = "MEGA_COMBO"
    TURN_END = "TURN_END"
    GAME_OVER = "GAME_OVER"


P = Phase
TRANSITIONS = {
    # El daño de estado (BURN al empezar turno, POISON al empezar interacción)
    # puede dejar a alguien a 0 HP: el combate termina en ese momento.
    P.TURN_START: {P.DRAW, P.GAME_OVER},
    P.DRAW: {P.REDRAW},
    P.REDRAW: {P.INTERACTION_START},
    P.INTERACTION_START: {P.CARD_SELECTION, P.GAME_OVER},
    P.CARD_SELECTION: {P.CARD_REVEAL},
    P.CARD_REVEAL: {P.CARD_RESOLUTION},
    # Tras resolver (daño normal ya aplicado): 3 hits -> MEGA_COMBO (daño adicional);
    # después: iniciativa -> nueva interacción automática; sin iniciativa -> TURN_END.
    # No hay ninguna fase que pregunte "¿continuar?".
    P.CARD_RESOLUTION: {P.MEGA_COMBO, P.INTERACTION_START, P.TURN_END},
    P.MEGA_COMBO: {P.INTERACTION_START, P.TURN_END},
    P.TURN_END: {P.TURN_START, P.GAME_OVER},
    P.GAME_OVER: set(),
}

AUTO_PHASES = {P.TURN_START, P.DRAW, P.INTERACTION_START, P.CARD_REVEAL, P.CARD_RESOLUTION,
               P.MEGA_COMBO, P.TURN_END}


class InvalidTransition(Exception):
    pass


class StateMachine:
    def __init__(self, initial=P.TURN_START):
        self.phase = initial
        self.history = [initial]

    def go(self, phase):
        if phase not in TRANSITIONS[self.phase]:
            raise InvalidTransition(f"{self.phase.value} -> {phase.value}")
        self.phase = phase
        self.history.append(phase)

    @property
    def is_auto(self):
        return self.phase in AUTO_PHASES
