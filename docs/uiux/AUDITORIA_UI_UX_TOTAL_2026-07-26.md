# Auditoría UI/UX total — Michi Music Player

Fecha: 26 de julio de 2026
Alcance: shell QML, sistema visual, controles fundacionales, materiales, estados,
iconografía, búsqueda contextual y rutas especializadas de alto uso.

## Resultado ejecutivo

La interfaz tenía una buena dirección visual, pero no un sistema completamente
cerrado. El acabado variaba según la antigüedad de cada página: coexistían
controles redondos y rectangulares, colores literales y tokens, estados vacíos
duplicados, pictogramas SVG y glifos Unicode, búsquedas locales y contextuales,
y dos capas simultáneas para mostrar carga/error.

Este parche convierte esas decisiones dispersas en contratos reutilizables:

- acento azul frío para navegación, selección y foco;
- color cálido reservado a reproducción y ecualización;
- superficies obsidianas con textura original de muy baja intensidad;
- botones utilitarios con hover rectangular redondeado, no circular;
- caja óptica de iconos de acción 24×24 y trazo redondeado de 1,7 px;
- objetivo interactivo mínimo de 44 px;
- foco visible de 2 px;
- una sola búsqueda contextual por página;
- una sola autoridad visual para carga y error del shell;
- estados vacíos, no disponibles y de error con una gramática común.

El parche no cambia el layout aprobado de `NowPlayingBar` ni modifica la lógica
de reproducción.

## Datos de la auditoría

| Indicador | Antes | Después |
|---|---:|---:|
| Archivos QML auditados | 465 | 466 |
| Referencias a tokens de color inexistentes | 5 | 0 |
| Referencias tipográficas inexistentes | 1 | 0 |
| Colores literales no aprobados | 40 en 6 archivos | 0 |
| Estados con paywall ficticio | 3 | 0 |
| Bindings que ocultaban su propio objeto de contexto | 7 | 0 |
| Controles fundacionales con icono Unicode | 2 | 0 |
| Buscadores locales duplicados en páginas contextualizadas | 2 | 0 |
| Capas visuales de carga/error del shell | 2 | 1 |
| Rutas QML truncadas detectadas | 1 | 0 |

El repositorio mantiene 98 archivos de pruebas con aproximadamente 967
aserciones de contrato basadas en texto. No todas son incorrectas, pero esta
densidad explica por qué una prueba obsoleta puede obligar a reintroducir
chrome antiguo. La nueva prueba valida responsabilidades y semántica, no una
cadena de píxeles o la presencia de un control duplicado.

## Hallazgos priorizados

### P0 — Ruta Home Audio imposible de cargar

`ZoneDetailPage.qml` terminaba literalmente en `signal deleteR`. Se reconstruyó
la página completa y se conectaron sus operaciones reales:

- volumen de zona;
- silencio;
- selección de fuente;
- compensación de latencia;
- renombrar;
- agrupar y desagrupar;
- eliminar;
- actualización y recuperación de errores;
- adaptación compacta y navegación por teclado.

### P0 — Tokens referenciados pero inexistentes

Varias páginas solicitaban `surface`, `surfaceElevated`, `border`,
`accentFaint`, `accentGreen` y `smallSize` sin que existiera un contrato
completo. El tema ahora incorpora alias de compatibilidad y tokens semánticos
para glass, chrome, scrim, sheen, textura, estados y bordes.

### P0 — Objetos de contexto ocultos por propiedades homónimas

Siete componentes declaraban patrones como
`property var devicesBridge: typeof devicesBridge ...`. La propiedad local
ocultaba el objeto de contexto que intentaba leer y podía dejar la página en
estado no disponible aunque el bridge existiera. Se renombraron los handles
internos en Jobs, acciones de reproducción, Dispositivos, Apariencia y Radio.

### P1 — Fragmentación de superficie

`GlassCard`, `MichiCard` y los materiales aceptaban variantes que no siempre
tenían representación real. Se normalizaron `base`, `solid`, `glass`, `ghost`,
`primary`, `elevated` y las variantes de estado.

La textura no se replica por fila o tarjeta. Se aplica en superficies grandes
mediante `TextureOverlay`, evitando multiplicar nodos, capas y efectos.

### P1 — Geometría de interacción inconsistente

`MichiIconButton` usaba una cápsula circular para cualquier acción. Ahora:

- el valor predeterminado es un rectángulo redondeado de 12 px;
- `circular` queda como excepción explícita;
- selección y foco tienen bordes diferenciados;
- la selección puede mostrar un marcador inferior;
- el icono predeterminado es monocromático.

`MichiSearchField`, `MichiSegmentedControl`, `MichiComboBox`, botones, banners
y toasts comparten alturas, radios, foco y transición.

### P1 — Búsqueda duplicada

Radio y Playlists mantenían un buscador dentro del contenido pese a que el shell
ya ofrecía un contrato contextual. Ambas páginas publican ahora:

- placeholder;
- consulta;
- estado de carga;
- contador;
- acción de recarga.

El encabezado superior es el único propietario visual. Los formularios de
Radio mantienen sus campos de nombre, URL, códec y país porque no son
buscadores de contenido.

### P1 — Mensajes sin correspondencia con el producto

Radio, Mix y Conexiones afirmaban que se necesitaba una “suscripción premium”.
El repositorio no contiene un sistema de suscripciones que respalde esa
promesa. Los estados ahora explican la condición real: el bridge o backend no
está activo y puede configurarse desde Ajustes.

### P2 — Iconografía mezclada

Los packs existentes mezclan trazos de 1,2 a 2 px y algunos PNG rasterizados.
Este parche no reemplaza de forma riesgosa toda la iconografía de reproducción;
crea un núcleo consistente para acciones, estados y las páginas intervenidas.

Se añadieron 21 recursos originales:

- 16 iconos de acción;
- 3 iconos de estado;
- 2 texturas SVG.

No se incorporó contenido gráfico de terceros.

## Dirección visual

### Superficies

1. Fondo de aplicación: oscuro y estable.
2. Chrome de navegación: más opaco que el contenido.
3. Página: textura de grano apenas perceptible.
4. Glass: transparencia controlada con borde interno y brillo superior.
5. Hero: contornos abstractos originales, únicamente en áreas destacadas.
6. Popup: superficie fuerte, sin borde azul permanente.

El azul indica interacción o estado activo. No se usa para decorar todos los
bordes. Naranja, coral y violeta cálido permanecen en reproducción y EQ.

### Iconos

| Regla | Valor |
|---|---|
| Caja óptica | 24×24 |
| Trazo de acción | 1,7 px |
| Terminaciones | Redondeadas |
| Estado normal | Texto secundario |
| Hover | Texto primario |
| Activo | Azul Michi |
| Área interactiva | 44×44 mínimo |

### Movimiento

- 120–180 ms para hover, presión y cambio de borde;
- escala mínima solo al presionar;
- sin animación decorativa continua;
- respeto de `MichiTheme.reducedMotion`;
- textura estática, sin shader ni blur.

## Investigación web y decisión de recursos

Se revisaron recursos gráficos con licencia clara:

| Recurso | Uso potencial | Licencia / cautela | Decisión |
|---|---|---|---|
| [Tabler Icons](https://github.com/tabler/tabler-icons) | Base vectorial consistente | MIT | Referencia válida para ampliar el pack; no copiado |
| [PatternFills](https://github.com/iros/patternfills) | Patrones SVG repetibles | MIT | Válido, pero innecesario para este parche |
| [Invisible Textures](https://github.com/timscargill/Invisible-Textures) | Texturas monocromas sutiles | MIT | Referencia visual; no copiado |
| [Hero Patterns](https://heropatterns.com/) | Patrones de fondo SVG | CC BY 4.0 | Requiere atribución; no incorporado |
| [Haikei](https://haikei.app/) | Generación de fondos abstractos | Revisar términos del recurso exportado | Solo ideación |
| [fffuel](https://fffuel.co/license/) | Generadores SVG | Permite uso, restringe redistribución de assets | No adecuado para copiar al repositorio |
| [PNGTextures](https://github.com/javve/pngtextures.com) | Catálogo de texturas | Revisar licencia de cada recurso | No incorporado |

La solución usa dos texturas originales de Michi. Esto evita contaminación de
licencias y permite redistribuir el parche junto al proyecto GPL.

## Decisiones específicas para QML

La documentación oficial de
[Qt Quick MultiEffect](https://doc.qt.io/qt-6/qml-qtquick-effects-multieffect.html)
indica que blur y shadow son las funciones más costosas y recomienda limitar el
tamaño de las fuentes procesadas. La documentación de
[Item layers](https://doc.qt.io/qt-6/qml-qtquick-item.html) advierte que las
capas rompen el batching y que su uso excesivo aumenta el coste de render.

Por ello, este parche:

- no añade blur;
- no activa `layer.enabled` por tarjeta;
- no genera sombras por fila;
- usa `Image.Tile` para grano estático;
- reserva contornos para hero;
- conserva `MultiEffect` solo en el componente pequeño de icono monocromático.

## Accesibilidad

El contrato usa 44 px como mínimo de producto. WCAG 2.2 define 24×24 CSS px
como mínimo AA para el criterio de tamaño de objetivo y recomienda objetivos
mayores cuando sea posible:
[Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

El foco adopta un perímetro sólido de 2 px y un halo exterior discreto. Esta
dirección coincide con la guía de
[Focus Appearance](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html),
que ejemplifica un perímetro de 2 px y exige contraste perceptible.

## Estrategia de pruebas

Se añadió `scripts/audit_qml_ui.py`, ejecutable sin PySide6:

```bash
python scripts/audit_qml_ui.py --strict
```

Valida:

- referencias de tema;
- bindings que ocultan objetos de contexto;
- colores fuera de allowlist;
- paywalls ficticios;
- glifos Unicode en fundamentos;
- buscadores duplicados;
- propiedad del estado del shell;
- tamaño interactivo;
- sintaxis XML y caja óptica de los nuevos SVG.

La suite runtime sigue siendo obligatoria en un equipo con PySide6:

```bash
pytest -q tests/qml/test_uiux_system_contract.py
pytest -q tests/qml/test_qml_components.py
pytest -q tests/qml/test_qml_compile_all.py
pytest -q tests/qml/test_qml_instance_all.py
```

## Límites deliberados

- No se cambió la lógica de audio.
- No se alteró la composición aprobada de `NowPlayingBar`.
- No se sustituyeron los iconos cálidos de transporte.
- No se importaron texturas de repositorios externos.
- No se deshabilitaron pruebas.
- No se cambiaron archivos de Michi AI que ya estaban pendientes en la copia de
  trabajo.

## Criterios de aceptación visual

1. Ningún hover utilitario es circular salvo `circular: true`.
2. No aparece una segunda búsqueda en Radio, Playlists o Biblioteca.
3. El foco se distingue sin depender únicamente del color de relleno.
4. La textura es perceptible solo al observar la superficie, no sobre el texto.
5. La ruta `zone_detail` carga y conserva todas sus operaciones.
6. Radio, Mix y Conexiones explican disponibilidad real, no monetización ficticia.
7. El shell no muestra dos spinners o dos errores superpuestos.
8. A 800×600 ningún control fundamental tiene un objetivo menor de 44 px.
