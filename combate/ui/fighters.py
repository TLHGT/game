"""Escenario del combate: un suelo y los personajes del combate encima.

Solo dibuja: lee el estado del motor (fase, Stability, resultado) y el tiempo
de la vista. Las animaciones no se guardan en ningún sitio: se calculan cada
frame a partir de `view.phase_time`, así que siempre van sincronizadas con
la fase en curso.

Poses (en bucle):
    STABLE      erguido, respirando
    UNSTABLE    agachado, tambaleándose, con estrellitas de mareo
    CAMBIOS     (fase REDRAW) sujeta un abanico de cartas y las baraja

Animaciones de un golpe (fase CARD_RESOLUTION; en bucle en MEGA COMBO):
    ATTACK / MAGIC / BREAK   embestida, proyectil o salto con onda en el suelo
    GUARD                    se cubre con un escudo
    hit recibido             (solo quien pierde la interacción y recibe hit)
                             retroceso, destello y chispas

Sprites: los mismos del mapa (AssetManager: PNG en assets/ o placeholder),
mirando a la derecha. El de la derecha se voltea.
"""
import math

import pygame

from combate.game.rules import WIN
from combate.game.state_machine import Phase
from combate.ui import theme as T

FLOOR_TOP = 268                 # el suelo: rectángulo bajo los personajes
FLOOR_H = 70
FEET_Y = 312
FIGHTER_X = (532, 758)
MAX_SCALE, MAX_H, MAX_W = 2.4, 150, 150
LUNGE = 46                      # px que avanza al atacar

OFFENSIVE = ("ATTACK", "MAGIC", "BREAK")
IMPACT = {"ATTACK": 0.26, "MAGIC": 0.42, "BREAK": 0.36}    # cuándo llega el golpe (s)
HIT_TIME = 0.6
MEGA_PERIOD = 0.5               # MEGA COMBO: una embestida cada medio segundo


# --- Sprites ------------------------------------------------------------------
_assets = None
_sprites = {}


def _load(key):
    """Imagen del mapa para `key` (None si no hay AssetManager disponible)."""
    global _assets
    try:
        if _assets is None:
            from game import settings
            from render.assets import AssetManager
            _assets = AssetManager(settings.ASSET_DIR)
        return _assets.get(key)
    except Exception:           # p. ej. sin modo de vídeo: silueta genérica
        return None


def _silhouette():
    s = pygame.Surface((34, 56), pygame.SRCALPHA)
    pygame.draw.circle(s, (200, 204, 218), (17, 12), 10)
    pygame.draw.rect(s, (160, 166, 186), (7, 22, 20, 22), border_radius=6)
    pygame.draw.rect(s, (110, 116, 136), (9, 44, 7, 12))
    pygame.draw.rect(s, (110, 116, 136), (18, 44, 7, 12))
    return s


def fighter_key(engine, view, i):
    """Clave del sprite de cada jugador: la que fije la escena o el avatar del personaje."""
    keys = getattr(view, "fighter_keys", None)
    if keys and keys[i]:
        return keys[i]
    ch = engine.players[i].character
    return f"{(ch.avatar if ch else None) or 'player'}_right_0"


def fighter_sprite(key, flip):
    if (key, flip) not in _sprites:
        img = _load(key) or _silhouette()
        w, h = img.get_size()
        k = min(MAX_SCALE, MAX_H / h, MAX_W / w)
        img = pygame.transform.scale(img, (max(1, round(w * k)), max(1, round(h * k))))
        _sprites[(key, flip)] = pygame.transform.flip(img, True, False) if flip else img
    return _sprites[(key, flip)]


# --- Utilidades -----------------------------------------------------------------
def _ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def _lerp(a, b, u):
    return a + (b - a) * u


class Pose:
    """Desplazamiento, giro y escala del sprite respecto a su punto de apoyo."""

    def __init__(self):
        self.dx = self.dy = 0.0
        self.angle = 0.0        # grados, positivo = antihorario
        self.sx = self.sy = 1.0
        self.white = 0.0        # destello blanco 0..1
        self.red = 0.0          # tinte rojo 0..1
        self.grey = False
        self.ice = False        # tinte azul (FREEZE)


# --- Escenario ------------------------------------------------------------------
def draw_stage(surface, stage, t):
    """Fondo (pared) y el rectángulo del suelo."""
    T.panel(surface, stage, color=(20, 24, 34), border=(64, 70, 96))
    wall = pygame.Rect(stage.x + 3, stage.y + 3, stage.w - 6, FLOOR_TOP - stage.y - 3)
    pygame.draw.rect(surface, (26, 32, 42), wall, border_top_left_radius=10, border_top_right_radius=10)
    for y in range(wall.y + 22, wall.bottom, 26):                    # azulejos de la pared
        pygame.draw.line(surface, (32, 39, 50), (wall.x, y), (wall.right - 1, y))
    for k, x in enumerate(range(wall.x + 20, wall.right, 40)):
        for y in range(wall.y, wall.bottom, 52):
            xx = x + (20 if (y // 52) % 2 else 0)
            if xx < wall.right:
                pygame.draw.line(surface, (32, 39, 50), (xx, y + 22), (xx, min(wall.bottom, y + 48)))
    pygame.draw.rect(surface, (40, 48, 60), (wall.x, wall.bottom - 10, wall.w, 10))   # zócalo

    floor = pygame.Rect(stage.x + 10, FLOOR_TOP, stage.w - 20, FLOOR_H)
    pygame.draw.rect(surface, (52, 58, 72), floor, border_radius=6)
    vanish = (floor.centerx, floor.y - 260)                          # baldosas en perspectiva
    for k in range(-7, 8):
        x = floor.centerx + k * 64
        top = (_lerp(vanish[0], x, 260 / (260 + FLOOR_H)), floor.y)
        pygame.draw.line(surface, (60, 67, 82), top, (x, floor.bottom - 1))
    for y in (floor.y + 18, floor.y + 40):
        pygame.draw.line(surface, (60, 67, 82), (floor.x, y), (floor.right - 1, y))
    pygame.draw.line(surface, (92, 100, 122), floor.topleft, (floor.right - 1, floor.y), 2)
    pygame.draw.rect(surface, (78, 86, 106), floor, 2, border_radius=6)
    T.text(surface, "VS", 26, (78, 84, 108), (stage.centerx, FLOOR_TOP - 40), "center")


# --- Personajes -----------------------------------------------------------------
def draw_fighters(surface, engine, view):
    phase, t = engine.phase, view.time
    for i, p in enumerate(engine.players):
        f = 1 if i == 0 else -1                 # hacia dónde mira (+1 derecha)
        img = fighter_sprite(fighter_key(engine, view, i), flip=i == 1)
        pose, fx = Pose(), []
        _base_pose(pose, engine, p, i, f, t)
        _action_pose(pose, engine, view, i, f, fx)
        foot = (FIGHTER_X[i], FEET_Y)
        _shadow(surface, foot, img.get_width(), pose)
        if phase != Phase.GAME_OVER:
            _stability_ring(surface, foot, img.get_width(), p.stable, t)
        for effect in fx:                        # efectos detrás del sprite
            if effect[0] == "behind":
                effect[1](surface)
        top = _blit_pose(surface, img, foot, pose)
        head = (foot[0] + pose.dx, top)
        _overlays(surface, engine, p, i, f, t, img, foot, pose, head)
        for effect in fx:
            if effect[0] == "front":
                effect[1](surface)
        T.text(surface, p.name, 14, T.PLAYER_COLORS[i], (foot[0], FEET_Y + 8), "midtop")


def status_of(p):
    """Estado alterado activo ("BURN", "FREEZE"...) o None."""
    return p.status.id.value if p.status is not None else None


def _base_pose(pose, engine, p, i, f, t):
    """Pose en bucle: STABLE, UNSTABLE, cambio de cartas, estado o fin de la partida."""
    phase = engine.phase
    if phase == Phase.GAME_OVER and engine.winner is not None:
        if engine.winner != i:                  # K.O.: tumbado de espaldas
            pose.angle = f * 90
            pose.grey = True
            return
        pose.dy = -10 * abs(math.sin(t * 5))    # el ganador da saltitos
        return
    status = status_of(p)
    if status == "FREEZE":                      # congelado: inmóvil y azulado
        pose.ice = True
        return
    if status == "SLEEP":                       # dormido: cabecea despacio
        pose.angle = -f * (6 + 3 * math.sin(t * 1.6))
        pose.sy = 0.96 + 0.03 * math.sin(t * 1.6)
        return
    if phase == Phase.REDRAW:                   # sujeta las cartas, algo echado hacia atrás
        pose.angle = f * 4 + 1.5 * math.sin(t * 2)
        pose.sy = 1 + 0.015 * math.sin(t * 2.4)
        return
    if status == "PARALYZE":                    # calambres: tirones cortos
        pose.dx = 3 * math.sin(t * 40 + i) if int(t * 3) % 3 == 0 else 0
    if p.stable:                                # respiración tranquila
        b = math.sin(t * 2.4 + i)
        pose.sy = 1 + 0.02 * b
        pose.sx = 1 - 0.01 * b
        return
    pose.sy, pose.sx = 0.86, 1.08               # UNSTABLE: agachado y tambaleándose
    pose.angle = f * 4 + 10 * math.sin(t * 3.3 + i)
    pose.dx += 2 * math.sin(t * 9 + i)


def _impact_time(card_type):
    return IMPACT.get(card_type, 0.3)


def _action_pose(pose, engine, view, i, f, fx):
    """Animación de la carta jugada y, si pierde con hit, la de recibir el golpe."""
    r, phase = engine.result, engine.phase
    if r is None or phase not in (Phase.CARD_RESOLUTION, Phase.MEGA_COMBO):
        return
    t = view.phase_time
    other = 1 - i
    if phase == Phase.MEGA_COMBO:               # ráfaga de embestidas del que activa el Mega Combo
        if t >= MEGA_PERIOD * 3:
            return
        local = (t % MEGA_PERIOD) / MEGA_PERIOD * 0.7
        if r.mega_combo == i:
            _offensive(pose, "ATTACK", local, i, f, fx)
        elif r.mega_combo == other:
            _hit(pose, local - IMPACT["ATTACK"], i, f, fx)
        return

    cards, frozen = r.cards, r.status_actions or (None, None)
    mine = cards[i].card_type if cards[i] is not None and frozen[i] is None else None
    theirs = cards[other].card_type if cards[other] is not None and frozen[other] is None else None
    start = None
    if r.outcome == WIN and r.winner == other and r.received_hit[i]:
        if theirs in OFFENSIVE:
            start = _impact_time(theirs)
        elif mine in OFFENSIVE:                 # contraataque: el golpe llega al chocar
            start = _impact_time(mine) + 0.06
        else:
            start = 0.3
    # Si le golpean, su propia animación se corta en ese instante y se apaga
    own_t = t if start is None else min(t, start)
    own, own_fx = Pose(), []
    if mine in OFFENSIVE:
        _offensive(own, mine, own_t, i, f, own_fx)
    elif mine == "GUARD":
        _guard(own, own_t, i, f, own_fx, block_at=_impact_time(theirs) if theirs in OFFENSIVE else None)
    if start is None or t <= start:
        fx.extend(own_fx)
    keep = 1.0 if start is None or t <= start else 1 - _ease((t - start) / 0.25)
    pose.dx += own.dx * keep
    pose.dy += own.dy * keep
    pose.angle += own.angle * keep
    pose.sx *= _lerp(1, own.sx, keep)
    pose.sy *= _lerp(1, own.sy, keep)
    if start is not None:
        _hit(pose, t - start, i, f, fx)


def _front(i, f, dx=0):
    return FIGHTER_X[i] + dx + f * 40


def _offensive(pose, kind, t, i, f, fx):
    color = T.PROPERTY_COLORS[kind]
    target_x = FIGHTER_X[1 - i]
    if kind == "ATTACK":                        # amago atrás, embestida, vuelta
        if t < 0.12:
            k = _ease(t / 0.12)
            pose.dx, pose.angle = -10 * f * k, 6 * f * k
        elif t < 0.24:
            k = _ease((t - 0.12) / 0.12)
            pose.dx, pose.angle = f * _lerp(-10, LUNGE, k), f * _lerp(6, -12, k)
        elif t < 0.36:
            pose.dx, pose.angle = f * LUNGE, -12 * f
        elif t < 0.7:
            k = _ease((t - 0.36) / 0.34)
            pose.dx, pose.angle = f * LUNGE * (1 - k), -12 * f * (1 - k)
        if 0.2 <= t < 0.44:
            u = (t - 0.2) / 0.24
            x = FIGHTER_X[i] + f * (LUNGE + 46)
            fx.append(("front", lambda s, u=u, x=x: _slash(s, (x, FEET_Y - 70), f, u, color)))
    elif kind == "MAGIC":                       # alza los brazos y lanza un orbe
        if t < 0.2:
            k = _ease(t / 0.2)
            pose.dx, pose.angle, pose.sy = -6 * f * k, 4 * f * k, 1 + 0.08 * k
        elif t < 0.3:
            k = _ease((t - 0.2) / 0.1)
            pose.dx, pose.angle, pose.sy = f * _lerp(-6, 16, k), f * _lerp(4, -8, k), _lerp(1.08, 1, k)
        elif t < 0.46:
            pose.dx, pose.angle = 16 * f, -8 * f
        elif t < 0.75:
            k = _ease((t - 0.46) / 0.29)
            pose.dx, pose.angle = 16 * f * (1 - k), -8 * f * (1 - k)
        if t < 0.3:
            fx.append(("behind", lambda s, k=t / 0.3: _aura(s, (FIGHTER_X[i] + pose.dx, FEET_Y - 60), k, color)))
        if 0.22 <= t < IMPACT["MAGIC"]:
            u = (t - 0.22) / (IMPACT["MAGIC"] - 0.22)
            x = _lerp(_front(i, f, 16 * f), target_x, u)
            fx.append(("front", lambda s, x=x: _orb(s, (x, FEET_Y - 72), color, f)))
        elif IMPACT["MAGIC"] <= t < IMPACT["MAGIC"] + 0.2:
            u = (t - IMPACT["MAGIC"]) / 0.2
            fx.append(("front", lambda s, u=u: _burst(s, (target_x, FEET_Y - 72), u, color)))
    elif kind == "BREAK":                       # se agacha, salta y cae con una onda en el suelo
        if t < 0.1:
            k = _ease(t / 0.1)
            pose.sy, pose.sx = 1 - 0.15 * k, 1 + 0.1 * k
        elif t < 0.36:
            k = (t - 0.1) / 0.26
            pose.dx, pose.dy = f * LUNGE * _ease(k), -55 * math.sin(math.pi * k)
            pose.angle, pose.sy = -f * 18 * math.sin(math.pi * k), 1.05
        elif t < 0.46:
            k = (t - 0.36) / 0.1
            pose.dx, pose.sy, pose.sx = f * LUNGE, _lerp(0.82, 1, k), _lerp(1.14, 1, k)
        elif t < 0.75:
            k = _ease((t - 0.46) / 0.29)
            pose.dx = f * LUNGE * (1 - k)
        if IMPACT["BREAK"] <= t < IMPACT["BREAK"] + 0.32:
            u = (t - IMPACT["BREAK"]) / 0.32
            x = FIGHTER_X[i] + f * (LUNGE + 40)
            fx.append(("behind", lambda s, u=u, x=x: _shockwave(s, (x, FEET_Y), u, color)))


def _guard(pose, t, i, f, fx, block_at=None):
    """Retrocede un poco y levanta un escudo delante."""
    if t < 0.12:
        k = _ease(t / 0.12)
    elif t < 0.9:
        k = 1.0
    else:
        k = 1 - _ease((t - 0.9) / 0.2)
    pose.dx, pose.angle, pose.sx = -8 * f * k, 3 * f * k, 1 - 0.05 * k
    if k <= 0:
        return
    flash = 0.0
    if block_at is not None and block_at <= t < block_at + 0.25:
        flash = 1 - (t - block_at) / 0.25
    center = (FIGHTER_X[i] + pose.dx + f * 46, FEET_Y - 62)
    fx.append(("front", lambda s: _shield(s, center, f, k, flash)))


def _hit(pose, u, i, f, fx):
    """Recibe el golpe: retroceso, destello blanco, parpadeo rojo y chispas."""
    if u < 0 or u >= HIT_TIME:
        return
    a = _ease(u / 0.12) if u < 0.12 else 1 - _ease((u - 0.12) / (HIT_TIME - 0.12))
    pose.dx += -f * 34 * a
    pose.angle += f * 16 * a
    pose.white = max(0.0, 1 - u / 0.12)
    if u < 0.45 and int(u * 18) % 2 == 0:
        pose.red = 0.7
    if u < 0.25:
        center = (FIGHTER_X[i] + pose.dx + f * 10, FEET_Y - 70)
        fx.append(("front", lambda s, k=u / 0.25: _sparks(s, center, k)))


# --- Dibujo ---------------------------------------------------------------------
def _blit_pose(surface, img, foot, pose):
    """Dibuja el sprite girado/escalado alrededor de sus pies. Devuelve la y de la cabeza."""
    w, h = img.get_size()
    sw, sh = max(1, round(w * pose.sx)), max(1, round(h * pose.sy))
    if (sw, sh) != (w, h):
        img = pygame.transform.scale(img, (sw, sh))
    if pose.white or pose.red or pose.grey or pose.ice:
        img = img.copy()
        if pose.ice:
            img.fill((150, 210, 255), special_flags=pygame.BLEND_RGB_MULT)
            img.fill((30, 50, 70), special_flags=pygame.BLEND_RGB_ADD)
        if pose.grey:
            img.fill((120, 120, 130), special_flags=pygame.BLEND_RGB_MULT)
        if pose.red:
            img.fill((255, int(255 * (1 - 0.6 * pose.red)), int(255 * (1 - 0.6 * pose.red))),
                     special_flags=pygame.BLEND_RGB_MULT)
            img.fill((int(110 * pose.red), 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if pose.white:
            v = int(220 * pose.white)
            img.fill((v, v, v), special_flags=pygame.BLEND_RGB_ADD)
    fx, fy = foot[0] + pose.dx, foot[1] + pose.dy
    if pose.angle:
        rotated = pygame.transform.rotate(img, pose.angle)
        center = pygame.Vector2(fx, fy) + pygame.Vector2(0, -sh / 2).rotate(-pose.angle)
        surface.blit(rotated, rotated.get_rect(center=center))
    else:
        surface.blit(img, img.get_rect(midbottom=(round(fx), round(fy))))
    return fy - sh * math.cos(math.radians(pose.angle))


def _shadow(surface, foot, width, pose):
    lift = max(0.0, -pose.dy) / 60
    w = max(10, int(width * 0.8 * (1 - 0.4 * lift)))
    s = pygame.Surface((w, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, int(110 * (1 - 0.5 * lift))), s.get_rect())
    surface.blit(s, s.get_rect(center=(foot[0] + pose.dx, foot[1] - 2)))


def _stability_ring(surface, foot, width, stable, t):
    """Aro en el suelo: verde tranquilo (STABLE) o rojo que late (UNSTABLE)."""
    w = int(width * 0.95)
    s = pygame.Surface((w + 8, 22), pygame.SRCALPHA)
    if stable:
        color, alpha = T.STABLE_COLOR, 90
    else:
        color, alpha = T.UNSTABLE_COLOR, int(150 + 80 * math.sin(t * 8))
    pygame.draw.ellipse(s, (*color, alpha), s.get_rect().inflate(-4, -4), 2)
    surface.blit(s, s.get_rect(center=(foot[0], foot[1] - 2)))


def _overlays(surface, engine, p, i, f, t, img, foot, pose, head):
    phase = engine.phase
    if phase == Phase.GAME_OVER:
        return
    _status_effect(surface, status_of(p), foot, img.get_size(), pose, head, f, t + i * 0.37)
    if phase == Phase.REDRAW:
        hand = (foot[0] + pose.dx + f * 30, foot[1] - img.get_height() * 0.5)
        _card_fan(surface, hand, f, t, done=engine.redraw_done[i])
        if engine.redraw_done[i]:
            T.text(surface, "LISTO", 13, T.STABLE_COLOR, (head[0], head[1] - 12), "center", shadow=True)
    elif not p.stable and status_of(p) not in ("FREEZE", "SLEEP"):
        _dizzy(surface, (head[0], head[1] - 8), t + i)
        drop_t = (t * 1.3 + i * 0.5) % 1.0                 # gota de sudor
        if drop_t < 0.7:
            x = head[0] - f * 18
            y = head[1] + 14 + drop_t * 18
            pygame.draw.circle(surface, (150, 210, 255), (int(x), int(y)), 3)
            pygame.draw.polygon(surface, (150, 210, 255), [(x - 3, y - 1), (x + 3, y - 1), (x, y - 7)])


def _alpha_surface(size):
    return pygame.Surface(size, pygame.SRCALPHA)


def _slash(surface, center, f, u, color):
    """Tajo: tres arcos que barren de arriba abajo y se desvanecen."""
    s = _alpha_surface((120, 120))
    alpha = int(255 * (1 - u))
    sweep = math.pi * 0.9 * min(1.0, u * 2.2)
    start = math.pi * 0.55
    for k, (r, c) in enumerate(((52, (255, 255, 255)), (44, color), (36, color))):
        rect = pygame.Rect(60 - r, 60 - r, 2 * r, 2 * r)
        pygame.draw.arc(s, (*c, alpha), rect, start - sweep, start, 5 - k)
    if f < 0:
        s = pygame.transform.flip(s, True, False)
    surface.blit(s, s.get_rect(center=center))


def _aura(surface, center, k, color):
    s = _alpha_surface((140, 140))
    for r in range(3):
        pygame.draw.circle(s, (*color, int(60 * k)), (70, 70), int(30 + 18 * k + r * 10), 3)
    surface.blit(s, s.get_rect(center=center))


def _orb(surface, center, color, f):
    x, y = center
    for k in range(5):                                   # estela
        pygame.draw.circle(surface, T.mix(color, T.BG, 0.2 + k * 0.15), (int(x - f * k * 9), int(y)), 9 - k)
    s = _alpha_surface((48, 48))
    pygame.draw.circle(s, (*color, 90), (24, 24), 22)
    surface.blit(s, s.get_rect(center=center))
    pygame.draw.circle(surface, color, (int(x), int(y)), 11)
    pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), 5)


def _burst(surface, center, u, color):
    s = _alpha_surface((120, 120))
    pygame.draw.circle(s, (*color, int(200 * (1 - u))), (60, 60), int(14 + 40 * u), 4)
    pygame.draw.circle(s, (255, 255, 255, int(160 * (1 - u))), (60, 60), int(8 + 26 * u), 2)
    surface.blit(s, s.get_rect(center=center))


def _shockwave(surface, center, u, color):
    s = _alpha_surface((200, 50))
    w, h = int(40 + 150 * u), int(10 + 24 * u)
    pygame.draw.ellipse(s, (*color, int(230 * (1 - u))), pygame.Rect(100 - w // 2, 25 - h // 2, w, h), 4)
    surface.blit(s, s.get_rect(center=center))
    for k in range(4):                                   # cascotes
        a = math.pi * (0.15 + 0.23 * k)
        r = 20 + 60 * u
        x = center[0] + math.cos(a) * r
        y = center[1] - math.sin(a) * r * 1.2 + 40 * u * u
        pygame.draw.rect(surface, T.mix(color, (90, 80, 70), 0.5), (int(x), int(y), 5, 5))


def _shield(surface, center, f, k, flash):
    color = T.mix(T.PROPERTY_COLORS["GUARD"], (255, 255, 255), flash)
    s = _alpha_surface((70, 130))
    rect = pygame.Rect(0, 0, 44, 110)
    rect.center = (35, 65)
    pygame.draw.ellipse(s, (*color, int((70 + 90 * flash) * k)), rect)
    pygame.draw.ellipse(s, (*color, int(230 * k)), rect, 4)
    pygame.draw.ellipse(s, (255, 255, 255, int(120 * k)), rect.inflate(-18, -40), 2)
    if f < 0:
        s = pygame.transform.flip(s, True, False)
    surface.blit(s, s.get_rect(center=center))


def _sparks(surface, center, k):
    for n in range(8):
        a = n * math.pi / 4 + 0.3
        r0, r1 = 8 + 20 * k, 20 + 34 * k
        p0 = (center[0] + math.cos(a) * r0, center[1] + math.sin(a) * r0)
        p1 = (center[0] + math.cos(a) * r1, center[1] + math.sin(a) * r1)
        pygame.draw.line(surface, T.GOLD if n % 2 else (255, 255, 255), p0, p1, 3)


def _star(surface, center, r, color):
    x, y = center
    pts = [(x, y - r), (x + r * 0.3, y - r * 0.3), (x + r, y), (x + r * 0.3, y + r * 0.3),
           (x, y + r), (x - r * 0.3, y + r * 0.3), (x - r, y), (x - r * 0.3, y - r * 0.3)]
    pygame.draw.polygon(surface, color, pts)


def _dizzy(surface, center, t):
    """Estrellitas que giran sobre la cabeza (UNSTABLE)."""
    for k in range(3):
        a = t * 4 + k * 2 * math.pi / 3
        x = center[0] + math.cos(a) * 26
        y = center[1] + math.sin(a) * 7
        _star(surface, (x, y), 8 if math.sin(a) > 0 else 5, T.GOLD if k % 2 else T.UNSTABLE_COLOR)


def _card_fan(surface, hand, f, t, done):
    """Abanico de cartas en la mano; si aún está cambiando, una sale volando y vuelve otra."""
    base = pygame.Surface((16, 22), pygame.SRCALPHA)
    pygame.draw.rect(base, (36, 40, 60), base.get_rect(), border_radius=3)
    pygame.draw.rect(base, T.GOLD, base.get_rect(), 2, border_radius=3)
    for k, ang in enumerate((-22, 0, 22)):
        img = pygame.transform.rotate(base, ang * f + 4 * math.sin(t * 2))
        off = pygame.Vector2(0, -12).rotate(-ang * f)
        surface.blit(img, img.get_rect(center=(hand[0] + off.x, hand[1] + off.y)))
    if done:
        return
    u = (t % 0.9) / 0.9
    if u < 0.5:                                          # sale volando hacia atrás
        k = u / 0.5
        pos = (hand[0] - f * 40 * k, hand[1] - 20 - 30 * math.sin(math.pi * k))
        img = pygame.transform.rotate(base, -f * 360 * k)
        img.set_alpha(int(255 * (1 - k)))
    else:                                                # entra la nueva desde arriba
        k = (u - 0.5) / 0.5
        pos = (hand[0], hand[1] - 50 * (1 - k) - 12)
        img = base.copy()
        img.set_alpha(int(255 * k))
    surface.blit(img, img.get_rect(center=pos))


# --- Estados alterados ------------------------------------------------------------
def _status_effect(surface, status, foot, size, pose, head, f, t):
    """FREEZE cubo de hielo · SLEEP zzz · PARALYZE rayitos · BURN llamitas · POISON burbujas."""
    if status is None:
        return
    w, h = size
    body = pygame.Rect(0, 0, int(w * 0.8), int(h * 0.85))
    body.midbottom = (foot[0] + pose.dx, foot[1] + pose.dy)
    if status == "FREEZE":
        _ice_cube(surface, foot, size, pose)
    elif status == "SLEEP":
        _zzz(surface, (head[0] + f * 14, head[1] + 6), f, t)
    elif status == "PARALYZE":
        _sparks_around(surface, body, t)
    elif status == "BURN":
        _small_flames(surface, body, t)
    elif status == "POISON":
        _bubbles(surface, body, t)


def _ice_cube(surface, foot, size, pose):
    """Cubo de hielo en perspectiva: cara frontal, tapa y lateral, con brillos."""
    w, h = size
    d = 16                                               # profundidad de la tapa y el lateral
    front = pygame.Rect(0, 0, w + 14, h + 10)
    front.midbottom = (foot[0] + pose.dx - d // 2, foot[1] + 6)
    s = _alpha_surface((front.w + d + 4, front.h + d + 4))
    fr = pygame.Rect(2, d + 2, front.w, front.h)
    top = [(fr.x, fr.y), (fr.x + d, fr.y - d), (fr.right + d, fr.y - d), (fr.right, fr.y)]
    side = [(fr.right, fr.y), (fr.right + d, fr.y - d), (fr.right + d, fr.bottom - d), (fr.right, fr.bottom)]
    ice = T.ICE_COLOR
    pygame.draw.polygon(s, (*T.mix(ice, (255, 255, 255), 0.45), 120), top)
    pygame.draw.polygon(s, (*T.mix(ice, (20, 40, 70), 0.35), 110), side)
    pygame.draw.rect(s, (*ice, 80), fr)
    for poly in (top, side):
        pygame.draw.polygon(s, (*ice, 220), poly, 2)
    pygame.draw.rect(s, (*ice, 230), fr, 3)
    pygame.draw.line(s, (255, 255, 255, 170), (fr.x + 8, fr.y + 10), (fr.x + 8, fr.y + fr.h // 2), 3)
    pygame.draw.line(s, (255, 255, 255, 120), (fr.x + 15, fr.y + 10), (fr.x + 15, fr.y + fr.h // 4), 2)
    pygame.draw.line(s, (255, 255, 255, 90), (fr.right - 12, fr.bottom - 26), (fr.right - 22, fr.bottom - 12), 2)
    surface.blit(s, (front.x - 2, front.y - d - 2))


def _zzz(surface, start, f, t):
    """Tres Z que suben haciendo eses, crecen y se desvanecen."""
    for k in range(3):
        u = (t * 0.55 + k / 3) % 1.0
        x = start[0] + f * (8 + 26 * u) + 5 * math.sin(u * 9)
        y = start[1] - 50 * u
        T.text(surface, "Z", int(12 + 12 * u), (190, 200, 255), (x, y), "center",
               alpha=int(255 * min(1.0, (1 - u) * 2.5)), shadow=True)


def _bolt(surface, a, b, color, width=2):
    """Rayito en zigzag de a a b."""
    pts = [a]
    for k in (1, 2, 3):
        x = _lerp(a[0], b[0], k / 4) + (5 if k % 2 else -5)
        y = _lerp(a[1], b[1], k / 4)
        pts.append((x, y))
    pts.append(b)
    pygame.draw.lines(surface, color, False, pts, width)


def _sparks_around(surface, body, t):
    """Rayitos amarillos que chisporrotean alrededor del cuerpo (cambian a saltos)."""
    color = T.STATUS_COLORS["PARALYZE"]
    tick = int(t * 9)
    for k in range(4):
        if (tick + k) % 4 == 0:                          # parpadean
            continue
        rnd = (tick * 7 + k * 13) % 17 / 17
        side = -1 if (tick + k) % 2 else 1
        x = body.centerx + side * (body.w // 2 + 2) - side * rnd * 10
        y = body.y + 10 + rnd * body.h * 0.7
        _bolt(surface, (x, y), (x + side * 22, y + 26), (255, 255, 255), 5)
        _bolt(surface, (x, y), (x + side * 22, y + 26), color, 3)


def _small_flames(surface, body, t):
    """Llamitas que suben desde el cuerpo y se apagan."""
    for k in range(5):
        u = (t * 1.1 + k / 5) % 1.0
        x = body.x + body.w * ((k * 0.37 + 0.1) % 1.0) + 3 * math.sin(t * 8 + k)
        y = body.bottom - 10 - body.h * 0.75 * u
        size = 7 * (1 - u) + 2
        outer = T.mix(T.STATUS_COLORS["BURN"], (255, 60, 30), u)
        pygame.draw.polygon(surface, outer, [(x - size, y), (x, y - size * 2.2), (x + size, y)])
        pygame.draw.circle(surface, outer, (int(x), int(y)), int(size))
        inner = size * 0.5
        pygame.draw.polygon(surface, (255, 230, 120), [(x - inner, y), (x, y - inner * 2.2), (x + inner, y)])


def _bubbles(surface, body, t):
    """Burbujas moradas que suben y revientan."""
    color = T.STATUS_COLORS["POISON"]
    for k in range(5):
        u = (t * 0.7 + k / 5) % 1.0
        x = body.x + body.w * ((k * 0.29 + 0.15) % 1.0) + 4 * math.sin(u * 7 + k)
        y = body.bottom - 14 - (body.h + 10) * u
        r = int(4 + 5 * u)
        if u > 0.9:                                      # revienta
            for a in range(0, 360, 60):
                v = pygame.Vector2(r + 3, 0).rotate(a)
                pygame.draw.circle(surface, color, (int(x + v.x), int(y + v.y)), 1)
            continue
        pygame.draw.circle(surface, T.mix(color, (40, 10, 60), 0.3), (int(x), int(y)), r + 1)
        pygame.draw.circle(surface, color, (int(x), int(y)), r)
        pygame.draw.circle(surface, (235, 210, 255), (int(x - r * 0.35), int(y - r * 0.35)), max(1, r // 3))
