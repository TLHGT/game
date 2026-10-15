"""Bucle principal y orquestación de sistemas.

Orden de cada frame:
    INPUT -> PLAYER UPDATE -> COLLISION -> INTERACTION DETECTION
    -> WORLD UPDATE -> CAMERA UPDATE -> RENDER -> UI

La instancia de Game hace además de "contexto" para los interactuables
(ver entities/interactable.py): show_dialogue, notify, unlock_secret,
start_battle...

Combate: cuando un enemigo (entities/enemy.py) toca al jugador, la
exploración se congela y se abre una BattleScene (game/battle_scene.py), que
usa el combate de cartas de combate/. Al terminar se vuelve al mapa.

Aldea del vacío: la misión (systems/village_quest.py, ctx.village) cambia la
fase del mapa; GameMap.update la aplica y llama a on_phase_changed.
"""
import math

import pygame

from combate.cards.card_database import PLAYER_CARDS
from combate.cards.deck_store import DeckStore
from combate.game.characters import CHARACTERS
from entities.enemy import Enemy
from entities.chest import CARD_PREFIX
from entities.hospital import power_messages
from entities.player import DEFAULT_AVATAR, Player
from game import settings
from game.battle_scene import BattleScene
from game.deck_scene import DeckEditScene
from game.camera import Camera
from game.input import InputHandler
from render.assets import AssetManager
from render.renderer import Renderer
from systems.game_state import GameState
from systems.interaction_system import InteractionSystem
from systems.perk_puzzle import PerkPuzzle
from systems.secret_system import SecretSystem
from systems.village_quest import BOSS_SECRET, END, PHASE_FLAG, PHASE_NAMES, TRADE_NAMES, VillageQuest
from ui.debug_overlay import DebugOverlay
from ui.dialogue import DialogueBox
from ui.interaction_prompt import InteractionPrompt
from ui.notification import NotificationManager
from ui.choice_menu import ChoiceMenu
from ui.pause_menu import PauseMenu
from ui.text import font as text_font
from world.collision import move_and_collide
from world.map_loader import load_map, map_exists

FADE_SPEED = 3.5   # fundido de transición (por segundo)
JUMP_TIME = 0.55   # duración del salto de Hero (segundos)
JUMP_HEIGHT = 70   # altura visual del arco (píxeles)
BLACKOUT_TIME = 2.5   # pozo de la aldea: segundos de pantalla negra
CHICKEN_ESCAPE = (40, 1480)   # por dónde huye el pollo humanoide (borde oeste de la aldea)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(settings.TITLE)
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = AssetManager(settings.ASSET_DIR)
        self.input = InputHandler()
        self.camera = Camera(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        self.renderer = Renderer(self.assets, self.screen.get_size())

        # Sistemas de juego
        self.state = GameState()
        self.secrets = SecretSystem()
        self.secrets.add_listener(self._on_secret_unlocked)
        self.interaction = InteractionSystem()
        self.perks = PerkPuzzle(self.state, settings.PERK_SEQUENCE)   # máquinas de ventajas del hospital
        self.village = VillageQuest(self.state, settings.VILLAGE_SEED)  # misión de la Aldea del vacío

        # UI
        self.dialogue = DialogueBox(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        self.prompt = InteractionPrompt()
        self.notifications = NotificationManager(settings.SCREEN_WIDTH)
        self.debug = DebugOverlay()
        self.debug.enabled = settings.DEBUG_START_ENABLED
        self.choice = ChoiceMenu()      # menús de elección (pisos del ascensor)

        # Combate: un único mazo propio de la exploración (settings.HOSPITAL_DECK),
        # guardado en decks_hospital.json y sin cartas repetidas. El duelo PvP
        # (combate/decks.json) no se toca.
        self.store = DeckStore(path=settings.DECKS_PATH, builtins={settings.PLAYER_DECK: settings.HOSPITAL_DECK},
                               unique=True)
        self.store.apply()
        self.pause = PauseMenu(self.state, self.usable_decks(), self.assets)   # TAB: personaje y mazo
        self.deck_scene = None          # editor de mazos abierto desde la pausa
        self.battle = None              # BattleScene mientras hay un combate
        self._pending_battle = None     # enemigo durante el fundido de entrada
        self.battles_won = 0

        self.player = Player()
        self.world = None
        self.fade = 1.0                 # 1 = negro, 0 = visible
        self._pending_map = None        # (map_id, spawn) durante un fundido
        self._spawn = settings.START_SPAWN
        self._jump = None               # (inicio, destino, tiempo) durante un salto
        self._blackout = None           # [segundos, mensaje]: pantalla negra del pozo
        self.load_map(settings.START_MAP, settings.START_SPAWN)

    # ======================================================================
    # API de contexto para interactuables
    # ======================================================================
    def show_dialogue(self, pages, speaker=None, on_close=None):
        self.player.stop()
        self.dialogue.open(pages, speaker, on_close)

    def notify(self, text, style="info"):
        self.notifications.push(text, style)

    def unlock_secret(self, secret_id):
        return self.secrets.unlock(secret_id)

    def open_choice(self, title, options, on_choose):
        """Menú de elección: [(texto, disponible, valor)] -> on_choose(valor)."""
        self.player.stop()
        self.choice.open(title, options, on_choose)

    def travel(self, map_id, spawn="default", message=None):
        """Cambia de mapa con fundido (ascensor, teletransportes...)."""
        if map_exists(map_id):
            self._pending_map = (map_id, spawn)
            if message:
                self.notify(message)

    # --- Cartas bloqueadas (todas menos settings.AVAILABLE_CARDS) ----------
    def locked_cards(self):
        """Cartas del jugador que aún no se pueden usar: las que no están en
        AVAILABLE_CARDS y no se han encontrado en un cofre."""
        return {c for c in PLAYER_CARDS
                if c not in settings.AVAILABLE_CARDS and not self.state.inventory.has(CARD_PREFIX + c)}

    def usable_decks(self):
        """Mazos que se pueden elegir: los que no llevan cartas bloqueadas."""
        locked = self.locked_cards()
        return [n for n in self.store.names() if not locked & set(self.store.get(n))]

    def on_card_unlocked(self, card_id):
        self.pause.refresh_decks(self.usable_decks())

    @property
    def busy(self):
        """True si el jugador no controla la exploración (diálogo, fundido, combate, salto)."""
        return (self.dialogue.is_open or self._pending_map is not None or self.pause.is_open
                or self.choice.is_open
                or self._pending_battle is not None or self.battle is not None or self._jump is not None
                or self._blackout is not None)

    # ======================================================================
    # Habilidades de aventura (entities/adventure.py)
    # ======================================================================
    @property
    def player_character(self):
        return CHARACTERS[self.pause.character]

    @property
    def player_character_name(self):
        return self.player_character.name

    @property
    def ability(self):
        """Habilidad de aventura del personaje elegido en la pausa ("burn", "jump"...)."""
        return self.player_character.adventure

    def _sync_avatar(self):
        """El sprite del mapa es el avatar del personaje elegido en la pausa."""
        self.player.avatar = self.player_character.avatar or DEFAULT_AVATAR

    def jump_to(self, target):
        """Salto de Hero: arco por encima de muros y desniveles hasta `target`."""
        self.player.stop()
        self._jump = ((self.player.x, self.player.y), (float(target[0]), float(target[1])), 0.0)

    def _update_jump(self, dt):
        (x0, y0), (x1, y1), t = self._jump
        t = min(1.0, t + dt / JUMP_TIME)
        self.player.x = x0 + (x1 - x0) * t
        self.player.y = y0 + (y1 - y0) * t
        self._jump = ((x0, y0), (x1, y1), t)
        if t >= 1.0:
            self._jump = None
            self.player.sprite_offset = (0, 0)
            for zone in self.world.exits + self.world.triggers:   # aterrizar no dispara salidas
                zone.check_enter(self.player.rect)

    # ======================================================================
    # Aldea del vacío (systems/village_quest.py)
    # ======================================================================
    def on_phase_changed(self, world):
        """La misión cambió la fase del mapa: suelo nuevo, y que nadie quede atrapado."""
        self.renderer.prepare(world)
        self._unstick()
        if world.phase_flag == PHASE_FLAG and world.phase in PHASE_NAMES:
            self.notify(PHASE_NAMES[world.phase], "area")

    def _unstick(self):
        """Si algo sólido apareció encima del jugador, lo aparta al hueco libre más cercano."""
        p = self.player
        if p.rect.collidelist(self.world.solids_near(p.rect)) == -1:
            return
        x0, y0 = p.x, p.y
        for radius in range(10, 400, 10):
            for k in range(16):
                a = k * math.tau / 16
                p.x, p.y = x0 + math.cos(a) * radius, y0 + math.sin(a) * radius
                if p.rect.collidelist(self.world.solids_near(p.rect)) == -1:
                    return
        p.x, p.y = x0, y0

    def on_soul_dropped(self, trade):
        """Un aldeano hueco vencido suelta su alma (solo en la fase de las almas)."""
        result = self.village.grant_soul(trade)
        if result == "got":
            self.notify(f"Recoges el alma de un {TRADE_NAMES[trade]}. Llévala a su círculo del vacío.", "discovery")
        elif result == "full":
            self.notify("Ya llevas un alma: la nueva se deshace en humo morado.")

    def _chicken(self):
        return self.world.get_interactable("pollo") if self.world else None

    def chicken_mutates(self):
        self.village.set_chicken("mutated")
        chicken = self._chicken()
        if chicken is not None:
            chicken.run_away(CHICKEN_ESCAPE)
        self.notify("El pollo humanoide se pierde entre los árboles quemados.", "discovery")

    def _scare_chicken(self):
        """Empieza un combate con el pollo en brazos: huye al gallinero."""
        if self.village.chicken != "carried":
            return
        self.village.set_chicken("coop")
        chicken = self._chicken()
        if chicken is not None:
            chicken.return_home()
        self.notify("El pollo se asusta, aletea y huye de vuelta al gallinero.")

    def blackout_to_start(self, message):
        """Pozo especial: pantalla negra unos segundos y de vuelta al principio del mapa."""
        self.player.stop()
        self._blackout = [BLACKOUT_TIME, message]

    def _update_blackout(self, dt):
        self._blackout[0] -= dt
        self.fade = 1.0
        if self._blackout[0] > 0:
            return
        message = self._blackout[1]
        self._blackout = None
        x, y = self.world.spawns.get("default", (64, 64))
        self.player.x, self.player.y = float(x), float(y)
        self.camera.snap_to(self.player.x, self.player.y)
        for zone in self.world.exits + self.world.triggers:
            zone.check_enter(self.player.rect)
        self.notify(message, "discovery")

    # ======================================================================
    # Combate
    # ======================================================================
    def start_battle(self, enemy):
        if self.busy or enemy.defeated:
            return
        self.player.stop()
        self._scare_chicken()
        if enemy.intro:
            self.show_dialogue(enemy.intro, speaker=enemy.name,
                               on_close=lambda: self._begin_battle(enemy))
        else:
            self._begin_battle(enemy)

    def _begin_battle(self, enemy):
        self._pending_battle = enemy

    def _open_battle(self, enemy):
        # Lo elegido en la pausa (nunca un mazo con cartas bloqueadas)
        deck, character = self.pause.deck, self.pause.character
        self.battle = BattleScene(self.screen, enemy, deck, character, settings.PLAYER_COMBAT_NAME)

    def _end_battle(self):
        battle, self.battle = self.battle, None
        enemy, result = battle.enemy, battle.result
        self.fade = 1.0
        if result == "win":
            self.battles_won += 1
            enemy.on_defeated(self)
            if enemy.victory:
                self.show_dialogue(enemy.victory, speaker=enemy.name)
            else:
                self.notify(f"Has vencido a {enemy.name}.", "discovery")
        elif result == "lose":
            # Vuelves al punto de entrada del mapa; los enemigos regresan a su sitio
            self.load_map(self.world.id, self._spawn)
            for it in self.world.all_interactables:
                if isinstance(it, Enemy):
                    it.on_escaped()
            self.notify("Has sido derrotado... Te recuperas en la entrada de la zona.", "discovery")
        else:
            enemy.on_escaped()
            self.notify("Consigues escapar." if result == "flee" else "Empate: el enemigo retrocede.")

    def _on_secret_unlocked(self, secret_id, info):
        if info.get("unlock_message"):
            self.notify(info["unlock_message"], "discovery")
        if secret_id == BOSS_SECRET:                 # Aldea: el insecto ha caído, el portal se cierra
            self.village.set_phase(END)
        for message in power_messages(secret_id, self.secrets):
            self.notify(message, "discovery")
        if self.world:
            self.world.on_secret_unlocked(secret_id, self)

    # ======================================================================
    # Mapas
    # ======================================================================
    def load_map(self, map_id, spawn="default"):
        # Recuerda el estado de los objetos del mapa que se abandona
        # (cofres abiertos, etapas de la radio...). Base del futuro guardado.
        if self.world:
            self.state.map_states[self.world.id] = {
                it.id: it.get_state() for it in self.world.all_interactables if it.id}
        self.world = load_map(map_id)
        self._spawn = spawn
        saved = self.state.map_states.get(map_id, {})
        for it in self.world.all_interactables:
            if it.id in saved:
                it.set_state(saved[it.id])
        self.world.apply_phase(self.world.current_phase(self.state))   # mapas con fases (aldea)
        for s in self.world.secrets:
            self.secrets.register(s["id"], s.get("name", ""), s.get("unlock_message"))
            if self.secrets.is_unlocked(s["id"]):      # secretos ya conseguidos
                self.world.on_secret_unlocked(s["id"], self)
        x, y = self.world.spawns.get(spawn) or self.world.spawns.get("default", (64, 64))
        self.player.x, self.player.y = float(x), float(y)
        self.player.stop()
        self.camera.set_world_size(self.world.width, self.world.height)
        self.camera.snap_to(self.player.x, self.player.y)
        self.renderer.prepare(self.world)
        # Marca como "dentro" las zonas en las que ya aparece el jugador,
        # para no disparar una salida nada más llegar.
        for zone in self.world.exits + self.world.triggers:
            zone.check_enter(self.player.rect)
        self.notify(self.world.name, "area")

    def _handle_exit(self, transition):
        if map_exists(transition.target_map):
            self._pending_map = (transition.target_map, transition.target_spawn)
        else:
            # El mapa destino aún no existe: solo informamos.
            self.notify(transition.message or "Has llegado al final de la zona.", "discovery")

    # ======================================================================
    # Bucle
    # ======================================================================
    def run(self):
        while self.running:
            dt = min(self.clock.tick(settings.FPS) / 1000.0, 1 / 20)
            self.step(dt, pygame.event.get())
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def step(self, dt, events):
        # --- COMBATE: mientras dura, la exploración está en pausa ----------
        if self.battle is not None:
            self.battle.step(dt, events)
            if not self.battle.running:
                self.running = False
            elif self.battle.finished:
                self._end_battle()
            return

        # --- EDITOR DE MAZOS (desde la pausa) --------------------------------
        if self.deck_scene is not None:
            self.deck_scene.step(dt, events)
            if not self.deck_scene.running:
                self.running = False
            elif self.deck_scene.finished:
                self.pause.refresh_decks(self.usable_decks(), prefer=self.deck_scene.selected)
                self.deck_scene = None
            return

        # --- PAUSA: el mundo se congela -------------------------------------
        if self.pause.is_open:
            if any(ev.type == pygame.QUIT for ev in events):
                self.running = False
            self.pause.handle_events(events)
            if self.pause.request == "edit_decks":
                self.pause.request = None
                self.deck_scene = DeckEditScene(self.screen, self.store, selected=self.pause.deck,
                                                locked=self.locked_cards(), single=True)
            return

        # --- MENÚ DE ELECCIÓN (ascensor): el mundo se congela ------------------
        if self.choice.is_open:
            if any(ev.type == pygame.QUIT for ev in events):
                self.running = False
            self.choice.handle_events(events)
            self._update_fade(dt)
            return

        # --- INPUT --------------------------------------------------------
        self.input.process_events(events)
        if self.input.quit_requested:
            self.running = False
        if self.input.pressed("debug"):
            self.debug.toggle()
        if self.input.pressed("pause") and not self.busy:
            self.player.stop()
            self._sync_avatar()
            self.player.update(dt)
            self.pause.open()
            return

        if self._blackout is not None:
            self._update_blackout(dt)
            self.notifications.update(dt)
            return

        busy = self.busy
        if self.dialogue.is_open:
            if self.input.pressed("confirm"):
                self.dialogue.advance()
        elif not busy:
            # --- PLAYER UPDATE + COLLISION --------------------------------
            self.player.set_move_input(self.input.move_vector())
            move_and_collide(self.player, self.player.velocity.x * dt,
                             self.player.velocity.y * dt, self.world)
            # --- INTERACTION DETECTION ------------------------------------
            self.interaction.update(self.player, self.world.interactables, self.ability)
            if self.input.pressed("interact"):
                self.interaction.interact(self)
        if busy:
            self.player.stop()
        self._sync_avatar()
        self.player.update(dt)
        if self._jump is not None:
            self._update_jump(dt)
            if self._jump is not None:              # arco: el sprite sube y baja
                t = self._jump[2]
                self.player.sprite_offset = (0, -round(math.sin(t * math.pi) * JUMP_HEIGHT))

        # --- WORLD UPDATE -------------------------------------------------
        self.world.update(dt, self)
        if not busy:
            for ex in self.world.exits:
                if ex.check_enter(self.player.rect):
                    self._handle_exit(ex)

        # --- CAMERA UPDATE ------------------------------------------------
        self.camera.update(dt, self.player.x, self.player.y)

        # --- UI UPDATE ----------------------------------------------------
        prompt_target = None if self.busy else self.interaction.target
        self.prompt.update(dt, prompt_target)
        self.dialogue.update(dt)
        self.notifications.update(dt)
        self._update_fade(dt)

    def _draw_carried(self):
        """Aldea: qué llevas encima (el alma de un aldeano, el pollo)."""
        if self.world.phase_flag != PHASE_FLAG:
            return
        lines = []
        if self.village.soul:
            lines.append(f"Alma de {TRADE_NAMES[self.village.soul]}")
        if self.village.chicken == "carried":
            lines.append("Pollo en brazos")
        y = 16
        for line in lines:
            surf = text_font(18, bold=True).render(line, True, (230, 200, 255))
            box = surf.get_rect(topleft=(16, y)).inflate(18, 10)
            panel = pygame.Surface(box.size, pygame.SRCALPHA)
            panel.fill((30, 16, 44, 200))
            self.screen.blit(panel, box)
            pygame.draw.rect(self.screen, (150, 90, 210), box, 2, border_radius=6)
            self.screen.blit(surf, (box.x + 9, box.y + 5))
            y += box.h + 6

    def _update_fade(self, dt):
        if self._pending_battle is not None:
            self.fade = min(1.0, self.fade + dt * settings.BATTLE_FADE_SPEED)
            if self.fade >= 1.0:
                enemy, self._pending_battle = self._pending_battle, None
                self._open_battle(enemy)
        elif self._pending_map:
            self.fade = min(1.0, self.fade + dt * FADE_SPEED)
            if self.fade >= 1.0:
                map_id, spawn = self._pending_map
                self._pending_map = None
                self.load_map(map_id, spawn)
        else:
            self.fade = max(0.0, self.fade - dt * FADE_SPEED * 0.6)

    # ======================================================================
    # Render
    # ======================================================================
    def draw(self):
        if self.deck_scene is not None:
            self.deck_scene.draw()
            return
        if self.battle is not None:
            self.battle.draw()
            return
        # --- RENDER -------------------------------------------------------
        self.renderer.draw_world(self.screen, self.world, self.player, self.camera)
        if self.debug.enabled:
            self.debug.draw_world(self.screen, self)
        # --- UI -----------------------------------------------------------
        if not self.dialogue.is_open:
            self.prompt.draw(self.screen, self.camera, self.assets)
        self.notifications.draw(self.screen)
        self.dialogue.draw(self.screen)
        if self.debug.enabled:
            self.debug.draw_text(self.screen, self)
        self._draw_carried()
        self.choice.draw(self.screen)
        self.pause.draw(self.screen)
        if self.fade > 0:
            veil = pygame.Surface(self.screen.get_size())
            veil.set_alpha(int(255 * self.fade))
            self.screen.blit(veil, (0, 0))
