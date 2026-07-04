# Checklist — Prueba Física de Audio QML

## Requisitos
- Terminal + entorno gráfico (KDE/GNOME/Xfce)
- Altavoces o auriculares conectados
- Al menos un archivo MP3, FLAC y WAV en la biblioteca
- Conexión a internet (para radio y letras)
- Qt multimedia configurado: `export QT_QPA_PLATFORM=wayland` o `xcb`

## Ejecutar
```bash
cd /home/cristian/music_player
bash scripts/qml_physical_audio_test.sh
```

## Checklist Manual (21 pasos)

### Biblioteca y reproducción básica
- [ ] **1. Biblioteca carga**: Click "Biblioteca" en sidebar — tabla de canciones visible
- [ ] **2. Play MP3**: Click en canción MP3 — suena por altavoces
- [ ] **3. Play FLAC**: Click en canción FLAC — suena correctamente
- [ ] **4. Play WAV**: Click en canción WAV — suena correctamente
- [ ] **5. Cover art**: Canción con carátula incrustada — cover visible en NowPlayingBar
- [ ] **6. Placeholder**: Canción sin carátula — placeholder/monograma visible

### Control de reproducción
- [ ] **7. Pause/Play**: Espacio o botón play — pausa y reanuda
- [ ] **8. Seek**: Arrastrar slider — posición cambia, audio sigue
- [ ] **9. Volumen**: Slider de volumen — cambia nivel
- [ ] **10. Mute**: Botón mute — silencia; otro click — restaura
- [ ] **11. Next**: Click "siguiente" — siguiente canción suena
- [ ] **12. Prev**: Click "anterior" — canción anterior suena

### Modos y cola
- [ ] **13. Shuffle**: Toggle shuffle — orden de reproducción se mezcla
- [ ] **14. Repeat**: Toggle repeat — modo cambia (none/all/one)
- [ ] **15. Queue**: Panel de cola — lista de canciones visibles
- [ ] **16. ExpandedPanel**: Click NowPlayingBar — panel expandido se abre

### Funcionalidad específica
- [ ] **17. Letras**: Navegar a "Letra" — letra visible (si LRCLIB tiene datos)
- [ ] **18. Letras sincronizadas**: Si la canción tiene LRC — línea activa se resalta
- [ ] **19. Radio**: Navegar a "Radio" — emisoras cargan
- [ ] **20. Radio play**: Click emisora — stream suena

### Responsive
- [ ] **21. Redimensionar**: Arrastrar borde de ventana — UI se adapta sin solapamientos

## Resultado

| Total | Sí | No |
|-------|----|----|
| 21 | __/21 | __/21 |

- [ ] Todos los pasos funcionan → **APTO para VERIFIED (85%)**
- [ ] 18+ pasos funcionan → **APTO con incidentes menores**
- [ ] < 18 pasos → **NO APTO — revisar errores en /tmp/michi_qml_audio_test.log**

## Una vez completado
```bash
# Actualizar el reporte
echo "✅ Audio físico verificado el $(date +%Y-%m-%d)" >> docs/QML_PHYSICAL_AUDIO_REPORT.md
# Recalcular score
python scripts/qml_migration_score.py
```
