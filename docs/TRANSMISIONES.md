# Transmisiones

Transmisiones es la seccion de Michi Music Player para **radio en vivo y podcasts**.

## Estructura

- **Sidebar**: item "Transmisiones" en el hub central.
- **Pagina**: `BroadcastHubPage` con header, summary cards y 5 tabs.
- **Compatibilidad**: la ruta antigua "radio" sigue funcionando y redirige a la pestana "En vivo".

## Tabs

| Tab | Descripcion |
|---|---|
| En vivo | RadioWidget existente. Anadir, editar, duplicar, favoritos, eliminar emisoras. |
| Podcasts | Grid de shows suscritos. Anadir feed RSS, ver episodios. |
| Episodios | Lista compacta con filtros (Todos, Nuevos, En progreso). Reproducir, ver progreso. |
| Descargas | Episodios descargados. Eliminar descarga. |
| Historial | Timeline de radio y podcasts escuchados. |

## Dependencias

- `RadioWidget` y `RadioManager` existentes.
- `PodcastManager` coordina `PodcastFeedParser` + `PodcastRepository`.
- `PodcastRepository` usa SQLite con WAL en `app_data_dir/podcasts.db`.
- `PodcastFeedParser` parsea RSS 2.0 y Atom con `xml.etree.ElementTree`.

## Archivos clave

| Archivo | Rol |
|---|---|
| `ui/broadcast/broadcast_hub_page.py` | Hub principal |
| `ui/broadcast/radio_live_tab.py` | Envuelve RadioWidget |
| `ui/broadcast/podcasts_tab.py` | Grid de shows |
| `ui/broadcast/episodes_tab.py` | Lista de episodios |
| `ui/broadcast/downloads_tab.py` | Descargas offline |
| `ui/broadcast/history_tab.py` | Historial |
| `ui/broadcast/add_feed_dialog.py` | Dialogo anadir feed RSS |
| `streaming/podcast_manager.py` | Logica de podcasts |
| `streaming/podcast_repository.py` | SQLite storage |
| `streaming/podcast_feed_parser.py` | Parser RSS/Atom |
| `streaming/podcast_downloads.py` | Descarga de episodios |
| `streaming/podcast_models.py` | Modelos de datos |
| `streaming/broadcast_history.py` | Historial JSON (legacy) |

## Tests

```
pytest tests/test_broadcast_navigation.py
```
