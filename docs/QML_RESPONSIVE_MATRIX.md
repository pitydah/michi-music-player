# QML Responsive Matrix

Fecha: 2026-07-05

Tipo de evaluacion: auditoria estatica de layout QML. No se modifico codigo ni se ejecutaron capturas visuales. La matriz se basa en `Main.qml`, shell, componentes y paginas prioritarias.

## Viewports

| Viewport | Estado esperado | Riesgos principales | Paginas/componentes afectados | Prioridad |
|---|---|---|---|---|
| 800x600 | No soportado formalmente | `Main.qml` define `minimumWidth: 1024` y `minimumHeight: 640`; sidebar 250 + now playing 100 deja poco contenido; toolbar de biblioteca no cabe. | `Main.qml`, `AppShell.qml`, `Sidebar.qml`, `HeaderBar.qml`, `LibraryPage.qml`, `NowPlayingBar.qml` | P1 |
| 1024x768 | Parcial | Cabe por minimo cercano, pero sidebar 250 consume 24%; Header search y Library toolbar compiten; now playing horizontal puede truncar volumen/extra. | Shell, Library, NowPlayingBar, PlaybackPage | P1 |
| 1280x720 | Aceptable con deuda | Densidad util, pero altura baja reduce listas y paginas con heroes de 140 px; playback queue/history queda ajustado. | Playback, Library, Radio, SmartTagging, AudioLab | P2 |
| 1366x768 | Bueno para alpha | Layout principal usable; toolbar de biblioteca todavia puede apretarse si hay badges y botones visibles. | LibraryPage, HeaderBar, HomePage | P2 |
| 1920x1080 | Mejor punto actual | Shell, biblioteca y playback respiran bien; cards 2 columnas se ven correctas. | General | P3 |
| 2560x1440 | Usable pero poco escalado | Font pixel sizes fijos pueden sentirse pequenos; grids mantienen celdas pequenas y dejan mucho whitespace. | Album grids, AudioLab, Connections, HomeAudio | P2 |
| 3840x2160 | Usable con riesgo de miniaturizacion | Sin density/scale tokens, la UI depende de Qt/OS scaling; si escala 1.0, textos 10-13 px y controles 22-36 px son pequenos. | Todo QML, especialmente badges/meta/controls | P2 |

## Breakpoints recomendados

| Breakpoint | Rango | Layout esperado |
|---|---:|---|
| compact | 800-1023 px | Sidebar collapsed por defecto; header sin search ancho; now playing compacto; grids 1 columna; toolbar de biblioteca wrap/overflow visible. |
| regular | 1024-1439 px | Sidebar normal o collapsible; grids 2 columnas; now playing con controles completos pero volumen compacto. |
| wide | 1440-2559 px | Layout actual principal; grids 2-4 columnas segun contenido; playback 2 columnas. |
| ultra | 2560+ px | Constrained content width para paginas de lectura/formularios; grids con mas columnas; tipografia/density scale opcional. |

## HiDPI

| Escala | Estado esperado | Riesgo | Recomendacion |
|---|---|---|---|
| 125% | Probablemente usable si Qt scaling esta activo | Algunos controles de 22/24 px siguen bajos como hit target | Definir minimo tactil/desktop de 32-36 px para acciones secundarias y 40-44 para primarias. |
| 150% | Usable con iconos raster a revisar | PNG 32 px puede verse suave segun sourceSize/devicePixelRatio | Preferir SVG monocromo o assets 2x para iconos principales. |
| 200% | Riesgo de overflow en toolbar y dialogs fijos | `CommandPalette` 400x320, dialogs 280/320, heroes fijos | Usar width relativo con max/min y content-driven height. |

## Riesgos responsive por componente

| Componente | Riesgo | Accion |
|---|---|---|
| `Sidebar.qml` | Ancho fijo 250 y collapse manual; no auto-collapse por viewport | Auto compact bajo 1024 px y persistencia de estado. |
| `HeaderBar.qml` | Search `Math.min(280, root.width * 0.25)` puede quedar pequeno o competir con titulo | Ocultar/compactar search bajo compact; usar command palette como busqueda global. |
| `NowPlayingBar.qml` | Layout por porcentajes 22/40/20 mas spacers; boton extra de 22 px | Variante compact: cover 40, info elided, controles esenciales, volumen en menu. |
| `LibraryPage.qml` | Toolbar de 40 px con search, badges y 3 botones en una fila | Toolbar wrap o overflow menu; badges a segunda linea bajo regular. |
| `SongTable.qml` | Columnas por porcentajes y play button hover invisible consumen ancho | Column schema con min widths y columnas ocultables en compact. |
| Album views | Celdas fijas 150-200 px | Calcular cellWidth por available width; 1/2/3/4+ columnas. |
| `CommandPalette.qml` | 400x320 fijo | `width: Math.min(parent.width - margins, 560)` y height relativa. |
| `HomePage.qml` | Row de dos cards 48% | Cambiar a Column bajo 1100 px. |
| `AudioLabPage.qml` | Grids de 2 columnas fijas | 1 columna compact, 2 regular, 3 wide. |
| `ConnectionsPage.qml` | Grid 2 columnas para servers | 1 columna compact. |
| `HomeAudioModeSelector.qml` | Altura fija 120 y cards internas | Segment control compacto o tabs bajo 1024. |

## Reglas de aceptacion futuras

| Regla | Verificacion |
|---|---|
| 800x600 renderiza sin controles cortados | Capturas QML en offscreen o Playwright/Qt screenshot por ruta principal. |
| 1024x768 no oculta acciones primarias | Smoke visual: home, library, playback, settings. |
| 4K no deja contenido flotando sin max-width | Captura 3840x2160 con paginas de formularios y listas. |
| 125/150/200% mantienen hit targets | Medicion visual o test QML de sizes minimos. |
| No hay texto solapado en botones/cards | Test QML con strings largos y width compact. |

## Matriz por pagina prioritaria

| Pagina | 800x600 | 1024x768 | 1920x1080 | 4K | Accion |
|---|---|---|---|---|---|
| Main/AppShell | Bloqueado | Ajustado | Bueno | Pequeno | Breakpoints y min size. |
| Sidebar/Header | Ajustado | Aceptable | Bueno | Bueno | Auto collapse y header compact. |
| NowPlayingBar | Riesgo alto | Riesgo medio | Bueno | Pequeno | Variante compact y hit targets. |
| PlaybackPage | 1 columna necesaria | Aceptable | Bueno | Muy abierto | Panel widths y max content. |
| LibraryPage | Toolbar no cabe | Ajustado | Bueno | Bueno | Toolbar responsive. |
| SongTable | Columnas cortadas | Ajustado | Bueno | Bueno | Columnas ocultables/min-width. |
| Album views | 1 columna | 2-3 columnas | Bueno | Celdas pequenas | Responsive cells. |
| Metadata/SmartTagging | Formularios ajustados | Aceptable | Bueno | Muy ancho | Max width para formularios. |
| Lyrics | Aceptable si tokens corrigen | Bueno | Bueno | Texto muy ancho | Max line width. |
| Radio/Mix/Settings | Aceptable | Bueno | Bueno | Muy abierto | Max content + empty states. |
| AudioLab/Connections/HomeAudio | 1 columna necesaria | Ajustado | Bueno | Cards pequenas | Grid responsive. |
