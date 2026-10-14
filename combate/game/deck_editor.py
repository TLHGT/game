"""Estado del menú inicial y del editor de mazos. Sin Pygame: la UI
(ui/menu_screen.py, ui/deck_screen.py) solo dibuja esto y llama a sus métodos.

El editor trabaja sobre una COPIA del mazo: nada se guarda hasta GUARDAR.
"""
from combate.cards.card_database import CARD_DATA, CARDS, PLAYER_CARDS
from combate.cards.deck_store import NAME_RE
from combate.game.characters import CHARACTERS, playable_characters

CATALOG = [d["id"] for d in CARD_DATA]      # todas las cartas, en el orden de la base de datos


class MenuState:
    """Elección de personaje y mazo de cada jugador antes de la partida."""

    def __init__(self, store, decks=None, characters=None):
        self.store = store
        names = store.names()
        decks = decks or (names[0], names[0])
        self.choice = [d if store.exists(d) else names[0] for d in decks]
        ids = playable_characters()             # los enemigos no se pueden elegir
        characters = characters or (ids[0], ids[min(1, len(ids) - 1)])
        self.character = [c if c in ids else ids[0] for c in characters]

    def cycle_character(self, player, step):
        ids = playable_characters()
        i = ids.index(self.character[player]) if self.character[player] in ids else 0
        self.character[player] = ids[(i + step) % len(ids)]

    def cycle(self, player, step):
        names = self.store.names()
        i = names.index(self.choice[player]) if self.choice[player] in names else 0
        self.choice[player] = names[(i + step) % len(names)]

    def refresh(self):
        """Tras editar: si un mazo elegido ya no existe, vuelve al primero."""
        names = self.store.names()
        self.choice = [d if d in names else names[0] for d in self.choice]


class DeckEditor:
    def __init__(self, store, selected=None, locked=(), single=False):
        self.store = store
        # Cartas que aún no se pueden usar (la exploración las desbloquea con cofres)
        self.locked = set(locked)
        # Un solo mazo (la exploración): no se crean, duplican, renombran ni borran mazos
        self.single = single
        self.message = ""
        self.editing_name = False
        self._load(selected if selected and store.exists(selected) else store.names()[0])

    # --- Estado -----------------------------------------------------------------
    def _load(self, name):
        self.selected = name                 # mazo guardado que se edita (None = nuevo, sin guardar)
        self.name = name
        self.cards = self.store.get(name)
        self.editing_name = False

    @property
    def size(self):
        return self.store.rules.DECK_SIZE

    @property
    def is_new(self):
        return self.selected is None

    @property
    def dirty(self):
        if self.is_new:
            return True
        return self.name != self.selected or self.cards != self.store.get(self.selected)

    @property
    def valid(self):
        return not self.errors()

    def errors(self):
        errors = self.store.name_errors(self.name) + self.store.validate(self.cards)
        locked = sorted({cid for cid in self.cards if cid in self.locked})
        if locked:
            errors.append("lleva cartas bloqueadas: " + ", ".join(CARDS[c]["name"] for c in locked))
        if self.name != self.selected and self.store.exists(self.name):
            errors.append(f"ya existe un mazo llamado '{self.name}'")
        return errors

    def counts(self):
        """[(id, copias)] en el orden del catálogo."""
        return [(cid, self.cards.count(cid)) for cid in CATALOG if cid in self.cards]

    def count(self, card_id):
        return self.cards.count(card_id)

    # --- Cartas -------------------------------------------------------------------
    def add(self, card_id):
        if card_id not in PLAYER_CARDS:            # ni desconocidas ni exclusivas de enemigos
            return False
        if card_id in self.locked:
            self.message = f"{CARDS[card_id]['name']} está bloqueada: búscala en un cofre del hospital"
            return False
        if self.store.unique and card_id in self.cards:
            self.message = f"{CARDS[card_id]['name']} ya está en el mazo: no se pueden repetir cartas"
            return False
        if len(self.cards) >= self.size:
            self.message = f"El mazo ya tiene {self.size} cartas: quita una antes"
            return False
        self.cards.append(card_id)
        self.message = ""
        return True

    def remove(self, card_id):
        if card_id not in self.cards:
            return False
        # quita la ÚLTIMA copia, para no reordenar el resto
        del self.cards[len(self.cards) - 1 - self.cards[::-1].index(card_id)]
        self.message = ""
        return True

    def clear(self):
        self.cards = []
        self.message = ""

    # --- Mazos --------------------------------------------------------------------
    def select(self, name):
        if name == self.selected and not self.is_new:
            return True
        if self.dirty:
            self.message = "Hay cambios sin guardar: GUARDAR o DESCARTAR"
            return False
        self._load(name)
        self.message = ""
        return True

    def _free_name(self, base):
        base = base[:16]
        if not self.store.exists(base):
            return base
        n = 2
        while self.store.exists(f"{base}_{n}"):
            n += 1
        return f"{base}_{n}"

    def new_deck(self):
        if self.single:
            self.message = "Aquí solo tienes un mazo: cambia sus cartas y GUARDA"
            return False
        if self.dirty:
            self.message = "Hay cambios sin guardar: GUARDAR o DESCARTAR"
            return False
        self.selected, self.name, self.cards = None, self._free_name("mazo"), []
        self.editing_name = False
        self.message = "Mazo nuevo: añade 10 cartas del catálogo"
        return True

    def duplicate(self):
        if self.single:
            self.message = "Aquí solo tienes un mazo: cambia sus cartas y GUARDA"
            return False
        if self.dirty:
            self.message = "Hay cambios sin guardar: GUARDAR o DESCARTAR"
            return False
        cards = list(self.cards)
        self.selected, self.name, self.cards = None, self._free_name(f"{self.name}_copia"), cards
        self.message = "Copia creada: cambia lo que quieras y GUARDA"
        return True

    def save(self):
        errors = self.errors()
        if errors:
            self.message = f"No se puede guardar: {errors[0]}"
            return False
        old = self.selected
        self.store.save(self.name, self.cards)
        renamed = old is not None and old != self.name
        if renamed and not self.store.is_builtin(old):
            self.store.delete(old)          # renombrar un mazo propio
        self.selected = self.name
        self.editing_name = False
        self.message = f"'{self.name}' guardado"
        return True

    def discard(self):
        if self.is_new:
            self._load(self.store.names()[0])
        else:
            self._load(self.selected)
        self.message = "Cambios descartados"

    def can_delete(self):
        return not self.single and not self.is_new and not self.store.is_builtin(self.selected)

    def can_restore(self):
        return not self.is_new and self.store.is_modified(self.selected)

    def delete(self):
        if not self.can_delete():
            return False
        name = self.selected
        self.store.delete(name)
        self._load(self.store.names()[0])
        self.message = f"'{name}' borrado"
        return True

    def restore(self):
        if not self.can_restore():
            return False
        self.store.restore(self.selected)
        self._load(self.selected)
        self.message = f"'{self.selected}' restaurado al original"
        return True

    # --- Nombre -------------------------------------------------------------------
    def start_editing_name(self):
        if self.single:
            self.message = "Aquí solo tienes un mazo: cambia sus cartas y GUARDA"
            return False
        if not self.is_new and self.store.is_builtin(self.selected):
            self.message = "Los mazos de fábrica no se renombran: usa DUPLICAR"
            return False
        self.editing_name = True
        return True

    def type_char(self, ch):
        if not self.editing_name or not ch:
            return False
        ch = ch.lower().replace(" ", "_")
        if len(self.name) >= 20 or not NAME_RE.match(ch):
            return False
        self.name += ch
        return True

    def backspace(self):
        if self.editing_name and self.name:
            self.name = self.name[:-1]
            return True
        return False

    def stop_editing_name(self):
        self.editing_name = False
