# Beta Product Audit — Michi Music Player v0.2.0-alpha.1

## Auditoría por área

| Área | Estado | Visible | Backend real | UI real | Tests | Riesgo | Acción |
|---|---|---|---|---|---|---|---|
| **Inicio (Home Dashboard)** | Estable | ✅ | ✅ | ✅ Widgets | ✅ 58+ | Bajo | Mantener |
| **Biblioteca (LibraryState)** | Estable | ✅ | ✅ | ✅ Widgets | ✅ 228+ | Bajo | Mantener |
| **Canciones** | Estable | ✅ | ✅ | ✅ Widgets/QML | ✅ 80+ | Bajo | Mantener |
| **Álbumes** | Estable | ✅ | ✅ | ✅ Widgets | ✅ 23+ | Bajo | Mantener |
| **Artistas** | Estable | ✅ | ✅ | ✅ Widgets | ✅ 8+ | Bajo | Mantener |
| **Géneros** | En validación | ✅ | ✅ | ✅ Widgets | ✅ 8+ | Medio | Revisar search |
| **Carpetas** | Estable | ✅ | ✅ | ✅ Widgets | ✅ 7+ | Bajo | Mantener |
| **Playlists QtWidgets** | En validación | ✅ | ✅ | ✅ | ✅ 5 files | Medio | Revisar botones muertos |
| **Playlists QML** | Experimental | ✅ | ✅ | Parcial | ✅ Bridge test | Medio | Conectar a LibraryDB (hecho) |
| **Mix** | En validación | ✅ | Parcial | ✅ Widgets | Parcial | Medio | Recomendación real pendiente |
| **NowPlaying QtWidgets** | Estable | ✅ | ✅ | ✅ | Parcial | Bajo | Mantener |
| **NowPlaying QML** | Experimental | ✅ | Parcial | Parcial | Parcial | Medio | Conectar PlayerService |
| **Audio Lab QtWidgets** | En validación | ✅ | Parcial | ✅ | Parcial | Medio | Clasificar módulos |
| **Audio Lab QML** | Experimental | Parcial | Parcial | Placeholder | Mínimo | Medio | Estados honestos |
| **Michi Link (Conexiones)** | En validación | ✅ | ✅ | ✅ | Parcial | Medio | UI de estado completa |
| **Sync/Devices** | En validación | ✅ | ✅ | ✅ Widgets | Parcial | Medio | Estados honestos |
| **Radio QtWidgets** | Estable | ✅ | ✅ | ✅ | ✅ | Bajo | Mantener |
| **Radio QML** | Experimental | Parcial | ✅ | Placeholder | Mínimo | Bajo | Estados honestos |
| **Home Audio** | Experimental | ✅ | Parcial | ✅ Widgets | Parcial | Alto | Backend multiroom complejo |
| **Settings QtWidgets** | Estable | ✅ | ✅ | ✅ | ✅ | Bajo | Mantener |
| **Settings QML** | Experimental | ✅ | ✅ | Parcial | Mínimo | Bajo | Estados honestos |
| **Michi AI** | Experimental | ✅ | Parcial | Parcial | Parcial | Medio | Mejorar respuestas |
| **QML Shell** | Experimental | ✅ | Parcial | Parcial | 165 tests | Medio | No default aún |
| **QtWidgets (fallback)** | Estable | ✅ | ✅ | ✅ | Suite completa | Bajo | Mantener |

## Leyenda

- **Estable**: listo para uso real, backend y UI conectados, tests pasan
- **En validación**: funcional pero necesita revisión de producto antes de declarar beta
- **Experimental**: existe pero puede cambiar, no prometido como estable
- **Parcial**: implementación incompleta o con placeholders
- **Placeholder**: esqueleto sin backend real conectado
- **Oculto**: no visible en UI principal

## Acciones prioritarias para beta

1. Michi Link UI: unificar estados (not_configured → error), emparejamiento real
2. Playlists: revisar botones muertos, tooltips para no implementado
3. NowPlaying: bit-perfect state claro, backend activo visible
4. Audio Lab: módulos clasificados honestamente
5. QML: estados loading/empty/error/experimental en todas las páginas
6. Known Issues + Beta Checklist

Document generado: 2026-07-01
