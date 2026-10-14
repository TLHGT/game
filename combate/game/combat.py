"""Motor de combate: orquesta turnos, interacciones y combos.

No depende de Pygame. La UI:
    - llama a advance() en las fases automáticas (tras su animación);
    - llama a redraw/finish_redraw/select/confirm según el input;
    - lee engine.pop_events() para animaciones y mensajes.

Flujo de un turno:
    TURN_START (+Mana, estados de inicio de turno) -> DRAW (hasta 5) -> REDRAW (2 cambios)
    -> INTERACTION_START (estados de inicio de interacción) -> CARD_SELECTION -> CARD_REVEAL
    -> CARD_RESOLUTION   efectos -> hits -> daño (HP o ICE CUBE) -> Stability -> combo
                         -> estados nuevos -> estados de fin de interacción
    -> MEGA_COMBO        solo si alguien llegó a 3 hits: daño ADICIONAL, combo = 0
    -> ¿iniciativa?  sí: INTERACTION_START (automático) · no: TURN_END
    TURN_END -> TURN_START | GAME_OVER
    (TURN_START / INTERACTION_START -> GAME_OVER si el daño de un estado deja a alguien a 0 HP)

Status Effects (game/status.py): cada transición llama a los ganchos de los
estados desde UN solo sitio (_status_turn_start, _status_interaction_start,
_status_interaction_end, _wake_on_hit), así nada se ejecuta dos veces.
"""
from dataclasses import dataclass, field, replace

from combate.cards.card_database import make_card, make_deck_cards
from combate.cards.card_effects import EffectContext, run_effects
from combate.cards.deck import Deck
from combate.game.characters import apply_pct, get_character
from combate.game.config import CHANNEL_MAGIC, RULES
from combate.game.rules import (DAMAGE_BREAK_ICE, DAMAGE_INTERACTION, DAMAGE_MEGA_COMBO, DRAW, WIN, DamageEvent,
                        label, reaches_mega_combo, resolve_interaction, sequence_continues)
from combate.game.state_machine import Phase, StateMachine
from combate.game.style import DRAW as STYLE_DRAW, LOSE as STYLE_LOSE, ULTIMATE_CATEGORIES, WIN as STYLE_WIN
from combate.game.status import (APPLIED, BLOCKED, BREAK_ICE, IMMUNE, LOCK_FREEZE, LOCK_PASS, REFRESHED, REPLACED,
                         STATUS_ACTIONS, WAIT, StatusId, try_apply_status)
from combate.players.player import Player

PASS = "PASS"


@dataclass
class Event:
    kind: str            # turn, mana, hp, stability, hit, message, reveal, ready, win, combo, game_over...
    player: int = None
    data: dict = field(default_factory=dict)


class CombatEngine:
    def __init__(self, decks=("duelo", "duelo"), rules=RULES, seed=None,
                 names=("PLAYER 1", "PLAYER 2"), card_lists=None, shuffle=True, characters=(None, None)):
        self.rules = rules
        self.players = []
        for i in range(2):
            cards = card_lists[i] if card_lists else make_deck_cards(decks[i])
            deck = Deck(cards, seed=None if seed is None else seed + i, shuffle=shuffle)
            self.players.append(Player(i, names[i], deck, rules))
        for p, cid in zip(self.players, characters or (None, None)):   # se conserva toda la partida
            p.character = get_character(cid)
            p.passive = p.character.make_passive() if p.character else None
        self.sm = StateMachine(Phase.TURN_START)
        self.turn = 1
        self.interaction_number = 0         # interacciones en el turno actual
        self.events = []
        self.selection = [None, None]       # Card | PASS | None
        self.confirmed = [False, False]
        self.pending_cost = [0, 0]          # Mana ya cobrado al confirmar, aún no revelado
        self.special_selection = [None, None]   # SPECIAL opcional de cada jugador
        self._special_flags = [{}, {}]      # banderas de las SPECIAL para el resto de la resolución
        self.redraw_done = [False, False]
        self.result = None                  # InteractionResult de la interacción actual
        self._mega_bonus = 0                # daño extra de Mega Combo pedido por efectos
        self.winner = None
        self.status_actions = [None, None]  # BREAK_ICE / WAIT del jugador congelado
        self._shielded = [False, False]     # congelado al revelar: protegido toda la interacción
        self._status_result = None          # InteractionResult en curso (para anotar estados)
        self.status_log = []                # (índice, texto): últimos mensajes de estados (UI)
        self.ultimate_pick = [None, None]   # categoría de definitiva elegida en esta interacción
        self._special_notes = []            # notas de efectos al revelar (Taunt, SET_AFFINITY...)

    # ------------------------------------------------------------------
    @property
    def phase(self):
        return self.sm.phase

    def emit(self, kind, player=None, **data):
        self.events.append(Event(kind, player, data))

    def pop_events(self):
        events, self.events = self.events, []
        return events

    def opponent(self, player):
        return self.players[1 - player.index]

    # ==================================================================
    # Mana: el coste depende de la INTERACCIÓN, no de la carta
    # ==================================================================
    def play_cost(self, player_index, card):
        """PASS -> 0. Definitiva -> 0 siempre. SPECIAL -> SPECIAL_MANA_COST siempre.
        Acción principal: 1ª interacción del turno -> 0; desde la 2ª -> 1 Mana
        (igual para ATTACK, GUARD y BREAK). Efectos MODIFY_PLAY_COST pueden
        ajustarlo sin romper la regla base."""
        if card is None or card == PASS or card in STATUS_ACTIONS:
            return 0
        if card.is_ultimate:                   # la definitiva no cuesta ni exige Mana
            return 0
        if card.is_special:
            cost = self.rules.SPECIAL_MANA_COST
        else:
            free = self.interaction_number <= self.rules.FREE_INTERACTIONS_PER_TURN
            cost = 0 if free else self.rules.PLAY_MANA_COST
        for data in card.effects_when("cost"):
            if data["type"] == "MODIFY_PLAY_COST":
                cost += data.get("amount", 0)
        return max(0, cost)

    def total_cost(self, player_index, main=None, special=None):
        """Coste total = acción principal + SPECIAL opcional."""
        return self.play_cost(player_index, main) + self.play_cost(player_index, special)

    def can_play(self, player_index, card):
        """¿Puede elegir `card` ahora, sumando lo que ya tiene elegido en el otro hueco?"""
        p = self.players[player_index]
        if self.status_lock(player_index):          # PARALYZE / SLEEP / FREEZE: ni cartas ni SPECIAL
            return False
        if card.is_special:
            cost = self.total_cost(player_index, self.selection[player_index], card)
        else:
            cost = self.total_cost(player_index, card, self.special_selection[player_index])
        return card.can_play(p, cost)

    def playable_cards(self, player_index):
        """Acciones principales que puede elegir (las SPECIAL van aparte)."""
        return [c for c in self.players[player_index].hand
                if not c.is_special and self.can_play(player_index, c)]

    def playable_specials(self, player_index):
        return [c for c in self.players[player_index].hand
                if c.is_special and self.can_play(player_index, c)]

    def displayed_mana(self, player_index):
        """Mana que muestra la UI: el cobro al confirmar no se ve hasta el
        REVEAL, para no delatar si el rival eligió carta o PASS."""
        return self.players[player_index].mana + self.pending_cost[player_index]

    # ==================================================================
    # Fases automáticas
    # ==================================================================
    def advance(self):
        phase = self.phase
        if phase == Phase.TURN_START:
            self._turn_start()
        elif phase == Phase.DRAW:
            self._draw()
        elif phase == Phase.INTERACTION_START:
            self._interaction_start()
        elif phase == Phase.CARD_REVEAL:
            self._resolve()
        elif phase == Phase.CARD_RESOLUTION:
            self._after_resolution()
        elif phase == Phase.MEGA_COMBO:
            self._continue_or_end()
        elif phase == Phase.TURN_END:
            self._turn_end()
        else:
            raise RuntimeError(f"La fase {phase.value} espera input, no advance()")

    def run_auto(self, limit=200):
        """Avanza todas las fases automáticas hasta necesitar input (tests)."""
        while self.sm.is_auto and limit > 0:
            self.advance()
            limit -= 1

    def _turn_start(self):
        self.interaction_number = 0
        self.emit("turn", turn=self.turn)
        if self.turn > 1 or self.rules.REGEN_ON_FIRST_TURN:
            for p in self.players:
                gained = p.gain_mana(self.rules.MANA_REGEN)
                if gained:
                    self.emit("mana", p.index, amount=gained)
        self._status_turn_start()
        if self._end_if_defeated():
            return
        for p in self.players:                 # pasivas de inicio de turno (p. ej. Alerta)
            if p.passive is not None:
                p.passive.on_turn_start(p, self)
        self.sm.go(Phase.DRAW)

    def _draw(self):
        for p in self.players:
            p.draw_to_full()
            p.redraws_left = self.rules.MAX_REDRAWS
        self.redraw_done = [self.rules.MAX_REDRAWS == 0] * 2
        self.sm.go(Phase.REDRAW)
        self._check_redraw_done()

    def _interaction_start(self):
        self.selection = [None, None]
        self.confirmed = [False, False]
        self.pending_cost = [0, 0]
        self.special_selection = [None, None]
        self._special_flags = [{}, {}]
        self.result = None
        self.status_actions = [None, None]
        self._shielded = [False, False]
        self.ultimate_pick = [None, None]
        self.interaction_number += 1           # PASS no lo reinicia; solo un turno nuevo
        self._status_interaction_start()       # POISON, antes de elegir
        if self._end_if_defeated():
            return
        self.sm.go(Phase.CARD_SELECTION)
        for p in self.players:
            lock = self.status_lock(p.index)
            if lock == LOCK_PASS:              # PARALYZE / SLEEP: PASS obligatorio, sin SPECIAL
                self.selection[p.index] = PASS
                self.confirmed[p.index] = True
                self._status_note(p.index, f"{p.name} está {p.status.name}: PASS obligatorio")
                self.emit("ready", p.index, auto=True)
                continue
            if lock == LOCK_FREEZE:            # elige BREAK ICE o WAIT
                st = p.status
                self._status_note(p.index, f"{p.name} está FREEZE: ICE CUBE {st.cube_hp}/{st.cube_max} HP")
                continue
            if not self.playable_cards(p.index):   # sin acción principal posible: PASS
                self.selection[p.index] = PASS
                if not self.playable_specials(p.index) and not self.ultimate_options(p.index):
                    # ...y sin SPECIAL ni definitiva: confirmado solo
                    self.confirmed[p.index] = True
                    self.emit("ready", p.index, auto=True)
        self._check_both_confirmed()

    # ==================================================================
    # REDRAW
    # ==================================================================
    def redraw(self, player_index, card_index):
        if self.phase != Phase.REDRAW or self.redraw_done[player_index]:
            return False
        p = self.players[player_index]
        if p.redraws_left <= 0 or not 0 <= card_index < len(p.hand):
            return False
        p.redraw(card_index)
        self.emit("redraw", player_index, index=card_index)
        if p.redraws_left == 0:
            self.redraw_done[player_index] = True
        self._check_redraw_done()
        return True

    def finish_redraw(self, player_index):
        if self.phase != Phase.REDRAW:
            return
        self.redraw_done[player_index] = True
        self._check_redraw_done()

    def _check_redraw_done(self):
        if all(self.redraw_done):
            self.sm.go(Phase.INTERACTION_START)

    # ==================================================================
    # CARD_SELECTION
    # ==================================================================
    def select(self, player_index, choice):
        """choice: índice de carta en la mano o PASS.
        Una carta SPECIAL se marca/desmarca como SPECIAL (máx. 1); cualquier otra
        carta (o PASS) es la acción principal. Se valida el coste TOTAL."""
        if self.phase != Phase.CARD_SELECTION or self.confirmed[player_index]:
            return False
        p = self.players[player_index]
        if self.status_lock(player_index) == LOCK_FREEZE:
            # Congelado: solo BREAK ICE o WAIT (PASS se interpreta como WAIT)
            choice = WAIT if choice == PASS else choice
            if choice not in STATUS_ACTIONS:
                return False
            self.selection[player_index] = choice
            return True
        if choice in STATUS_ACTIONS:
            return False
        if choice == PASS:
            self.selection[player_index] = PASS
            self._sync_ultimate(player_index)
            return True
        if not 0 <= choice < len(p.hand):
            return False
        card = p.hand[choice]
        if card.is_special:
            if self.special_selection[player_index] is card:     # volver a pulsarla la quita
                self.special_selection[player_index] = None
                return True
            if not self.can_play(player_index, card):
                return False
            self.special_selection[player_index] = card
            self._sync_ultimate(player_index)
            return True
        if not self.can_play(player_index, card):
            return False
        self.selection[player_index] = card
        self._sync_ultimate(player_index)
        return True

    def confirm(self, player_index):
        if self.phase != Phase.CARD_SELECTION or self.selection[player_index] is None:
            return False
        if self.confirmed[player_index]:
            return False
        if self.ultimate_pick[player_index] and not self.ultimate_available(player_index):
            return False                       # ya no cumple los requisitos de la definitiva
        # El coste TOTAL (principal + SPECIAL) se paga AL CONFIRMAR
        choice = self.selection[player_index]
        cost = self.total_cost(player_index, choice, self.special_selection[player_index])
        if cost > self.players[player_index].mana:
            return False
        if cost:
            self.players[player_index].spend_mana(cost)
            self.pending_cost[player_index] = cost
        self.confirmed[player_index] = True
        self.emit("ready", player_index)
        self._check_both_confirmed()
        return True

    def _check_both_confirmed(self):
        if not all(self.confirmed):
            return
        self._enforce_status_locks()
        ultimates, ultimate_lines = self._reveal_ultimates()
        cards = []
        paid = tuple(self.pending_cost)
        specials = tuple(self.special_selection)
        for p in self.players:                 # revelar: jugar las cartas (ya pagadas)
            choice = self.selection[p.index]
            if paid[p.index]:
                self.emit("mana", p.index, amount=-paid[p.index])   # ahora se ve en la UI
            if specials[p.index] is not None and not self._is_ultimate(specials[p.index]):
                p.take_card(specials[p.index])
            if choice in STATUS_ACTIONS:       # congelado: no juega carta (tampoco es PASS)
                self.status_actions[p.index] = choice
                cards.append(None)
                continue
            if choice == PASS:
                cards.append(None)
                continue
            if not self._is_ultimate(choice):  # la definitiva no sale de la mano ni va al descarte
                p.take_card(choice)
            cards.append(choice)
        self.pending_cost = [0, 0]
        # Las SPECIAL se resuelven ANTES del matchup: p. ej. Recover cambia la
        # Stability que se usará para desempatar.
        special_lines = ultimate_lines + self._resolve_specials(specials, cards)
        a, b = self.players
        self.result = resolve_interaction(cards[0], cards[1], a.stable, b.stable, self.rules,
                                          names=(a.name, b.name))
        self.result.mana_paid = paid
        self.result.interaction_number = self.interaction_number
        self.result.specials = specials
        self.result.special_lines = special_lines
        self.result.status_actions = tuple(self.status_actions)
        self.result.ultimates = ultimates
        # Congelado al revelar: el cubo le protege durante TODA esta interacción,
        # aunque se rompa a mitad (el daño sobrante no pasa al jugador).
        self._shielded = [p.has_status(StatusId.FREEZE) for p in self.players]
        for i, frozen in enumerate(self._shielded):
            other = cards[1 - i]
            if frozen and other is not None and self.result.lines:
                self.result.lines[0] = f"{label(other)} vs ICE CUBE"
        self.sm.go(Phase.CARD_REVEAL)
        self.emit("reveal", cards=cards)

    def _resolve_specials(self, specials, cards):
        """Ejecuta los efectos when="special" de cada SPECIAL. Lo que cambia la
        Stability se aplica YA; el resto de banderas se guarda para los pasos
        siguientes de la resolución. Nada de esto es específico de una carta."""
        lines = []
        for i, sc in enumerate(specials):
            if sc is None:
                continue
            p = self.players[i]
            ctx = EffectContext(self, p, self.players[1 - i], sc, cards[1 - i])
            self._special_notes = []
            run_effects(sc, "special", ctx)
            self.emit("special", i, name=sc.name)
            self.emit("message", i, text=f"{sc.name.upper()}!")
            notes, self._special_notes = self._special_notes, []
            flags = dict(ctx.flags)
            if flags.pop("recover_stability", False):
                if not p.stable:
                    p.stable = True
                    lines.append(f"{p.name}: {sc.name.upper()} -> STABLE")
                    self.emit("stability", i, stable=True)
                    self.emit("message", i, text="STABLE!")
                else:
                    lines.append(f"{p.name}: {sc.name.upper()} (ya estaba STABLE)")
            else:
                extra = f" ({' · '.join(notes)})" if notes else ""
                lines.append(f"{p.name}: {sc.name.upper()}{extra}")
            self._special_flags[i] = flags
        return lines

    # ==================================================================
    # CARD_REVEAL -> CARD_RESOLUTION
    #   efectos -> hits -> daño normal -> Stability -> combo -> iniciativa (-> Mega Combo)
    # ==================================================================
    @property
    def combo_holder(self):
        """Jugador con combo en curso (como mucho uno: solo el ganador hace hit)."""
        return next((p.index for p in self.players if p.combo_hits), None)

    def _resolve(self):
        self._apply_result(self.result)
        self.sm.go(Phase.CARD_RESOLUTION)

    def _apply_result(self, r):
        cards = r.cards
        ctxs = [EffectContext(self, self.players[i], self.players[1 - i], cards[i], cards[1 - i])
                for i in range(2)]
        # 1. Efectos de las cartas (solo activan banderas; se aplican en cada paso)
        self._status_result = r                # notas de estados y pasivas van a esta resolución
        for i in range(2):
            ctxs[i].flags.update(self._special_flags[i])   # lo que dejaron las SPECIAL
            run_effects(cards[i], "play", ctxs[i])
        if r.outcome == WIN:
            run_effects(cards[r.winner], "win", ctxs[r.winner])
            run_effects(cards[r.loser], "lose", ctxs[r.loser])
            self.emit("win", r.winner)
            for tag in r.tags:
                self.emit("message", r.winner, text=f"{tag}!")

        self._status_result = r
        self._determine_hits(r, ctxs)     # 2. ¿quién recibe un HIT? (el ICE CUBE no cuenta)
        self._apply_damage(r, ctxs)       # 3. daño normal: HP o ICE CUBE
        self._break_ice(r)                #    BREAK ICE / WAIT del jugador congelado
        self._wake_on_hit(r)              #    un HIT real despierta (SLEEP)
        self._apply_stability(r, ctxs)    # 4. Stability (usa received_hit)
        self._apply_combo(r, ctxs)        # 5. combo (y si toca, Mega Combo después)
        self._apply_style(r)              #    Estilo: una vez por interacción y jugador
        self._apply_pending_statuses(r, ctxs)   # 6. estados que aplican las cartas (APPLY_STATUS)
        for p in self.players:                  #    pasivas que reaccionan al resultado (Elemental Wolf)
            if p.passive is not None:
                p.passive.after_interaction(p, self, r)
        self._status_interaction_end()    # 7. PARALYZE expira, SLEEP descuenta
        self._decide_flow(r, ctxs)        # 8. iniciativa (los estados no la tocan)
        self._status_result = None

    # --- 2. Hits -------------------------------------------------------------------
    def _determine_hits(self, r, ctxs):
        """Registra EXPLÍCITAMENTE quién recibió un hit. HIT y DAÑO son conceptos
        distintos: una carta puede hacer hit sin daño o daño sin hit."""
        received = [False, False]
        if r.outcome == WIN and r.cards[r.winner].generates_hit:
            if self._shielded[r.loser]:
                # Golpear el ICE CUBE no es un HIT contra el jugador congelado
                r.consequences.append(f"{label(r.cards[r.winner])} golpea el ICE CUBE: sin HIT")
            else:
                r.hit_generated = 1 + ctxs[r.winner].flags.get("extra_hits", 0)
                received[r.loser] = True
        r.received_hit = tuple(received)

    # --- 3. Daño normal ---------------------------------------------------------
    def _apply_damage(self, r, ctxs):
        if r.outcome != WIN:
            return
        w, l = self.players[r.winner], self.players[r.loser]
        wc, lc = r.cards[r.winner], r.cards[r.loser]
        amount = max(0, wc.damage + ctxs[r.winner].flags.get("damage_bonus", 0))
        passed = lc is None and not self._shielded[r.loser]     # congelado no es PASS: daña al cubo
        if passed and self.rules.PASS_BLOCKS_DAMAGE:
            amount = 0
            r.consequences.append(f"{l.name} pasa: sin daño")
        if amount:
            event = DamageEvent(DAMAGE_INTERACTION, w.index, l.index, amount, action=wc.card_type,
                                channel=wc.damage_channel, element=wc.element)
            self._apply_passive(r, event)
            self._apply_target_passive(r, event)
            self._deal_damage(r, event)
        elif lc is not None:
            r.consequences.append(f"{label(wc)}: sin daño")

    def _deal_damage(self, r, event):
        """Único punto donde el daño de combate llega a un jugador. Con FREEZE
        lo absorbe el ICE CUBE; si el cubo se rompió en esta interacción, el
        jugador sigue protegido hasta que termine (sin daño sobrante)."""
        target = self.players[event.target]
        if event.heal:                          # pasiva del objetivo: este daño le cura
            healed = min(event.amount, target.max_hp - target.hp)
            target.hp += healed
            r.damage_events.append(event)
            gain = f"+{healed} HP" if healed else "ya tiene la vida al máximo"
            r.consequences.append(f"{target.name} absorbe {event.element}: {gain}")
            if healed:
                self.emit("hp", target.index, amount=healed, damage_type="heal", element=event.element)
            return
        st = target.status
        if st is not None and st.id == StatusId.FREEZE:
            event.to_cube = True
            st.cube_hp = max(0, st.cube_hp - event.amount)
            r.damage_events.append(event)
            r.consequences.append(f"ICE CUBE de {target.name} -{event.amount} ({st.cube_hp}/{st.cube_max})")
            self.emit("ice", target.index, amount=-event.amount, cube_hp=st.cube_hp, cube_max=st.cube_max)
            if st.cube_hp <= 0:
                self.remove_status(target.index, f"ICE CUBE destruido: {target.name} queda libre", r)
            return
        if self._shielded[event.target]:
            event.to_cube = True
            r.damage_events.append(event)
            r.consequences.append(f"{target.name} protegido: el hielo absorbe {event.amount}")
            return
        target.hp = max(0, target.hp - event.amount)
        r.damage_events.append(event)
        origin = [t for t in ("MAGIC" if event.channel == CHANNEL_MAGIC else None, event.element) if t]
        r.consequences.append(f"{target.name} -{event.amount} HP" + (f" ({' · '.join(origin)})" if origin else ""))
        self.emit("hp", target.index, amount=-event.amount, damage_type=event.kind, channel=event.channel,
                  element=event.element)

    # --- 4. Stability ------------------------------------------------------------------
    def _apply_stability(self, r, ctxs):
        """Regla definitiva (en este orden de prioridad):

            A. EMPATE real          -> ambos STABLE.
            B. Si no hay empate     -> cada jugador UNSTABLE que NO recibió un hit
                                       recupera STABLE; si lo recibió, sigue UNSTABLE.
                                       (La iniciativa NO interviene.)
            C. EFECTOS explícitos   -> se aplican al final para que nada los anule:
                                       primero desestabilizar (causes_instability,
                                       CAUSE_INSTABILITY), luego recuperar
                                       (recovers_stability, RECOVER_STABILITY).

        Se calcula el estado final de cada jugador y se aplica una sola vez.
        """
        before = [p.stable for p in self.players]
        target = list(before)
        reason = ["", ""]

        # A / B: regla general
        if r.outcome != WIN:
            target = [True, True]
            reason = ["empate", "empate"]
            r.consequences.append("EMPATE: ambos STABLE")
        else:
            for i in range(2):
                if not before[i]:
                    if r.received_hit[i]:
                        reason[i] = "recibió hit"
                    else:
                        target[i], reason[i] = True, "no recibió hit"

        # C: efectos explícitos de las cartas
        if r.outcome == WIN:
            w, l = r.winner, r.loser
            wc, lc = r.cards[w], r.cards[l]
            destabilizes = wc.causes_instability or ctxs[w].flags.get("cause_instability")
            protected = (ctxs[l].flags.get("protect_stability") or self._shielded[l]
                         or (lc is None and self.rules.PASS_PROTECTS_STABILITY))
            if destabilizes and not protected:
                target[l], reason[l] = False, f"{label(wc)}"
            elif destabilizes:
                r.consequences.append(f"{self.players[l].name} protege su Stability")
            else:
                r.consequences.append(f"{label(wc)} no desestabiliza")
            if wc.recovers_stability:
                target[w], reason[w] = True, label(wc)
        for i in range(2):
            if ctxs[i].flags.get("recover_stability"):
                target[i], reason[i] = True, label(r.cards[i])

        for i, p in enumerate(self.players):
            self._set_stability(r, p, target[i], reason[i])

    def _set_stability(self, r, player, stable, reason=""):
        why = f" ({reason})" if reason else ""
        if player.stable == stable:
            if not stable:
                r.consequences.append(f"{player.name} sigue UNSTABLE{why}")   # no se acumula
            return
        player.stable = stable
        r.stability_changes[player.index] = stable
        if reason != "empate":         # el empate ya tiene su propia línea
            r.consequences.append(f"{player.name} -> {'STABLE' if stable else 'UNSTABLE'}{why}")
        self.emit("stability", player.index, stable=stable)
        self.emit("message", player.index, text="STABLE!" if stable else "UNSTABLE!")

    # --- 5. Combo (hits CONSECUTIVOS, uno por jugador) ------------------------------
    def _apply_combo(self, r, ctxs):
        for i, p in enumerate(self.players):
            scored = r.outcome == WIN and r.winner == i and r.hit_generated > 0
            if scored:
                p.combo_hits = self.combo_after_hit(i, r.hit_generated)
                r.consequences.append(f"{p.name}: +{r.hit_generated} HIT ({p.combo_hits}/{self.rules.MAX_COMBO_HITS})")
                self.emit("hit", i, hits=p.combo_hits, gained=r.hit_generated)
                self._mega_bonus = ctxs[i].flags.get("mega_bonus", 0)
                continue
            # Sin hit en esta interacción: la cadena se rompe (salvo protección)
            protected = ctxs[i].flags.get("protect_combo") and not ctxs[1 - i].flags.get("break_opponent_combo")
            if p.combo_hits and not protected:
                p.combo_hits = 0
                r.consequences.append(f"{p.name}: COMBO ROTO -> 0")
                self.emit("combo_break", i)
                self.emit("message", i, text="COMBO ROTO")
            elif p.combo_hits:
                r.consequences.append(f"{p.name}: combo protegido ({p.combo_hits})")
        r.combo_after = tuple(p.combo_hits for p in self.players)
        r.mega_combo = next((p.index for p in self.players if reaches_mega_combo(p.combo_hits, self.rules)), None)

    # --- 4. ¿Hay otra interacción? (iniciativa; independiente del combo) ---------------
    def _decide_flow(self, r, ctxs):
        # Las líneas de las SPECIAL van primero: ocurrieron antes del matchup
        r.consequences[0:0] = r.special_lines
        flags = {k: v for c in ctxs for k, v in c.flags.items()}
        continues = sequence_continues(r.cards[0], r.cards[1])
        if flags.get("keep_sequence"):
            continues = True
        if flags.get("end_sequence"):
            continues = False
        r.continues = continues
        if r.mega_combo is not None:
            r.consequences.append(f"{self.players[r.mega_combo].name}: {self.rules.MAX_COMBO_HITS} HIT COMBO!")
        if not all(p.alive for p in self.players):
            r.consequences.append("K.O.")
        elif continues:
            who = [label(c) for c in r.cards if c is not None and c.has_initiative]
            r.consequences.append(f"SIGUE: iniciativa de {' y '.join(dict.fromkeys(who)) or 'un efecto'}")
        else:
            r.consequences.append("FIN DEL TURNO: nadie tiene iniciativa")

    # ==================================================================
    # Tras mostrar la resolución: Mega Combo y continuación (sin preguntar)
    # ==================================================================
    def _after_resolution(self):
        r = self.result
        target_alive = r.mega_combo is not None and self.players[1 - r.mega_combo].alive
        if target_alive:
            self.sm.go(Phase.MEGA_COMBO)
            self._mega_combo(r)
        else:
            self._continue_or_end()

    def _mega_combo(self, r):
        """Daño ADICIONAL, como evento separado del daño normal. Luego combo = 0."""
        p = self.players[r.mega_combo]
        amount = self.rules.MEGA_COMBO_DAMAGE + self._mega_bonus
        flow_line = r.consequences.pop()            # "SIGUE..." / "FIN DEL TURNO" va al final
        self.emit("mega_combo", p.index, hits=p.combo_hits, damage=amount)
        r.consequences.append("MEGA COMBO!")
        event = DamageEvent(DAMAGE_MEGA_COMBO, p.index, 1 - p.index, amount)
        self._apply_passive(r, event)
        self._apply_target_passive(r, event)
        self._deal_damage(r, event)
        r.consequences.append(f"{p.name}: COMBO RESET -> 0")
        r.consequences.append("K.O." if not self.players[1 - p.index].alive else flow_line)
        p.combo_hits = 0
        self._mega_bonus = 0
        r.combo_after = tuple(pl.combo_hits for pl in self.players)
        self.emit("combo_reset", p.index)

    def _continue_or_end(self):
        r = self.result
        if not all(p.alive for p in self.players):
            self.sm.go(Phase.TURN_END)
        elif r.continues:
            self.sm.go(Phase.INTERACTION_START)
        else:
            self.sm.go(Phase.TURN_END)

    # ==================================================================
    # TURN_END
    # ==================================================================
    def _turn_end(self):
        if self._end_if_defeated():
            return
        for p in self.players:          # un combo no sobrevive al final de la secuencia
            p.combo_hits = 0
        self.turn += 1
        self.sm.go(Phase.TURN_START)

    # ==================================================================
    # Personajes: pasivas (las reglas de cada una están en game/characters.py)
    # ==================================================================
    def combo_after_hit(self, player_index, hits):
        """Combo que tendrá el jugador tras conseguir `hits` en esta interacción.
        Única fórmula: la usan _apply_combo y la pasiva de Hero."""
        return min(self.rules.MAX_COMBO_HITS, self.players[player_index].combo_hits + hits)

    def _apply_passive(self, r, event):
        """La pasiva de quien CAUSA el daño, una sola vez por evento. Solo
        daño de interacción y de Mega Combo (BURN/POISON no pasan por aquí)."""
        source = self.players[event.source]
        if source.passive is None or event.passive_applied:
            return
        event.passive_applied = True
        pct = source.passive.damage_bonus_pct(event, self, r)
        if not pct:
            return
        event.base_amount, event.passive_pct = event.amount, pct
        event.amount = apply_pct(event.amount, pct)
        r.consequences.append(f"{source.character.name.upper()}: {source.passive.name.upper()} +{pct}% "
                              f"({event.base_amount} -> {event.amount})")
        self.emit("passive", source.index, pct=pct, base=event.base_amount, amount=event.amount)

    def _apply_target_passive(self, r, event):
        """La pasiva de quien RECIBE el daño (p. ej. Elemental Wolf: su elemento le
        cura, el contrario le hace x1.5). Una vez por evento, tras la del atacante."""
        target = self.players[event.target]
        if target.passive is None:
            return
        target.passive.incoming_damage(event, self, r)
        if event.weak_base is not None and event.weak_base != event.amount:
            if event.amount < event.weak_base:      # resistencia (lobos de fuego / hielo)
                what = event.element or "SIN ELEMENTO"
                r.consequences.append(f"{target.character.name.upper()}: RESISTE {what} "
                                      f"({event.weak_base} -> {event.amount})")
                self.emit("message", target.index, text="¡RESISTE!")
            else:
                r.consequences.append(f"{target.character.name.upper()}: DÉBIL A {event.element} "
                                      f"({event.weak_base} -> {event.amount})")
                self.emit("message", target.index, text="¡DEBILIDAD!")

    def passive_note(self, text):
        """Línea de una pasiva o efecto: va a la resolución en curso (o, al
        revelar las SPECIAL, junto a la línea de la SPECIAL)."""
        if self._status_result is not None:
            self._status_result.consequences.append(text)
        else:
            self._special_notes.append(text)

    def passive_heal(self, player_index, amount, reason=""):
        """Curación de una pasiva (Undead), hasta la vida máxima. Devuelve lo curado."""
        p = self.players[player_index]
        healed = min(amount, p.max_hp - p.hp)
        if healed <= 0:
            return 0
        p.hp += healed
        self._status_note(player_index, f"{p.name}: {reason} +{healed} HP")
        self.emit("hp", player_index, amount=healed, damage_type="heal")
        return healed

    def passive_alert(self, owner_index):
        """Pasiva Alerta: el rival queda UNSTABLE (al empezar el turno)."""
        owner, foe = self.players[owner_index], self.players[1 - owner_index]
        self.emit("message", owner_index, text="¡ALERTA!")
        self._status_note(foe.index, f"{owner.name}: SEÑAL DE ALERTA -> {foe.name} UNSTABLE")
        if foe.stable:
            foe.stable = False
            self.emit("stability", foe.index, stable=False)
            self.emit("message", foe.index, text="UNSTABLE!")

    def passive_status(self, owner_index, target_index, status, r, mode=""):
        """Una pasiva aplica un estado (con las reglas normales de inmunidad y reemplazo)."""
        owner, target = self.players[owner_index], self.players[target_index]
        r.consequences.append(f"{owner.character.name.upper()}: {target.name} le golpea en modo {mode} -> {status}")
        return self.apply_status(target_index, status, r)

    def set_affinity(self, player_index, element):
        """Efecto SET_AFFINITY: cambia el elemento de una pasiva que lo admita."""
        from combate.game.characters import ELEMENT_NAMES
        p = self.players[player_index]
        handler = getattr(p.passive, "set_affinity", None)
        if handler is None:
            return False
        changed = handler(element)
        name = ELEMENT_NAMES.get(element, element)
        self.passive_note(f"{p.name}: MODO {name}" + ("" if changed else " (ya estaba)"))
        if changed:
            self.emit("message", player_index, text=f"MODO {name}!")
            self.emit("affinity", player_index, element=element)
        return changed

    def gain_style(self, player_index, amount):
        """Puntos de Estilo directos (Taunt). No cuenta como victoria ni toca la racha."""
        p = self.players[player_index]
        top = self.rules.ULTIMATE_RANK
        had_ultimate = p.style.ultimate_unlocked(self.rules)
        change = p.style.gain(amount, self.rules)
        has_ultimate = p.style.ultimate_unlocked(self.rules)
        self.passive_note(f"+{change.delta} ESTILO")
        self.emit("style", player_index, outcome="gain", delta=change.delta, points=change.points_after,
                  rank=change.rank_after, streak=change.streak_after, streak_reset=False)
        if change.rank_after == top and change.rank_before != top:
            text = f"{p.name}: RANGO {top}" + (" · DEFINITIVA DISPONIBLE" if has_ultimate else "")
            self.emit("message", player_index, text=text, style=True)
        elif had_ultimate and not has_ultimate:
            self.emit("message", player_index, text=f"{p.name} baja de {top}: DEFINITIVA BLOQUEADA", style=True)
        return change

    def _end_if_defeated(self):
        """Condición de derrota (0 HP). Termina el combate en el acto."""
        dead = [p for p in self.players if not p.alive]
        if not dead:
            return False
        self.winner = self.opponent(dead[0]).index if len(dead) == 1 else None
        self.sm.go(Phase.GAME_OVER)
        self.emit("game_over", self.winner)
        return True

    # ==================================================================
    # Status Effects (las reglas de cada estado están en game/status.py)
    # ==================================================================
    def status_lock(self, player_index):
        """None | LOCK_PASS (PARALYZE, SLEEP) | LOCK_FREEZE."""
        st = self.players[player_index].status
        return st.lock if st else None

    def status_choices(self, player_index):
        """Acciones de estado disponibles: [BREAK_ICE, WAIT] congelado, [PASS]
        paralizado/dormido, [] sin restricción."""
        lock = self.status_lock(player_index)
        if lock == LOCK_FREEZE:
            return [BREAK_ICE, WAIT]
        if lock == LOCK_PASS:
            return [PASS]
        return []

    def apply_status(self, target_index, status_id, r=None):
        """Aplica un estado siguiendo la regla de inmunidad y reemplazo.
        Devuelve APPLIED | REPLACED | REFRESHED | IMMUNE | BLOCKED."""
        p = self.players[target_index]
        sid = StatusId(status_id)
        outcome, previous = try_apply_status(p, sid, self.rules)
        text = {
            APPLIED: f"{sid.value} aplicado a {p.name}",
            REPLACED: f"{p.name}: {previous.id.value if previous else ''} -> {sid.value}",
            REFRESHED: f"{p.name}: {sid.value} reiniciado",
            IMMUNE: f"{p.name} es inmune a {sid.value}",
            BLOCKED: f"{p.name} está {previous.name if previous else ''}: inmune a {sid.value}",
        }[outcome]
        self._status_note(target_index, text, r)
        if outcome in (APPLIED, REPLACED, REFRESHED):
            self.emit("status", target_index, status=sid.value, change=outcome)
        return outcome

    def remove_status(self, player_index, text=None, r=None):
        """Elimina el estado activo. Idempotente: si ya no hay, no hace nada."""
        p = self.players[player_index]
        old = p.status
        if old is None:
            return False
        p.status = None
        self._status_note(player_index, text or f"{old.id.value} ha terminado", r)
        self.emit("status", player_index, status=None, change="removed", previous=old.id.value)
        return True

    # --- API que usan las definiciones de game/status.py --------------------------
    def status_damage(self, player, amount, status):
        """Daño periódico (BURN, POISON): no es un HIT, no toca el combo ni la Stability."""
        player.hp = max(0, player.hp - amount)
        self._status_note(player.index, f"{status.id.value}: -{amount} HP")
        self.emit("hp", player.index, amount=-amount, damage_type=status.id.value.lower())

    def expire_status(self, player, status, text):
        """Fin natural de un estado. Si ya se eliminó (o fue reemplazado), no hace nada."""
        if player.status is status:
            self.remove_status(player.index, text)

    def _status_note(self, player_index, text, r=None):
        r = r or self._status_result
        if r is not None:
            r.consequences.append(text)
            r.status_changes.append((player_index, text))
        self.status_log.append((player_index, text))
        del self.status_log[:-12]
        self.emit("message", player_index, text=text, status=True)

    # --- Transiciones (cada una se ejecuta una sola vez) ------------------------------
    def _status_turn_start(self):
        for p in self.players:
            if p.status is not None:
                p.status.definition.on_turn_start(p.status, p, self)

    def _status_interaction_start(self):
        for p in self.players:
            st = p.status
            if st is not None:
                st.fresh = False                # desde ahora cuenta y bloquea acciones
                st.definition.on_interaction_start(st, p, self)

    def _status_interaction_end(self):
        """La interacción que aplicó el estado (fresh) no cuenta."""
        for p in self.players:
            st = p.status
            if st is not None and not st.fresh:
                st.definition.on_interaction_end(st, p, self)

    def _wake_on_hit(self, r):
        for i, p in enumerate(self.players):
            st = p.status
            if r.received_hit[i] and st is not None and not st.fresh:
                st.definition.on_hit_received(st, p, self)

    def _enforce_status_locks(self):
        """Seguridad al revelar: una selección guardada nunca salta un bloqueo."""
        for i, p in enumerate(self.players):
            lock = self.status_lock(i)
            if lock is None:
                continue
            if self.pending_cost[i]:
                p.gain_mana(self.pending_cost[i])
                self.pending_cost[i] = 0
            self.special_selection[i] = None
            if lock == LOCK_PASS:
                self.selection[i] = PASS
            elif self.selection[i] not in STATUS_ACTIONS:
                self.selection[i] = WAIT
            self._sync_ultimate(i)

    def _break_ice(self, r):
        """BREAK ICE: daño al cubo propio. Sin HIT, sin combo, sin iniciativa, sin Mana."""
        for i, action in enumerate(r.status_actions):
            p = self.players[i]
            if action == BREAK_ICE:
                if p.has_status(StatusId.FREEZE):
                    r.consequences.append(f"{p.name}: BREAK ICE")
                    self._deal_damage(r, DamageEvent(DAMAGE_BREAK_ICE, i, i, self.rules.BREAK_ICE_DAMAGE))
                else:
                    r.consequences.append(f"{p.name}: BREAK ICE (el cubo ya estaba roto)")
            elif action == WAIT:
                r.consequences.append(f"{p.name}: WAIT (no ataca el cubo)")

    def _apply_pending_statuses(self, r, ctxs):
        """Aplica los APPLY_STATUS de esta interacción (cartas y SPECIAL) si se
        cumplen sus condiciones sobre el resultado real. Van después del daño:
        un estado recién aplicado no afecta a la ventana que lo aplicó."""
        for i in range(2):
            for data in ctxs[i].flags.get("apply_status", []):
                if not self._status_condition(data, r, i):
                    continue
                target = i if data.get("target") == "self" else 1 - i
                self.apply_status(target, data["status"], r)

    @staticmethod
    def _status_condition(data, r, i):
        outcome = data.get("if_outcome")
        if outcome == "win" and not (r.outcome == WIN and r.winner == i):
            return False
        if outcome == "lose" and not (r.outcome == WIN and r.winner != i):
            return False
        if outcome == "draw" and r.outcome != DRAW:
            return False
        main_type = data.get("if_main_type")
        if main_type is not None and (r.cards[i] is None or r.cards[i].card_type != main_type):
            return False
        if data.get("if_hit") and not r.received_hit[1 - i]:
            return False
        return True

    # ==================================================================
    # Estilo y definitiva (reglas y tablas en game/style.py y game/config.py)
    # ==================================================================
    def _apply_style(self, r):
        """Actualiza el Estilo de ambos jugadores con el resultado REAL de la
        interacción. Una sola vez por interacción (aunque se llame de nuevo)."""
        if r.style_changes:
            return
        changes = []
        for i, p in enumerate(self.players):
            if r.outcome == DRAW:
                outcome = STYLE_DRAW
            else:
                outcome = STYLE_WIN if r.winner == i else STYLE_LOSE
            had_ultimate = p.style.ultimate_unlocked(self.rules)
            # PASS como acción principal sin recibir un HIT: ni penalización ni reinicio de racha
            passed = r.cards[i] is None and r.status_actions[i] is None
            protected = passed and not r.received_hit[i]
            change = p.style.record(outcome, self.rules, protected=protected)
            changes.append(change)
            has_ultimate = p.style.ultimate_unlocked(self.rules)
            self.emit("style", i, outcome=outcome, delta=change.delta, points=change.points_after,
                      rank=change.rank_after, streak=change.streak_after, streak_reset=change.streak_reset)
            top = self.rules.ULTIMATE_RANK
            if change.rank_after == top and change.rank_before != top:
                text = f"{p.name}: RANGO {top}" + (" · DEFINITIVA DISPONIBLE" if has_ultimate else "")
                self.emit("message", i, text=text, style=True)
            elif had_ultimate and not has_ultimate:
                self.emit("message", i, text=f"{p.name} baja de {top}: DEFINITIVA BLOQUEADA", style=True)
        r.style_changes = tuple(changes)

    def ultimate_available(self, player_index):
        """Desbloqueada (rango S, sin usar), combate activo y sin estado que bloquee acciones."""
        p = self.players[player_index]
        active = self.phase != Phase.GAME_OVER and all(pl.alive for pl in self.players)
        return active and p.style.ultimate_unlocked(self.rules) and not self.status_lock(player_index)

    def ultimate_card(self, player_index, category):
        """Carta que resuelve la definitiva: de momento, la normal de la categoría
        (rules.ULTIMATE_CARDS). Aquí se podrá elegir una técnica propia de cada
        personaje sin tocar el resto del sistema."""
        return replace(make_card(self.rules.ULTIMATE_CARDS[category]), is_ultimate=True)

    @staticmethod
    def _is_ultimate(choice):
        """`choice` puede ser una carta, PASS, BREAK_ICE, WAIT o None."""
        return getattr(choice, "is_ultimate", False)

    def _without_ultimate(self, card):
        return None if self._is_ultimate(card) else card

    def ultimate_options(self, player_index):
        """Categorías que puede elegir ahora: disponible y pagable lo ya elegido en
        el otro hueco (la definitiva en sí cuesta 0: play_cost)."""
        if self.phase != Phase.CARD_SELECTION or not self.ultimate_available(player_index):
            return []
        main = self._without_ultimate(self.selection[player_index])
        special = self._without_ultimate(self.special_selection[player_index])
        mana = self.players[player_index].mana
        options = []
        for category in ULTIMATE_CATEGORIES:
            card = self.ultimate_card(player_index, category)
            cost = self.total_cost(player_index, main, card) if card.is_special \
                else self.total_cost(player_index, card, special)
            if cost <= mana:
                options.append(category)
        return options

    def select_ultimate(self, player_index, category):
        """Elige la definitiva como acción principal (o como SPECIAL). Máx. una por
        interacción; volver a elegir la misma la quita. Se revela y resuelve como
        cualquier carta (mismas reglas), pero sin coste de Mana."""
        if self.phase != Phase.CARD_SELECTION or self.confirmed[player_index]:
            return False
        if category not in self.ultimate_options(player_index):
            return False
        previous = self.ultimate_pick[player_index]
        self._clear_ultimate(player_index)
        if previous == category:
            return True
        card = self.ultimate_card(player_index, category)
        if card.is_special:
            self.special_selection[player_index] = card
        else:
            self.selection[player_index] = card
        self.ultimate_pick[player_index] = category
        return True

    def _clear_ultimate(self, i):
        if self._is_ultimate(self.selection[i]):
            self.selection[i] = None
        if self._is_ultimate(self.special_selection[i]):
            self.special_selection[i] = None
        self.ultimate_pick[i] = None

    def _sync_ultimate(self, i):
        """Si otra elección ocupó su hueco, la definitiva deja de estar elegida."""
        if not (self._is_ultimate(self.selection[i]) or self._is_ultimate(self.special_selection[i])):
            self.ultimate_pick[i] = None

    def _reveal_ultimates(self):
        """Al revelar: valida otra vez y gasta el uso (una sola vez)."""
        used, lines = [None, None], []
        for i, p in enumerate(self.players):
            category = self.ultimate_pick[i]
            if category is None:
                continue
            if not p.style.use_ultimate(self.rules) or self.status_lock(i):
                # No debería pasar (se valida al confirmar): se anula sin cobrarla
                card = self.selection[i] if self._is_ultimate(self.selection[i]) else self.special_selection[i]
                refund = min(self.pending_cost[i], self.play_cost(i, card))
                p.gain_mana(refund)
                self.pending_cost[i] -= refund
                self._clear_ultimate(i)
                if self.selection[i] is None:
                    self.selection[i] = PASS
                continue
            used[i] = category
            lines.append(f"{p.name}: DEFINITIVA ({category})")
            self.emit("ultimate", i, category=category)
            self.emit("message", i, text=f"DEFINITIVA: {category}", style=True)
        return tuple(used), lines
