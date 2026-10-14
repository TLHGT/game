# Assets

Esta carpeta puede estar vacía: si falta un PNG, el juego genera un
placeholder automáticamente (`render/placeholders.py`).

Para usar arte real, guarda un PNG con el nombre de la clave. Si no existe el
nombre exacto, se prueban versiones más cortas quitando sufijos
(`player_left_1.png` → `player_left.png` → `player.png`).

El sprite se dibuja con su **borde inferior centrado en los pies** del objeto.

| Clave                                  | Uso                                        |
|----------------------------------------|--------------------------------------------|
| `player_{down,up,left,right}_{0,1,2}`  | Avatar por defecto (0 = quieto, 1-2 = pasos) |
| `avatar_{blaze,jurgenoid}_{dir}_{0,1,2}` | Avatares propios de los personajes       |
| `npc_{look}`                           | NPC (`npc_woodcutter`, `npc_traveler`...)  |
| `tree_{0-3}`, `pine_{0-1}`             | Árboles                                    |
| `rock`, `stump`, `log`, `bush`, `tall_grass`, `pillar`, `pillar_broken` | Decorado |
| `stalagmite_{0-2}`, `cave_rock_{0-1}`, `crystal_{0-1}`, `glowshroom` | Decorado de cueva |
| `wall_cave`, `rootwall`, `rootwall_burning{0,1}` | Muro de roca / maraña de raíces (Blaze) |
| `wolf_fire`, `wolf_ice`                | Fire Wolf / Ice Wolf (miran a la derecha)  |
| `perk_{quick_revive,juggernog,speed_cola,double_tap,pack_a_punch}_{on,off}` | Máquinas de ventajas |
| `generator_{off,on}`                   | Activador de energía de cada piso          |
| `wall_rubble`                          | Derrumbe que bloquea un paso               |
| `chest_closed`, `chest_open`           | Cofre                                      |
| `sign`, `tablet`, `shrine`             | Carteles / inscripciones / altar           |
| `radio_off`, `radio_static`, `radio_on`| Radio del easter egg                       |
| `wall_stone`, `wall_ruin`              | Muros (se escalan al tamaño del muro)      |
| `door_{wood,gate,secret}_{closed,open}`| Puertas (se escalan al tamaño de la puerta)|
| `ground_grass`, `ground_forest`        | Texturas de suelo repetibles (opcionales)  |
