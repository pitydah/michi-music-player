# Smoke Test Checklist — Music Player

## Instrucciones

Marca cada caso con `[x]` cuando pase la prueba. Anota fallas, bugs o comportamientos extraños en la columna **Notas**.

---

## 1. Inicio / Home

| Caso | Estado | Notas |
|---|---|---|
| Abrir la app desde frío (splash → home) | [ ] | |
| Home carga sin errores visibles en consola | [ ] | |
| Texto recortado al cargar (no hay contenido fantasma) | [ ] | |
| Las tarjetas/secciones principales se renderizan completas | [ ] | |
| Clic en una tarjeta → navega a la sección correspondiente | [ ] | |
| Scroll vertical suave en lista de tarjetas | [ ] | |
| Redimensionar a 320 px de ancho → layout se adapta sin solapamiento | [ ] | |
| Tab navega en orden lógico (tarjeta → tarjeta → footer) | [ ] | |
| Enter activa la tarjeta enfocada | [ ] | |
| Escape no rompe la navegación (cierra modales si hay) | [ ] | |

---

## 2. Biblioteca — álbumes

| Caso | Estado | Notas |
|---|---|---|
| Navegar: Inicio → Biblioteca → Álbumes | [ ] | |
| Estado vacío: mensaje "No hay álbumes" y botón de acción | [ ] | |
| Estado con datos: grid de álbumes con carátula, título, año | [ ] | |
| Clic en álbum → abre vista detalle con lista de canciones | [ ] | |
| Botón de reproducción (▶) en la vista detalle reproduce desde el inicio | [ ] | |
| Menú contextual en álbum (Agregar a cola, Agregar a playlist, etc.) | [ ] | |
| Scroll vertical continuo sin saltos ni cuadrícula rota | [ ] | |
| Ventana estrecha (360 px): grid cambia a 1-2 columnas sin cortar carátulas | [ ] | |
| Tab y Enter sobre las tarjetas de álbum | [ ] | |
| Clipping: nombres largos de álbum no se solapan con otros elementos | [ ] | |

---

## 3. Biblioteca — artistas

| Caso | Estado | Notas |
|---|---|---|
| Navegar: Inicio → Biblioteca → Artistas | [ ] | |
| Estado vacío: mensaje informativo | [ ] | |
| Lista/grid de artistas con nombre, imagen (o inicial) | [ ] | |
| Clic en artista → vista con discografía y canciones | [ ] | |
| Botón ▶ en vista artista reproduce toda la discografía | [ ] | |
| Menú contextual en artista (Reproducir después, Agregar a playlist) | [ ] | |
| Scroll en lista larga de artistas | [ ] | |
| Redimensionar: lista responsiva sin perder legibilidad | [ ] | |
| Teclado: navegación con Tab por tarjetas | [ ] | |
| Clipping: nombres de artista con tilde o caracteres especiales se ven completos | [ ] | |

---

## 4. Biblioteca — canciones

| Caso | Estado | Notas |
|---|---|---|
| Navegar: Inicio → Biblioteca → Canciones | [ ] | |
| Estado vacío: "No hay canciones" | [ ] | |
| Lista ordenada con #, título, artista, duración, álbum | [ ] | |
| Clic en una canción → empieza a reproducir desde esa canción | [ ] | |
| Botón de menú (⋯) en cada fila → opciones disponibles | [ ] | |
| Scroll horizontal no aparece (columnas se ajustan al ancho) | [ ] | |
| Ventana estrecha: columnas se ocultan (duración y álbum colapsados) | [ ] | |
| Tab navega fila por fila; Enter la reproduce | [ ] | |
| Escape desde menú contextual lo cierra | [ ] | |
| Clipping: títulos largos muestran ellipsis sin romper la fila | [ ] | |

---

## 5. Biblioteca — carpetas

| Caso | Estado | Notas |
|---|---|---|
| Navegar: Inicio → Biblioteca → Carpetas | [ ] | |
| Estado vacío: mensaje "Agrega una carpeta" | [ ] | |
| Navegación por árbol de directorios (expandir/colapsar) | [ ] | |
| Clic en archivo de audio → reproduce inmediatamente | [ ] | |
| Ruta completa visible en breadcrumb o cabecera | [ ] | |
| Scroll en árbol grande (100+ carpetas) | [ ] | |
| Redimensionar: árbol se ajusta sin truncar rutas | [ ] | |
| Tab navega elementos expandibles; Enter abre/cierra carpeta | [ ] | |
| Escape no cierra la vista si hay confirmación de carga pendiente | [ ] | |
| Clipping: rutas largas con ellipsis o tooltip al hover | [ ] | |

---

## 6. Biblioteca — géneros

| Caso | Estado | Notas |
|---|---|---|
| Navegar: Inicio → Biblioteca → Géneros | [ ] | |
| Estado vacío: mensaje claro | [ ] | |
| Lista de géneros con badge de cantidad | [ ] | |
| Clic en género → filtra canciones/álbumes de ese género | [ ] | |
| Botón ▶ en etiqueta de género reproduce mezcla aleatoria | [ ] | |
| Scroll vertical en lista de géneros | [ ] | |
| Ventana estrecha: layout en lista simple en lugar de grid | [ ] | |
| Tab y Enter sobre cada género | [ ] | |
| Escape desde vista filtrada vuelve a la lista completa | [ ] | |
| Clipping: nombres compuestos "Rock & Roll" se ven completos | [ ] | |

---

## 7. Now Playing / Reproducción

| Caso | Estado | Notas |
|---|---|---|
| Abrir Now Playing desde cualquier sección (clic en minibar/fab) | [ ] | |
| Sin canción activa: pantalla en gris o mensaje "Nada en reproducción" | [ ] | |
| Con canción activa: carátula, título, artista, barra de progreso | [ ] | |
| Botones ▶/⏸, ⏮, ⏭ funcionan | [ ] | |
| Barra de progreso: clic en posición adelanta/atrasa | [ ] | |
| Volumen: slider funcional y sin clipping en el label | [ ] | |
| Like/Dislike (♡) se refleja inmediatamente | [ ] | |
| Flecha atrás (←) cierra Now Playing | [ ] | |
| Teclado: Espacio → play/pause; ← → atrás; → → siguiente | [ ] | |
| Redimensionar: layout responsivo, carátula no se sale del viewport | [ ] | |

---

## 8. Cola / Queue

| Caso | Estado | Notas |
|---|---|---|
| Abrir cola desde Now Playing (tap en icono lista) | [ ] | |
| Cola vacía: mensaje "Cola vacía" con sugerencia | [ ] | |
| Cola con canciones: lista ordenada con draggable handle | [ ] | |
| Arrastrar item para reordenar (drag & drop) | [ ] | |
| Botón eliminar (✕) en cada item → quita de cola | [ ] | |
| Clic en item → reproduce desde esa canción | [ ] | |
| "Reproducir después" desde menú contextual agrega item en 2° posición | [ ] | |
| Scroll en cola larga (50+ canciones) | [ ] | |
| Ventana estrecha: drag & drop sigue funcionando | [ ] | |
| Teclado: Tab por items; Delete elimina el item enfocado | [ ] | |

---

## 9. Playlists

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Playlists desde navegación principal | [ ] | |
| Estado vacío: "No hay playlists" + botón Crear | [ ] | |
| Crear playlist: diálogo con nombre, descripción, carátula | [ ] | |
| Playlist con canciones: lista ordenada, arrastrable | [ ] | |
| Botón ▶ reproduce toda la playlist | [ ] | |
| Menú contextual en playlist (Editar, Duplicar, Eliminar) | [ ] | |
| Diálogo de confirmación al eliminar playlist | [ ] | |
| Scroll en playlist de 100+ canciones | [ ] | |
| Ventana estrecha: grid de playlists colapsa a 1 columna | [ ] | |
| Teclado: Tab entre playlists; Enter abre; Delete con confirmación | [ ] | |

---

## 10. Mix

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Mix | [ ] | |
| Sin datos de escucha: "Explora música para generar mixes" | [ ] | |
| Mix generado: tarjetas con carátula, nombre y duración estimada | [ ] | |
| Botón ▶ en tarjeta reproduce el mix | [ ] | |
| Botón Refresh/New Mix → genera nueva mezcla | [ ] | |
| Menú contextual en tarjeta (Agregar a biblioteca, Compartir) | [ ] | |
| Scroll horizontal en fila de mixes (si aplica) | [ ] | |
| Redimensionar: wraps a grid en pantalla angosta | [ ] | |
| Teclado: Tab por tarjetas; Enter reproduce | [ ] | |
| Clipping: descripción larga con ellipsis | [ ] | |

---

## 11. Audio Lab

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Audio Lab | [ ] | |
| Interfaz se ve completa sin errores de CSS | [ ] | |
| Toggle master habilitar/deshabilitar audio lab | [ ] | |
| Sliders de efectos se mueven suavemente | [ ] | |
| Cambio en slider se refleja en audio (en tiempo real o con botón aplicar) | [ ] | |
| Botón Reset vuelve a valores por defecto | [ ] | |
| Redimensionar: sliders no se salen del contenedor | [ ] | |
| Teclado: Tab entre sliders; flechas izquierda/derecha ajustan valor | [ ] | |
| Escape desde un diálogo interno (confirmación) | [ ] | |
| Clipping: etiquetas de slider no se cortan | [ ] | |

---

## 12. Ecualizador

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Ecualizador desde Audio Lab o menú | [ ] | |
| Bandas del ecualizador se renderizan correctamente | [ ] | |
| Arrastrar banda hacia arriba/abajo → cambio audible | [ ] | |
| Presets (Rock, Pop, Jazz, Clásico, Plano) cargan valores correctos | [ ] | |
| Preset personalizado se guarda al mover bandas | [ ] | |
| Botón Reset/Flat | [ ] | |
| Redimensionar: bandas no se solapan ni se salen del canvas | [ ] | |
| Teclado: Tab por presets; Enter aplica; Escape cierra | [ ] | |
| Ventana estrecha: ecualizador se desplaza verticalmente sin romperse | [ ] | |
| Clipping: etiquetas de frecuencia en eje X se ven completas | [ ] | |

---

## 13. Dispositivos / Devices

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Dispositivos | [ ] | |
| Sin dispositivos: "No hay dispositivos conectados" + botón buscar | [ ] | |
| Con dispositivos: lista con nombre, tipo, estado (conectado/disponible) | [ ] | |
| Clic en dispositivo → cambia salida de audio | [ ] | |
| Botón Refresh busca dispositivos nuevos | [ ] | |
| Desconectar dispositivo desde menú contextual | [ ] | |
| Scroll en lista larga | [ ] | |
| Redimensionar: filas responsivas | [ ] | |
| Teclado: Tab por lista; Enter conecta/desconecta | [ ] | |
| Clipping: nombres de dispositivo largos con ellipsis | [ ] | |

---

## 14. Conexiones / Connections

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Conexiones (en menú lateral o settings) | [ ] | |
| Sin conexiones: "Conecta tus servicios" con lista de proveedores | [ ] | |
| Con conexiones activas: muestra servicio, estado, última sincronización | [ ] | |
| Botón Conectar inicia flujo OAuth (abre navegador o modal) | [ ] | |
| Conexión exitosa: estado cambia a "Conectado" | [ ] | |
| Botón Desconectar → confirmación → elimina conexión | [ ] | |
| Error de conexión: mensaje legible y botón Reintentar | [ ] | |
| Scroll en lista de conexiones | [ ] | |
| Ventana estrecha: layout pila en lugar de fila | [ ] | |
| Teclado: Tab por botones y estados | [ ] | |

---

## 15. Home Audio

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Home Audio | [ ] | |
| Sin dispositivos: mensaje "No hay dispositivos Home Audio" | [ ] | |
| Con dispositivos: tarjetas con nombre, zona, estado | [ ] | |
| Clic en dispositivo → panel de control (play/pause, volumen, grupo) | [ ] | |
| Botón Agrupar con otro dispositivo | [ ] | |
| Desagrupar desde menú contextual | [ ] | |
| Scroll en grid de dispositivos | [ ] | |
| Redimensionar: tarjetas responsivas sin perder info | [ ] | |
| Teclado: Tab entre tarjetas; Enter abre panel | [ ] | |
| Clipping: nombres de zona no se cortan | [ ] | |

---

## 16. Configuración / Settings

| Caso | Estado | Notas |
|---|---|---|
| Navegar a Configuración | [ ] | |
| Todas las secciones de settings se renderizan (Audio, Cuenta, Apariencia, etc.) | [ ] | |
| Toggle switches funcionan (on/off) | [ ] | |
| Sliders (tamaño fuente, opacidad) se actualizan en vivo | [ ] | |
| Selectores (idioma, tema) cambian la UI inmediatamente | [ ] | |
| Botón de cerrar sesión → confirmación → redirige a login | [ ] | |
| Scroll en página de settings (múltiples secciones) | [ ] | |
| Ventana estrecha: settings en lista vertical legible | [ ] | |
| Teclado: Tab por todos los controles; Space activa toggle | [ ] | |
| Clipping: etiquetas de opción completas en todos los anchos | [ ] | |

---

## 17. Michi Assistant

| Caso | Estado | Notas |
|---|---|---|
| Abrir Michi Assistant (atalajo o botón) | [ ] | |
| Interfaz del asistente se despliega sin errores | [ ] | |
| Entrada de texto: escribir comando → respuesta del asistente | [ ] | |
| Comandos básicos: "reproduce [canción]", "siguiente", "pausa" | [ ] | |
| El asistente responde con texto y/o acción ejecutada | [ ] | |
| Cerrar asistente con ✕ o Escape | [ ] | |
| Reabrir conserva el historial de la sesión | [ ] | |
| Redimensionar: burbuja de chat no se sale del viewport | [ ] | |
| Teclado: Enter envía mensaje; Escape cierra; Tab en input | [ ] | |
| Clipping: mensajes largos con scroll interno | [ ] | |

---

## Resumen por sección

| Sección | Navegación | Datos | Botones | Teclado | Scroll | Clipping | Observaciones |
|---|---|---|---|---|---|---|---|
| Inicio / Home | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Biblioteca — álbumes | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Biblioteca — artistas | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Biblioteca — canciones | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Biblioteca — carpetas | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Biblioteca — géneros | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Now Playing / Reproducción | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Cola / Queue | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Playlists | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Mix | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Audio Lab | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Ecualizador | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Dispositivos / Devices | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Conexiones / Connections | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Home Audio | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Configuración / Settings | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
| Michi Assistant | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | |
