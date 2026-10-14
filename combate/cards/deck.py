"""Mazo con pila de robo y descarte. Barajar usa una semilla para que las
partidas (y los tests) sean reproducibles. El azar solo decide el ORDEN de
robo, nunca quién gana una interacción."""
import random


class Deck:
    def __init__(self, cards, seed=None, shuffle=True):
        self.rng = random.Random(seed)
        self.draw_pile = list(cards)
        self.discard_pile = []
        if shuffle:
            self.rng.shuffle(self.draw_pile)

    def __len__(self):
        return len(self.draw_pile)

    def draw(self):
        """Roba una carta. Si la pila está vacía, baraja el descarte."""
        if not self.draw_pile and self.discard_pile:
            self.draw_pile = self.discard_pile
            self.discard_pile = []
            self.rng.shuffle(self.draw_pile)
        return self.draw_pile.pop() if self.draw_pile else None

    def discard(self, card):
        self.discard_pile.append(card)
