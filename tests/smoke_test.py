"""Prueba automática sin ventana que recorre el mapa y verifica los criterios.

    python tests/smoke_test.py            # solo comprobaciones
    python tests/smoke_test.py --shots    # además guarda capturas en tests/shots/
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from game.game import Game  # noqa: E402

DT = 1 / 60
SHOTS = "--shots" in sys.argv
SHOT_DIR = os.path.join(ROOT, "tests", "shots")


def key_event(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)


class Bot:
    def __init__(self):
        self.g = Game()
        self.ok = 0

    def check(self, cond, label):
        status = "OK " if cond else "FALLO"
        print(f"[{status}] {label}")
        if not cond:
            raise SystemExit(1)
        self.ok += 1

    def tick(self, n=1, events=()):
        for i in range(n):
            self.g.step(DT, list(events) if i == 0 else [])
        self.g.draw()

    def shot(self, name):
        if SHOTS:
            os.makedirs(SHOT_DIR, exist_ok=True)
            self.g.draw()
            pygame.image.save(self.g.screen, os.path.join(SHOT_DIR, name + ".png"))

    def in_encounter(self):
        g = self.g
        return g.dialogue.is_open or g.battle is not None or g._pending_battle is not None

    def resolve_encounter(self, result="win"):
        """Termina el encuentro con un enemigo (intro, combate, texto final).
        El combate en sí se prueba en tests/battle_test.py; aquí se da por
        resuelto con `result`."""
        g = self.g
        for _ in range(600):
            if g.dialogue.is_open:
                self.close_dialogue()
            elif g.battle is not None:
                self.last_battle = g.battle
                g.battle.finish(result)
                self.tick()
            elif g._pending_battle is not None:
                self.tick()
            else:
                break
        self.tick(5)

    def walk(self, *points, timeout=12.0):
        p = self.g.player
        for tx, ty in points:
            t = 0.0
            while True:
                if self.in_encounter():     # un enemigo nos ha alcanzado por el camino
                    self.g.input.move_override = None
                    self.resolve_encounter()
                    t = 0.0
                    continue
                d = pygame.Vector2(tx - p.x, ty - p.y)
                if d.length() < 4:
                    break
                self.g.input.move_override = d.normalize() if d.length() > 0 else (0, 0)
                self.g.step(DT, [])
                t += DT
                if t > timeout:
                    self.g.input.move_override = None
                    raise SystemExit(f"[FALLO] Atascado yendo a {(tx, ty)}; jugador en {(p.x, p.y)}")
        self.g.input.move_override = (0, 0)
        self.tick(20)
        self.g.input.move_override = None

    def press_e(self):
        self.tick(1, [key_event(pygame.K_e)])

    def close_dialogue(self):
        guard = 0
        while self.g.dialogue.is_open and guard < 40:
            self.press_e()   # completa el texto
            self.press_e()   # pasa página / cierra
            guard += 1

    def target_id(self):
        t = self.g.interaction.target
        return t.id if t else None


def main():
    # Esta prueba recorre la exploración: sin enemigos que se crucen en el camino
    # (los combates se prueban en tests/battle_test.py).
    from game import settings
    settings.ENEMIES_ENABLED = False
    settings.START_MAP = "forest"           # el hospital es el nivel principal; esta prueba es del bosque
    b = Bot()
    g = b.g
    p = g.player
    b.tick(60)
    b.shot("01_inicio")

    # 1. Movimiento 8 direcciones + diagonal normalizada
    x0, y0 = p.x, p.y
    g.input.move_override = (1, -1)
    g.input.move_override = g.input.move_vector()
    b.tick(30)
    moved = pygame.Vector2(p.x - x0, p.y - y0).length()
    expected = p.speed * DT * 30
    b.check(abs(moved - expected) < 2, f"Diagonal normalizada ({moved:.1f}px ~ {expected:.1f}px)")
    g.input.move_override = (0, 0)
    b.tick(1)
    x1 = p.x
    b.tick(5)
    b.check(p.x == x1, "Se detiene inmediatamente al soltar")

    # 3. Colisión: andar hacia el norte desde el inicio choca con el bosque
    b.walk((70, 1200))
    g.input.move_override = (0, -1)
    b.tick(120)
    b.check(abs(p.y - (1040 + p.hitbox_h)) < 1, f"Choca con el bosque (y={p.y:.1f})")
    g.input.move_override = None

    # 2. Cámara sigue al jugador
    b.walk((70, 1200), (460, 1200), (780, 1080))
    cam_before = g.camera.camera_x
    b.walk((1300, 1080))
    b.check(g.camera.camera_x > cam_before + 300, "La cámara sigue al jugador")
    b.check(0 <= g.camera.camera_y <= g.world.height - 720, "Cámara dentro de los límites")

    # 5-6. NPC
    b.walk((1520, 1040))
    b.check(b.target_id() == "brann", "NPC detectado en la ruta principal")
    b.check(g.interaction.target.get_prompt() == "E - Hablar", "Indicador 'E - Hablar'")
    b.shot("02_npc_prompt")
    b.press_e()
    b.check(g.dialogue.is_open and g.dialogue.speaker.startswith("Brann"), "Diálogo con NPC abierto")
    b.tick(200)
    b.shot("03_npc_dialogo")
    b.close_dialogue()
    b.check(not g.dialogue.is_open, "Diálogo cerrado con E")

    # 7-9. Desvío sur: cofre
    b.walk((1580, 1100), (1580, 1520), (1290, 1520))
    b.check(b.target_id() == "chest_potion", "Cofre detectado")
    b.press_e()
    chest = g.world.get_interactable("chest_potion")
    b.check(chest.opened and chest.sprite_key == "chest_open", "Cofre abierto (sprite cambiado)")
    b.check("Poción" in " ".join(g.dialogue.pages[0]), "Mensaje 'Has encontrado una Poción.'")
    b.tick(60)
    b.shot("04_cofre")
    b.close_dialogue()

    # NPC opcional
    b.walk((1580, 1530), (1760, 1530))
    b.check(b.target_id() == "mira", "NPC opcional detectado")

    # 10. Puerta cerrada (verja)
    b.walk((1580, 1530), (1580, 1770))
    b.check(b.target_id() == "rusty_gate", "Puerta cerrada detectada")
    b.press_e()
    b.check("Está cerrada." in " ".join(g.dialogue.pages[0]), "Mensaje 'Está cerrada.'")
    b.tick(60)
    b.shot("05_puerta")
    b.close_dialogue()
    g.input.move_override = (0, 1)
    b.tick(60)
    b.check(p.y <= 1800, "La verja cerrada bloquea el paso")
    gate = g.world.get_interactable("rusty_gate")
    b.check(gate.is_locked and hasattr(gate, "unlock"), "door.is_locked / door.unlock() disponibles")

    # 11-12. Radio
    b.walk((1580, 1100), (1960, 1120), (2740, 1200), (2740, 1600), (2735, 1700))
    b.check(b.target_id() == "old_radio", "Radio detectada")
    texts = []
    for _ in range(4):
        b.press_e()
        texts.append(" ".join(g.dialogue.pages[0]))
        b.close_dialogue()
    b.check(texts[0].startswith("Una radio vieja") and texts[3].startswith("01001000"),
            "La radio cambia con cada interacción")
    b.check(g.secrets.is_unlocked("arken_shrine"), "Secreto desbloqueado por la radio")
    door = g.world.get_interactable("ruins_secret_door")
    b.check(door.secret_unlocked and door.is_open and not door.solid, "La puerta secreta cambia de estado")
    b.tick(30)
    b.check(g.notifications.current and "oculto" in g.notifications.current.text,
            "Mensaje 'Has descubierto algo oculto...'")
    b.shot("06_radio")

    # 13. Zona secreta
    b.walk((2740, 1600), (2740, 1200), (2060, 1120), (2060, 700), (2080, 500))
    b.tick(200)
    b.shot("07_ruinas")
    b.walk((2080, 320), (2080, 240))
    b.tick(30)
    msgs = [n.text for n in g.notifications.queue] + ([g.notifications.current.text]
                                                       if g.notifications.current else [])
    b.check(any("Área secreta" in m for m in msgs), "Mensaje 'Área secreta descubierta.'")
    b.tick(90)
    b.shot("08_secreto")
    b.walk((1990, 190))
    b.press_e()
    b.close_dialogue()
    b.check(g.state.inventory.has("arken_amulet"), "Cofre del área secreta")

    # 14. Salida
    b.walk((2080, 320), (2060, 700), (2060, 1120), (2880, 1180), (3140, 1060))
    g.notifications.current = None
    g.notifications.queue.clear()
    b.walk((3590, 1060))
    b.tick(10)
    b.check(g.notifications.current and "final de la zona" in g.notifications.current.text,
            "Mensaje 'Has llegado al final de la zona.'")
    b.shot("09_salida")

    # 15. Debug
    b.tick(1, [key_event(pygame.K_F3)])
    b.check(g.debug.enabled, "F3 activa el modo debug")
    b.shot("10_debug")

    print(f"\nTodas las comprobaciones pasaron ({b.ok}).")
    pygame.quit()


if __name__ == "__main__":
    main()
