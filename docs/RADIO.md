# Radio en Michi Music Player

## Estado actual

La radio esta funcional y completamente integrada en la pestana "En vivo" de Transmisiones.

## Componentes

- `RadioWidget` (`streaming/radio_widget.py`): Lista/cards de emisoras con busqueda, edicion, favoritos, contexto.
- `RadioManager` (`streaming/radio_manager.py`): Gestiona emisoras en JSON, add/remove/duplicate/favorite/play.
- `RadioStation`: Modelo con id, name, url, image, tags, country, codec, favorite, played_at.

## Funcionalidad

- Anadir emisora por URL (dialogo con validacion)
- Editar nombre, URL, imagen, tags, pais, codec
- Duplicar emisora
- Marcar favorita
- Copiar URL al portapapeles
- Abrir web de la emisora
- Eliminar emisora
- Busqueda por nombre, URL, tags, pais
- Reproducir: emite `station_selected(url, name)` -> `PlayerService.play_url()`
- Grabacion via GStreamer (experimental)

## Cards

Cada emisora se muestra como `_StationCard` con:
- Nombre
- URL acortada
- Badge STREAM
- Badge favorito (estrella)
- Tags, pais, codec si existen
- Menu contextual con todas las acciones

## Integracion con Transmisiones

La radio se envuelve en `RadioLiveTab` dentro de `BroadcastHubPage`.
La señal `station_selected` se reemite como `BroadcastHubPage.play_track_requested`.

## Pendiente

- Metadata ICY: mostrar titulo actual/cancion en NowPlayingBar.
- Diagnostico de stream: validar URL, detectar tipo, content-type.
