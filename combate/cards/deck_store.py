"""Mazos editables por el jugador. Sin Pygame.

Los mazos de cards/card_database.py (DECKS) son los "de fábrica" y no se
modifican en el código. Los cambios del jugador se guardan en decks.json:

    {"decks": {"duelo": ["attack", ...], "mi_mazo": [...]}}

    - Un mazo de fábrica guardado en decks.json queda MODIFICADO; "restaurar"
      borra la modificación y vuelve al original.
    - Un nombre que no es de fábrica es un mazo PROPIO; se puede borrar.

DeckStore.apply() vuelca el resultado en DECKS para que CombatEngine (que lee
DECKS por nombre) use los mazos editados. Solo lo llama la aplicación, nunca
al importar: los tests siguen viendo los mazos de fábrica.

Otra aplicación (la exploración del hospital) puede usar su propio almacén:
DeckStore(path, builtins={"hospital": [...]}, unique=True) tiene solo esos mazos
de fábrica, no deja repetir cartas en un mazo y, al aplicar, AÑADE sus mazos a
DECKS sin borrar los demás. Repetir cartas solo se prohíbe al montar el mazo: en
combate, al acabarse el mazo se barajan los descartes y una carta puede volver.
"""
import json
import os
import re

from combate.cards.card_database import CARDS, DECKS, PLAYER_CARDS
from combate.game.config import RULES

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "decks.json")
BUILTIN_DECKS = {name: list(ids) for name, ids in DECKS.items()}     # copia de fábrica
NAME_RE = re.compile(r"^[a-z0-9_-]{1,20}$")


class DeckStore:
    def __init__(self, path=DEFAULT_PATH, rules=RULES, builtins=None, unique=False):
        self.path = path
        self.rules = rules
        self.own_builtins = builtins is not None
        self.builtins = {n: list(ids) for n, ids in builtins.items()} if self.own_builtins else BUILTIN_DECKS
        self.unique = unique            # un mazo no puede llevar dos copias de la misma carta
        self.warnings = []          # entradas de decks.json que no se pudieron usar
        self.user = self._load()

    # --- Lectura -----------------------------------------------------------------
    def _load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            self.warnings.append(f"No se pudo leer {os.path.basename(self.path)}: {exc}")
            return {}
        decks = {}
        for name, ids in (data.get("decks") or {}).items():
            errors = self.validate(ids) + self.name_errors(name)
            if errors:
                self.warnings.append(f"Mazo '{name}' ignorado: {errors[0]}")
            else:
                decks[name] = list(ids)
        return decks

    def names(self):
        """De fábrica (en su orden) y después los propios (alfabético)."""
        return list(self.builtins) + sorted(n for n in self.user if n not in self.builtins)

    def get(self, name):
        return list(self.user[name] if name in self.user else self.builtins[name])

    def exists(self, name):
        return name in self.user or name in self.builtins

    def is_builtin(self, name):
        return name in self.builtins

    def is_modified(self, name):
        return name in self.builtins and name in self.user and self.user[name] != self.builtins[name]

    def kind(self, name):
        if not self.is_builtin(name):
            return "propio"
        return "modificado" if self.is_modified(name) else "fábrica"

    # --- Validación ---------------------------------------------------------------
    def validate(self, ids):
        if not isinstance(ids, list):
            return ["no es una lista de cartas"]
        errors = []
        unknown = [c for c in ids if c not in CARDS]
        if unknown:
            errors.append(f"carta desconocida: {unknown[0]}")
        exclusive = [c for c in ids if c in CARDS and c not in PLAYER_CARDS]
        if exclusive:
            errors.append(f"carta exclusiva de un enemigo: {exclusive[0]}")
        if len(ids) != self.rules.DECK_SIZE:
            errors.append(f"debe tener {self.rules.DECK_SIZE} cartas (tiene {len(ids)})")
        if self.unique:
            repeated = sorted({c for c in ids if ids.count(c) > 1})
            if repeated:
                errors.append(f"carta repetida: {repeated[0]} (cada carta solo una vez)")
        return errors

    @staticmethod
    def name_errors(name):
        if not isinstance(name, str) or not NAME_RE.match(name):
            return ["nombre: 1-20 caracteres a-z, 0-9, _ o -"]
        return []

    # --- Escritura ------------------------------------------------------------------
    def save(self, name, ids):
        """Guarda un mazo (nuevo, propio o de fábrica modificado). Devuelve la lista de errores."""
        errors = self.name_errors(name) + self.validate(ids)
        if errors:
            return errors
        if self.is_builtin(name) and list(ids) == self.builtins[name]:
            self.user.pop(name, None)           # igual que el de fábrica: no hace falta guardarlo
        else:
            self.user[name] = list(ids)
        self._write()
        return []

    def restore(self, name):
        """Vuelve un mazo de fábrica a su versión original."""
        if self.is_builtin(name) and name in self.user:
            del self.user[name]
            self._write()
            return True
        return False

    def delete(self, name):
        """Borra un mazo propio (los de fábrica no se borran: se restauran)."""
        if name in self.user and not self.is_builtin(name):
            del self.user[name]
            self._write()
            return True
        return False

    def _write(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"decks": self.user}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def apply(self, decks=DECKS):
        """Deja `decks` (por defecto el DECKS global) con los mazos actuales."""
        if not self.own_builtins:
            decks.clear()
        decks.update({name: self.get(name) for name in self.names()})
        return decks
