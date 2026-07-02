# Podcasts en Michi Music Player

## Arquitectura

```
AddFeedDialog (UI)
  -> PodcastManager.add_feed(url)
    -> PodcastFeedParser.parse_feed(url)
      -> xml.etree.ElementTree (RSS 2.0 / Atom)
    -> PodcastRepository.add_show()
    -> PodcastRepository.upsert_episode() (por cada episodio)
```

## Modelos

- `PodcastShow`: titulo, autor, feed_url, image_url, episode_count, unread_count, favorite
- `PodcastEpisode`: guid, titulo, audio_url, duration_seconds, position_seconds, played, downloaded, local_path
- `PodcastDownload`: episode_id, status, progress, local_path
- `BroadcastHistoryItem`: entry_type (radio|podcast), ref_id, titulo, duration, completed

## PodcastRepository (SQLite)

Tablas: `podcast_shows`, `podcast_episodes`, `podcast_downloads`, `broadcast_history`.

Indices: guid, podcast_id, published_at, played, downloaded, entry_type.

Metodos principales: add_show, update_show, remove_show, get_shows, find_show_by_feed_url, upsert_episode, get_episodes_for_show, get_recent_episodes, get_unplayed_episodes, get_in_progress_episodes, get_downloaded_episodes, set_episode_position, mark_episode_played, add_history, get_history, get_counts.

## PodcastFeedParser

Soporta RSS 2.0 y Atom. Extrae: title, description, link, image (itunes o RSS), author, language, categories, items con enclosure de audio, guid, pubDate, itunes:duration.

Ignora items sin enclosure de audio. Normaliza duracion a segundos. Normaliza fechas a ISO.

## PodcastManager

Metodos: add_feed, refresh_feed, refresh_all, remove_show, get_shows, get_episodes, get_recent_episodes, get_unplayed, get_in_progress, get_downloaded, set_episode_position, mark_episode_played, mark_episode_unplayed, toggle_favorite, mark_downloaded, add_history, get_history, clear_history, get_counts.

## Descargas

`PodcastDownloads.download_episode()` descarga via HTTP con progreso y cancelacion.
Los archivos se guardan en `app_data_dir/podcast_downloads/{show_name}/{episode}.mp3`.
`remove_download()` elimina el archivo fisico.

## Progreso y completado

- La posicion se guarda cada ~15 segundos durante la reproduccion.
- Cuando la posicion alcanza el 90% de la duracion, el episodio se marca como completado.
- `NowPlayingBar` muestra badges PODCAST, NUEVO, EN PROGRESO, COMPLETADO, DESCARGADO.
