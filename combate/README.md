# Combate de cartas: prototipo PvP 1v1

Vertical slice de un sistema de combate por cartas con selección simultánea,
iniciativa, Stability, Mana y combos de hasta 3 hits. Python + Pygame, local
1v1 en el mismo teclado.

> **Juego una carta → vemos qué pasó → volvemos a elegir.** Tras cada
> interacción la pantalla explica **por qué** ganó quien ganó (`GUARD > ATTACK`,
> `ATTACK = ATTACK · PLAYER 1 STABLE > PLAYER 2 UNSTABLE`) y **qué pasó**
> (`sin hit`, `PLAYER 1 -> UNSTABLE`, `SIGUE: iniciativa de ATTACK`). Después
> vuelve sola a la selección de cartas. Nunca pregunta "¿continuar?".

## Instalación y ejecución

Requiere Python 3.9+.

```bash
pip install -r requirements.txt
python main.py              # o doble clic en jugar.bat
```

```bash
python main.py --deck starter          # el menú arranca con ese mazo para ambos
python main.py --p1 duelo --p2 laboratorio
python main.py --seed 42               # mismo orden de cartas (partida reproducible)
python main.py --sin-menu              # directo a la partida, sin menú
```

### Menú y editor de mazos

Al arrancar aparece un **menú**: eliges el **personaje** de cada jugador (`<` `>`
o `W`/`S` para J1 y flechas arriba/abajo para J2), su **mazo** (`A`/`D` para J1
y flechas izquierda/derecha para J2), **JUGAR** (`ENTER`) o **VER / EDITAR
MAZOS** (`M`).

En el **editor**:

- A la izquierda, todos los mazos: **FÁBRICA** (los de `cards/card_database.py`), **MODIF.** (de fábrica con cambios) y **PROPIO** (creados por ti).
- En el centro, el mazo que editas: nombre, `N / 10 CARTAS` y copias con `[-]` `[+]`.
- A la derecha, el **catálogo** con todas las cartas: clic para añadir, clic derecho para quitar; al pasar el ratón la ves en grande.
- **GUARDAR** (`ENTER`) solo funciona con 10 cartas exactas; **DESCARTAR** (`SUPR`) deshace. Si sales con cambios sin guardar, te pide confirmarlo.
- **NUEVO**, **DUPLICAR**; **RESTAURAR** vuelve un mazo de fábrica a su original y **BORRAR** elimina uno propio. Los de fábrica no se renombran (duplícalos); los propios sí (clic en el nombre y escribe).

Los cambios se guardan en **`decks.json`** en la raíz del proyecto; el código
de los mazos de fábrica no se toca. Si `decks.json` tiene un mazo inválido, se
ignora y el menú lo avisa. Al terminar una partida, **MENÚ / MAZOS** (`M`)
vuelve al menú; durante la partida, `ESC` también.

| Mazo | Cartas |
|---|---|
| `duelo` **(por defecto)** | 2 Attack, 2 Break, Guard, **Perfect Guard**, **Unbreakable Guard**, Revenge, Overdrive, **Recover** (SPECIAL) |
| `starter` | 3 Attack, 2 Guard, 2 Break, Perfect Guard, Revenge, Overdrive |
| `laboratorio` | Unbreakable Guard, Break Guard, Heavy Blow, Crescendo, Drain, Focus, Feint, Iron Stance, Desperation, Overdrive |
| `arcano` | Para probar **MAGIC**: 2 Magic, Fire Bolt, 2 Flame (SPECIAL), Attack, Break, 2 Guard, Recover |
| `estados` | Cartas de prueba de los **Status Effects**: Searing Break, Venom Strike, Stun Guard, Frost Guard, Lullaby + básicas y Recover |

El mazo por defecto se cambia en `DEFAULT_DECKS` (`game/config.py`).

## Controles

| Acción | Jugador 1 | Jugador 2 |
|---|---|---|
| Elegir carta 1-5 | `1` `2` `3` `4` `5` | `Q` `W` `E` `R` `T` |
| PASS | `ESPACIO` | `TAB` |
| Definitiva (en rango S) | `6` | `Y` |
| Confirmar | `ENTER` | `SHIFT izq.` |

- También con el **ratón**: clic en cartas y botones.
- **Cambios** (inicio de turno): pulsa una carta para descartarla y robar otra (máx. 2); confirma al terminar.
- **Selección**: tu elección no se marca en pantalla ("Elección hecha (oculta)"); puedes cambiarla hasta confirmar.
- **SPECIAL**: con las mismas teclas. Pulsar una carta SPECIAL (morada, como Recover) la añade a tu jugada; si la pulsas otra vez, la quitas. Pulsar cualquier otra carta, o PASS, elige tu acción principal. Después confirmas.
- Confirmar durante una animación la acelera. `R` / `ENTER`: revancha. `M`: menú. `ESC`: volver al menú (en el menú, salir).

## Escenario y animaciones

En el centro de la pantalla hay un **suelo** con los dos personajes encima
(jugador 1 a la izquierda, jugador 2 a la derecha, mirándose) y, a cada lado,
la carta que ha jugado cada uno (boca abajo mientras eligen, se voltea al
revelar). Debajo del suelo sale el POR QUÉ ganó. Lo dibuja `ui/fighters.py`.

| Momento | Pose / animación |
|---|---|
| STABLE | Erguido, respirando. Aro verde en el suelo |
| UNSTABLE | Agachado y tambaleándose, estrellitas de mareo y gota de sudor. Aro rojo que late |
| Cambio de cartas (REDRAW) | Algo echado hacia atrás con un abanico de cartas en la mano: una sale volando y entra otra. Al terminar, «LISTO» |
| Carta ATTACK | Amago hacia atrás, embestida y tajo |
| Carta MAGIC | Aura, empuje y un orbe que cruza el escenario hasta el rival |
| Carta BREAK | Se agacha, salta hacia delante y cae con una onda en el suelo |
| Carta GUARD | Retrocede un paso y levanta un escudo, que destella si le llega un golpe |
| Pierde la interacción **y recibe hit** | Sale despedido hacia atrás, destello blanco, parpadeo rojo y chispas. Su propia animación se corta en ese instante |
| MEGA COMBO | Quien lo activa encadena tres embestidas; el rival recibe tres golpes |
| Fin de la partida | El perdedor cae de espaldas (K.O.) y el ganador da saltitos |
| FREEZE | Encerrado en un cubo de hielo (en perspectiva), inmóvil y azulado |
| SLEEP | Cabecea despacio y le salen «Z» flotando |
| PARALYZE | Rayitos amarillos que chisporrotean a su alrededor y tirones de calambre |
| BURN | Llamitas que suben por el cuerpo |
| POISON | Burbujas moradas que suben y revientan |

Las animaciones no guardan estado: se calculan cada frame a partir de la fase
y del tiempo que lleva (`View.phase_time`), así que van siempre sincronizadas
con la resolución. Los sprites son los del mapa (avatar del personaje,
`<avatar>_right_0`, o el que fije la escena en `View.fighter_keys`); el de la
derecha se voltea. Sin sprite disponible se dibuja una silueta.

## Reglas

### Cada carta tiene cuatro cosas independientes

| Concepto | Campo | Pregunta que responde |
|---|---|---|
| **Tipo** | `card_type` | ¿Contra qué gana? `GUARD > ATTACK`, `ATTACK > BREAK`, `BREAK > GUARD` |
| **Iniciativa** | `has_initiative` | ¿Mantiene viva la secuencia después de resolver? |
| **Resultado al ganar** | `damage`, `generates_hit`, `causes_instability`, `recovers_stability` | ¿Qué pasa si esta carta gana? |
| **Efectos** | `effects` | Cualquier otra cosa: Mana, hits extra, cambiar el resultado... |

En las cartas, el color y el icono indican el tipo, y los chips indican lo
demás: un **número** (daño normal si gana), **INI** (iniciativa), **HIT** (suma
hit de combo), **DES** (desestabiliza al rival) y **REC** (recupera tu
Stability). Ningún concepto se deduce de otro: el motor admite un ATTACK sin
iniciativa, un GUARD que desestabiliza, una carta que hace daño sin sumar hit
o una que suma hit sin hacer daño.

| Carta básica | Iniciativa | Si gana |
|---|---|---|
| ATTACK | Sí | 10 de daño, +1 hit de combo y el rival queda UNSTABLE |
| BREAK | Sí | 10 de daño, +1 hit de combo y el rival queda UNSTABLE |
| MAGIC | Sí | Como ATTACK, pero el daño es **mágico** (a distancia) |
| GUARD | No | Gana la interacción. **Sin daño, sin hit y sin desestabilizar** |
| PASS | No | No hace nada: no gana nunca contra una carta y recibe todo lo que haga la carta rival |

### MAGIC

MAGIC es una **acción principal ofensiva** propia (`card_type="MAGIC"`), no una
etiqueta de ATTACK. Se **enfrenta como ATTACK** (`MATCHUP_AS = {"MAGIC": "ATTACK"}`
en `game/config.py`), sin tocar el triángulo:

- `GUARD > MAGIC`, `MAGIC > BREAK`.
- `MAGIC = MAGIC` y `MAGIC = ATTACK`: choque entre ofensivas; lo desempatan la Stability y la prioridad. Ninguna gana a la otra por tipo.
- Iniciativa, coste (gratis en la 1ª interacción, 1 Mana después, más la SPECIAL si la hay), hits, combo y Mega Combo: exactamente como cualquier acción principal.

Cada carta tiene tres propiedades independientes del tipo:

| Propiedad | Campo | Ejemplo |
|---|---|---|
| Canal de daño | `damage_channel` | `"physical"` (ATTACK, BREAK) · `"magic"` (MAGIC) |
| Elemento | `element` | `"FIRE"` en Fire Bolt · `None` en Magic |
| Efectos | `effects` | FLAME: `APPLY_STATUS` BURN si ganas con MAGIC |

El **elemento nunca aplica estados**: Fire Bolt no quema; para eso hace falta un
efecto explícito como FLAME. Cada `DamageEvent` guarda su origen (`action`,
`channel`, `element`) y los efectos pueden reaccionar al canal del rival con
`vs_channel` (p. ej. un GUARD que solo gana Mana contra daño mágico). Las
excepciones, como una MAGIC que ignore GUARD, se hacen con efectos de la carta
(`MODIFY_RESULT` con `vs: "GUARD"`), no con reglas globales.

### Personajes

Cada jugador elige un personaje antes de la partida (pueden repetirse) y lo
conserva hasta el final. Cada personaje tiene **una pasiva**; usa las mismas
cartas y reglas que todos.

| Personaje | Pasiva | Efecto |
|---|---|---|
| **Blaze** | Afinidad ígnea | Las cartas con `element="FIRE"` hacen **+10%** de daño directo (MAGIC, ATTACK o lo que sea: cuenta el elemento de la carta) |
| **Jurgenoid** | Undead | Cada HIT recibido le da una marca (todo el combate). Al empezar cada turno se cura 0.5% de su vida máxima por marca, redondeado (medios hacia arriba) |
| **Hero** | Impulso consecutivo | Según su combo de HIT consecutivos: 1º HIT +0%, **2º +5%**, **3º +10%**; el daño adicional del **MEGA COMBO +15%** |

- La pasiva solo afecta al daño que **causa** su dueño, **una vez por evento**, en `CombatEngine._apply_passive` (daño de interacción y de Mega Combo). BURN, POISON y BREAK ICE no pasan por ahí.
- **Blaze** no quema: para aplicar BURN hace falta un efecto como FLAME. El Mega Combo no tiene elemento, así que no recibe su +10%.
- **Hero** no lleva contador propio: lee el combo del motor con `combo_after_hit`, la misma función que actualiza `combo_hits`. Si el combo se rompe (perder, empatar, ganar sin HIT, golpear un ICE CUBE, fin del turno), su progresión vuelve a cero.
- **Redondeo**: el daño es entero; los porcentajes se redondean al más cercano, los medios hacia arriba (10 +5% = 11, 20 +15% = 23).
- En combate, bajo el HUD de cada jugador está su personaje y el estado de la pasiva (`HERO · combo 1/3 · próximo HIT +5%`); al pasar el ratón se ve la ficha completa. Cuando la pasiva aumenta un daño, la ficha se ilumina y la resolución lo explica (`BLAZE: AFINIDAD ÍGNEA +10% (10 -> 11)`).
- Sin personaje (`CombatEngine(characters=(None, None))`, como en los tests antiguos) no hay pasivas.

**Personajes de enemigos**: `Character(..., playable=False)`. Tienen pasiva como
cualquier otro, pero no salen en los menús de selección (`playable_characters()`).
De momento: **Dron de seguridad** (Alerta: cada 3 turnos deja UNSTABLE al rival),
**Elemental Wolf** (afinidad FUEGO/HIELO: su elemento le cura, el contrario x1.5, sin elemento u
otro elemento x0.5; golpearle con ATTACK quema o congela), y **Fire Wolf** / **Ice Wolf** (pasiva
`element_ward`, «Fire element» / «Ice element»: el daño de cartas de su elemento le
cura, el del elemento contrario es normal y el de cartas sin elemento o de otro
elemento se reduce a la mitad, medios hacia arriba; el Mega Combo no es una carta
y hace el daño normal). Mazos `fire_wolf` y `ice_wolf` en `ENEMY_DECKS`. Sus cartas exclusivas (`ENEMY_CARD_DATA`) y
mazos (`ENEMY_DECKS`) no están en el catálogo ni en `DECKS`. Ganchos de pasiva
nuevos: `incoming_damage`, `on_turn_start`, `after_interaction`, `set_affinity`,
`on_defeat`.

**Enemigos de la Aldea del vacío**:

| Personaje | Pasiva | Efecto |
|---|---|---|
| **Herrero**, **Granjero**, **Vendedor** (aldeanos huecos) | **Corrupted** | La primera vez que se quedan a 0 HP recuperan el **50%** de su vida máxima y se **transforman** (nombre «… CORRUPTO» y otro sprite, con tentáculos y ojos de más). Transformados, cada interacción que **ganan haciendo HIT** te quita **1 de Mana máximo** (nunca baja de 1) |
| **Void Insect** (jefe) | **Void insect** | **Part of the void** (todo el combate): el daño de cartas **VOID** le **cura el doble**. **Void breeding**: cada HIT recibido le da **1 carga** (máx. 10). A 0 HP aparecen **dos crías**, una tras otra, con **cargas x10 / 2 HP** cada una (10 cargas = 50 HP; sin cargas no hay crías), solo con Part of the void. Después vuelve con el **50%** de su vida: **Void consumption**, cada interacción que gana con HIT te quita el **20% de tu vida máxima** |

Todo el jefe es **un solo combate**: tu vida y tu Mana siguen igual entre etapas. Al
cambiar de etapa (o al transformarse un aldeano) el luchador nuevo empieza sin
estado alterado, STABLE y sin combo, pero las consecuencias del golpe que tumbó a la
forma anterior (desestabilizar, un Mega Combo) le llegan igual.

- `on_defeat(owner, engine)` se llama en cuanto el dueño se queda a 0 HP (daño de
  interacción, de estados o de una carta); puede llamar a
  `engine.transform(i, hp, max_hp, name, sprite, text)` para seguir en pie con otra forma.
  La pantalla cambia el sprite con el evento `transform`.
- `engine.reduce_max_mana(i, n)` y `engine.reduce_max_hp(i, pct)`: el HUD tacha los
  huecos de Mana y el tramo de vida máxima perdidos.
- `Player.damage_taken_mult` (1 por defecto): multiplica todo el daño que recibe ese
  jugador, también BURN/POISON. La exploración pone x2 a los enemigos de los que se puede huir.

**Cartas bloqueadas** (solo en la exploración): `DeckEditor(store, locked=...)`
recibe las cartas que aún no se pueden usar; salen en gris en el catálogo, no se
pueden añadir y un mazo que las lleve no es válido para guardar.

**Almacén propio** (solo en la exploración): `DeckStore(path, builtins={...},
unique=True)` tiene sus propios mazos de fábrica, prohíbe cartas repetidas en un
mazo y, al aplicar, añade sus mazos a `DECKS` sin borrar los demás.
`DeckEditor(..., single=True)` impide crear, duplicar, renombrar o borrar mazos.
El duelo PvP usa el almacén normal: ahí sí se pueden repetir cartas.

**Añadir un personaje**: `register_character(Character(id, nombre, descripción,
id_de_pasiva, configuración))` en `game/characters.py`. Opcional para la
exploración: `adventure=` (habilidad de aventura) y `avatar=` (sprite en el
mapa; `None` = el de por defecto). Una pasiva nueva es una
subclase de `Passive` con `@passive("id")` que implementa
`damage_bonus_pct(event, engine, r)`. El motor no cambia.

### Estilo y definitiva

Cada jugador acumula **Estilo** ganando **interacciones** seguidas (es otro
contador, distinto del combo de HIT). Cuenta el resultado real de la
interacción: gana quien la gana, aunque no haga daño (un GUARD que bloquea gana).

| Victoria consecutiva | 1ª | 2ª | 3ª | 4ª | 5ª y siguientes |
|---|---:|---:|---:|---:|---:|
| Puntos | +3 | +6 | +12 | +24 | +48 |

| Rango | D Desafiante | C Competente | B Experto | A Élite | S Supremo |
|---|---|---|---|---|---|
| Puntos | 0-8 | 9-20 | 21-44 | 45-299 | 300+ |
| Empate | −3 | −8 | −15 | −30 | −50 |
| Derrota | −6 | −16 | −30 | −60 | −100 |

- Al **empatar o perder**, la racha vuelve a 0 y se resta según el rango **anterior** a la interacción (con 320 en S, perder deja 220 y rango A). Nunca baja de 0.
- **Excepción con PASS**: si tu acción principal es PASS y **no recibes un HIT**, no pierdes puntos y conservas la racha, aunque la interacción cuente como empate o derrota. Si recibes un HIT, se aplican la penalización y el reinicio normales. Vale también para el PASS automático u obligatorio; WAIT/BREAK ICE (FREEZE) no cuentan como PASS.
- Una actualización por interacción y jugador. BURN, POISON y el daño del MEGA COMBO no dan Estilo.
- Sigue las reglas actuales del resultado: **PASS + PASS es empate** y **pasar contra una carta es perder**, también cuando el PASS es automático (sin cartas o sin Mana) u obligatorio (PARALYZE, SLEEP, FREEZE).

**Definitiva**: disponible mientras el jugador esté en **S** y no la haya usado
en la partida; si baja de S se bloquea, y si vuelve a S sin haberla usado, se
desbloquea. Se usa **una vez por partida** (el uso no se olvida al cambiar de
rango; solo una partida nueva lo reinicia).

- Durante la elección aparece **DEFINITIVA [ATK] [GRD] [BRK] [MAG] [SPC]** (tecla `6` para J1, `Y` para J2: recorre las categorías). Como las cartas, la elección queda oculta hasta el REVEAL.
- Provisionalmente, cada categoría es **la carta normal** (Attack, Guard, Break, Magic; SPC = Recover junto a tu acción principal), marcada en dorado como DEFINITIVA. Mismo coste de Mana, mismas reglas, sin bonificaciones. No sale de la mano ni entra en el mazo.
- El uso se gasta al revelar, una sola vez. Se puede sustituir por técnicas propias de cada personaje cambiando `CombatEngine.ultimate_card` (o `ULTIMATE_CARDS` en `game/config.py`).

En combate, bajo la ficha del personaje: rango, puntos, racha, barra hacia el
siguiente rango (MÁX en S) y `DEF LISTA` / `DEF USADA` / `DEF (S)`. Tras cada
interacción aparece `+12 ESTILO` o `-30 ESTILO · RACHA 0`, y avisos al llegar a S
o perderlo.

### Turno

1. **+1 Mana** (máx. 5). El turno 1 se juega con los 3 iniciales.
2. **Robar hasta 5** cartas (si el mazo se acaba, se baraja el descarte).
3. **2 cambios**.
4. **Secuencia** de interacciones:

```
AMBOS ELIGEN (carta o PASS) → REVEAL → ¿QUIÉN GANA?
   → efectos → HITS → DAÑO NORMAL (el HP baja ya) → STABILITY → COMBO (+1 hit o 0)
   → ¿3 hits seguidos? → MEGA COMBO: daño ADICIONAL (otro evento) → combo = 0
   → ¿alguno jugó con INICIATIVA? → sí: nueva interacción (automática)
                                    no: fin del turno
```

Todas las cartas de la mano se pueden jugar en cualquier interacción si puedes
pagar el coste de la interacción y cumples su condición. Ya no hay cartas de
interrupción.

### Cartas SPECIAL

Una SPECIAL **no es una acción principal**: acompaña a ATTACK, GUARD, BREAK o
PASS en la misma interacción (como máximo **1 por jugador**).

- No entra en el matchup, **nunca tiene iniciativa**, no hace daño ni hit y no cuenta como interacción.
- Cuesta siempre **1 Mana** (`SPECIAL_MANA_COST`), sea la interacción que sea, **además** del coste de la acción principal.
- Se resuelve **al revelar, antes del enfrentamiento**: sus efectos tienen el momento `"special"`.
- Se roba, ocupa sitio en la mano y se puede cambiar como cualquier otra carta.

**Recover** (SPECIAL, 1 Mana): recupera STABLE **en el momento**. Si ya estabas
STABLE no cambia nada, pero el Mana se gasta igualmente.

```
J1 UNSTABLE: RECOVER + ATTACK      J2 STABLE: ATTACK
   ↓ REVEAL: RECOVER se aplica primero → J1 STABLE
   ↓ ATTACK = ATTACK con ambos STABLE → DRAW
   (sin Recover, J2 habría ganado por Stability)
```

Después sigue la resolución normal: si J1 recibe un hit en esa misma
interacción, puede volver a quedar UNSTABLE. La recuperación natural (no
recibir hit) no cambia.

| Jugada | Interacción 1 | Interacción 2+ |
|---|---|---|
| ATTACK/GUARD/BREAK | 0 | 1 |
| PASS | 0 | 0 |
| RECOVER + ATTACK | **1** | **2** |
| RECOVER + PASS | **1** | **1** |

No se puede confirmar una combinación que no puedas pagar: con 1 Mana en la
interacción 2, RECOVER + ATTACK queda deshabilitado, pero RECOVER + PASS sí vale.

### Mana

**Cada turno te da una interacción gratuita. Después, cada vez que juegues una
carta (ATTACK, GUARD o BREAK, da igual cuál) gastas 1 Mana. PASS nunca cuesta.**

```
MANA
├── Máximo 5 · inicio de partida 3 · +1 al empezar cada turno (nunca durante el turno)
│   (algunos enemigos de la aldea reducen el máximo de su rival: Player.max_mana, nunca menos de 1)
├── INTERACCIÓN 1 del turno:  ATTACK / GUARD / BREAK / PASS → GRATIS
├── INTERACCIÓN 2+:           ATTACK / GUARD / BREAK → 1 MANA · PASS → GRATIS
├── SPECIAL (opcional):       siempre 1 MANA, se suma a lo anterior
└── NUEVO TURNO: el contador de interacciones vuelve a 1
```

- El coste lo decide **el número de interacción**, no la carta: las cartas ya no tienen coste propio.
- PASS no reinicia el contador: si la interacción 2 es PASS + GUARD, la siguiente es la 3.
- La interacción 1 es gratis aunque en ella nadie juegue carta. La 2 ya cuesta.
- El Mana **se paga al confirmar** la carta y no se devuelve, gane o pierda. El HUD muestra el descuento **al revelar**, para no delatar si el rival eligió carta o PASS.
- Con 0 Mana desde la interacción 2, las cartas aparecen como **UNAVAILABLE** y solo puedes pasar. Si no puedes jugar nada, el PASS es automático.
- En la mano, cada carta lleva una etiqueta **FREE**, **1 MANA** o **UNAVAILABLE**, y la cabecera indica si la interacción es gratis.
- Las futuras reglas especiales de Mana irán como efectos (`MODIFY_PLAY_COST`, momento `cost`) que se suman a la regla base sin romperla.

### ¿Quién gana?

1. **PASS**: una carta gana a PASS. PASS contra PASS es empate.
2. **Efectos que cambian el resultado**, por ejemplo Unbreakable Guard frente a BREAK.
3. **Tipo**: `GUARD > ATTACK`, `ATTACK > BREAK`, `BREAK > GUARD`.
4. **Mismo tipo → Stability**: STABLE gana a UNSTABLE, **solo si hay choque** (al menos una carta con iniciativa). `GUARD = GUARD` es empate aunque uno esté UNSTABLE. Si ambos tienen la misma Stability, sigue empatado.
5. **Prioridad** de la carta (Overdrive tiene 1).
6. **Empate**: no pasa nada y, si hay iniciativa, se juega otra interacción.

### ¿Qué pasa al ganar?

Lo decide **la carta ganadora**, no el hecho de ganar:

- **Daño normal**: el `damage` de la carta, aplicado **al resolver la interacción**. Attack y Break hacen 10; Guard, 0.
- **Hit de combo**: solo si la carta tiene `generates_hit`. Guard gana, pero no hace hit.
- **Desestabilizar**: solo si tiene `causes_instability`. `ATTACK` contra `GUARD`: gana Guard y **el atacante no queda UNSTABLE**.
- **Recuperar Stability**: ver la sección siguiente. Depende de si **recibiste un hit**, no de ganar.
- **Quien pasa** no hace nada: recibe el daño normal, el hit y la desestabilización de la carta rival como si no se defendiera. Solo conserva sus cartas (no gasta ninguna).

### Stability (definitiva)

- **Binaria**: STABLE o UNSTABLE. Nunca se acumula ("sigue UNSTABLE").
- **Desempate**: con el mismo tipo y **choque** (alguna carta con iniciativa), STABLE gana a UNSTABLE. Ganar por Stability **no cambia** el estado de nadie por sí mismo.
- **Al final de cada interacción**, en este orden de prioridad:

```
            ¿EMPATE REAL? (mismo tipo sin desempate, PASS+PASS, Parry...)
             /            \
           SÍ              NO
            │               │
     AMBOS → STABLE   para cada jugador UNSTABLE:
                         ¿recibió un HIT en esta interacción?
                           sí → sigue UNSTABLE
                           no → STABLE
            │               │
            └───────┬───────┘
                    ▼
        EFECTOS EXPLÍCITOS (siempre al final, para que nada los anule)
          1. desestabilizar: causes_instability / CAUSE_INSTABILITY
             (Perfect Guard, el ATTACK o BREAK que gana...)
             salvo protección: Iron Stance
          2. recuperar: recovers_stability / RECOVER_STABILITY (Desperation)
```

- **La iniciativa no interviene en la recuperación**: lo que cuenta es si recibiste un **hit** (`InteractionResult.received_hit`). El hit y el daño son conceptos distintos: una carta puede hacer hit sin daño o daño sin hit.
- El estado final se calcula entero y se aplica una sola vez. Por eso nunca ves un "→ STABLE" seguido de un "→ UNSTABLE" en la misma interacción.
- Cambiar de turno no la modifica.

| Situación | Resultado |
|---|---|
| `ATTACK = ATTACK`, STABLE vs UNSTABLE | Gana el STABLE (hit); el UNSTABLE recibió hit → **sigue UNSTABLE** |
| `ATTACK = ATTACK`, ambos STABLE o ambos UNSTABLE | **DRAW** → ambos STABLE |
| `GUARD = GUARD`, sea cual sea la Stability | **DRAW** (sin choque) → ambos STABLE, fin del turno |
| J1 UNSTABLE: `ATTACK` vs `GUARD` | Guard gana sin hit → **J1 recupera STABLE** |
| J2 UNSTABLE: `ATTACK` vs `BREAK` | Attack gana con hit → **J2 sigue UNSTABLE** |
| `ATTACK` vs `PERFECT GUARD` | Perfect Guard gana → **J1 → UNSTABLE** (efecto explícito, aunque no recibió hit) |

### Iniciativa y fin del turno

Después de cada interacción, **si al menos uno jugó una carta con iniciativa, se
juega otra interacción automáticamente**. Si ninguno la tenía (por ejemplo
`GUARD + GUARD`, `GUARD + PASS` o `PASS + PASS`), **el turno termina**. La
iniciativa no influye en quién gana.

Los efectos `END_SEQUENCE` y `KEEP_SEQUENCE` pueden forzar una u otra cosa.
No hay bucles infinitos: cada interacción gasta cartas, y sin cartas solo
queda PASS.

### Daño, combo y Mega Combo

Son dos cosas distintas:

| | Cuándo | Cuánto |
|---|---|---|
| **Daño de interacción** | Cada vez que gana una carta con daño, al resolver | El `damage` de la carta (10 en Attack y Break) |
| **Mega Combo** | Al conseguir **3 hits consecutivos** | **20 de daño adicional**, como evento aparte |

- El combo es **de cada jugador** (`combo_hits`) y cuenta **hits consecutivos**.
- En cada interacción, quien consigue un hit suma 1. Quien no lo consigue **vuelve a 0**, ya sea porque pierde, empata o gana con una carta sin hit. Nadie hereda el combo del otro.
- El **tercer hit hace las dos cosas**: su daño normal (−10) y, a continuación, el Mega Combo (−20). En total son 30, pero se ven y se registran como dos daños separados (`InteractionResult.damage_events`).
- Tras el Mega Combo, el combo vuelve a **0** y la secuencia **sigue o termina según la iniciativa**, como siempre. El Mega Combo no termina el turno.
- Al terminar el turno, los combos vuelven a 0.
- La partida acaba cuando alguien llega a **0 HP** (si alguien queda K.O., la secuencia se corta en ese momento).

En pantalla, el **daño normal** sale en rojo durante la resolución (`PLAYER 2 -10 HP`). El **Mega Combo** tiene su propio momento: `3 HIT COMBO!`, `MEGA COMBO!`, un `-20` grande en dorado y `COMBO RESET -> 0`.

### Cartas

| Carta | Tipo | INI | Si gana / efecto |
|---|---|---|---|
| Attack | ATTACK | Sí | Hit + desestabiliza |
| Break | BREAK | Sí | Hit + desestabiliza |
| Guard | GUARD | No | Nada más que ganar |
| **Perfect Guard** | GUARD | No | **Desestabiliza al rival** (sin hit) |
| **Unbreakable Guard** | GUARD | No | **No puede perder contra BREAK: lo vence** (sin hit, sin desestabilizar) |
| Revenge | ATTACK | Sí | Solo estando UNSTABLE. Ignora la Stability en el empate. Si gana, recuperas Stability |
| Overdrive | ATTACK | Sí | Prioridad 1: gana los empates entre ATTACK |
| Desperation | GUARD | No | Al jugarla recuperas Stability, ganes o pierdas |
| Break Guard | BREAK | Sí | Si vence a GUARD: +1 hit extra |
| Feint | ATTACK | Sí | También vence a GUARD |
| Parry | GUARD | No | Anula la interacción: empate |
| Iron Stance | GUARD | No | Si pierdes, no pierdes Stability |
| Heavy Blow | ATTACK | Sí | +10 de daño normal (20 en total) |
| Crescendo | ATTACK | Sí | Si con ella llegas al Mega Combo: +10 de daño de Mega Combo |
| Focus | GUARD | No | Tu combo no se rompe en esta interacción aunque no hagas hit |
| Mana Surge | GUARD | No | +1 Mana |
| **Recover** | **SPECIAL** | No | Se juega junto a la acción principal (1 Mana): recupera STABLE antes del enfrentamiento |
| Drain | BREAK | Sí | El rival pierde 1 Mana |
| **Magic** | **MAGIC** | Sí | Hit + desestabiliza; daño mágico |
| Fire Bolt | MAGIC | Sí | Como Magic, con elemento FIRE (sin estados) |
| **Flame** | **SPECIAL** | No | Si ganas la interacción con una carta MAGIC: BURN al rival |
| Ice Shard | MAGIC | Sí | Como Magic, con elemento ICE (sin estados) |
| **Taunt** | **SPECIAL** | No | Solo gana 10 puntos de Estilo (sin contar como victoria ni tocar la racha) |
| **Heal** | **SPECIAL** | No | Recuperas **30 de vida** (hasta tu vida máxima). Disponible desde el principio en la exploración |
| **Void Impact** | ATTACK · VOID | Sí | 10 de daño, hit, desestabiliza y **recupera Stability si gana**. Al jugarla **pierdes 15 HP** y **quedas UNSTABLE** (gane, pierda o empate); si gana, **PARALYZE** al rival. Se forja en el yunque de la aldea |

Cartas **exclusivas** de los enemigos de la aldea (`ENEMY_CARD_DATA`):

| Enemigo | Carta | Tipo | Efecto |
|---|---|---|---|
| Herrero | Hammer Blow | BREAK | Si gana: +5 de daño |
| Herrero | Forge Spark | ATTACK · FIRE | Si gana: BURN |
| Herrero | Tempered Steel | GUARD | Si gana desestabiliza; si pierde no pierde Stability |
| Granjero | Pitchfork | ATTACK | Prioridad 1 |
| Granjero | Scythe Sweep | BREAK | Si vence a GUARD: +1 hit |
| Granjero | Rotten Crop | MAGIC | Si gana: POISON |
| Granjero | Harvest | SPECIAL | Recupera 10 de vida |
| Vendedor | Coin Toss | MAGIC | Si gana: +1 Mana |
| Vendedor | Haggle | SPECIAL | Al revelar: el rival pierde 1 Mana |
| Vendedor | Bribe | GUARD | Si gana: el rival pierde 1 Mana |
| Void Insect | Void Sting | ATTACK · VOID | Si gana: el rival pierde 1 de Mana máximo |
| Void Insect | Mana Leech | MAGIC · VOID | Si gana: el rival pierde 1 Mana y el insecto gana 1 |
| Void Insect | Chitin Shell | GUARD | Si gana desestabiliza; si pierde no pierde Stability |
| Void Insect | Void Buzz | SPECIAL | Si su acción principal hace HIT: el rival pierde 1 de Mana máximo |

Mazos (`ENEMY_DECKS`): `herrero` (Hammer Blow x2, Forge Spark x2, Tempered Steel x2,
Break Guard, Iron Stance, Attack, Guard), `granjero` (Pitchfork x2, Scythe Sweep x2,
Rotten Crop, Harvest x2, Guard x2, Recover), `vendedor` (Coin Toss x2, Haggle x2,
Bribe x2, Feint, Parry, Attack, Guard) y `void_insect` (Void Sting x3, Mana Leech x2,
Chitin Shell x2, Void Buzz, Break, Guard).

Efectos nuevos: `HEAL` (`amount`), `SELF_DAMAGE` (`amount`, no es HIT ni pasa por las
pasivas), `SELF_UNSTABLE` (queda UNSTABLE quien la juega, salvo que gane y la carta
recupere Stability) y `REDUCE_MAX_MANA` (`amount`; como `APPLY_STATUS`, se aplica tras
el daño y admite `if_outcome` / `if_hit`). Elemento nuevo: **VOID** (VACÍO).

### Status Effects (estados alterados)

Cada jugador tiene **como máximo un estado**. Solo los aplica un efecto
explícito de carta (`APPLY_STATUS`): **nunca por azar ni por elemento**. Son
independientes de la Stability, la iniciativa y el Mana. **RECOVER no los
elimina.** En este juego el turno es común (selección simultánea), así que
cada inicio de turno es un "turno propio" de los dos jugadores.

| Estado | Efecto | Termina |
|---|---|---|
| **BURN** `BRN` | −5 HP al **empezar cada turno** (no al aplicarse) | Tras 3 activaciones |
| **POISON** `PSN` | −3 HP al **empezar cada interacción** (varias veces por turno) | La duración (3 turnos) baja 1 al empezar cada turno; a 0, desaparece |
| **PARALYZE** `PRZ` | PASS obligatorio, sin SPECIAL, en la **siguiente** interacción | Al terminar esa interacción |
| **FREEZE** `FRZ` | Atrapado en un **ICE CUBE** (30 HP) que absorbe todo el daño de combate. Solo puede elegir **BREAK ICE** (15 al cubo) o **WAIT** | Al romperse el cubo |
| **SLEEP** `SLP` | PASS obligatorio, sin SPECIAL | Al recibir un **HIT real**, tras **3 interacciones posteriores**, o al empezar el siguiente turno (lo primero que ocurra) |

- **Aplicar**: si el objetivo es inmune (`Player.immunities`), no pasa nada. Si el estado activo lo bloquea, tampoco. Si no, el estado anterior se reemplaza (`BURN -> SLEEP`); el mismo estado se reinicia con sus contadores iniciales.
- **Inmunidad cruzada PARALYZE / SLEEP**: mientras uno de los dos está activo, el jugador es inmune a **ambos** (no se pueden encadenar ni reaplicar). El estado activo no se reinicia ni se alarga, y la inmunidad termina con él. BURN, POISON y FREEZE pueden reemplazarlos y ser reemplazados por ellos con normalidad. Se declara en cada definición (`StatusDefinition.blocks`), así que vale para cualquier carta futura.
- Un estado recién aplicado **no cuenta** la interacción que lo aplicó ni bloquea nada hasta la siguiente.
- **Daño periódico** (BURN/POISON): no es HIT, no suma combo, no toca la Stability. Si deja a alguien a 0 HP, la partida termina en ese momento.
- **FREEZE**: golpear el cubo **no es un HIT** (sin combo para el atacante, que sigue la regla normal: sin hit, el combo vuelve a 0) y no desestabiliza al congelado. Si el cubo se rompe, el daño sobrante **no** pasa al jugador: queda protegido toda esa interacción. Congelado no es PASS: el rival que gana sí le hace daño (al cubo). BREAK ICE y WAIT no cuestan Mana, no tienen iniciativa ni hacen hit; liberarse no da una acción extra.
- Orden dentro de una interacción: inicio (POISON) → selección → REVEAL (SPECIAL) → matchup → efectos → hits → daño (HP o ICE CUBE) → BREAK ICE → despertar por HIT → Stability → combo → **estados que aplican las cartas** → fin de interacción (PARALYZE, SLEEP) → iniciativa → Mega Combo.
- Valores en `game/config.py` (`BURN_DAMAGE`, `POISON_TURNS`, `ICE_CUBE_HP`, `BREAK_ICE_DAMAGE`...).

En pantalla, el estado aparece **al lado del nombre del jugador**, en su HUD (icono, nombre y contador: `BURN · 2 turnos`, `FREEZE · 20/30`). Al pasar el ratón por esa insignia se abre una ficha con el efecto, el contador y los últimos mensajes. Los estados se distinguen por icono y nombre, no solo por color. Las cartas que aplican un estado llevan su chip (`BRN`, `PSN`...). Congelado, la mano se sustituye por los botones **BREAK ICE** (tecla `1`/`Q`) y **WAIT** (tecla `2`/`W` o PASS).

## Decisiones de diseño a revisar

| Punto | Decisión | Dónde cambiarla |
|---|---|---|
| Daño normal y del Mega Combo | Cada carta ofensiva declara su `damage` (todas las actuales: 10); Mega Combo +20 | `damage` de cada carta, `MEGA_COMBO_DAMAGE` |
| Un empate durante un combo | Lo rompe (no hay hit, así que no es consecutivo) | `game/combat.py: _apply_combo` |
| `GUARD = GUARD` con distinta Stability | Empate (la Stability solo desempata si hay choque, es decir, alguna carta con iniciativa) | `STABILITY_TIEBREAK_NEEDS_INITIATIVE` |
| Stability del ganador UNSTABLE | Recupera (no recibió hit), según la regla del hit | `game/combat.py: _apply_stability` |
| Cartas que antes costaban más (Overdrive, Feint, Heavy Blow, Desperation...) | Ahora cuestan lo mismo que cualquier carta (regla de la interacción). Puede que algunas queden demasiado fuertes | `MODIFY_PLAY_COST` en sus datos |
| Mana visible al confirmar | El motor cobra al confirmar; el HUD lo enseña al revelar | `CombatEngine.displayed_mana` |
| Recover en el mazo por defecto | Sustituye a Desperation, que también recuperaba Stability; así el mazo sigue en 10 cartas | `DECKS["duelo"]` |
| Coste de las SPECIAL | Es una regla de la categoría (`SPECIAL_MANA_COST = 1`), no un campo de cada carta, igual que el resto del Mana | `game/config.py` |
| "+ SPECIAL" en el estado de la mano | Avisa de que has añadido una SPECIAL (no cuál). El rival ve tu mano igualmente | `ui/battle_screen.py` |
| Combo al terminar el turno | Se reinicia a 0 | `game/combat.py: _turn_end` |
| Carta contra PASS | PASS es literalmente pasar: gana quien juega y su carta se resuelve entera (daño, hit y desestabilizar). Antes, pasar bloqueaba el daño y protegía la Stability; se recupera con `PASS_BLOCKS_DAMAGE = True` y `PASS_PROTECTS_STABILITY = True` | `PASS_LOSES_INTERACTION`, `PASS_BLOCKS_DAMAGE`, `PASS_PROTECTS_STABILITY` |
| Antiguas interrupciones | Ahora son cartas normales: Desperation es un GUARD que recupera al jugarse; Parry, un GUARD que anula; Feint, un ATTACK que vence a GUARD | `cards/card_database.py` |
| Overdrive | Prioridad 1 (su "continuar" ya no hace falta) | `cards/card_database.py` |
| MAGIC contra ATTACK | Ofensivas equivalentes: lo deciden la Stability y la prioridad, como ATTACK = ATTACK | `MATCHUP_AS` |
| Mensaje de daño | Solo el daño mágico o con elemento lleva etiqueta (`-10 HP (MAGIC · FIRE)`); el físico conserva su texto | `CombatEngine._deal_damage` |
| MAGIC y FLAME en los mazos | Solo en el mazo de prueba `arcano`; los mazos por defecto no cambian | `DECKS` |
| Golpear el ICE CUBE | No es HIT: el combo del atacante se rompe por la regla general (sin hit = 0) | `CombatEngine._determine_hits` |
| Stability del congelado | El cubo le protege de desestabilizar; la recuperación natural sigue igual | `CombatEngine._apply_stability` |
| Estado aplicado por el 3er hit | El daño normal llega al HP; el estado se aplica después, así que con FREEZE el Mega Combo va al cubo | `CombatEngine._apply_result` |
| Duración de POISON | Cuenta el turno en que se aplica: activo el resto de ese turno y los dos siguientes | `POISON_TURNS`, `game/status.py` |
| Recuperar Stability | Solo con cartas o efectos de recuperación. Hay pocas: si un jugador se queda UNSTABLE mucho tiempo, habrá que añadir más | mazos en `cards/card_database.py` |

## Estructura del proyecto

```
main.py                    entrada (elige mazos por línea de comandos)
jugar.bat                  doble clic para jugar
game/
  config.py                reglas ajustables (RulesConfig) y mazos por defecto
  rules.py                 ¿quién gana? · ¿sigue? · ¿Mega Combo? · InteractionResult / DamageEvent
  status.py                Status Effects: StatusId, definiciones con ganchos, regla de aplicación/reemplazo
  combat.py                CombatEngine: _determine_hits -> _apply_damage -> _apply_stability
                           -> _apply_combo -> _decide_flow -> _mega_combo -> _continue_or_end
  state_machine.py         fases y transiciones válidas
  input_map.py             teclas -> acciones
  game.py                  App de Pygame: modos menú / mazos / partida, input, eventos -> animaciones
  deck_editor.py           estado del menú y del editor de mazos (sin Pygame)
  characters.py            personajes y pasivas (Blaze, Hero) · registro de personajes
  style.py                 Estilo: puntos, rangos, penalizaciones y definitiva (tablas en config.py)
cards/
  card.py                  Card: card_type (ATTACK/GUARD/BREAK/SPECIAL), has_initiative, damage, generates_hit...
  card_database.py         todas las cartas y mazos, como datos (TYPE_DEFAULTS solo es comodidad)
  card_effects.py          registro de efectos genéricos
  deck.py                  mazo + descarte
  deck_store.py            mazos editados: decks.json (fábrica / modificado / propio)
players/player.py          HP, Mana, Stability, mano...
ui/                        battle_screen, menu_screen, deck_screen, character_widget, style_widget, card_widget, player_hud, status_widget, animations, fighters (escenario y personajes), theme
tests/
  test_combat.py, test_stability.py, test_cards.py, test_mana.py, test_special.py, test_status.py, test_magic.py, test_decks.py, test_characters.py, test_style.py, test_fighters.py   (290 tests)
  ui_scenarios.py          los ejemplos del documento, jugados por la UI
  ui_smoke.py              partida completa por la UI
  ui_decks.py              menú y editor de mazos por la UI
```

La lógica (`game/rules.py`, `game/combat.py`, `cards/`, `players/`) **no
importa Pygame**.

## Tests

```bash
cd tests
python -m unittest                  # 381 tests (reglas, estados, MAGIC, mazos, personajes, Estilo;
                                    #   test_aldea.py: Heal, Void Impact, Corrupted, Void Insect)
python ui_scenarios.py --shots      # Attack/Guard, Perfect Guard, Unbreakable Guard... por la UI
python ui_smoke.py --shots          # partida completa por la UI + capturas en tests/shots/
python ui_decks.py --shots          # menú (personajes y mazos) y editor de mazos por la UI (decks.json temporal)
```

## Cómo crear una carta nueva

Solo datos, en `cards/card_database.py`. `card()` aplica los valores por
defecto del tipo y tú sobrescribes lo que quieras:

```python
card(id="riposte", name="Riposte", short="RIP", card_type="GUARD", category=CATEGORY_SPECIAL,
     has_initiative=True,          # un GUARD que mantiene la ofensiva
     generates_hit=True,           # ...y hace hit si gana
     description="Guard con iniciativa: si gana, hace hit."),
```

Campos: `card_type`, `has_initiative`, `damage`, `generates_hit`, `causes_instability`,
`recovers_stability`, `priority`, `play_condition`
(`"unstable"` / `"stable"`) y `effects`. Las cartas no tienen coste propio: el
Mana lo decide la interacción. Las ATTACK, MAGIC y BREAK **deben declarar su
`damage`** (no se hereda del tipo; `card()` da error si falta). Las actuales
hacen 10. Añádela a un mazo en `DECKS`, que debe tener
`DECK_SIZE` cartas.

### Una SPECIAL nueva

Igual, con `card_type="SPECIAL"` y efectos `when: "special"`. El motor no
necesita cambios:

```python
card(id="mana_burst", name="Mana Burst", short="MBS", card_type="SPECIAL", category=CATEGORY_SPECIAL,
     description="Ganas 2 Mana al revelar.",
     effects=[{"type": "GAIN_MANA", "when": "special", "amount": 2}]),
```

## Cómo crear un efecto nuevo

En `cards/card_effects.py`:

```python
@effect("HEAL")
def _heal(data, ctx):
    ctx.owner.hp = min(ctx.owner.rules.MAX_HP, ctx.owner.hp + data.get("amount", 5))
    ctx.engine.emit("hp", ctx.owner.index, amount=data.get("amount", 5))
```

Y en la carta: `effects=[{"type": "HEAL", "when": "win", "amount": 5}]`.

### Una carta que aplica un estado

Sin tocar el motor, con `APPLY_STATUS` y condiciones opcionales sobre el
resultado **real** de la interacción:

```python
card(id="flame", name="Flame", short="FLM", card_type="SPECIAL", category=CATEGORY_SPECIAL,
     description="Si ganas la interacción con una carta MAGIC: BURN al rival.",
     effects=[{"type": "APPLY_STATUS", "when": "special", "status": "BURN",
               "if_outcome": "win", "if_main_type": "MAGIC"}]),
```

`target`: `"opponent"` (por defecto) o `"self"`. Condiciones: `if_outcome`
(`win`/`lose`/`draw`), `if_main_type` (tipo de tu acción principal) e `if_hit`
(tu acción hizo un HIT real). Un estado nuevo es una subclase de
`StatusDefinition` en `game/status.py` registrada en `STATUS_DEFS`.

Momentos (`when`):

| Momento | Cuándo se ejecuta |
|---|---|
| `special` | Al revelar, **antes del matchup** (cartas SPECIAL). Lo que cambia la Stability se aplica en el acto; el resto de banderas pasa al resto de la resolución |
| `cost` | Al calcular el coste de jugarla (`MODIFY_PLAY_COST`) |
| `pre` | Al comparar: cambia quién gana. Lo leen `game/rules.py: _pre_modifier` y `resolve_interaction` |
| `play` | Siempre que se juega la carta |
| `win` | Si la carta gana |
| `lose` | Si la carta pierde |

Condiciones opcionales: `vs` (solo contra un tipo, p. ej. `"MAGIC"`) y `vs_channel` (solo contra un canal de daño, p. ej. `"magic"`). Para que el motor reaccione a
algo nuevo, el efecto activa una bandera en `ctx.flags` (`extra_hits`,
`damage_bonus`, `mega_bonus`, `protect_combo`, `break_opponent_combo`,
`protect_stability`, `recover_stability`, `cause_instability`,
`end_sequence`...), que consultan los pasos de `CombatEngine._apply_result`.

## Cómo modificar las reglas

- **Números**: `game/config.py`.
- **Relaciones entre tipos**: `BEATS` en `game/config.py` (clave vence a valor).
- **Quién gana y su explicación**: `game/rules.py: resolve_interaction`.
- **Consecuencias de ganar**: los datos de cada carta y `game/combat.py: _apply_result`.
- **Daño y combo**: `_apply_damage`, `_apply_combo` y `_mega_combo` en `game/combat.py`.
- **Cuándo sigue la secuencia**: `game/rules.py: sequence_continues` y `game/combat.py: _decide_flow` y `_continue_or_end`.
