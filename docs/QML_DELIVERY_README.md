# Michi Music Player QML Delivery

## Ejecutar

```bash
# Interfaz QML experimental (entrega)
python main.py --qml

# Interfaz clásica QtWidgets (fallback)
python main.py
```

## Funciones demostrables

| Función | Descripción |
|---|---|
| Biblioteca | Búsqueda, filtros, orden, paginación, reproducción |
| NowPlaying | Barra compacta, panel expandido, controles, seek, volumen |
| Álbumes/Artistas | Vistas por álbum y artista con detalle |
| Playlists | Crear, renombrar, eliminar, agregar canciones, reproducir |
| Radio | Listar, agregar, reproducir, eliminar emisoras |
| Metadata | Inspector con edición de título/artista/álbum |
| Settings | Perfiles de salida, diagnóstico |
| Diagnóstico | Estado de servicios, bridges y módulos |

## Limitaciones

- Los módulos experimentales (Audio Lab, Smart Tagging, Library Doctor, Disc Lab, EQ, etc.) no están en la navegación principal.
- Algunas funciones avanzadas solo están disponibles en la interfaz clásica QtWidgets.
- QML sigue siendo experimental y debe usarse con `--qml`.
