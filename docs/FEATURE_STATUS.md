# Feature Status — Michi Music Player v0.2.0-alpha.1

## Porcentajes estimados

| Componente | % |
|---|---|
| Backend/core | 86% |
| QtWidgets clásico | 85% |
| QML Foundation estructural | 80% |
| QML funcional real | 70% |
| Playlists QML | 74% |
| Connections/Michi Link QML | 74% |
| Library QML | 76% |
| Release beta pública | 78% |
| **Estado global** | **85%** |

## Tabla de áreas

| Área | Estado | Notas |
|---|---|---|
| **Versión** | `0.2.0-alpha.1` | `importlib.metadata` canonical |
| **QtWidgets (fallback estable)** | ✅ Estable | `python main.py` |
| **QML Foundation** | ✅ Experimental | 16+ bridges, sidebar, 12 rutas |
| **Sidebar QML** | ✅ Experimental | 10 items |
| **NavigationBridge** | ✅ Experimental | VALID_ROUTES controladas |
| **CoverBridge** | ✅ Experimental | QQuickPaintedItem, cache 256 |
| **Library QML** | ✅ Experimental | Canciones, Álbumes, Artistas, Carpetas |
| **NowPlayingBar QML** | ✅ Experimental | Controles, seek, volumen, cover |
| **Michi AI** | ✅ Experimental | Chat funcional |
| **Playlists QML** | ✅ Experimental | Hub + detail |
| **Metadata Inspector** | ✅ Experimental | Read-only |
| **Mix QML** | ⚠️ En validación | 6 categorías |
| **Audio Lab QML** | ⬜ Placeholder | Bridge con health stats |
| **Settings QML** | ⬜ Placeholder | Bridge + settings_manager |
| **Radio QML** | ⬜ Placeholder | Bridge + RadioManager |
| **Home Audio QML** | ⬜ Placeholder | Bridge + HA/Snapcast |
| **Sync/Devices QML** | ⚠️ En validación | DevicesBridge |
| **ContextMenu QML** | ⚠️ En validación | SongContextMenu básico |
| **Michi Link UI** | ⚠️ En validación | ConnectionsBridge |

**Estados:**
- ✅ Estable — listo para producción
- ✅ Experimental — funcional pero puede cambiar
- ⚠️ En validación — necesita tests/pulido
- ⬜ Placeholder — esqueleto, no funcional
