"""Mazos editables: DeckStore (decks.json) y estado del editor / menú (sin Pygame)."""
import json
import os
import shutil
import tempfile
import unittest

import helpers  # noqa: F401  (añade la raíz del proyecto al path)

from combate.cards.card_database import DECKS
from combate.cards.deck_store import BUILTIN_DECKS, DeckStore
from combate.game.combat import CombatEngine
from combate.game.config import RULES
from combate.game.deck_editor import CATALOG, DeckEditor, MenuState
from combate.game.state_machine import Phase

TEN = ["attack"] * 4 + ["guard"] * 3 + ["break"] * 3


class TmpStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "decks.json")
        self.store = DeckStore(self.path)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def reload(self):
        return DeckStore(self.path)

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)["decks"]


class TestDeckStore(TmpStore):
    def test_without_file_only_builtin(self):
        self.assertEqual(self.store.names(), list(BUILTIN_DECKS))
        self.assertEqual(self.store.get("duelo"), DECKS["duelo"])
        self.assertEqual(self.store.kind("duelo"), "fábrica")
        self.assertFalse(os.path.exists(self.path), "Solo leer no crea el archivo")

    def test_save_new_deck_persists(self):
        self.assertEqual(self.store.save("mi_mazo", TEN), [])
        self.assertEqual(self.saved(), {"mi_mazo": TEN})
        again = self.reload()
        self.assertEqual(again.get("mi_mazo"), TEN)
        self.assertEqual(again.kind("mi_mazo"), "propio")
        self.assertEqual(again.names()[-1], "mi_mazo")

    def test_modify_and_restore_builtin(self):
        self.store.save("duelo", TEN)
        self.assertEqual(self.reload().get("duelo"), TEN)
        self.assertEqual(self.store.kind("duelo"), "modificado")
        self.assertTrue(self.store.restore("duelo"))
        self.assertEqual(self.reload().get("duelo"), BUILTIN_DECKS["duelo"])
        self.assertFalse(self.store.delete("duelo"), "Los de fábrica no se borran")

    def test_saving_builtin_unchanged_stores_nothing(self):
        self.store.save("duelo", list(BUILTIN_DECKS["duelo"]))
        self.assertEqual(self.saved(), {})

    def test_validation(self):
        self.assertTrue(self.store.save("corto", ["attack"] * 9))
        self.assertTrue(self.store.save("raro", ["attack"] * 9 + ["no_existe"]))
        self.assertTrue(self.store.save("Con Espacios", TEN))
        self.assertTrue(self.store.save("", TEN))
        self.assertFalse(os.path.exists(self.path), "Nada inválido llega al archivo")

    def test_invalid_file_entries_are_ignored_with_warning(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"decks": {"bueno": TEN, "malo": ["attack"], "duelo": ["zzz"] * 10}}, f)
        store = self.reload()
        self.assertEqual(store.get("bueno"), TEN)
        self.assertFalse(store.exists("malo"))
        self.assertEqual(store.get("duelo"), BUILTIN_DECKS["duelo"])
        self.assertEqual(len(store.warnings), 2)

    def test_corrupt_file_does_not_crash(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{no es json")
        store = self.reload()
        self.assertEqual(store.names(), list(BUILTIN_DECKS))
        self.assertEqual(len(store.warnings), 1)

    def test_apply_feeds_the_engine(self):
        self.store.save("mi_mazo", TEN)
        self.store.save("duelo", ["guard"] * 10)
        decks = dict(DECKS)
        self.store.apply(decks)
        self.assertEqual(decks["mi_mazo"], TEN)
        self.assertEqual(decks["duelo"], ["guard"] * 10)
        self.store.delete("mi_mazo")
        self.store.apply(decks)
        self.assertNotIn("mi_mazo", decks)

    def test_builtin_decks_untouched_by_import(self):
        self.assertEqual(DECKS, BUILTIN_DECKS, "Importar el almacén no cambia los mazos del juego ni de los tests")


class TestDeckEditor(TmpStore):
    def setUp(self):
        super().setUp()
        self.ed = DeckEditor(self.store, "duelo")

    def test_starts_with_saved_copy(self):
        ed = self.ed
        self.assertEqual(ed.cards, BUILTIN_DECKS["duelo"])
        self.assertFalse(ed.dirty)
        ed.cards.append("x")
        self.assertEqual(self.store.get("duelo"), BUILTIN_DECKS["duelo"], "Edita una copia")

    def test_add_remove_and_limit(self):
        ed = self.ed
        self.assertFalse(ed.add("magic"), "Lleno: 10/10")
        self.assertIn("ya tiene 10", ed.message)
        self.assertTrue(ed.remove("attack"))
        self.assertTrue(ed.dirty)
        self.assertTrue(ed.add("magic"))
        self.assertEqual(ed.count("attack"), 1)
        self.assertEqual(ed.count("magic"), 1)
        self.assertFalse(ed.remove("lullaby"), "No está en el mazo")

    def test_counts_follow_catalog_order(self):
        ids = [cid for cid, _ in self.ed.counts()]
        self.assertEqual(ids, sorted(ids, key=CATALOG.index))
        self.assertEqual(sum(n for _, n in self.ed.counts()), RULES.DECK_SIZE)

    def test_save_and_discard(self):
        ed = self.ed
        ed.remove("recover")
        ed.add("lullaby")
        self.assertTrue(ed.save())
        self.assertFalse(ed.dirty)
        self.assertIn("lullaby", self.reload().get("duelo"))
        ed.remove("lullaby")
        ed.discard()
        self.assertIn("lullaby", ed.cards)

    def test_cannot_save_incomplete(self):
        ed = self.ed
        ed.remove("attack")
        self.assertFalse(ed.save())
        self.assertIn("10 cartas", ed.message)
        self.assertEqual(self.reload().get("duelo"), BUILTIN_DECKS["duelo"])

    def test_switching_with_unsaved_changes_is_blocked(self):
        ed = self.ed
        ed.remove("attack")
        self.assertFalse(ed.select("starter"))
        self.assertEqual(ed.selected, "duelo")
        ed.discard()
        self.assertTrue(ed.select("starter"))
        self.assertEqual(ed.cards, BUILTIN_DECKS["starter"])

    def test_new_deck_with_typed_name(self):
        ed = self.ed
        self.assertTrue(ed.new_deck())
        self.assertEqual((ed.cards, ed.is_new), ([], True))
        self.assertTrue(ed.start_editing_name())
        while ed.name:
            ed.backspace()
        for ch in "Mi Mazo!":
            ed.type_char(ch)
        self.assertEqual(ed.name, "mi_mazo", "Minúsculas, espacio -> _, sin símbolos")
        for cid in TEN:
            ed.add(cid)
        self.assertTrue(ed.save())
        self.assertEqual(self.reload().get("mi_mazo"), TEN)
        self.assertEqual(self.store.kind("mi_mazo"), "propio")

    def test_duplicate_builtin_and_rename_own(self):
        ed = self.ed
        self.assertFalse(ed.start_editing_name(), "Los de fábrica no se renombran")
        self.assertTrue(ed.duplicate())
        self.assertEqual(ed.name, "duelo_copia")
        self.assertTrue(ed.save())
        self.assertTrue(ed.start_editing_name())
        for _ in "copia":
            ed.backspace()
        for ch in "dos":
            ed.type_char(ch)
        self.assertTrue(ed.save())
        store = self.reload()
        self.assertTrue(store.exists("duelo_dos"))
        self.assertFalse(store.exists("duelo_copia"), "Renombrar un propio no deja el viejo")
        self.assertEqual(store.get("duelo"), BUILTIN_DECKS["duelo"])

    def test_name_clash_rejected(self):
        ed = self.ed
        ed.new_deck()
        ed.start_editing_name()
        while ed.name:
            ed.backspace()
        for ch in "starter":
            ed.type_char(ch)
        for cid in TEN:
            ed.add(cid)
        self.assertFalse(ed.save())
        self.assertIn("ya existe", ed.message)
        self.assertEqual(self.store.get("starter"), BUILTIN_DECKS["starter"])

    def test_delete_and_restore(self):
        ed = self.ed
        self.assertFalse(ed.can_delete())
        self.assertFalse(ed.can_restore())
        ed.remove("recover")
        ed.add("magic")
        ed.save()
        self.assertTrue(ed.can_restore())
        self.assertTrue(ed.restore())
        self.assertEqual(ed.cards, BUILTIN_DECKS["duelo"])
        ed.duplicate()
        ed.save()
        self.assertTrue(ed.can_delete())
        self.assertTrue(ed.delete())
        self.assertFalse(self.reload().exists("duelo_copia"))

    def test_edited_deck_is_used_in_a_game(self):
        ed = self.ed
        ed.clear()
        for _ in range(10):
            ed.add("magic")
        ed.save()
        decks = dict(DECKS)
        self.store.apply(decks)
        original = dict(DECKS)
        try:
            DECKS.clear()
            DECKS.update(decks)
            e = CombatEngine(decks=("duelo", "starter"), seed=1)
            e.run_auto()
            self.assertEqual(e.phase, Phase.REDRAW)
            self.assertTrue(all(c.id == "magic" for c in e.players[0].hand))
            self.assertEqual(len(e.players[0].hand) + len(e.players[0].deck), 10)
        finally:
            DECKS.clear()
            DECKS.update(original)


class TestMenuState(TmpStore):
    def test_cycle_and_refresh(self):
        self.store.save("zz", TEN)
        menu = MenuState(self.store, ("duelo", "no_existe"))
        self.assertEqual(menu.choice, ["duelo", "duelo"])
        menu.cycle(1, -1)
        self.assertEqual(menu.choice[1], "zz", "Da la vuelta al final de la lista")
        self.store.delete("zz")
        menu.refresh()
        self.assertEqual(menu.choice[1], self.store.names()[0])


HOSPITAL = ["attack", "guard", "break", "magic", "perfect_guard", "recover", "taunt",
            "stun_guard", "revenge", "overdrive"]


class TestSingleUniqueStore(unittest.TestCase):
    """Almacén de la exploración: un solo mazo de fábrica y sin cartas repetidas."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = DeckStore(path=os.path.join(self.dir, "decks_hospital.json"),
                               builtins={"hospital": HOSPITAL}, unique=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_only_its_own_deck(self):
        self.assertEqual(self.store.names(), ["hospital"])
        self.assertEqual(self.store.get("hospital"), HOSPITAL)

    def test_repeated_cards_are_invalid(self):
        bad = HOSPITAL[:-1] + ["attack"]
        self.assertTrue(any("repetida" in e for e in self.store.validate(bad)))
        self.assertEqual(self.store.validate(HOSPITAL), [])
        self.assertTrue(self.store.save("hospital", bad))            # lista de errores = no guardado
        self.assertEqual(self.store.get("hospital"), HOSPITAL)

    def test_default_store_still_allows_copies(self):
        self.assertEqual(DeckStore(path=os.path.join(self.dir, "x.json")).validate(TEN), [])

    def test_apply_adds_without_removing_other_decks(self):
        decks = {"duelo": list(DECKS["duelo"])}
        self.store.apply(decks)
        self.assertIn("duelo", decks)
        self.assertEqual(decks["hospital"], HOSPITAL)

    def test_editor_single_and_unique(self):
        ed = DeckEditor(self.store, locked={"fire_bolt"}, single=True)
        self.assertFalse(ed.new_deck())
        self.assertFalse(ed.duplicate())
        self.assertFalse(ed.start_editing_name())
        self.assertFalse(ed.can_delete())
        ed.remove("taunt")
        self.assertFalse(ed.add("guard"))                            # ya está
        self.assertFalse(ed.add("fire_bolt"))                        # bloqueada
        self.assertTrue(ed.add("heavy_blow"))
        self.assertTrue(ed.save())
        self.assertIn("heavy_blow", self.store.get("hospital"))

    def test_combat_can_still_draw_a_card_again(self):
        """Sin repetidas en el mazo, pero en combate los descartes vuelven al mazo."""
        e = CombatEngine(card_lists=(make_deck_cards_list(HOSPITAL), make_deck_cards_list(HOSPITAL)), seed=1)
        deck = e.players[0].deck
        first = deck.draw()
        deck.discard(first)
        drawn = [deck.draw() for _ in range(len(deck.draw_pile))]
        drawn.append(deck.draw())                                    # mazo vacío: se barajan los descartes
        self.assertIs(drawn[-1], first)


def make_deck_cards_list(ids):
    from combate.cards.card_database import make_card
    return [make_card(cid) for cid in ids]


if __name__ == "__main__":
    unittest.main()
