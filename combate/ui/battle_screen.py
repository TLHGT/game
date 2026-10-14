"""Pantalla de combate: dibuja el estado del motor y devuelve zonas clicables.

No toma decisiones de juego: solo lee `engine` y el estado visual `view`.
Tras cada interacción muestra dos bloques:
    POR QUÉ ganó   (dentro de la zona de batalla)   GUARD > ATTACK · PLAYER 2 WINS
    QUÉ PASÓ       (píldoras bajo la zona)           sin hit · -> UNSTABLE · SIGUE / FIN DEL TURNO
"""
import math

import pygame

from combate.game.combat import PASS
from combate.game.rules import WIN
from combate.game.state_machine import Phase
from combate.game.status import BREAK_ICE, LOCK_FREEZE, LOCK_PASS
from combate.ui import theme as T
from combate.ui.card_widget import CHIP_COLORS, draw_card, draw_card_back, draw_cost_tag, draw_empty_slot
from combate.ui.player_hud import HUD_W, draw_hud, hud_anchor
from combate.ui.character_widget import draw_character_chip, draw_character_panel
from combate.ui.style_widget import draw_style_row, draw_ultimate_picker
from combate.ui.status_widget import draw_freeze_actions, draw_status_badge, draw_status_icon, draw_status_panel

CARD_W, CARD_H = 112, 150
HAND_Y = 512
BIG_W, BIG_H = 132, 176
BATTLE = pygame.Rect(340, 136, 600, 300)
SLOTS = [pygame.Rect(BATTLE.centerx - 40 - BIG_W, BATTLE.y + 14, BIG_W, BIG_H),
         pygame.Rect(BATTLE.centerx + 40, BATTLE.y + 14, BIG_W, BIG_H)]

KEY_LABELS = [["1", "2", "3", "4", "5"], ["Q", "W", "E", "R", "T"]]
PASS_KEY = ["SPACE", "TAB"]
CONFIRM_KEY = ["ENTER", "SHIFT"]
ULTIMATE_KEY = ["6", "Y"]

PROMPTS = {
    Phase.TURN_START: "INICIO DE TURNO",
    Phase.DRAW: "ROBANDO CARTAS",
    Phase.REDRAW: "CAMBIOS: descarta y roba (máx. 2)",
    Phase.INTERACTION_START: "NUEVA INTERACCIÓN",
    Phase.CARD_SELECTION: "ELIGE CARTA O PASS",
    Phase.CARD_RESOLUTION: "RESOLUCIÓN",
    Phase.MEGA_COMBO: "MEGA COMBO!",
    Phase.TURN_END: "FIN DEL TURNO",
    Phase.GAME_OVER: "FIN DE LA PARTIDA",
}

RESULT_PHASES = (Phase.CARD_REVEAL, Phase.CARD_RESOLUTION, Phase.MEGA_COMBO, Phase.TURN_END)


def hand_rect(player_index, i):
    x0 = 24 if player_index == 0 else T.SCREEN_W - 24 - 5 * 120 + 8
    return pygame.Rect(x0 + i * 120, HAND_Y, CARD_W, CARD_H)


def side_pos(player_index):
    """Dónde aparecen los mensajes de cada jugador."""
    if player_index is None:
        return (T.SCREEN_W // 2, 300)
    return (180, 330) if player_index == 0 else (T.SCREEN_W - 180, 330)


class View:
    """Estado puramente visual que la UI mantiene entre frames."""

    def __init__(self, rules):
        self.time = 0.0
        self.phase_time = 0.0
        self.hp_shown = [rules.MAX_HP, rules.MAX_HP]
        self.pulse = [{}, {}]
        self.hover = None
        self.menu_available = False     # botón MENÚ al terminar (solo si la app tiene menú)
        self.ai_players = set()         # jugadores que controla la IA: mano oculta, sin botones
        self.exit_label = None          # si se fija, al terminar solo hay un botón (p. ej. CONTINUAR)


def _button(surface, rect, label, key, color, buttons, action, enabled=True, hover=None):
    rect = pygame.Rect(rect)
    hot = enabled and hover is not None and rect.collidepoint(hover)
    base = color if enabled else (60, 64, 80)
    pygame.draw.rect(surface, T.mix(base, (255, 255, 255), 0.18) if hot else base, rect, border_radius=8)
    T.text(surface, label, 17, T.BG if enabled else T.DIM, (rect.centerx, rect.centery - 6), "center")
    T.text(surface, f"[{key}]", 12, T.BG if enabled else T.DIM, (rect.centerx, rect.centery + 11), "center")
    if enabled:
        buttons.append((rect, action))


def draw_battle(surface, engine, view):
    buttons = []
    phase = engine.phase
    rules = engine.rules
    surface.fill(T.BG)
    _background(surface, view.time)

    for p in engine.players:
        draw_hud(surface, p, rules, view.hp_shown[p.index], view.time,
                 show_redraws=phase == Phase.REDRAW, pulse=view.pulse[p.index],
                 mana_shown=engine.displayed_mana(p.index))
    badges = _draw_status_badges(surface, engine, view)
    chips = {p.index: draw_character_chip(surface, engine, p, view.pulse[p.index].get("passive", 0))
             for p in engine.players if p.character is not None}
    for p in engine.players:
        draw_style_row(surface, engine, p, view.pulse[p.index].get("style", 0))
        if phase == Phase.CARD_SELECTION and p.index not in view.ai_players:
            draw_ultimate_picker(surface, engine, p, buttons, view.hover, ULTIMATE_KEY[p.index])

    # --- Columna central superior -----------------------------------------------
    cx = T.SCREEN_W // 2
    head = f"TURNO {engine.turn}"
    if engine.interaction_number:
        head += f"  ·  INTERACCIÓN {engine.interaction_number}"
    T.text(surface, head, 21, T.TEXT, (cx, 10), "midtop")
    _legend(surface, (cx, 70))                  # triángulo de tipos, bajo el turno
    _chip_legend(surface, (BATTLE.x // 2, 300))  # qué significa cada chip, a la izquierda
    if phase == Phase.MEGA_COMBO:
        size = int(28 + 4 * math.sin(view.time * 10))
        T.text(surface, "MEGA COMBO!", size, T.GOLD, (cx, 116), "center", shadow=True)
    elif phase == Phase.CARD_REVEAL:
        size = int(26 + 5 * math.sin(min(1.0, view.phase_time / 0.25) * math.pi))
        T.text(surface, "REVEAL!", size, T.TEXT, (cx, 116), "center", shadow=True)
    elif phase == Phase.CARD_SELECTION:
        free = engine.interaction_number <= rules.FREE_INTERACTIONS_PER_TURN
        cost_txt = "CARTA GRATIS" if free else f"CARTA: {rules.PLAY_MANA_COST} MANA · PASS GRATIS"
        T.text(surface, f"{cost_txt} · SPECIAL: {rules.SPECIAL_MANA_COST} MANA", 14,
               (120, 230, 150) if free else (150, 190, 255), (cx, 101), "midtop")
    else:
        T.text(surface, PROMPTS.get(phase, ""), 15, T.GOLD, (cx, 101), "midtop")
    holder = engine.combo_holder
    if holder is not None and phase not in (Phase.MEGA_COMBO, Phase.CARD_REVEAL):
        hp = engine.players[holder]
        T.text(surface, f"{hp.name} · COMBO {hp.combo_hits} / {rules.MAX_COMBO_HITS}", 14,
               T.PLAYER_COLORS[holder], (cx, 118), "midtop")

    # --- Zona de batalla --------------------------------------------------------
    T.panel(surface, BATTLE, color=(22, 26, 38), border=(64, 70, 96))
    T.text(surface, "VS", 34, (90, 96, 120), (BATTLE.centerx, SLOTS[0].centery), "center")
    _draw_slots(surface, engine, view)
    _draw_result(surface, engine)
    _draw_consequences(surface, engine, view)

    for p in engine.players:
        if p.index in view.ai_players:
            _draw_ai_hand(surface, engine, view, p)
        else:
            _draw_hand(surface, engine, view, p, buttons)

    # Fichas de personaje y de estado: al pasar el ratón (encima de todo lo demás)
    for i, rect in chips.items():
        if view.hover is not None and rect.collidepoint(view.hover):
            draw_character_panel(surface, engine, engine.players[i])
    for i, rect in badges.items():
        if view.hover is not None and rect.collidepoint(view.hover):
            draw_status_panel(surface, engine, i, view.time)

    if phase == Phase.GAME_OVER:
        _game_over(surface, engine, buttons, view)
    return buttons


# ---------------------------------------------------------------------------
def _draw_status_badges(surface, engine, view):
    """Estado alterado al lado del nombre de cada jugador, en su HUD."""
    badges = {}
    for p in engine.players:
        if p.status is None:
            continue
        x, y = hud_anchor(p.index)
        left = x + 14 + T.font(22).size(p.name)[0] + 12
        right = x + HUD_W - 12 - 132 - 10          # antes de la insignia de Stability
        badges[p.index] = draw_status_badge(surface, p.status, (left, y + 9), right - left, view.time,
                                            view.pulse[p.index].get("status", 0))
    return badges


def _background(surface, t):
    for i in range(14):
        y = 150 + i * 26
        c = T.mix(T.BG, T.BG2, 0.5 + 0.5 * math.sin(t * 0.6 + i * 0.5))
        pygame.draw.line(surface, c, (0, y), (T.SCREEN_W, y), 1)


def _legend(surface, center):
    """Recordatorio permanente en triángulo (compacto, bajo «TURNO X»):
    GUARD > ATTACK/MAGIC > BREAK > GUARD. Cada flecha va del que gana al que pierde."""
    cx, cy = center
    nodes = {                                   # vértice: (texto, posición)
        "GUARD": ("GRD", (cx, cy - 20)),
        "ATTACK": ("ATK/MAG", (cx + 64, cy + 16)),
        "BREAK": ("BRK", (cx - 64, cy + 16)),
    }
    f = T.font(13)
    sizes = {p: (f.size(lbl)[0] + 12, 18) for p, (lbl, _) in nodes.items()}
    for a, b in (("GUARD", "ATTACK"), ("ATTACK", "BREAK"), ("BREAK", "GUARD")):
        start, end = pygame.Vector2(nodes[a][1]), pygame.Vector2(nodes[b][1])
        d = (end - start).normalize()

        def edge(size, sign):                   # sale del borde de la etiqueta, no del centro
            w, h = size
            tx = (w / 2 + 3) / abs(d.x) if d.x else 1e9
            ty = (h / 2 + 3) / abs(d.y) if d.y else 1e9
            return d * min(tx, ty) * sign
        p0, p1 = start + edge(sizes[a], 1), end + edge(sizes[b], -1)
        color = T.PROPERTY_COLORS[a]
        n = pygame.Vector2(-d.y, d.x)
        pygame.draw.line(surface, color, p0, p1 - d * 4, 2)
        pygame.draw.polygon(surface, color, [p1, p1 - d * 7 + n * 4, p1 - d * 7 - n * 4])
    for prop, (label, pos) in nodes.items():
        w, h = sizes[prop]
        chip = pygame.Rect(0, 0, w, h)
        chip.center = pos
        if prop == "ATTACK":                    # ATK y MAG comparten vértice: dos colores
            left = pygame.Rect(chip.x, chip.y, w // 2, h)
            right = pygame.Rect(chip.x + w // 2, chip.y, w - w // 2, h)
            pygame.draw.rect(surface, T.PROPERTY_COLORS["ATTACK"], left, border_top_left_radius=5,
                             border_bottom_left_radius=5)
            pygame.draw.rect(surface, T.PROPERTY_COLORS["MAGIC"], right, border_top_right_radius=5,
                             border_bottom_right_radius=5)
        else:
            pygame.draw.rect(surface, T.PROPERTY_COLORS[prop], chip, border_radius=5)
        surface.blit(f.render(label, True, T.BG), f.render(label, True, T.BG).get_rect(center=chip.center))


def _chip_legend(surface, center):
    """Qué significa cada chip de las cartas (columna a la izquierda de la zona de batalla)."""
    items = [("10", "daño"), ("INI", "iniciativa"), ("HIT", "suma al combo"), ("DES", "desestabiliza"),
             ("REC", "recupera Stability")]
    f_chip = T.font(11)
    cx, cy = center
    T.text(surface, "CHIPS DE LAS CARTAS", 12, T.DIM, (cx, cy - 18 - len(items) * 11), "center")
    x0 = cx - 70
    for k, (chip, txt) in enumerate(items):
        y = cy - len(items) * 11 + k * 22 + 4
        r = pygame.Rect(x0, y - 7, 28, 14)
        pygame.draw.rect(surface, CHIP_COLORS.get(chip, (255, 255, 255)), r, border_radius=3)
        img = f_chip.render(chip, True, T.BG)
        surface.blit(img, img.get_rect(center=r.center))
        T.text(surface, txt, 13, T.DIM, (r.right + 8, y), "midleft", bold=False)


def _draw_slots(surface, engine, view):
    phase = engine.phase
    r = engine.result
    for i, slot in enumerate(SLOTS):
        color = T.PLAYER_COLORS[i]
        T.text(surface, engine.players[i].name, 15, color, (slot.centerx, slot.bottom + 4), "midtop")
        if r is not None and phase in RESULT_PHASES:
            card = r.cards[i]
            t = min(1.0, view.phase_time / 0.45) if phase == Phase.CARD_REVEAL else 1.0
            sx = abs(math.cos(math.pi * t)) if t < 1 else 1.0   # volteo horizontal
            rect = slot.copy()
            rect.w = max(2, int(slot.w * sx)); rect.centerx = slot.centerx
            if t < 0.5:
                draw_card_back(surface, rect, color)
                continue
            resolved = phase != Phase.CARD_REVEAL
            won = resolved and r.outcome == WIN and r.winner == i
            lost = resolved and r.outcome == WIN and r.winner != i
            action = r.status_actions[i] if r.status_actions else None
            if action is not None:
                _ice_placard(surface, rect, action)
            elif card is None:
                _pass_placard(surface, rect, dim=lost)
            else:
                draw_card(surface, card, rect, big=True, glow=color if won else None, dim=lost)
            special = r.specials[i] if r.specials else None
            if special is not None:
                mini = pygame.Rect(0, 0, 84, 112)
                mini.centery = slot.centery
                if i == 0:
                    mini.right = slot.left - 8
                else:
                    mini.left = slot.right + 8
                draw_card(surface, special, mini)
                T.text(surface, "+ SPECIAL", 12, T.PROPERTY_COLORS["SPECIAL"], (mini.centerx, mini.bottom + 3), "midtop")
        elif phase == Phase.CARD_SELECTION:
            if engine.confirmed[i]:
                draw_card_back(surface, slot, color, ready=True)
            elif engine.selection[i] is not None:
                draw_card_back(surface, slot, T.mix(color, T.BG, 0.5), label="·")
            else:
                draw_empty_slot(surface, slot, color, "ELIGIENDO...")
        else:
            draw_empty_slot(surface, slot, color, "")


def _pass_placard(surface, rect, dim=False):
    pygame.draw.rect(surface, (30, 34, 46), rect, border_radius=12)
    pygame.draw.rect(surface, (120, 126, 146), rect, 3, border_radius=12)
    if rect.w > 40:
        T.text(surface, "PASS", 32, (190, 194, 210), rect.center, "center")
    if dim:
        veil = pygame.Surface(rect.size, pygame.SRCALPHA)
        veil.fill((8, 10, 16, 140))
        surface.blit(veil, rect)


def _ice_placard(surface, rect, action):
    """Jugador congelado: no juega carta. Muestra su acción de estado."""
    pygame.draw.rect(surface, (24, 40, 56), rect, border_radius=12)
    pygame.draw.rect(surface, T.ICE_COLOR, rect, 3, border_radius=12)
    if rect.w > 40:
        draw_status_icon(surface, "FREEZE", (rect.centerx, rect.y + 44), 18)
        T.text(surface, "ICE CUBE", 18, T.ICE_COLOR, (rect.centerx, rect.y + 80), "center")
        T.text(surface, "BREAK ICE" if action == BREAK_ICE else "WAIT", 22, T.TEXT,
               (rect.centerx, rect.y + 116), "center")


def _draw_result(surface, engine):
    """POR QUÉ ganó quien ganó."""
    r = engine.result
    if r is None or engine.phase not in RESULT_PHASES or engine.phase == Phase.CARD_REVEAL:
        return
    y = SLOTS[0].bottom + 24
    lines = r.lines[:4]
    for k, line in enumerate(lines):
        if "WINS" in line and r.winner is not None:
            color = T.PLAYER_COLORS[r.winner]
        elif line == "DRAW":
            color = T.GOLD
        else:
            color = T.TEXT if k == 0 else (200, 204, 218)
        size = 20 if k == 0 or "WINS" in line or line == "DRAW" else 15
        T.text(surface, line, size, color, (BATTLE.centerx, y), "midtop", shadow=k == len(lines) - 1)
        y += size + 3


def _consequence_color(text):
    if text.startswith("MEGA COMBO") or "HIT COMBO" in text:
        return T.GOLD
    if "ICE CUBE" in text or "BREAK ICE" in text or "hielo" in text or "WAIT" in text:
        return T.ICE_COLOR
    for name, color in T.STATUS_COLORS.items():
        if name in text:
            return color
    if "despertado" in text:
        return T.STATUS_COLORS["SLEEP"]
    if " HP" in text:
        return (255, 120, 110)
    if "-> UNSTABLE" in text or "sigue UNSTABLE" in text or "COMBO ROTO" in text:
        return T.UNSTABLE_COLOR
    if "-> STABLE" in text or "protege" in text:
        return T.STABLE_COLOR
    if "HIT" in text and "sin hit" not in text:
        return T.GOLD
    if text.startswith("SIGUE"):
        return (140, 200, 255)
    if text.startswith("FIN DEL TURNO"):
        return (255, 170, 120)
    return (170, 176, 196)


def _draw_consequences(surface, engine, view):
    """QUÉ PASÓ: hit, Stability y si la secuencia sigue. En píldoras."""
    r = engine.result
    if r is None or engine.phase not in (Phase.CARD_RESOLUTION, Phase.MEGA_COMBO) or not r.consequences:
        return
    f = T.font(14)
    pills = [(c, f.size(c)[0] + 18) for c in r.consequences]
    rows, row, width = [], [], 0
    for item in pills:                          # reparte en filas de máx. 760 px
        if row and width + item[1] + 8 > 900:
            rows.append(row); row, width = [], 0
        row.append(item); width += item[1] + 8
    if row:
        rows.append(row)
    appear = min(1.0, view.phase_time / 0.2) if engine.phase == Phase.CARD_RESOLUTION else 1.0
    y = BATTLE.bottom + 1
    for row in rows[:3]:
        total = sum(w for _, w in row) + 8 * (len(row) - 1)
        x = T.SCREEN_W // 2 - total // 2
        for text, w in row:
            color = _consequence_color(text)
            rect = pygame.Rect(x, y, w, 22)
            T.panel(surface, rect, color=(26, 30, 42), border=color, radius=11, alpha=int(255 * appear))
            T.text(surface, text, 14, color, rect.center, "center", alpha=int(255 * appear))
            x += w + 6
        y += 25


def _draw_hand(surface, engine, view, p, buttons):
    phase = engine.phase
    i = p.index
    color = T.PLAYER_COLORS[i]
    lock = engine.status_lock(i) if phase == Phase.CARD_SELECTION else None
    if lock == LOCK_FREEZE:
        draw_freeze_actions(surface, engine, i, hand_rect(i, 0).x, HAND_Y, buttons, view.hover, KEY_LABELS[i],
                            PASS_KEY[i])
    for k in range(5 if lock != LOCK_FREEZE else 0):
        rect = hand_rect(i, k)
        if k >= len(p.hand):
            draw_empty_slot(surface, rect, (70, 76, 96), "")
            continue
        card = p.hand[k]
        dim, cost_label = False, None
        if phase == Phase.CARD_SELECTION:
            playable = engine.can_play(i, card)
            dim = not playable or engine.confirmed[i]
            auto_pass = engine.confirmed[i] and not engine.playable_cards(i)
            if lock == LOCK_PASS:
                cost_label = f"{p.status.definition.short}: BLOQUEADA"
            elif not engine.confirmed[i] or auto_pass:
                cost = engine.play_cost(i, card)
                if not playable:
                    cost_label = "UNAVAILABLE"
                elif card.is_special:
                    cost_label = f"SPECIAL · {cost} MANA"
                else:
                    cost_label = "FREE" if cost == 0 else f"{cost} MANA"
        elif phase == Phase.REDRAW:
            dim = engine.redraw_done[i]
        lift = -8 if (view.hover and rect.collidepoint(view.hover) and not dim) else 0
        draw_card(surface, card, rect.move(0, lift), key_label=KEY_LABELS[i][k], dim=dim)
        if cost_label:
            draw_cost_tag(surface, rect.move(0, lift), cost_label)
        buttons.append((rect, (i, "card", k)))

    row_y = 682
    x0 = hand_rect(i, 0).x
    status, can_pass, can_confirm = _hand_status(engine, p)
    pass_label = "WAIT" if lock == LOCK_FREEZE else "PASS · FREE"
    _button(surface, (x0, row_y, 118, 34), pass_label, PASS_KEY[i], (150, 156, 176), buttons, (i, "pass"),
            enabled=can_pass, hover=view.hover)
    _button(surface, (x0 + 126, row_y, 150, 34), "CONFIRMAR", CONFIRM_KEY[i], color, buttons, (i, "confirm"),
            enabled=can_confirm, hover=view.hover)
    T.text(surface, status, 16, T.TEXT if can_confirm or can_pass else T.DIM, (x0 + 290, row_y + 17), "midleft")


def _draw_ai_hand(surface, engine, view, p):
    """Mano de un jugador de la IA: boca abajo, sin teclas ni botones."""
    i = p.index
    color = T.PLAYER_COLORS[i]
    for k in range(5):
        rect = hand_rect(i, k)
        if k < len(p.hand):
            draw_card_back(surface, rect, T.mix(color, T.BG, 0.35))
        else:
            draw_empty_slot(surface, rect, (70, 76, 96), "")
    phase = engine.phase
    if phase == Phase.CARD_SELECTION:
        status = "LISTO ✓" if engine.confirmed[i] else "PENSANDO..."
    elif phase == Phase.REDRAW:
        status = "LISTO" if engine.redraw_done[i] else "CAMBIANDO CARTAS..."
    else:
        status = ""
    T.text(surface, status, 16, T.DIM, (hand_rect(i, 0).x, 699), "midleft")


def rules_cost(engine, i):
    """Lo que costaría jugar una carta normal ahora mismo."""
    free = engine.interaction_number <= engine.rules.FREE_INTERACTIONS_PER_TURN
    return 0 if free else engine.rules.PLAY_MANA_COST


def _hand_status(engine, p):
    phase, i = engine.phase, p.index
    if phase == Phase.REDRAW:
        if engine.redraw_done[i]:
            return "LISTO", False, False
        return f"Pulsa una carta para cambiarla ({p.redraws_left})", True, True
    if phase == Phase.CARD_SELECTION:
        lock = engine.status_lock(i)
        if lock == LOCK_PASS:
            return f"{p.status.name}: PASS OBLIGATORIO", False, False
        if lock == LOCK_FREEZE:
            if engine.confirmed[i]:
                return "LISTO ✓", False, False
            if engine.selection[i] is not None:
                return "Elección hecha (oculta)", True, True
            return "FREEZE: elige BREAK ICE o WAIT", True, False
        if engine.confirmed[i]:
            auto = engine.selection[i] == PASS and not engine.playable_cards(i)
            if auto and p.hand and p.mana < rules_cost(engine, i):
                return "SIN MANA: PASS AUTOMÁTICO", False, False
            return ("PASS AUTOMÁTICO" if auto else "LISTO ✓"), False, False
        extra = " + SPECIAL" if engine.special_selection[i] is not None else ""
        if engine.ultimate_pick[i]:
            return "Definitiva elegida (oculta)", True, engine.selection[i] is not None
        if engine.selection[i] is not None:
            return f"Elección hecha (oculta){extra}", True, True
        return f"Elige acción principal o PASS{extra}", True, False
    return "", False, False


def _game_over(surface, engine, buttons, view):
    veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    veil.fill((6, 8, 12, 190))
    surface.blit(veil, (0, 0))
    w = engine.winner
    title = "EMPATE" if w is None else f"{engine.players[w].name} WINS"
    if view.exit_label and w is not None:
        title = "DERROTA" if w in view.ai_players else "¡VICTORIA!"
    color = T.GOLD if w is None else T.PLAYER_COLORS[w]
    scale = 1 + 0.04 * math.sin(view.time * 3)
    T.text(surface, title, int(72 * scale), color, (T.SCREEN_W // 2, 280), "center", shadow=True)
    T.text(surface, f"Turnos jugados: {engine.turn}", 20, T.DIM, (T.SCREEN_W // 2, 340), "center")
    if view.exit_label:
        _button(surface, (T.SCREEN_W // 2 - 100, 380, 200, 46), view.exit_label, "ENTER", T.GOLD, buttons,
                (None, "exit"), hover=view.hover)
        return
    x = T.SCREEN_W // 2 - (190 if view.menu_available else 90)
    _button(surface, (x, 380, 180, 46), "REVANCHA", "R / ENTER", T.GOLD, buttons,
            (None, "restart"), hover=view.hover)
    if view.menu_available:
        _button(surface, (x + 200, 380, 180, 46), "MENÚ / MAZOS", "M", (140, 200, 255), buttons,
                (None, "menu"), hover=view.hover)
