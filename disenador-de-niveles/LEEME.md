# Diseñador de niveles

Editor visual de mapas para el prototipo **Bosque de Arken**. No hay que
instalar nada: abre `disenador.html` con doble clic (mejor en **Edge o
Chrome**, que permiten guardar directamente en un archivo).

```
disenador-de-niveles/
├── disenador.html        el editor
├── probar_mapa.bat       arrastra un mapa .json encima para jugarlo
├── mis_mapas/            guarda aquí tus mapas
└── ejemplos/
    └── bosque_de_arken.json   el mapa del juego, para curiosear
```

## Cómo se diseña un mapa

1. **Pinta las zonas caminables** con 🖌️ (tecla `B`). Todo lo que no pintes es
   bosque denso: el juego lo llena de árboles y no se puede atravesar.
   - Clic izquierdo pinta claro, clic derecho vuelve a poner bosque.
   - `Mayús` + arrastrar pinta un rectángulo entero.
   - Cada casilla son 40 px del juego. Un pasillo cómodo mide 3 casillas o más.
2. **Traza caminos** con 〰️ (tecla `P`): clic para cada punto, doble clic para
   terminar. Usa *Principal* para la ruta de la historia, *Sendero* para los
   desvíos y *Pisadas* para rincones casi secretos.
3. **Coloca cosas**: arrastra un elemento de la paleta al mapa, o haz clic en
   él y luego clic en el mapa (puedes poner varios seguidos; `Esc` para parar).
4. **Selecciona** cualquier cosa (`V`) para editarla en el panel derecho:
   diálogos de NPC, contenido de cofres, textos, secretos…
5. **Deja notas** para Claude:
   - Cada elemento tiene un campo **📝 Nota para Claude** («este NPC debería
     dar una misión», «aquí quiero un puente roto»…).
   - El elemento **📝 Nota** (tecla `N`) es una nota suelta en cualquier punto.
   - Sin nada seleccionado, el panel muestra la **nota general del mapa**
     (ambiente, historia, ideas).
6. Mira la sección **Revisión** del panel: avisa de problemas como objetos
   dentro del bosque, puertas sin zona caminable debajo, secretos sin definir,
   IDs repetidos… Haz clic en un aviso para ir a él.

## Guardar y probar

- **Guardar** (`Ctrl+S`): guarda en `mis_mapas/<id>.json`. Usa como ID del
  mapa algo sin espacios (`aldea`, `cueva_norte`…).
- El editor guarda una copia automática en el navegador; si cierras sin
  guardar, la recuperas al volver a abrirlo.
- **Probar en el juego**: arrastra el `.json` sobre `probar_mapa.bat`.
  También: `python ..\main.py mis_mapas\aldea.json`.
- Las **salidas** buscan el mapa destino en la misma carpeta: si guardas
  `aldea.json` y `cueva.json` juntos y la salida de la aldea apunta a `cueva`,
  podrás ir de una a otra.
- **Abrir** cualquier mapa del juego (incluido el ejemplo) para modificarlo.
  Los mapas del juego están en `..\maps\`; por ejemplo el nivel del
  hospital: `hospital_exterior.json` (la caverna) y `hospital_lobby.json`,
  `hospital_piso1.json` ... `hospital_piso4.json` (arrastra
  `hospital_exterior.json` sobre `probar_mapa.bat` para jugarlo entero).
  **Ojo:** el diseñador aún no conoce los elementos de cueva (estalagmitas,
  cristales, tema `cave`...) ni los del hospital nuevo (ascensor, activadores de
  energía en forma de cuadro eléctrico, máquinas de ventajas, cartas en cofres,
  derrumbes): si abres y guardas esos mapas con él, se pierden. Los pisos del
  hospital se generan con `python tools/generar_hospital.py` (desde la carpeta del juego); la caverna,
  de momento, a mano.

## Cómo pasarle el mapa a Claude

Guárdalo y dile algo como:

> «Recrea en el juego el mapa `disenador-de-niveles/mis_mapas/aldea.json`;
> lee las notas.»

El archivo ya está en el formato del juego, así que lo que dibujas funciona tal
cual. Las notas viajan dentro del archivo (el juego las ignora) para que Claude
sepa qué falta por construir: mecánicas nuevas, gráficos, misiones…

## Atajos

| Tecla | Acción |
|---|---|
| Rueda del ratón | Zoom |
| Espacio + arrastrar / botón central / arrastrar en vacío | Mover la vista |
| `V` `B` `P` `N` | Seleccionar · Pintar · Camino · Nota |
| `Supr` | Borrar lo seleccionado |
| `Ctrl+D` | Duplicar |
| `Ctrl+Z` / `Ctrl+Y` | Deshacer / rehacer |
| `Alt` mientras mueves | Mover sin ajustar a la rejilla |
| `0` | Ver todo el mapa |
| `Esc` | Volver a seleccionar |

## Notas técnicas

- `probar_mapa.bat` asume que esta carpeta está dentro de la del juego (`finalidad`).
- Firefox no deja guardar directamente en un archivo: en ese caso «Guardar»
  descarga el `.json` y tendrás que moverlo a `mis_mapas/`.
- Las casillas caminables se guardan como rectángulos en `walkable`; el resto
  de elementos usa exactamente las mismas claves que `maps/forest.json`.
