# QML Migration Architecture Rules

## Principios

1. QML no accede directo a DB.
2. QML no accede directo al audio engine.
3. QML no duplica services.
4. QML usa bridges.
5. Bridges usan services.
6. Services usan backend real.
7. QtWidgets permanece como fallback hasta completar paridad.
8. QML no será default hasta pasar release gate.
9. Features experimentales deben estar gated.
10. Safe mode debe seguir funcionando.
11. QML no debe exponer filepaths sensibles al usuario.
12. Acciones destructivas deben requerir confirmación.
13. Los datos demo deben estar gated y nunca aparecer como datos reales.

## Flujo permitido

```text
QML Page → QML Bridge → Service → Backend real
```

Ejemplo válido:
```text
NowPlayingBar.qml → NowPlayingBridge → PlayerService → GStreamerEngine
LibraryPage.qml → LibraryBridge → LibraryDB → SQLite
AssistantPage.qml → MichiAIBridge → MichiAIService → ContextService
```

## Flujos prohibidos

```text
QML Page → SQLite directo
QML Page → GStreamer directo
QML Page → filesystem directo con paths expuestos
QML Page → mocks como datos reales
QML Page → lógica duplicada de QtWidgets
```

## Contratos mínimos de bridge

| Bridge | Debe exponer | No debe exponer | Tests requeridos |
|---|---|---|---|
| NavigationBridge | routeChanged, navigate(route), currentRoute | — | route dispatch, invalid route |
| NowPlayingBridge | trackTitle, trackArtist, coverPath, isPlaying, position, duration, volume, muted, shuffleEnabled, repeatMode, queue, history, togglePlay, next, prev, seek, setVolume, toggleMute, toggleShuffle, toggleRepeat | filepaths internos, GStreamer state | state changes, play/pause, seek |
| PlaybackBridge | trackTitle, trackArtist, trackAlbum, isPlaying, position, duration, volume, queue, history, togglePlay, next, prev, seek | filepaths internos | state changes, queue |
| LibraryBridge | songs, albums, artists, folders, refresh, search, filterByArtist, filterByAlbum, play_song, songCount | DB internals, indexer state | data loading, search, filter |
| SettingsBridge | sections, get(key), set(key, value) | filepaths, raw config | get/set roundtrip |
| ConnectionsBridge | serverList, state, scanForServers, addManualServer, removeServer, connectServer | credentials expuestas, tokens | server add/remove, connect |
| HomeBridge | snapshot stats, refresh | — | snapshot format |
| MichiAIBridge | suggestions, sendMessage, responseReceived, refresh | — | chat roundtrip |
| PlaylistsBridge | playlists, createPlaylist, deletePlaylist, addSong, removeSong | filesystem paths | CRUD operations |
| RadioBridge | stations, search, playStation, stopStation | streaming internals | station list, play/stop |
| MixBridge | mixes, currentMixTitle, currentSongs, loadMix | recommendation engine | mix loading |
| MetadataBridge | trackInfo, fields, saveField, loadTrack | filepaths | field read/write |
| AudioLabBridge | totalTracks, missingMetadata, missingCovers | — | stats |
| DevicesBridge | pairedDevices, discoveredDevices, pairedCount, syncState, pairDevice, unpairDevice, triggerSync | tokens, keys | pair/unpair |
| HomeAudioBridge | mode, zones, setMode, setZone, refresh | network internals | mode switching |
| ThemeBridge | isDarkMode | — | — |
| CoverBridge | coverKey, coverChanged, paint | filepaths | cover loading |
| AppBridge | appVersion, appName, safeMode, quit | — | version string |

## Reglas para migrar una página

1. Identificar paridad en QtWidgets: qué página/widget existe y qué hace.
2. Identificar service existente: si el backend ya está implementado.
3. Crear o extender bridge solo si falta contrato: si el bridge no expone lo que la página QML necesita.
4. QML debe consumir bridge, no backend directo: nunca importar servicios desde QML.
5. Crear tests de bridge: al menos roundtrip básico.
6. Crear tests QML de existencia/instanciación: verificar que la página carga.
7. Ejecutar smoke routes: verificar que la navegación funciona.
8. Validar safe mode: las features experimentales no deben romper safe mode.
9. Documentar gaps: qué queda pendiente para la siguiente iteración.
10. No borrar QtWidgets hasta release gate: QtWidgets es el fallback estable.

## Reglas para crear un bridge nuevo

```python
# Template mínimo para un bridge
from PySide6.QtCore import QObject, Signal, Property, Slot

class MiBridge(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = None  # Inyectar desde afuera

    @Property("QVariantList", notify=stateChanged)
    def items(self):
        return self._service.get_items() if self._service else []

    @Slot(str)
    def doAction(self, param):
        if self._service:
            self._service.do_action(param)
```

## Registro de bridge en qml_main.py

```python
# Cada bridge debe registrarse en qml_main.py como context property:
engine.rootContext().setContextProperty("miBridge", mi_bridge)
```

## Verificación post-migración

```bash
# Después de migrar una página:
ruff check .                  # lint
python -m compileall -q .     # compile
pytest tests/qml/ -q          # QML tests
python scripts/smoke_ui_routes.py  # navegación
python main.py --qml          # visual
```
