# Accessibility Review — Presentation UI/UX

Estado de accesibilidad del modo presentación y reglas que deben mantenerse.

## Navegación por teclado

- Toda acción accesible vía teclado: navegación del sidebar, activación de
  botones, transporte de reproducción, diálogos.
- Orden de tabulación lógico: sidebar → header → contenido → player bar.
- `ActionButton` soporta activación por teclado (Enter/Espacio) con focus
  ring visible.

## Foco

- Focus ring visible en todos los controles interactivos (azul `#8FB7FF`).
- Nunca eliminar el outline sin reemplazo visible.
- El foco entra y sale de diálogos de forma contenida (focus trap en
  `ConfirmDialog`).

## Roles y nombres accesibles

- Controles con `Accessible.role` y `Accessible.name` donde aplica
  (botones, items de navegación, badges de estado).
- Sin emojis como sustitutos de iconografía o etiquetas: sistema de glifos.

## Internacionalización (qsTr)

- Cobertura: **525 strings** envueltos en `qsTr()`.
- Regla: todo string visible al usuario pasa por `qsTr()`, sin literales
  crudos en QML.

## Reduced motion

- Cuando el sistema solicita reduced-motion, se desactivan animaciones
  decorativas (ambient glow animado, transiciones de página, scale en
  botones). El estado sigue siendo comunicado por color/badge, no por
  movimiento.

## Targets mínimos

- Objetivos táctiles/de puntero: mínimo 32×32 px en controles de navegación
  y botones de acción; 44×44 px en transporte de reproducción.
- Opacidad de texto: mínimo 0.78 en navegación (regla absoluta del
  proyecto); 0.85 como baseline de items.

## Contraste

- Texto principal sobre canvas `#090B11`: opacidad ≥ 0.85.
- Acento `#8FB7FF` usado como indicador siempre acompañado de texto o
  icono: el color nunca es el único canal de información.
