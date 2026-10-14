"""Puzle de las máquinas de ventajas del hospital (homenaje a las perks de los
zombis de Black Ops).

Hay una máquina en cada piso del 1 al 4. En el ordenador del cuarto secreto del
lobby se lee una secuencia con los números del 1 al 4 (p. ej. 2413): es el orden en que hay
que encender las máquinas (primero la del piso 2, luego la del 4, la del 1 y la
del 3). Si se enciende una fuera de orden, todas se apagan y hay que empezar de
nuevo. Al completarla se desbloquea el secreto SECRET_ID (lo usa la máquina
Pack-a-Punch del cuarto secreto).

La secuencia es aleatoria en cada partida (settings.PERK_SEQUENCE la fija para
pruebas) y, como el progreso, vive en GameState: sobrevive al cambiar de mapa.
"""
import random

SECRET_ID = "perks_completas"
FLOORS = (1, 2, 3, 4)


class PerkPuzzle:
    def __init__(self, state, sequence=None, rng=None):
        self.state = state
        if not state.get_flag("perk_sequence"):
            seq = list(sequence) if sequence else random.Random(rng).sample(FLOORS, len(FLOORS))
            state.set_flag("perk_sequence", seq)
            state.set_flag("perk_progress", [])

    @property
    def sequence(self):
        return list(self.state.get_flag("perk_sequence"))

    @property
    def code(self):
        """La secuencia como se escribe en la pared: "2413"."""
        return "".join(str(n) for n in self.sequence)

    @property
    def progress(self):
        return list(self.state.get_flag("perk_progress", []))

    @property
    def complete(self):
        return self.progress == self.sequence

    def is_on(self, floor):
        return floor in self.progress

    def press(self, floor):
        """Enciende la máquina del piso `floor`. Devuelve:
        "on" (era la siguiente), "done" (era la última), "already" (ya estaba
        encendida) o "wrong" (fuera de orden: todas se apagan)."""
        progress = self.progress
        if self.complete or floor in progress:
            return "already"
        if self.sequence[len(progress)] != floor:
            self.state.set_flag("perk_progress", [])
            return "wrong"
        progress.append(floor)
        self.state.set_flag("perk_progress", progress)
        return "done" if self.complete else "on"
