"""Estado de un jugador. Sin Pygame: solo datos y operaciones simples."""
from combate.game.style import StyleState


class Player:
    def __init__(self, index, name, deck, rules):
        self.index = index            # 0 o 1
        self.name = name
        self.deck = deck
        self.rules = rules
        self.hp = rules.MAX_HP
        self.max_hp = rules.MAX_HP    # tope de curación (un enemigo puede empezar con menos)
        self.max_hp_lost = 0          # vida máxima que le han quitado en este combate (Void consumption)
        self.mana = rules.STARTING_MANA
        self.max_mana = rules.MAX_MANA  # tope de Mana (algunos enemigos lo reducen en combate)
        self.stable = True
        self.combo_hits = 0           # cadena de hits CONSECUTIVOS (propia de cada jugador)
        self.hand = []
        self.redraws_left = 0
        self.status = None            # StatusEffect activo (máx. 1) · game/status.py
        self.immunities = set()       # StatusId a los que es inmune (independiente de elementos)
        self.character = None         # Character elegido (game/characters.py) o None
        self.passive = None           # instancia de su pasiva para esta partida
        self.style = StyleState()     # Estilo de esta partida (nuevo en cada partida)

    # --- Status Effects -----------------------------------------------------
    def has_status(self, status_id):
        return self.status is not None and self.status.id == status_id

    # --- Mana ---------------------------------------------------------------
    def gain_mana(self, amount):
        before = self.mana
        self.mana = max(0, min(self.max_mana, self.mana + amount))
        return self.mana - before

    def spend_mana(self, amount):
        if amount > self.mana:
            raise ValueError(f"{self.name} no tiene {amount} de Mana")
        self.mana -= amount

    # --- Cartas -------------------------------------------------------------
    def draw_to_full(self):
        drawn = []
        while len(self.hand) < self.rules.MAX_HAND_SIZE:
            card = self.deck.draw()
            if card is None:
                break
            self.hand.append(card)
            drawn.append(card)
        return drawn

    def redraw(self, index):
        """Cambio: descarta la carta `index` y roba otra en su lugar."""
        if self.redraws_left <= 0 or not 0 <= index < len(self.hand):
            return None
        old = self.hand.pop(index)
        self.deck.discard(old)
        new = self.deck.draw()
        if new is not None:
            self.hand.insert(index, new)
        self.redraws_left -= 1
        return new

    def take_card(self, card):
        """Saca la carta de la mano (al jugarla o usarla) y la descarta."""
        self.hand.remove(card)
        self.deck.discard(card)

    def playable_cards(self, cost=0):
        return [c for c in self.hand if c.can_play(self, cost)]

    @property
    def stability_label(self):
        return "STABLE" if self.stable else "UNSTABLE"

    @property
    def alive(self):
        return self.hp > 0
