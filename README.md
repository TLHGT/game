# Hospital abandonado: exploración + combate de cartas

Prototipo jugable de RPG hecho con Python + Pygame que une dos proyectos:

- la **exploración** top-down / 2.5D del proyecto `map` (mapas, NPC, cofres,
  secretos, el hospital abandonado...);
- el **sistema de combate por cartas** del proyecto `combate-cartas`
  (selección simultánea, iniciativa, Stability, Mana, combos, estados...).

Exploras el mapa como siempre; los **enemigos** se mueven por él y, si te
tocan (o les hablas con `E`), empieza un combate de cartas contra ellos.
Al terminar vuelves al mapa en el mismo sitio. Los proyectos originales no se
han modificado: todo está copiado aquí.

**El nivel principal es el hospital abandonado** (`START_MAP` en
`game/settings.py`): el juego arranca en la caverna que hay delante del
hospital (`hospital_exterior`). El Bosque de Arken sigue
disponible (`python main.py maps/forest.json`).

Hay una **segunda versión**, la **Aldea del vacío** (`python main_aldea.py` o
`jugar_aldea.bat`; ver más abajo): otra dungeon con el **mismo código**, que
empieza en la aldea y guarda su mazo aparte. Los cambios de gameplay (cartas,
personajes, combate) valen para las dos.

> *"La historia te lleva por el mundo; la exploración te recompensa por desviarte."*

## Instalación

Requiere Python 3.9 o superior.

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py                        # el hospital (o doble clic en jugar.bat)
python main_aldea.py                  # la Aldea del vacío (o doble clic en jugar_aldea.bat)
python main.py maps/forest.json       # el Bosque de Arken
python main.py ruta/a/mi_mapa.json    # jugar un mapa concreto (p. ej. del diseñador de niveles)
python combate/main.py                # el duelo de cartas PvP original (2 jugadores, menú y editor de mazos)
```

Los mapas se pueden dibujar con el diseñador visual de la carpeta
`disenador-de-niveles/` (ver su `LEEME.md`); ya sabe colocar **enemigos**.

### Ejecutables para Windows

Cada versión tiene su propio `.exe` de un solo archivo (no necesitan Python ni
nada instalado; se publican en las *releases* de GitHub):

| Ejecutable | Versión | Mapas que lleva | Mazos |
|---|---|---|---|
| `dist/HospitalAbandonado.exe` | El hospital | `hospital_*.json` + `elevators.json` | `decks_hospital.json` |
| `dist/AldeaDelVacio.exe` | La Aldea del vacío | `aldea.json` | `decks_aldea.json` |

Los dos llevan `assets/`; el bosque y el duelo PvP no entran. Para regenerarlos:

```bash
pip install pyinstaller
python tools/build_exe.py            # HospitalAbandonado.exe
python tools/build_exe.py --aldea    # AldeaDelVacio.exe
```

Si junto al `.exe` existe una carpeta `maps/` o `assets/`, se usa esa en lugar
de la empaquetada. Los mazos editados se guardan junto al `.exe`.

Pruebas automáticas (sin ventana):

```bash
python tests/smoke_test.py            # exploración del bosque (sin enemigos)
python tests/hospital_test.py         # el hospital entero: menú de pausa, combates, pasivas de los enemigos
python tests/battle_test.py           # exploración + combate: encuentros, partida completa, huir, perder, ganar
python tests/aldea_test.py            # la Aldea del vacío entera: fases, almas, jefe y easter eggs
cd combate/tests && python -m unittest   # las pruebas de reglas del combate (test_hospital.py: Taunt, pasivas de enemigos)
# --shots en cualquiera de los tres primeros guarda capturas en tests/shots/
```

## Controles

| Acción                      | Teclado              | Gamepad          |
|-----------------------------|----------------------|------------------|
| Moverse (8 direcciones)     | WASD / flechas       | Stick izq. / cruceta |
| Interactuar / hablar        | E                    | A                |
| Avanzar / cerrar diálogo    | E / Enter            | A / B            |
| Menú de pausa (personaje y mazo) | TAB             | Start            |
| Modo debug                  | F3                   | Back / Select    |
| Salir                       | Esc                  | (n/a)            |

**Menú de pausa (TAB)**: congela el mundo. `W`/`S` eligen fila, `A`/`D`
cambian el valor y `TAB` / `ESC` vuelven al juego.

- **Personaje**: Hero, Blaze o Jurgenoid (los personajes jugables), con su pasiva de combate y su habilidad de aventura.
- **Mazo**: cualquier mazo del jugador (los de fábrica y los creados con el
  editor de `python combate/main.py`), con sus cartas a la vista.
- **Editar mazos** (`ENTER`): abre el editor de mazos del combate dentro del
  juego. Puedes crear mazos nuevos, duplicar uno, cambiar sus cartas (clic en
  el catálogo para añadir, clic derecho para quitar), renombrar los tuyos,
  restaurar los de fábrica y borrar los propios. **GUARDAR** exige 10 cartas.
  Al volver (`ESC`), el mazo que tenías abierto queda elegido. Se guarda en
  `combate/decks.json` (el mismo archivo que usa el duelo PvP). Las cartas
  exclusivas de enemigos no salen en el catálogo.

La elección vale para el siguiente combate y se guarda en la partida.

En combate (eres el jugador 1; el enemigo lo juega la IA y su mano va boca abajo):

| Acción | Tecla |
|---|---|
| Elegir carta 1-5 (o cambiarla en la fase de cambios) | `1` `2` `3` `4` `5` (o clic) |
| PASS | `ESPACIO` |
| Definitiva (en rango S de Estilo) | `6` |
| Confirmar / acelerar animación | `ENTER` |
| Huir (si el enemigo lo permite) | `ESC` |
| **Registro del combate** (pausa el combate) | `TAB` (se cierra con `TAB` o `ESC`; `W`/`S`, flechas o rueda para desplazar) |
| Al terminar: CONTINUAR (volver al mapa) | `ENTER` |

El **registro** muestra todo el combate turno a turno: qué jugó cada uno
(con su SPECIAL), por qué ganó quien ganó, el daño, la Stability, el combo, los
estados y lo que pasa al empezar cada turno (BURN, POISON, la Alerta de los
drones...). Mientras está abierto, el combate se detiene.

**PASS** es literalmente pasar turno: no haces nada y la carta del rival se
resuelve entera (daño, hit y desestabilizar). También cuando el PASS es
automático por falta de Mana o cartas, u obligatorio por PARALYZE o SLEEP.

Las reglas completas del combate están en `combate/README.md`.

## Avatares

Cada personaje jugable puede tener su propio **avatar**: el sprite con el que
se le ve al explorar (y en el recuadro del menú de pausa). Cambia en cuanto
eliges otro personaje en la pausa.

| Personaje | Avatar |
|---|---|
| **Blaze** | Propio: chaqueta roja, bufanda naranja, pelo en punta como una llama y fuego en la mano |
| **Hero** | El avatar por defecto (el aventurero de azul y bufanda roja), por ahora |
| **Jurgenoid** | Propio: caballero no muerto **de viento** inspirado en Vaseraga (*Granblue Fantasy*): orejas erune, pelo plateado, ojos que brillan, armadura pesada con hombreras, guadaña gigante y capa hecha jirones, en jade y blanco |

Se define con `avatar=` en `Character` (`combate/game/characters.py`);
`None` = el avatar por defecto (`player`). La clave de imagen es
`<avatar>_<dirección>_<paso>` (p. ej. `avatar_blaze_left_1`): los dibuja
`render/placeholders.py` (`avatar()`), o un PNG en `assets/` con ese nombre.

## Habilidades de aventura

Cada personaje jugable tiene, además de su pasiva de combate, una **habilidad
de aventura** para el mapa. No hay un botón para usarla: al acercarte a un
objeto preparado para ella, si llevas a ese personaje (menú de pausa, TAB),
aparece el indicador **E** y la usas como cualquier otra interacción. Con el
otro personaje, el objeto no ofrece nada.

| Personaje | Habilidad | Objeto del mapa | Qué hace |
|---|---|---|---|
| **Blaze** | Quemar | Pared de hojas o maraña de raíces (`leaf_wall`, `"style": "roots"`) | La quema: arde un momento y deja el paso libre (se recuerda al cambiar de mapa) |
| **Hero** | Saltar | Punto de salto (`jump_spot`, losa con flecha) | Salta en arco por encima de muros hasta su `target` |

En la caverna de delante del hospital (`hospital_exterior`):
- **Maraña de raíces** al este de la caverna: detrás hay un rincón con un cofre (Éter).
- **Plataforma alta** de roca junto a la entrada: solo se llega saltando con
  Hero desde la losa de abajo; dentro hay un cofre (Insignia de héroe) y otra
  losa para bajar.

En el JSON del mapa (o con el diseñador, grupo «Habilidades de aventura»):

```json
{ "type": "leaf_wall", "id": "hojas_1", "rect": [x, y, w, h], "height": 70 },   // "style": "roots" en cuevas
{ "type": "jump_spot", "id": "salto_1", "pos": [x, y], "target": [x, y], "verb": "Saltar arriba" }
```

La zona de detrás de la pared o la de destino del salto debe ser `walkable`,
pero sin otro acceso. Para el salto, pon otra losa dentro para volver.
**Una habilidad nueva**: `adventure="..."` en el personaje
(`combate/game/characters.py`) y un interactuable con
`requires_ability = "..."` (ver `entities/adventure.py`).

## Combate en el mapa

- **Encuentro**: los enemigos deambulan, patrullan o esperan quietos. Si te
  ven cerca, te persiguen (más despacio que tú: se pueden esquivar). Al
  tocarte, o si les hablas con `E` («Luchar»), la pantalla funde a negro y
  empieza el combate. Algunos dicen algo antes (`intro`).
- **Victoria**: el enemigo desaparece del mapa para siempre (se recuerda al
  cambiar de mapa), te da su recompensa si la tiene y puede desbloquear un
  secreto (el Elemental Wolf abre la verja del tesoro).
- **Derrota**: vuelves al punto por el que entraste al mapa y los enemigos
  regresan a su sitio. No se pierde nada.
- **Huir** (`ESC`) o **empate**: vuelves al mapa donde estabas y el enemigo
  tarda 3 s en volver a atacar. Los jefes no dejan huir.
- Cada combate empieza de cero (100 HP, 3 de Mana), como en el duelo original.
- **El escenario**: en el centro de la pantalla hay un suelo con los dos
  personajes encima (tu avatar a la izquierda; el enemigo, con su sprite del
  mapa, a la derecha) y, a cada lado, la carta que ha jugado cada uno.
  Ver «Escenario y animaciones» en `combate/README.md`.
- **Tu mazo y personaje**: el personaje se cambia en el menú de pausa (TAB).
  Mazo solo hay uno, `hospital` (`HOSPITAL_DECK` en `game/settings.py`), que se
  edita desde la pausa; ver «Mazo y cartas en el hospital» más abajo.

### Personajes

Los enemigos son **personajes como los jugables**: cada uno tiene su ficha
(`Character`) y su pasiva, que se ve bajo su HUD en el combate. La diferencia
es que tienen `playable=False`: nunca salen en el menú de pausa ni en el menú
del duelo PvP. Todo está en `combate/game/characters.py`.

| Personaje | Jugable | Pasiva |
|---|---|---|
| **Hero** | Sí | Impulso consecutivo: 2º HIT +5%, 3º +10%, Mega Combo +15% |
| **Blaze** | Sí | Afinidad ígnea: cartas de FUEGO +10% de daño |
| **Jurgenoid** | Sí | **Undead**: cada HIT recibido le da una marca (duran todo el combate); al empezar cada turno se cura 0.5% de su vida máxima por marca (1 marca = 1 HP, 2 = 1, 3 = 2, 4 = 2...: medios hacia arriba). Un golpe de 2 HIT da 2 marcas. Sin habilidad de aventura por ahora |
| Dron de seguridad | No | **Alerta**: cada 3 turnos (turnos 3, 6, 9...) lanza una señal de alerta al empezar el turno y te deja UNSTABLE |
| Elemental Wolf | No | **Afinidad elemental**, ver abajo |
| Herrero, Granjero, Vendedor | No | **Corrupted**: a 0 HP recuperan el 50% de su vida y se transforman; transformados, cada HIT que te hacen te quita 1 de Mana máximo. Ver «Aldea del vacío» |
| Void Insect | No | **Part of the void**, **Void breeding** y **Void consumption** (jefe de la aldea). Ver «Aldea del vacío» |

**Elemental Wolf** (jefe de la azotea). Está siempre en **MODO FUEGO** o
**MODO HIELO** (empieza en FUEGO) y cambia con sus cartas exclusivas:

- **Si le haces HIT con una carta ATTACK** te infliges **BURN** (modo FUEGO)
  o **FREEZE** (modo HIELO). Las MAGIC y BREAK no son de contacto: no castigan.
- **Daño de su mismo elemento**: le **cura** esa cantidad (hasta su vida máxima).
- **Daño del elemento contrario**: **x1.5** (se aplica después de la pasiva del
  atacante: Blaze con Fire Bolt en modo HIELO hace 10 → 11 → 17).
- **Daño de cartas sin elemento o de otro elemento** (Attack, Break, Magic...):
  **x0.5**, medios hacia arriba (10 → 5). El Mega Combo no es daño de una
  carta: le hace el daño normal.

Su mazo (`ENEMY_DECKS["elemental_wolf"]`) lleva cuatro cartas **exclusivas**:

| Carta | Tipo | Efecto |
|---|---|---|
| Infernal Shift | SPECIAL | Al revelar: pasa a MODO FUEGO (antes del enfrentamiento) |
| Glacial Shift | SPECIAL | Al revelar: pasa a MODO HIELO |
| Flame Fang | ATTACK · FIRE | 10 de daño; al jugarla pasa a MODO FUEGO |
| Frost Fang | ATTACK · ICE | 10 de daño; al jugarla pasa a MODO HIELO |

Las cartas exclusivas (`ENEMY_CARD_DATA`) no salen en el catálogo del editor
y no se pueden meter en un mazo del jugador. Los mazos de enemigos
(`ENEMY_DECKS`) tampoco salen en los menús.

### Cartas y mazo nuevos para el jugador

| Carta | Tipo | Efecto |
|---|---|---|
| **Taunt** | SPECIAL (1 Mana) | Solo gana **10 puntos de Estilo**. No cuenta como victoria, no cambia la racha |
| Ice Shard | MAGIC · ICE | Como Magic, con elemento HIELO (para la debilidad del lobo) |
| **Heal** | SPECIAL (1 Mana) | Recuperas **30 de vida**. Disponible desde el principio (en las dos versiones) |
| **Void Impact** | ATTACK · VOID | 10 de daño; al jugarla pierdes 15 HP y quedas UNSTABLE; si gana, PARALYZE al rival y recuperas Stability. Se forja en el yunque de la aldea. Ojo: al Void Insect le **cura** |

Mazo `elemental` (sigue existiendo para el duelo PvP; en el hospital no se usa):
Attack x2, Fire Bolt, Ice Shard x2, Break, Guard, Perfect Guard, Recover y Taunt.

**Mazo y cartas en el hospital** (`game/settings.py`): en la exploración solo
hay **un mazo**, `hospital` (Attack, Guard, Break, Magic, Perfect Guard, Recover,
Taunt, Stun Guard, Revenge y Overdrive). Se edita desde la pausa (TAB > Editar
mazos), pero no se pueden crear, duplicar, renombrar ni borrar mazos, y **no se
pueden repetir cartas** en el mazo. Eso solo afecta a montar el mazo: en combate,
cuando se acaba el mazo, los descartes se barajan y una carta puede volver a salir.
Se guarda en `decks_hospital.json`, aparte de los mazos del duelo PvP
(`combate/decks.json`), que siguen como siempre.

Cartas **disponibles** (`AVAILABLE_CARDS`): las diez del mazo más Heavy Blow,
Venom Strike y Heal. **Todas las demás están bloqueadas** (en gris, «BLOQUEADA», en el
editor). Algunas se consiguen en cofres del hospital: **Ice Shard** al fondo del
Piso 1 y **Fire Bolt** al fondo del Piso 2 (`"card": "ice_shard"` en el cofre).

### Enemigos

| Enemigo | Dónde | Personaje / mazo |
|---|---|---|
| Dron de seguridad | Hospital, lobby y piso 1 | Dron de seguridad (Alerta), mazo `security_droid`, 60 HP |
| **Fire Wolf** | Hospital, piso 2 (deambula) | Fire element: el FUEGO le cura, el HIELO le hace daño normal, el resto la mitad; mazo `fire_wolf` (Fire Bolt x2, Flame...), 100 HP |
| **Ice Wolf** | Hospital, piso 3 (deambula) | Ice element: el HIELO le cura, el FUEGO le hace daño normal, el resto la mitad; mazo `ice_wolf` (Ice Shard x2, Frost Guard...), 100 HP |
| **Elemental Wolf** (jefe) | Hospital, piso 4 | Elemental Wolf, mazo `elemental_wolf`, 100 HP, sin huida |
| Lobo gris | Bosque, camino principal | Sin personaje; ofensivo (Attack, Overdrive, Heavy Blow), 50 HP |
| Seta venenosa | Bosque, desvío del cofre | Sin personaje; envenena (Venom Strike) y duerme (Lullaby), 50 HP |
| Lobo alfa | Bosque, camino este (patrulla) | Pasiva Hero; ofensivo, 80 HP, deja un colmillo |
| Seta ancestral | Bosque, ruinas | Sin personaje; como la seta, 80 HP |

Los enemigos del bosque no se han tocado en esta versión (el foco es el hospital).

### Cómo añadir un enemigo

Solo datos, en la lista `interactables` del mapa (o con el diseñador):

```json
{ "type": "enemy", "id": "lobo_2", "name": "Lobo gris", "sprite": "wolf_grey", "pos": [900, 1000],
  "deck": ["attack", "attack", "attack", "break", "break", "guard", "guard", "overdrive", "heavy_blow", "revenge"],
  "hp": 60, "character": null, "aggression": 0.5, "randomness": 0.6,
  "behavior": "wander", "radius": 120, "aggro": 170, "speed": 80,
  "intro": ["Te gruñe."], "victory": ["Huye entre los árboles."],
  "unlocks_secret": null, "reward": { "item": "colmillo", "name": "un Colmillo" },
  "can_flee": true }
```

- `deck`: lista de 10 ids de carta o el nombre de un mazo (`"duelo"`, `"estados"`... o de enemigo: `"security_droid"`, `"elemental_wolf"`).
- `character`: su personaje (pasiva). Para un enemigo nuevo con pasiva propia: `register_character(Character(..., playable=False))` en `combate/game/characters.py`.
- `behavior`: `"wander"` (pasea dentro de `radius`), `"patrol"` (recorre `"patrol": [[x, y], ...]`) o `"guard"` (quieto).
- `aggro`: distancia a la que te persigue (`0` = solo hay combate si lo tocas o le hablas).
- `aggression` (−1 defensiva … 1 agresiva) y `randomness` (0 = siempre su mejor jugada) ajustan la IA (`combate/game/ai.py`).
- `sprite`: `wolf_grey`, `shroom`, `npc_droid`, `wolf_ghost`, o cualquier PNG de `assets/` (p. ej. `assets/goblin.png` → `"sprite": "goblin"`).

## Aldea del vacío (segunda versión)

`python main_aldea.py`, `jugar_aldea.bat` o `AldeaDelVacio.exe`. Velmora es una
aldea destruida, en llamas: un **insecto del vacío** ha dejado **huecos** a sus
habitantes (no están muertos) y está abriendo un **portal en el cielo**. El mapa
(`maps/aldea.json`) lo genera `python tools/generar_aldea.py`; la misión está en
`systems/village_quest.py` y sus objetos en `entities/village.py`.

**El mapa cambia con cada paso de la misión** (fases; ver «Mapas con fases»):

| Fase | Qué hay que hacer | Cómo cambia el mapa |
|---|---|---|
| 1 · Los relojes | En la plaza hay **12 activadores del vacío**, uno por hora del reloj. En **3 casas** hay un **diario** con una hora: esas son las posiciones (14:00 = el 2, 9:00 = el 9, 0:00/12:00 = el 12). Hay que activar las tres, en cualquier orden; **una equivocada las apaga todas** | Barricadas en llamas cierran la granja, la herrería y el mercado; fuente seca en la plaza |
| 2 · Las almas | Cada **herrero / granjero / vendedor** vencido da su **alma** (solo se lleva **una** a la vez; arriba a la izquierda se ve cuál). Hay que llevar **3 almas** de cada oficio a su **círculo del vacío**: herrero → herrería, granjero → granja, vendedor → mercado. **Un alma equivocada hace escapar todas las de ese círculo** | Se apagan las llamas; desaparecen los activadores; grietas del vacío en la plaza; aparecen los tres círculos |
| 3 · El portal | Con **Hero** se salta de roca en roca (habilidad Saltar) hasta el portal. El **Void Insect** está tras una **barrera**: para romperla hace falta la carta **Void Impact**, que se forja en el **yunque** de la herrería con **3 partes del insecto** (pata, ala y aguijón) escondidas en **casas al azar**. Rota la barrera, se lucha con él (sin huida) | Los círculos se vuelven cristales; aparecen las **rocas flotantes** y los puntos de salto; las partes aparecen en las casas |
| 4 · Fin | — | El portal se cierra y se apagan los fuegos |

Los aldeanos **vuelven a aparecer** 40 s después de vencerlos (si estás lejos), así
que nunca faltan almas. Son enemigos normales: deambulan, te persiguen y se puede huir.

**Easter eggs** (siempre disponibles, en cualquier fase; las casas, barriles, pozos y
el gallinero no se cierran nunca):

1. **Peluches**: en 3 casas al azar hay un peluche con aura del vacío. Tocar los tres en
   la misma partida: «Alguien te observa» (por ahora solo eso).
2. **El pollo**: en el gallinero queda un único pollo. Cógelo (E) y llévalo a las
   **semillas del vacío** que hay en **3 barriles al azar** (hay que romperlos; por
   toda la aldea hay 14). Con las tres, **muta en un pollo humanoide y huye**. Si
   empieza un combate mientras lo llevas, **huye de vuelta al gallinero** (las
   semillas que ya se comió cuentan).
3. **El pozo**: hay 3 pozos; en uno al azar, a la **3ª vez** que te asomas la pantalla
   se pone negra unos segundos y vuelves al principio: «Buen intento».

Todo lo aleatorio (horas, casas de diarios / peluches / partes, barriles, pozo) **cambia
en cada partida** (`VILLAGE_SEED` en `game/settings.py` lo fija para las pruebas).

### Enemigos de la aldea

| Enemigo | Dónde | Personaje / mazo |
|---|---|---|
| **Herrero** | Herrería y calles | Corrupted; mazo `herrero` (martillazos, chispas de la forja, acero templado), 100 HP |
| **Granjero** | Granja y calles | Corrupted; mazo `granjero` (horca, guadaña, cosecha podrida, Harvest), 100 HP |
| **Vendedor** | Mercado y calles | Corrupted; mazo `vendedor` (monedas, regateo, sobornos), 100 HP |
| **Void Insect** (jefe) | La roca más alta, junto al portal (quieto, tras su barrera) | Void insect; mazo `void_insect` (aguijones y zumbidos que quitan Mana máximo), 100 HP, sin huida |

Detalles de las pasivas y las cartas en `combate/README.md` («Personajes» y «Cartas»).

### Mapas con fases

Un mapa con `"phase_flag": "<flag>"` cambia según `GameState.get_flag(flag)`.
Cualquier zona caminable (`{"rect": [...], "phases": [3, 4]}`), muro, obstáculo,
decoración, interactuable, trigger o área / camino / detalle del suelo puede llevar
`"phases": [...]`: solo existe en esas fases. Al cambiar la fase, `GameMap.apply_phase`
rehace la colisión y el juego repinta el suelo (`Game.on_phase_changed`); si algo
sólido aparece encima del jugador, se le aparta. Objetos nuevos (`entities/village.py`):
`phase_block` (llamas / cristales que cierran un paso), `clock_activator`,
`village_item` (diario, peluche o parte en una casa), `void_circle`, `anvil`,
`void_barrier`, `barrel`, `chicken` y `well`. Enemigos: `"respawn": segundos`,
`"soul": "herrero"` y `"requires_secret"` (no hay combate hasta desbloquearlo).

## Qué hay en el mapa

```
                   [ÁREA SECRETA]  (oculta bajo el follaje)
                         | puerta con hiedra
                     [RUINAS]
                         |
[ENTRADA] ── camino ── [NPC Brann] ──── camino ──── [SALIDA → Aldea]
                         |                    |
             [COFRE] ── desvío ── [Mira]   [RADIO] (rincón "inútil")
                         |
                 [VERJA CERRADA] (escaleras al otro lado)
```

- **Ruta principal**: camino ancho y claro de oeste a este. Se puede terminar
  el mapa sin hacer nada más.
- **Desvíos**: senderos más estrechos y con hierba. El del sureste casi no se
  ve: solo unas pisadas.
- **Secreto**: habla con la radio 4 veces → *"Has descubierto algo oculto..."* →
  el muro con hiedra de las ruinas se abre → la zona secreta se revela al entrar.

## Nivel de prueba: hospital abandonado

Inspirado en las Ruinas del Hospital Antiguo de *Blue Dragon* (estructura y
mecánicas; textos, nombres y gráficos propios). Para jugarlo: doble clic en
`jugar_hospital.bat`, o `python main.py maps/hospital_exterior.json`.

Cada puerta, escalera o viaje en ascensor **cambia de escena** (fundido).

| Mapa | Contenido |
|---|---|
| `hospital_exterior` | **Caverna** con la fachada del hospital: cofre de la entrada, **maraña de raíces** (Blaze), **plataforma alta** (Hero), charca de cristales. El túnel del sur está **derrumbado**: no se puede volver atrás |
| `hospital_lobby` | Con luz, solo **drones**. Ascensor en el centro. Ala este (energía del lobby y palanca del portón) solo se alcanza bajando desde el Piso 1. **Sala del personal** cerrada (cuarto secreto) |
| `hospital_piso1` | A oscuras, solo **drones**. Ala oeste aislada por derrumbes; en el centro y el este: energía, Quick Revive y, al fondo, la carta **Ice Shard** |
| `hospital_piso2` | A oscuras, **Fire Wolves**. Al llegar no se puede alcanzar su energía: hay que subir al Piso 3 y bajar por otra escalera. Al fondo, la carta **Fire Bolt**; Juggernog |
| `hospital_piso3` | A oscuras, **Ice Wolves**. Un rellano con dos escaleras de bajada; el resto (energía, Speed Cola) se alcanza desde el Piso 2 |
| `hospital_piso4` | Solo en ascensor, cuando están activas **todas** las energías (y entonces tiene luz). **Elemental Wolf**; tras su verja, la **llave de acceso** al cuarto secreto. Double Tap |

**Recorrido**: Lobby (entrada) → escalera al Piso 1 (ala oeste) → baja al ala este
del Lobby (energía + palanca que abre el portón hacia la entrada) → sube al Piso 1
(centro: energía, Ice Shard) → Piso 2 (sin acceso a su energía) → rellano del
Piso 3 → baja al otro lado del Piso 2 (energía, Fire Bolt) → sube al Piso 3
(energía) → ascensor al Piso 4 → Elemental Wolf → llave → cuarto secreto.

**Ascensor y energía**: cada piso tiene un **activador de energía** (cuadro
eléctrico). Sin él, el ascensor de ese piso no funciona; en los pisos 1-3 además
enciende las luces. El ascensor abre un menú con los pisos y solo deja ir a los
que tienen corriente. El Piso 4 pide las cuatro energías (lobby y pisos 1-3).
Los pisos y lo que pide cada uno están en `maps/elevators.json`.

**Máquinas de ventajas** (homenaje a las perks de los zombis de *Black Ops*):
Quick Revive (piso 1), Juggernog (piso 2), Speed Cola (piso 3) y Double Tap
(piso 4). En el **ordenador** del cuarto secreto sale una secuencia con los números
del 1 al 4 (p. ej. `2413`, **aleatoria: cambia en cada partida**): es el orden de los pisos en
que hay que encenderlas. Si te equivocas, se apagan todas. Con las cuatro en
orden, la máquina **Pack-a-Punch** del cuarto secreto da una *Lata de
Pack-a-Punch* (de momento es solo un objeto: falta decidir para qué sirve).
`PERK_SEQUENCE` en `game/settings.py` fija la secuencia (pruebas).

**Generador**: los cinco pisos los crea `python tools/generar_hospital.py`
(rejilla de 3 x 3 salas por piso; qué pasos están abiertos, derrumbados o
cerrados, y dónde va cada cosa). Para cambiar el diseño es más cómodo tocar ese
script y volver a ejecutarlo (sobrescribe los JSON del hospital, no el de la
caverna).

`python tests/hospital_test.py` lo juega entero y comprueba con un buscador de
caminos (`tests/pathing.py`) que los pasos bloqueados lo están de verdad.

Novedades del motor que estrena: salas a oscuras con halo de luz
(`hidden_areas` con `"style": "dark"` + `"secret"`), mapas de interior
(`"ground": {"background": "void"}` y sin `forest`), suelo `tiles`, paredes
`hospital`, puertas `metal`, `secret_door` con `style`, objetos secretos con
`verb` y `vanish`, y mobiliario (`bed`, `cabinet`, `rubble`).

Cuevas (`hospital_exterior`): `"ground": {"theme": "cave"}` pinta roca oscura
fuera de las zonas caminables y tierra de cueva dentro, con viñeta más oscura;
`"forest": {"style": "cave"}` rellena con estalagmitas y rocas en vez de
árboles (`pine_ratio` = proporción de estalagmitas). Elementos nuevos:
`stalagmite`, `cave_rock`, `crystal` (sólidos), `glowshroom` (decoración),
muros `"style": "cave"`, caminos `"style": "cave"` y detalle de suelo `puddles`.

## Estructura del proyecto

```
main.py                     punto de entrada (jugar.bat: doble clic)
main_aldea.py               punto de entrada de la Aldea del vacío (jugar_aldea.bat)
game/
  game.py                   bucle principal; también es el "contexto" de interacción
  battle_scene.py           combate dentro de la exploración (usa combate/)
  deck_scene.py             editor de mazos dentro de la exploración (usa combate/)
  settings.py               todos los valores ajustables
  camera.py                 cámara con suavizado y límites
  input.py                  teclado/gamepad → acciones
entities/
  entity.py                 Entity (punto base, hitbox, sprite) y RectEntity
  player.py                 movimiento en 8 direcciones
  interactable.py           clase base Interactable
  npc.py, chest.py, door.py, sign.py, secret_object.py
  enemy.py                  enemigo del mapa: se mueve, te persigue y abre el combate
  adventure.py              objetos de habilidades de aventura: pared de hojas (Blaze), punto de salto (Hero)
  hospital.py               ascensor, máquinas de ventajas, pintada con la secuencia, Pack-a-Punch
  village.py                objetos de la Aldea del vacío (reloj, círculos, yunque, barrera, pollo...)
  props.py                  árboles, rocas, muros (definidos como datos)
world/
  map.py                    GameMap (walls, obstacles, interactables, exits, secrets...)
  map_loader.py             JSON → GameMap, registro de tipos
  collision.py              rejilla de colisión + move_and_collide
  transition.py             MapTransition, TriggerZone, HiddenArea
  forest.py                 relleno procedural del bosque denso
systems/
  interaction_system.py     elige el objeto con el que interactuar
  secret_system.py          registro global de secretos
  game_state.py             flags, inventario provisional, estado por mapa
  perk_puzzle.py            puzle de las máquinas de ventajas
  village_quest.py          misión de la Aldea del vacío por fases y sus easter eggs
render/
  assets.py                 AssetManager (PNG o placeholder)
  placeholders.py           gráficos provisionales (solo dibujo)
  village_sprites.py        gráficos provisionales de la aldea (aldeanos huecos, Void Insect...)
  ground.py                 pinta el suelo una vez
  renderer.py               orden por Y, sombras, transparencias, follaje
ui/
  dialogue.py, interaction_prompt.py, notification.py, debug_overlay.py, text.py
  pause_menu.py             menú de pausa (TAB): personaje, mazo y editor de mazos
  choice_menu.py            menú de elección (pisos del ascensor)
maps/
  forest.json               el Bosque de Arken
  hospital_*.json           el hospital abandonado (hospital_exterior: la caverna; el resto, generados)
  elevators.json            pisos del ascensor y la energía que pide cada uno
  aldea.json                la Aldea del vacío (generada)
assets/                     PNG opcionales (ver assets/README.md)
combate/                    el proyecto combate-cartas, como paquete (ver combate/README.md)
  game/ai.py                IA de los enemigos (nuevo)
  game/characters.py        personajes jugables y de enemigos, con sus pasivas
  main.py                   el duelo PvP original, con menú y editor de mazos
disenador-de-niveles/       editor visual de mapas (HTML)
tests/
  smoke_test.py             exploración
  hospital_test.py          el hospital entero
  aldea_test.py             la Aldea del vacío entera
  pathing.py                buscador de caminos de las pruebas (¿se puede llegar de A a B?)
tools/
  generar_hospital.py       genera los pisos del hospital
  generar_aldea.py          genera la Aldea del vacío
  build_exe.py              genera dist/HospitalAbandonado.exe (o AldeaDelVacio.exe con --aldea)
  battle_test.py            exploración + combate
```

**Cómo se unen los dos proyectos**: la exploración no sabe nada de cartas.
`Enemy` solo llama a `ctx.start_battle(self)`. `Game` congela el mapa y crea
una `BattleScene`, que es la `App` del combate (`combate/game/game.py`) sin su
ventana ni su menú: mismo motor, mismas animaciones y misma pantalla. El
jugador 2 lo controla `CardAI` y la pantalla oculta su mano
(`View.ai_players`). Al terminar, `BattleScene.result` (`win`, `lose`,
`draw`, `flee`) decide qué pasa en el mapa (`Game._end_battle`).

Cambios respecto a los originales: los imports del combate llevan el prefijo
`combate.` (para no chocar con los paquetes `game` y `ui` de la exploración),
`combate/ui/battle_screen.py` admite jugadores de la IA y un botón CONTINUAR,
el centro de la pantalla es un escenario con los personajes animados
(`combate/ui/fighters.py`; `View.fighter_keys` elige el sprite de cada uno)
y los mapas tienen enemigos. Todo lo demás es igual.

**Orden de cada frame** (`Game.step` / `Game.draw`): input → jugador → colisión →
detección de interacción → mundo → cámara → render → UI.

**Separación lógica/render**: las entidades solo exponen posición y clave de
sprite. Solo `render/` sabe cómo se dibujan.

### Conceptos clave

- **Coordenadas**: todo vive en coordenadas de mundo. La cámara convierte con
  `screen = world - camera`. Ver `Camera.world_to_screen`.
- **Punto base**: `(x, y)` de una entidad es el centro de sus pies. Se usa para
  ordenar la profundidad (`sort_y`) y la hitbox se apoya ahí. El sprite puede
  ser mucho más grande que la parte sólida.
- **Bosque**: el mapa declara las zonas *caminables* (`walkable`); todo lo demás
  es bosque denso, sólido y relleno de árboles automáticamente.
- **Contexto de interacción**: `interact(self, ctx)` recibe el `Game`, que ofrece
  `ctx.show_dialogue(...)`, `ctx.notify(...)`, `ctx.unlock_secret(...)`,
  `ctx.secrets`, `ctx.state`, `ctx.world` y `ctx.player`.

## Cómo añadir un nuevo NPC

Solo datos. En la lista `interactables` del mapa:

```json
{ "type": "npc", "id": "herrera", "name": "Olga, la herrera", "look": "default",
  "pos": [900, 1000],
  "dialogue": ["Primera vez que hablas con ella.", "Segunda página."],
  "repeat_dialogue": ["Lo que dice las siguientes veces."],
  "conditional_dialogue": [
    { "requires_secret": "arken_shrine", "pages": ["Dice esto si el secreto está desbloqueado."] }
  ] }
```

Para un aspecto nuevo: añade una entrada a `NPC_LOOKS` en
`render/placeholders.py` o guarda `assets/npc_<look>.png`.

## Cómo añadir un nuevo interactuable

1. Crea la clase heredando de `Interactable`:

```python
# entities/lever.py
from entities.interactable import Interactable

class Lever(Interactable):
    prompt_verb = "Usar"

    def __init__(self, x, y, obj_id, flag):
        super().__init__(x, y, obj_id, "Palanca", "lever_off", hitbox=(20, 12))
        self.flag = flag
        self.on = False

    def interact(self, ctx):
        self.on = not self.on
        self.sprite_key = "lever_on" if self.on else "lever_off"
        ctx.state.set_flag(self.flag, self.on)
        ctx.notify("Se oye un mecanismo a lo lejos...")

    def get_state(self):            # para que sobreviva al cambiar de mapa
        return {"on": self.on}

    def set_state(self, state):
        self.on = state.get("on", False)
        self.sprite_key = "lever_on" if self.on else "lever_off"

    @classmethod
    def from_data(cls, d):
        return cls(d["pos"][0], d["pos"][1], d.get("id"), d.get("flag", "lever"))
```

2. Regístrala en `world/map_loader.py`: `INTERACTABLE_TYPES["lever"] = Lever`.
3. Dale gráfico: `assets/lever_off.png` / `lever_on.png`, o una función en
   `render/placeholders.py` (en `make()`).
4. Colócala en el JSON: `{ "type": "lever", "id": "lever_1", "pos": [x, y], "flag": "puente" }`.

## Cómo añadir un secreto

1. Decláralo en `secrets` del mapa:

```json
{ "id": "cueva_oculta", "name": "Cueva oculta", "unlock_message": "Algo ha cambiado en el bosque..." }
```

2. Decide **qué lo desbloquea**. Cualquier código puede llamar a
   `ctx.unlock_secret("cueva_oculta")`. Por ejemplo un `secret_object` con
   `"unlocks_secret": "cueva_oculta", "unlock_stage": 3`.
3. Decide **qué cambia** al desbloquearse. Cualquier interactuable con
   `secret_id == "cueva_oculta"` recibe `on_secret_unlocked(ctx)`. Para una
   puerta basta con:

```json
{ "type": "secret_door", "id": "puerta_cueva", "secret": "cueva_oculta",
  "rect": [x, y, 80, 40], "hidden_text": "Unas raíces enormes tapan algo." }
```

   Los NPC pueden cambiar su diálogo con `conditional_dialogue`, y los
   `triggers` pueden exigir `"requires_secret"`.
4. (Opcional) Oculta la zona con follaje hasta que se pise:
   `"hidden_areas": [{ "rect": [...] }]`, y anuncia la llegada con un trigger:
   `{ "rect": [...], "message": "Área secreta descubierta.", "style": "discovery" }`.

Recuerda que la zona tras la puerta también debe estar en `walkable`, igual
que el hueco de la propia puerta (la puerta cerrada es la que bloquea).

Los secretos son **globales**: un secreto de un mapa puede afectar a otro.

## Cómo crear un nuevo mapa

1. Crea `maps/village.json` (el `id` debe coincidir con el nombre del archivo):

```json
{
  "id": "village",
  "name": "Aldea de Vell",
  "size": [1600, 1000],
  "spawns": { "default": [100, 500], "from_forest": [100, 500] },
  "walkable": [[0, 300, 1600, 400]],
  "forest": { "seed": 1 },
  "ground": { "paths": [{ "style": "main", "width": 110, "points": [[0, 500], [1600, 500]] }] },
  "walls": [], "obstacles": [], "decorations": [], "interactables": [],
  "secrets": [], "triggers": [], "hidden_areas": [],
  "exits": [{ "rect": [0, 300, 20, 400], "target_map": "forest", "target_spawn": "from_village" }]
}
```

2. Listo. La salida del Bosque de Arken ya apunta a `"target_map": "village",
   "target_spawn": "from_forest"`. Mientras `village.json` no existe solo muestra
   *"Has llegado al final de la zona."*; en cuanto existe, hace un fundido y
   carga la aldea. Los cofres abiertos y demás estado se conservan al volver.

Consejos de diseño para que la ruta principal se lea sola:
- Camino `"main"` ancho y claro para la ruta principal; `"trail"` estrecho para
  desvíos; `"faint"` (solo pisadas) para rincones secretos.
- Haz los desvíos cortos y con la entrada visible desde el camino principal.
- Usa F3 para ver colisiones (rojo), zonas de interacción (amarillo),
  triggers (cian) y salidas (magenta).

## Puntos de extensión previstos

| Sistema futuro     | Dónde engancharlo                                                    |
|--------------------|----------------------------------------------------------------------|
| Inventario         | `systems/game_state.py`: `Inventory` (hoy solo una lista de ids)     |
| Llaves             | `Door.key_id`: ya abre si `inventory.has(key_id)`                    |
| Guardado / carga   | `GameState.to_dict()`, `SecretSystem.get_state()`, `get_state/set_state` de cada interactuable |
| Diálogos ramificados | `NPC.pick_pages` / `DialogueBox`                                   |
| Quests             | `GameState.flags` + `TriggerZone` + callbacks `on_close` de diálogos |
| Combate / enemigos | **Hecho**: `entities/enemy.py` + `game/battle_scene.py` + `combate/` |
| Vida entre combates | hoy cada combate empieza con 100 HP; guardar el HP en `GameState` y pasarlo a `BattleScene.new_game` (la mesa de operaciones del hospital podría curar) |
| Elegir personaje y mazo | **Hecho**: menú de pausa (`ui/pause_menu.py`, TAB) |
| Editar mazos dentro del juego | **Hecho**: menú de pausa → Editar mazos (`game/deck_scene.py`) |
| Puzzles complejos  | heredar de `SecretObject` y sobrescribir `on_stage_reached`          |
