# Radio QWidget Extraction Plan

This document catalogs business logic found in QtWidgets UI files that must
be extracted into `core/radio/` or `infrastructure/radio/` in future branches.

## Files to Review

### `streaming/radio_widget.py`

| Class/Method | Responsibility | Target Service |
|---|---|---|
| `RadioWidget._load_stations()` | Loads station list from RadioManager | `RadioService.list_stations()` |
| `RadioWidget.set_filter(text)` | Filters stations by name/genre | `RadioService.search_stations()` |
| `RadioWidget._render_card(station)` | Builds QWidget card for a station | UI only — keep |
| `RadioWidget.station_selected` | Signal emitted on station click | UI only — keep |

### `streaming/radio_manager.py`

| Class/Method | Responsibility | Target Service |
|---|---|---|
| `RadioManager._load()` | JSON file I/O for stations | `SqliteStationRepository` |
| `RadioManager._save()` | JSON file I/O | `SqliteStationRepository` |
| `RadioManager.add()` | CRUD | `RadioService.create_station()` |
| `RadioManager.remove()` | CRUD | `RadioService.delete_station()` |
| `RadioManager.update()` | CRUD | `RadioService.update_station()` |
| `RadioManager.toggle_favorite()` | CRUD | `RadioService.set_favorite()` |
| `RadioManager.find_by_url()` | Query | `StationRepository.find_by_url()` |
| `RadioManager.mark_played()` | Tracking | `StationRepository.mark_played()` |

## Extraction Order

1. Replace `RadioManager` with `RadioService` inside `RadioWidget`
2. Wire `RadioService.event_bus` to `RadioWidget` Qt signals
3. Remove `RadioManager` entirely
4. Migrate JSON data to SQLite via import service
