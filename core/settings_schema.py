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
                       placeholder="hw:0,0"),
        SettingsEntry("audio/allow_resample", "Permitir remuestreo", ENTRY_BOOL, True),
        SettingsEntry("audio/resample_quality", "Calidad de remuestreo", ENTRY_SELECT, "medium",
                       options=[{"value": "low", "label": "Baja"},
                                {"value": "medium", "label": "Media"},
                                {"value": "high", "label": "Alta"},
                                {"value": "ultra", "label": "Ultra"}]),
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

# ── All categories lookup ──

ALL_CATEGORIES: list[SettingsCategory] = [
    GENERAL, LIBRARY, PLAYBACK, AUDIO, MPD, GSTREAMER,
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
