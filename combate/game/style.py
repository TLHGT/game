"""Estilo: puntos por ganar interacciones seguidas, rangos D..S y definitiva. Sin Pygame.

Cada jugador tiene su StyleState (Player.style). Es independiente del combo de
HIT: cuenta INTERACCIONES ganadas según el resultado real (InteractionResult),
no el daño ni los hits.

    ganar   +3, +6, +12, +24, +48 y después +48 por victoria (rules.STYLE_WIN_REWARDS)
    empatar / perder
            penalización según el rango ANTERIOR a la resolución (rules.STYLE_PENALTIES);
            la racha vuelve a 0; los puntos nunca bajan de 0
            Excepción: si jugaste PASS y no recibiste un HIT, no pasa nada (ni puntos ni racha)
    rango   D 0-8 · C 9-20 · B 21-44 · A 45-299 · S 300+ (rules.STYLE_RANKS)

Definitiva: DESBLOQUEADA mientras el rango es S y no se ha usado (ultimate_unlocked).
El USO es otro dato (ultimate_used) que no cambia con el rango y solo se
reinicia con una partida nueva (un StyleState nuevo).

CombatEngine._apply_style llama a record() UNA vez por interacción y jugador.
"""
from dataclasses import dataclass

WIN, DRAW, LOSE = "win", "draw", "lose"
ULTIMATE_CATEGORIES = ("ATTACK", "GUARD", "BREAK", "MAGIC", "SPECIAL")


def rank_for(points, rules):
    """(código, nombre) del rango para esos puntos."""
    code, name = rules.STYLE_RANKS[0][:2]
    for c, n, minimum in rules.STYLE_RANKS:
        if points >= minimum:
            code, name = c, n
    return code, name


def next_rank(points, rules):
    """(código, mínimo) del siguiente rango, o None en el máximo."""
    for c, _, minimum in rules.STYLE_RANKS:
        if points < minimum:
            return c, minimum
    return None


def rank_progress(points, rules):
    """0..1 dentro del rango actual hacia el siguiente (1.0 en el máximo)."""
    nxt = next_rank(points, rules)
    if nxt is None:
        return 1.0
    floor = max(m for _, _, m in rules.STYLE_RANKS if m <= points)
    return (points - floor) / (nxt[1] - floor)


def win_reward(streak, rules):
    """Puntos por la victoria nº `streak` de la racha (1 = primera)."""
    rewards = rules.STYLE_WIN_REWARDS
    return rewards[min(streak, len(rewards)) - 1]


def penalty(rank_code, outcome, rules):
    draw_pen, lose_pen = rules.STYLE_PENALTIES[rank_code]
    return draw_pen if outcome == DRAW else lose_pen


@dataclass
class StyleChange:
    """Qué hizo una interacción al Estilo de un jugador (para la UI y los tests)."""
    outcome: str
    points_before: int
    points_after: int
    rank_before: str
    rank_after: str
    streak_before: int
    streak_after: int

    @property
    def delta(self):
        return self.points_after - self.points_before

    @property
    def streak_reset(self):
        return self.streak_before > 0 and self.streak_after == 0


@dataclass
class StyleState:
    points: int = 0
    streak: int = 0                 # victorias consecutivas en interacciones (no es el combo)
    ultimate_used: bool = False     # historial: ¿la gastó en esta partida?
    last_change: StyleChange = None

    def rank(self, rules):
        return rank_for(self.points, rules)[0]

    def ultimate_unlocked(self, rules):
        """Disponibilidad (derivada del rango): S y aún sin usar."""
        return self.rank(rules) == rules.ULTIMATE_RANK and not self.ultimate_used

    def record(self, outcome, rules, protected=False):
        """Aplica el resultado de UNA interacción y devuelve el cambio.
        protected: empate/derrota tras jugar PASS sin recibir un HIT; no resta
        puntos ni reinicia la racha (el cambio queda registrado con delta 0)."""
        before_points, before_rank, before_streak = self.points, self.rank(rules), self.streak
        if outcome == WIN:
            self.streak += 1
            self.points += win_reward(self.streak, rules)
        elif not protected:
            self.points = max(0, self.points - penalty(before_rank, outcome, rules))   # rango ANTERIOR
            self.streak = 0
        self.last_change = StyleChange(outcome, before_points, self.points, before_rank, self.rank(rules),
                                       before_streak, self.streak)
        return self.last_change

    def gain(self, points, rules):
        """Suma puntos sin ganar una interacción (p. ej. la carta Taunt): la racha no cambia."""
        before_points, before_rank = self.points, self.rank(rules)
        self.points = max(0, self.points + points)
        self.last_change = StyleChange("gain", before_points, self.points, before_rank, self.rank(rules),
                                       self.streak, self.streak)
        return self.last_change

    def use_ultimate(self, rules):
        """Gasta la definitiva. False (y no cambia nada) si no estaba desbloqueada."""
        if not self.ultimate_unlocked(rules):
            return False
        self.ultimate_used = True
        return True
