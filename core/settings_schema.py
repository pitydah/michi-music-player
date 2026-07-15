"""SettingsSchema — typed definitions for all settings categories, entries, validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

ENTRY_TEXT = "text"
ENTRY_INT = "int"
ENTRY_BOOL = "bool"
ENTRY_SELECT = "select"
ENTRY_FILE = "file"
ENTRY_AUDIO_DEVICE = "audio_device"
ENTRY_SECRET = "secret"
ENTRY_DIRECTORY = "directory"
ENTRY_FLOAT = "float"
ENTRY_SLIDER = "slider"
ENTRY_ACTION = "action"


@dataclass
class SettingsEntry:
    key: str
    label: str
    entry_type: str = ENTRY_TEXT
    default: Any = ""
    options: list[dict] | None = None  # [{value, label}] for select
    placeholder: str = ""
    hint: str = ""
    validator: Callable[[Any], tuple[bool, str]] | None = None
    requires_restart: bool = False
    min_value: int | None = None
    max_value: int | None = None
    category: str = "general"
    platforms: list[str] | None = None       # None = all, or ["Linux", "Windows", "Darwin"]
    requires_capability: str = ""            # capability name, empty = always available
    experimental: bool = False
    visible_when: str = ""                   # expression or capability key


@dataclass
class SettingsSection:
    id: str
    title: str
    entries: list[SettingsEntry] = field(default_factory=list)


@dataclass
class SettingsCategory:
    id: str
    title: str
    icon: str = ""
    sections: list[SettingsSection] = field(default_factory=list)


# ── Validators ──

def _port_validator(v: Any) -> tuple[bool, str]:
    try:
        p = int(v)
        if 1 <= p <= 65535:
            return True, ""
        return False, "Puerto debe estar entre 1 y 65535"
    except (ValueError, TypeError):
        return False, "Debe ser un número"


def _positive_int(v: Any) -> tuple[bool, str]:
    try:
        if int(v) >= 0:
            return True, ""
        return False, "Debe ser un número positivo"
    except (ValueError, TypeError):
        return False, "Debe ser un número"


def _sample_rate_validator(v: Any) -> tuple[bool, str]:
    valid = [0, 44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000]
    try:
        if int(v) in valid:
            return True, ""
        return False, f"Frecuencia no soportada: {v}"
    except (ValueError, TypeError):
        return False, "Debe ser un número"


# ── All categories ──

GENERAL = SettingsCategory("general", "General", "settings", sections=[
    SettingsSection("paths", "Rutas", entries=[
        SettingsEntry("general/music_folder", "Carpeta de música", ENTRY_FILE, "~/Música"),
        SettingsEntry("general/download_folder", "Carpeta de descargas", ENTRY_FILE, "~/Descargas"),
    ]),
    SettingsSection("behavior", "Comportamiento", entries=[
        SettingsEntry("general/start_minimized", "Iniciar minimizado", ENTRY_BOOL, False),
        SettingsEntry("general/confirm_exit", "Confirmar al salir", ENTRY_BOOL, False),
        SettingsEntry("general/remember_session", "Recordar sesión", ENTRY_BOOL, True),
    ]),
])

LIBRARY = SettingsCategory("library", "Biblioteca", "library", sections=[
    SettingsSection("scan", "Escaneo", entries=[
        SettingsEntry("library/auto_scan", "Escaneo automático", ENTRY_BOOL, True),
        SettingsEntry("library/exclude_hidden", "Excluir ocultos", ENTRY_BOOL, True),
    ]),
    SettingsSection("cache", "Caché", entries=[
        SettingsEntry("library/covers_cache_size", "Tamaño caché carátulas", ENTRY_INT, 100,
                       validator=_positive_int, hint="Número de carátulas en memoria"),
    ]),
])

PLAYBACK = SettingsCategory("playback", "Reproducción", "play", sections=[
    SettingsSection("defaults", "Valores por defecto", entries=[
        SettingsEntry("playback/default_volume", "Volumen por defecto", ENTRY_INT, 70,
                       min_value=0, max_value=100, hint="0-100%"),
        SettingsEntry("playback/repeat_mode", "Modo repetición", ENTRY_SELECT, "none",
                       options=[{"value": "none", "label": "No repetir"},
                                {"value": "all", "label": "Repetir todo"},
                                {"value": "one", "label": "Repetir una"}]),
        SettingsEntry("playback/shuffle_default", "Aleatorio por defecto", ENTRY_BOOL, False),
    ]),
    SettingsSection("audio_processing", "Procesamiento", entries=[
        SettingsEntry("playback/replaygain", "ReplayGain", ENTRY_BOOL, False),
        SettingsEntry("playback/crossfade", "Crossfade (segundos)", ENTRY_INT, 0,
                       min_value=0, max_value=30, validator=_positive_int),
        SettingsEntry("playback/gapless", "Reproducción sin pausa", ENTRY_BOOL, True),
    ]),
])

AUDIO = SettingsCategory("audio", "Audio", "speaker", sections=[
    SettingsSection("device", "Dispositivo", entries=[
        SettingsEntry("audio/device", "Dispositivo de salida", ENTRY_AUDIO_DEVICE, "default"),
        SettingsEntry("audio/mode", "Modo de audio", ENTRY_SELECT, "standard",
                       options=[{"value": "standard", "label": "Estándar"},
                                {"value": "exclusive", "label": "Exclusivo"},
                                {"value": "bitperfect", "label": "Bit-perfect"}]),
        SettingsEntry("audio/sample_rate", "Frecuencia de muestreo", ENTRY_SELECT, "0",
                       options=[{"value": "0", "label": "Automático"},
                                {"value": "44100", "label": "44100 Hz"},
                                {"value": "48000", "label": "48000 Hz"},
                                {"value": "88200", "label": "88200 Hz"},
                                {"value": "96000", "label": "96000 Hz"},
                                {"value": "192000", "label": "192000 Hz"}],
                       validator=_sample_rate_validator),
        SettingsEntry("audio/buffer_ms", "Buffer (ms)", ENTRY_INT, 100,
                       min_value=20, max_value=2000, validator=_positive_int),
        SettingsEntry("audio/profile", "Perfil de audio", ENTRY_SELECT, "standard",
                       options=[{"value": "standard", "label": "Estándar"},
                                {"value": "headphones", "label": "Auriculares"},
                                {"value": "speakers", "label": "Altavoces"},
                                {"value": "hi_fi", "label": "Hi-Fi"},
                                {"value": "studio", "label": "Estudio"}]),
    ]),
    SettingsSection("output", "Salida", entries=[
        SettingsEntry("audio/output_device_id", "Dispositivo de salida", ENTRY_AUDIO_DEVICE, "auto"),
        SettingsEntry("audio/alsa_device", "Dispositivo ALSA", ENTRY_TEXT, "",
                       placeholder="hw:0,0", platforms=["Linux"]),
        SettingsEntry("audio/allow_resample", "Permitir remuestreo", ENTRY_BOOL, True),
        SettingsEntry("audio/resample_quality", "Calidad de remuestreo", ENTRY_SELECT, "medium",
                       options=[{"value": "low", "label": "Baja"},
                                {"value": "medium", "label": "Media"},
                                {"value": "high", "label": "Alta"},
                                {"value": "ultra", "label": "Ultra"}]),
        SettingsEntry("audio/wasapi_exclusive", "WASAPI exclusivo", ENTRY_BOOL, False,
                       hint="Solo Windows", platforms=["Windows"]),
    ]),
])

MPD = SettingsCategory("mpd", "MPD", "mpd", sections=[
    SettingsSection("connection", "Conexión", entries=[
        SettingsEntry("mpd/host", "Servidor MPD", ENTRY_TEXT, "localhost",
                       placeholder="localhost"),
        SettingsEntry("mpd/port", "Puerto MPD", ENTRY_INT, 6600,
                       validator=_port_validator, min_value=1, max_value=65535),
        SettingsEntry("mpd/password", "Contraseña MPD", ENTRY_TEXT, "",
                       placeholder="(opcional)", hint="Dejar vacío si no tiene contraseña"),
    ]),
    SettingsSection("behavior", "Comportamiento", entries=[
        SettingsEntry("mpd/enabled", "MPD habilitado", ENTRY_BOOL, False,
                       hint="Requiere MPD instalado y configurado"),
        SettingsEntry("mpd/auto_start", "Iniciar MPD automáticamente", ENTRY_BOOL, False),
    ]),
])

GSTREAMER = SettingsCategory("gstreamer", "GStreamer", "gstreamer", sections=[
    SettingsSection("buffer", "Buffer", entries=[
        SettingsEntry("gstreamer/buffer_size", "Tamaño de buffer (bytes)", ENTRY_INT, 4096,
                       validator=_positive_int),
        SettingsEntry("gstreamer/latency", "Latencia (ms)", ENTRY_INT, 50,
                       min_value=10, max_value=500),
    ]),
])

BUFFER = SettingsCategory("buffer", "Buffer", "buffer", sections=[
    SettingsSection("general", "General", entries=[
        SettingsEntry("buffer/ms", "Buffer (ms)", ENTRY_INT, 100,
                       min_value=20, max_value=5000, hint="Tamaño del buffer de audio"),
        SettingsEntry("buffer/prebuffer", "Pre-buffer (ms)", ENTRY_INT, 50,
                       min_value=0, max_value=2000),
        SettingsEntry("buffer/stream", "Buffer streaming (ms)", ENTRY_INT, 200,
                       min_value=50, max_value=10000),
    ]),
])

GAPLESS = SettingsCategory("gapless", "Sin pausa", "gapless", sections=[
    SettingsSection("behavior", "Comportamiento", entries=[
        SettingsEntry("gapless/enabled", "Reproducción sin pausa", ENTRY_BOOL, True),
        SettingsEntry("gapless/crossfade_duration", "Duración crossfade (ms)", ENTRY_INT, 0,
                       min_value=0, max_value=10000, hint="0 = desactivado"),
        SettingsEntry("gapless/fade_style", "Estilo de fade", ENTRY_SELECT, "equal_power",
                       options=[{"value": "equal_power", "label": "Equal power"},
                                {"value": "equal_gain", "label": "Equal gain"},
                                {"value": "linear", "label": "Lineal"}]),
    ]),
])

REPLAYGAIN = SettingsCategory("replaygain", "ReplayGain", "replaygain", sections=[
    SettingsSection("mode", "Modo", entries=[
        SettingsEntry("replaygain/mode", "Modo ReplayGain", ENTRY_SELECT, "disabled",
                       options=[{"value": "disabled", "label": "Desactivado"},
                                {"value": "track", "label": "Por pista"},
                                {"value": "album", "label": "Por álbum"}]),
        SettingsEntry("replaygain/preamp", "Pre-amplificación (dB)", ENTRY_INT, 0,
                       min_value=-15, max_value=15),
        SettingsEntry("replaygain/fallback_gain", "Ganancia por defecto (dB)", ENTRY_INT, -6,
                       min_value=-20, max_value=0),
        SettingsEntry("replaygain/prevent_clipping", "Prevenir recorte", ENTRY_BOOL, True),
    ]),
])

EQ_DSP = SettingsCategory("eq_dsp", "EQ y DSP", "eq", sections=[
    SettingsSection("eq", "Ecualizador", entries=[
        SettingsEntry("eq/enabled", "EQ activado", ENTRY_BOOL, False),
        SettingsEntry("eq/preset", "Preajuste EQ", ENTRY_SELECT, "flat",
                       options=[{"value": "flat", "label": "Plano"},
                                {"value": "rock", "label": "Rock"},
                                {"value": "pop", "label": "Pop"},
                                {"value": "jazz", "label": "Jazz"},
                                {"value": "classical", "label": "Clásica"},
                                {"value": "custom", "label": "Personalizado"}]),
    ]),
    SettingsSection("dsp", "DSP", entries=[
        SettingsEntry("dsp/chain", "Cadena DSP", ENTRY_TEXT, "",
                       placeholder="eq,compressor,limiter", hint="Separado por comas"),
        SettingsEntry("dsp/compressor", "Compresor", ENTRY_BOOL, False),
        SettingsEntry("dsp/limiter", "Limitador", ENTRY_BOOL, False),
        SettingsEntry("dsp/stereo_enhance", "Mejora estéreo", ENTRY_BOOL, False),
    ]),
])

BITPERFECT = SettingsCategory("bitperfect", "Bit-perfect", "bitperfect", sections=[
    SettingsSection("mode", "Modo", entries=[
        SettingsEntry("bitperfect/enabled", "Modo bit-perfect", ENTRY_BOOL, False,
                       hint="Requiere dispositivo compatible"),
        SettingsEntry("bitperfect/exclusive_mode", "Modo exclusivo", ENTRY_BOOL, False),
        SettingsEntry("bitperfect/dsd_mode", "Modo DSD", ENTRY_SELECT, "pcm",
                       options=[{"value": "pcm", "label": "PCM"},
                                {"value": "native", "label": "Nativo"},
                                {"value": "dop", "label": "DoP"}]),
        SettingsEntry("bitperfect/wasapi_exclusive", "WASAPI exclusivo", ENTRY_BOOL, False,
                       hint="Solo Windows", platforms=["Windows"]),
    ]),
])

CACHE = SettingsCategory("cache", "Caché", "cache", sections=[
    SettingsSection("sizes", "Tamaños", entries=[
        SettingsEntry("cache/covers_size", "Caché carátulas (MB)", ENTRY_INT, 50,
                       validator=_positive_int, hint="Límite de carátulas en disco"),
        SettingsEntry("cache/metadata_size", "Caché metadatos (MB)", ENTRY_INT, 20,
                       validator=_positive_int),
        SettingsEntry("cache/thumbnail_size", "Caché miniaturas (MB)", ENTRY_INT, 30,
                       validator=_positive_int),
    ]),
    SettingsSection("behavior", "Comportamiento", entries=[
        SettingsEntry("cache/auto_clean", "Limpiar automáticamente", ENTRY_BOOL, True),
        SettingsEntry("cache/clean_interval_days", "Intervalo limpieza (días)", ENTRY_INT, 7,
                       min_value=1, max_value=365),
    ]),
])

NETWORK = SettingsCategory("network", "Red", "network", sections=[
    SettingsSection("timeouts", "Timeouts", entries=[
        SettingsEntry("network/radio_timeout", "Timeout radio (s)", ENTRY_INT, 15,
                       min_value=5, max_value=120),
        SettingsEntry("network/lyrics_timeout", "Timeout letras (s)", ENTRY_INT, 10,
                       min_value=3, max_value=60),
        SettingsEntry("network/metadata_timeout", "Timeout metadatos (s)", ENTRY_INT, 10,
                       min_value=3, max_value=60),
        SettingsEntry("network/discovery_timeout", "Timeout descubrimiento (s)", ENTRY_INT, 5,
                       min_value=1, max_value=30),
    ]),
])

RADIO = SettingsCategory("radio_settings", "Radio", "radio", sections=[
    SettingsSection("playback", "Reproducción", entries=[
        SettingsEntry("radio/default_codec", "Codec por defecto", ENTRY_SELECT, "MP3",
                       options=[{"value": "MP3", "label": "MP3"},
                                {"value": "AAC", "label": "AAC"},
                                {"value": "OGG", "label": "Ogg Vorbis"},
                                {"value": "FLAC", "label": "FLAC"}]),
        SettingsEntry("radio/auto_reconnect", "Reconexión automática", ENTRY_BOOL, True),
        SettingsEntry("radio/reconnect_delay", "Espera reconexión (s)", ENTRY_INT, 5,
                       min_value=1, max_value=60),
        SettingsEntry("radio/buffer_size", "Buffer radio (KB)", ENTRY_INT, 64,
                       validator=_positive_int, hint="64-1024 KB"),
    ]),
])

LYRICS_SETTINGS = SettingsCategory("lyrics_settings", "Letras", "lyrics", sections=[
    SettingsSection("provider", "Proveedor", entries=[
        SettingsEntry("lyrics/provider", "Proveedor de letras", ENTRY_SELECT, "lrclib",
                       options=[{"value": "lrclib", "label": "LRCLIB"},
                                {"value": "genius", "label": "Genius"},
                                {"value": "musixmatch", "label": "Musixmatch"}]),
        SettingsEntry("lyrics/auto_search", "Búsqueda automática", ENTRY_BOOL, True),
        SettingsEntry("lyrics/cache_days", "Días en caché", ENTRY_INT, 30,
                       min_value=1, max_value=365),
        SettingsEntry("lyrics/offline_fallback", "Fallback sin conexión", ENTRY_BOOL, True),
    ]),
])

DEVICES = SettingsCategory("devices_settings", "Dispositivos", "devices", sections=[
    SettingsSection("sync", "Sincronización", entries=[
        SettingsEntry("devices/sync_enabled", "Sincronización activada", ENTRY_BOOL, False),
        SettingsEntry("devices/sync_interval", "Intervalo sincronización (min)", ENTRY_INT, 30,
                       min_value=5, max_value=1440),
        SettingsEntry("devices/sync_path", "Ruta de sincronización", ENTRY_FILE, "",
                       placeholder="/mnt/device/Music"),
        SettingsEntry("devices/auto_discover", "Descubrimiento automático", ENTRY_BOOL, True),
    ]),
])

CONNECTIONS = SettingsCategory("connections_settings", "Conexiones", "connections", sections=[
    SettingsSection("server", "Servidor", entries=[
        SettingsEntry("connections/server_port", "Puerto del servidor", ENTRY_INT, 53318,
                       validator=_port_validator, min_value=1024, max_value=65535),
        SettingsEntry("connections/auto_discovery", "Descubrimiento automático", ENTRY_BOOL, True),
        SettingsEntry("connections/pairing_timeout", "Timeout emparejamiento (s)", ENTRY_INT, 30,
                       min_value=10, max_value=120),
    ]),
])

HOME_AUDIO = SettingsCategory("home_audio_settings", "Home Audio", "home_audio", sections=[
    SettingsSection("home_assistant", "Home Assistant", entries=[
        SettingsEntry("home_audio/ha_host", "Host Home Assistant", ENTRY_TEXT, "",
                       placeholder="192.168.1.100"),
        SettingsEntry("home_audio/ha_port", "Puerto Home Assistant", ENTRY_INT, 8123,
                       validator=_port_validator),
        SettingsEntry("home_audio/ha_token", "Token Home Assistant", ENTRY_TEXT, "",
                       placeholder="Ingrese token"),
    ]),
    SettingsSection("snapcast", "Snapcast", entries=[
        SettingsEntry("home_audio/snapcast_host", "Host Snapcast", ENTRY_TEXT, "localhost"),
        SettingsEntry("home_audio/snapcast_port", "Puerto Snapcast", ENTRY_INT, 1704,
                       validator=_port_validator),
    ]),
])

PRIVACY = SettingsCategory("privacy", "Privacidad", "privacy", sections=[
    SettingsSection("history", "Historial", entries=[
        SettingsEntry("privacy/history_enabled", "Historial activado", ENTRY_BOOL, True),
        SettingsEntry("privacy/history_limit", "Límite del historial", ENTRY_INT, 500,
                       min_value=10, max_value=10000, hint="Número máximo de entradas"),
        SettingsEntry("privacy/telemetry", "Telemetría", ENTRY_BOOL, False),
    ]),
])

APPEARANCE = SettingsCategory("appearance", "Apariencia", "appearance", sections=[
    SettingsSection("theme", "Tema", entries=[
        SettingsEntry("appearance/theme", "Tema", ENTRY_SELECT, "dark",
                       options=[{"value": "dark", "label": "Oscuro"},
                                {"value": "light", "label": "Claro"},
                                {"value": "system", "label": "Del sistema"}]),
        SettingsEntry("appearance/compact_mode", "Modo compacto", ENTRY_BOOL, False),
        SettingsEntry("appearance/cover_size", "Tamaño carátulas", ENTRY_INT, 260,
                       min_value=100, max_value=600),
        SettingsEntry("appearance/language", "Idioma", ENTRY_SELECT, "es",
                       options=[{"value": "es", "label": "Español"},
                                {"value": "en", "label": "English"}]),
    ]),
])

ACCESSIBILITY = SettingsCategory("accessibility", "Accesibilidad", "accessibility", sections=[
    SettingsSection("display", "Pantalla", entries=[
        SettingsEntry("accessibility/font_size", "Tamaño de fuente", ENTRY_SELECT, "normal",
                       options=[{"value": "small", "label": "Pequeña"},
                                {"value": "normal", "label": "Normal"},
                                {"value": "large", "label": "Grande"},
                                {"value": "xlarge", "label": "Muy grande"}]),
        SettingsEntry("accessibility/high_contrast", "Alto contraste", ENTRY_BOOL, False),
        SettingsEntry("accessibility/reduce_motion", "Reducir movimiento", ENTRY_BOOL, False),
        SettingsEntry("accessibility/focus_indicators", "Indicadores de foco", ENTRY_BOOL, True),
    ]),
    SettingsSection("audio", "Audio", entries=[
        SettingsEntry("accessibility/mono", "Modo mono", ENTRY_BOOL, False),
        SettingsEntry("accessibility/balance", "Balance (L/R)", ENTRY_INT, 0,
                       min_value=-100, max_value=100, hint="-100 = solo izquierdo, 100 = solo derecho"),
    ]),
])

ADVANCED = SettingsCategory("advanced", "Avanzado", "advanced", sections=[
    SettingsSection("logging", "Registro", entries=[
        SettingsEntry("advanced/log_level", "Nivel de log", ENTRY_SELECT, "warning",
                       options=[{"value": "debug", "label": "Debug"},
                                {"value": "info", "label": "Info"},
                                {"value": "warning", "label": "Warning"},
                                {"value": "error", "label": "Error"},
                                {"value": "critical", "label": "Critical"}]),
        SettingsEntry("advanced/dev_mode", "Modo desarrollador", ENTRY_BOOL, False),
        SettingsEntry("advanced/experimental_features", "Funciones experimentales", ENTRY_BOOL, False),
    ]),
    SettingsSection("performance", "Rendimiento", entries=[
        SettingsEntry("advanced/thread_pool_size", "Tamaño del pool de hilos", ENTRY_INT, 4,
                       min_value=1, max_value=16),
        SettingsEntry("advanced/max_covers_parallel", "Carátulas en paralelo", ENTRY_INT, 4,
                       min_value=1, max_value=16),
    ]),
])

DIAGNOSTICS_SETTINGS = SettingsCategory("diagnostics_settings", "Diagnóstico", "diagnostics", sections=[
    SettingsSection("tools", "Herramientas", entries=[]),
])

# ── All categories lookup ──

ALL_CATEGORIES: list[SettingsCategory] = [
    GENERAL, LIBRARY, PLAYBACK, AUDIO, MPD, GSTREAMER,
    BUFFER, GAPLESS, REPLAYGAIN, EQ_DSP, BITPERFECT, CACHE, NETWORK,
    RADIO, LYRICS_SETTINGS, DEVICES, CONNECTIONS, HOME_AUDIO,
    PRIVACY, APPEARANCE, ACCESSIBILITY, ADVANCED, DIAGNOSTICS_SETTINGS,
]


def get_category(cat_id: str) -> SettingsCategory | None:
    for c in ALL_CATEGORIES:
        if c.id == cat_id:
            return c
    return None


def get_entry(key: str) -> SettingsEntry | None:
    for cat in ALL_CATEGORIES:
        for section in cat.sections:
            for entry in section.entries:
                if entry.key == key:
                    return entry
    return None


def get_default(key: str) -> Any:
    entry = get_entry(key)
    return entry.default if entry else None


def validate(key: str, value: Any) -> tuple[bool, str]:
    entry = get_entry(key)
    if not entry:
        return False, "Clave desconocida"
    if entry.validator:
        return entry.validator(value)
    if entry.entry_type == ENTRY_INT:
        try:
            v = int(value)
            if entry.min_value is not None and v < entry.min_value:
                return False, f"Mínimo: {entry.min_value}"
            if entry.max_value is not None and v > entry.max_value:
                return False, f"Máximo: {entry.max_value}"
            return True, ""
        except (ValueError, TypeError):
            return False, "Debe ser un número entero"
    return True, ""
