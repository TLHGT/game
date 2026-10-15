"""IA sencilla para controlar a un jugador del combate (los enemigos del mapa).

Sin Pygame. Solo usa la API pública del motor, igual que la UI:
    ai.act(engine)   -> hace como mucho UNA decisión (cambios, elegir, confirmar)

No mira la mano del rival: decide con lo que vería un jugador en pantalla
(Stability, combo, Mana y las cartas que el rival ha ido revelando).

Personalidad (parámetros del enemigo en el JSON del mapa):
    aggression   > 0 prefiere atacar, < 0 prefiere defender
    randomness   0 = siempre la mejor jugada; valores altos = más impredecible
"""
import math
import random

from combate.game.combat import PASS
from combate.game.state_machine import Phase
from combate.game.status import BREAK_ICE, LOCK_FREEZE, WAIT

OFFENSIVE = ("ATTACK", "MAGIC")


def matchup_type(card, rules):
    return rules.MATCHUP_AS.get(card.card_type, card.card_type)


class CardAI:
    def __init__(self, index=1, aggression=0.0, randomness=0.6, seed=None):
        self.index = index
        self.aggression = aggression
        self.randomness = max(0.05, randomness)
        self.rng = random.Random(seed)
        self.seen = {"ATTACK": 1, "GUARD": 1, "BREAK": 1}   # tipos que ha revelado el rival
        self.seen_elements = {}                              # elementos de las cartas del rival
        self._last_result = None

    # ------------------------------------------------------------------
    def needs_input(self, engine):
        i = self.index
        if engine.phase == Phase.REDRAW:
            return not engine.redraw_done[i]
        if engine.phase == Phase.CARD_SELECTION:
            return not engine.confirmed[i]
        return False

    def observe(self, engine):
        """Aprende qué suele jugar el rival (llamar cada frame; es barato)."""
        r = engine.result
        if r is None or r is self._last_result or engine.phase == Phase.CARD_SELECTION:
            return
        self._last_result = r
        card = r.cards[1 - self.index]
        if card is not None and not card.is_special:
            t = matchup_type(card, engine.rules)
            self.seen[t] = self.seen.get(t, 0) + 1
            if card.element:
                self.seen_elements[card.element] = self.seen_elements.get(card.element, 0) + 1

    def act(self, engine):
        if not self.needs_input(engine):
            return False
        if engine.phase == Phase.REDRAW:
            self._redraw(engine)
        else:
            self._select(engine)
        return True

    # ------------------------------------------------------------------
    def _redraw(self, engine):
        """Cambia las cartas que ahora no podría jugar (p. ej. Revenge estando STABLE)."""
        p = engine.players[self.index]
        for k, card in enumerate(p.hand):
            if p.redraws_left <= 0:
                break
            useless = (card.play_condition == "unstable" and p.stable) or \
                      (card.play_condition == "stable" and not p.stable)
            if useless:
                engine.redraw(self.index, k)
                if engine.phase != Phase.REDRAW or engine.redraw_done[self.index]:
                    return
        engine.finish_redraw(self.index)

    def _select(self, engine):
        i = self.index
        p = engine.players[i]
        if engine.status_lock(i) == LOCK_FREEZE:
            engine.select(i, BREAK_ICE if self.rng.random() < 0.8 else WAIT)
            engine.confirm(i)
            return
        if engine.selection[i] is None or engine.selection[i] == PASS:
            options = engine.ultimate_options(i)
            if options and "ATTACK" in options and self.rng.random() < 0.85:
                engine.select_ultimate(i, "ATTACK")
            else:
                choice = self._pick_main(engine)
                if choice != PASS:
                    choice = p.hand.index(choice)
                engine.select(i, choice)
            self._maybe_special(engine)
        if not engine.confirm(i):
            # Por si una SPECIAL dejó la jugada sin pagar: se quita y se reintenta
            if engine.special_selection[i] is not None and not engine.ultimate_pick[i]:
                engine.select(i, p.hand.index(engine.special_selection[i]))
            if not engine.confirm(i):
                engine.select(i, PASS)
                engine.confirm(i)

    def _pick_main(self, engine):
        i = self.index
        playable = engine.playable_cards(i)
        if not playable:
            return PASS
        scored = [(self._score(engine, c), c) for c in playable]
        scored.append((self._score_pass(engine), PASS))
        best = max(s for s, _ in scored)
        weights = [math.exp((s - best) / self.randomness) for s, _ in scored]
        return self.rng.choices([c for _, c in scored], weights=weights)[0]

    def _score(self, engine, card):
        rules = engine.rules
        me = engine.players[self.index]
        foe = engine.players[1 - self.index]
        t = matchup_type(card, rules)
        score = 1.0 + card.damage / 20 + 0.3 * card.priority
        # Contraataca lo que más juega el rival
        total = sum(self.seen.values())
        beaten = rules.BEATS.get(t)
        if beaten:
            score += 1.2 * self.seen.get(beaten, 0) / total
        # Stability: en un espejo con choque gana el STABLE
        if t in OFFENSIVE or t == "ATTACK":
            if me.stable and not foe.stable:
                score += 0.9
            if not me.stable and foe.stable:
                score -= 0.5
            score += self.aggression
            if me.combo_hits == rules.MAX_COMBO_HITS - 1:
                score += 0.6                    # a por el Mega Combo
        if t == "GUARD":
            if not me.stable and foe.stable:
                score += 0.8
            if foe.combo_hits == rules.MAX_COMBO_HITS - 1:
                score += 0.8                    # corta el Mega Combo del rival
            score -= self.aggression * 0.5
        if card.recovers_stability and not me.stable:
            score += 1.4
        foe_element = getattr(foe.passive, "element", None)     # rival con afinidad elemental
        if foe_element:
            if card.element == foe_element:
                score -= 2.0                    # le curaría
            elif card.element:
                score += 1.2                    # su debilidad
            if card.card_type == "ATTACK":
                score -= 0.6                    # golpearle cuerpo a cuerpo tiene castigo
        if card.causes_instability and foe.stable:
            score += 0.3
        return score

    def _score_pass(self, engine):
        i = self.index
        me = engine.players[i]
        cost = engine.play_cost(i, engine.playable_cards(i)[0])
        score = 0.1
        if cost and me.mana <= cost:
            score += 0.4                        # guarda el último Mana (pero pasar recibe todo el golpe)
        return score

    def _wants_affinity(self, me, card):
        """Elemental Wolf: cambia al elemento que más usa el rival (así le cura);
        si aún no ha visto ninguno, de vez en cuando por sorpresa."""
        current = getattr(me.passive, "element", None)
        target = next((e["element"] for e in card.effects if e["type"] == "SET_AFFINITY"), None)
        if current is None or target == current:
            return False
        if self.seen_elements:
            favourite = max(self.seen_elements, key=self.seen_elements.get)
            return favourite == target
        return self.rng.random() < 0.3

    def _maybe_special(self, engine):
        i = self.index
        me = engine.players[i]
        main = engine.selection[i]
        for card in engine.playable_specials(i):
            effects = {e.get("type") for e in card.effects}
            useful = False
            if (card.recovers_stability or "RECOVER_STABILITY" in effects) and not me.stable:
                useful = True
            elif any(e.get("if_main_type") for e in card.effects):
                useful = main not in (None, PASS) and \
                    any(e.get("if_main_type") == main.card_type for e in card.effects)
            elif "APPLY_STATUS" in effects:
                useful = main not in (None, PASS) and self.rng.random() < 0.6
            elif "SET_AFFINITY" in effects:
                useful = self._wants_affinity(me, card)
            elif "HEAL" in effects:              # Harvest / Heal: solo si le falta vida
                amount = next(e.get("amount", 0) for e in card.effects if e["type"] == "HEAL")
                useful = me.max_hp - me.hp >= amount
            elif effects & {"REDUCE_MANA", "REDUCE_MAX_MANA"}:   # Haggle, Void Buzz
                foe = engine.players[1 - i]
                conditional = any(e.get("if_hit") for e in card.effects)
                useful = (foe.mana > 0 or "REDUCE_MAX_MANA" in effects) and self.rng.random() < 0.6 \
                    and (not conditional or main not in (None, PASS))
            elif "GAIN_STYLE" in effects:
                spare = me.mana - engine.total_cost(i, main, card)
                useful = spare >= 1 and self.rng.random() < 0.5
            if useful:
                engine.select(i, me.hand.index(card))
                return
