# Diagnóstico de Audio Lab

## ¿Qué hace?

Diagnóstico analiza archivos de audio individuales o carpetas completas y genera un reporte técnico con datos como formato, frecuencia de muestreo, profundidad de bits, canales, duración y calidad estimada (lossless, hires, lossy, DSD).

Incluye un análisis espectral experimental para archivos WAV PCM que evalúa si el contenido espectral es coherente con la resolución declarada.

## Servicios que reutiliza

| Servicio | Propósito |
|---|---|
| `audio/format_probe.py` | Detecta formato, codec, sample rate, bit depth, canales |
| `audio/quality_classifier.py` | Clasifica calidad (lossless/hires/lossy/dsd) desde metadatos |
| `core/audio_analysis/spectral_authenticator.py` | Análisis espectral vía FFT para WAV PCM |

## Cache

Los resultados de diagnóstico se almacenan en una base de datos SQLite (`diagnostics_cache.db`) para evitar recalibrar archivos que no han cambiado. La cache usa `mtime` + `size` como clave de invalidación.

- Si el archivo no ha cambiado, el segundo análisis devuelve el resultado cacheado.
- Si el archivo cambió (diferente `mtime` o `size`), se recalcula.
- Archivos inexistentes no se cachean.

## Coherencia espectral Hi-Res

El análisis espectral usa FFT (tamaño 8192, ventana Hann) para examinar el contenido espectral de un archivo WAV PCM y estimar si la resolución declarada es coherente con el contenido real.

**Etiquetas de resultado:**

| Veredicto | Significado |
|---|---|
| `HI_RES_COHERENT` | El contenido espectral alcanza frecuencias propias de la resolución declarada |
| `LOSSLESS_COHERENT` | El contenido espectral es compatible con una fuente sin pérdidas |
| `SUSPICIOUS_UPSAMPLING` | El techo espectral está muy por debajo de lo esperado |
| `POSSIBLE_LOSSY_SOURCE` | Baja energía en frecuencias altas, sugiere origen lossy |
| `INCONCLUSIVE` | No hay suficiente información para concluir |
| `ANALYSIS_ERROR` | No se pudo completar el análisis |

**Importante:** Los resultados son **probabilísticos**. No deben interpretarse como:
- Prueba definitiva de autenticidad
- Confirmación de fraude
- Reemplazo de análisis profesional

## Formatos soportados

### Diagnóstico general
Todos los formatos que `format_probe` soporta: FLAC, WAV, MP3, Ogg, Opus, M4A, AIFF, WavPack, APE, DSF, DFF.

### Análisis espectral
Solo WAV PCM (8, 16, 24 y 32 bits, mono y estéreo). No soporta FLAC, MP3 ni otros formatos comprimidos.

## Limitaciones actuales

- El análisis espectral no soporta FLAC directamente (requiere decodificación previa a WAV).
- No hay gráficos espectrales en la UI.
- La integración visual con Biblioteca (badges, filtros) está en etapa inicial.
- La cola de análisis no es persistente entre reinicios de la app.
- El análisis de carpeta usa un worker `QThread` que no tiene límite de concurrencia.

## Próximos pasos

- Badges técnicos en la tabla de Biblioteca (colores hires/lossless/lossy/dsd).
- Filtros de búsqueda `quality:` y `key:`.
- Análisis espectral de FLAC mediante decodificación temporal a PCM.
- Cola de análisis persistente.
- Reporte exportable a texto/JSON.
