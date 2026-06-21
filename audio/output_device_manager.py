"""Audio Device Info + detection — DAC-aware device listing."""
from dataclasses import dataclass, field


_DAC_BRANDS = [
    "topping", "fiio", "smsl", "schiit", "ifi", "focusrite", "scarlett",
    "dragonfly", "xmos", "ess", "akm", "cambridge", "denon", "marantz",
    "teac", "audioquest", "burr-brown", "dac", "dsd", "hifi", "pro audio",
    "rme", "motu", "presonus", "behringer", "focusrite scarlett",
]


@dataclass
class AudioDeviceInfo:
    id: str = ""
    display_name: str = ""
    backend: str = "auto"  # alsa, pipewire, pulseaudio, jack, auto
    device_string: str = ""
    card_index: int = -1
    device_index: int = -1
    is_default: bool = False
    is_usb: bool = False
    is_hw: bool = False
    is_plug: bool = False
    is_virtual: bool = False
    is_dac_candidate: bool = False
    supports_exclusive: bool = False
    supports_bitperfect: bool = False
    supports_dop: bool = False
    supports_native_dsd: bool = False
    supported_rates: list[int] = field(default_factory=list)
    supported_formats: list[str] = field(default_factory=list)
    channels_min: int = 2
    channels_max: int = 2
    description: str = ""


BUILTIN_DEVICES = [
    AudioDeviceInfo(
        id="auto",         display_name="Auto (PipeWire/PulseAudio)",
        backend="auto", device_string="autoaudiosink",
        is_default=True, description="Salida por defecto",
        supported_rates=[44100, 48000, 88200, 96000],
    ),
    AudioDeviceInfo(
        id="pipewire",         display_name="PipeWire",
        backend="pipewire", device_string="pipewiresink",
        description="PipeWire (escritorio moderno)",
        supported_rates=[44100, 48000, 88200, 96000, 176400, 192000],
    ),
    AudioDeviceInfo(
        id="pulseaudio",         display_name="PulseAudio",
        backend="pulseaudio", device_string="pulsesink",
        description="PulseAudio (legacy)",
    ),
    AudioDeviceInfo(
        id="alsa_default",         display_name="ALSA (default)",
        backend="alsa", device_string="alsasink",
        description="ALSA default del sistema",
    ),
    AudioDeviceInfo(
        id="test",         display_name="Test (null sink)",
        backend="test", device_string="fakesink",
        description="Sink de prueba sin audio",
    ),
]


def list_devices() -> list[AudioDeviceInfo]:
    devices = list(BUILTIN_DEVICES)

    # ALSA cards via /proc
    try:
        with open("/proc/asound/cards") as f:
            for line in f:
                if "[" in line and "]" in line:
                    raw = line.strip()
                    card_num = raw.split()[0].rstrip(":")
                    card_id = line.split("[")[1].split("]")[0].strip()
                    name_lower = f"{card_id} {raw}".lower()
                    is_usb = "usb" in name_lower
                    is_dac = any(b in name_lower for b in _DAC_BRANDS)

                    # hw device
                    dev = AudioDeviceInfo(
                        id=f"alsa_hw_{card_num}",
                        display_name=f"hw:{card_num},0 ({card_id})",
                        backend="alsa",
                        device_string=f"alsasink device=hw:{card_num},0",
                        card_index=int(card_num) if card_num.isdigit() else -1,
                        is_hw=True, is_usb=is_usb,
                        is_dac_candidate=is_dac or is_usb,
                        supports_exclusive=True,
                        supports_bitperfect=True,
                        description="ALSA hw directo" + (" — DAC" if is_dac else ""),
                    )
                    if not any(d.id == dev.id for d in devices):
                        devices.append(dev)

                    # plughw variant
                    plughw = AudioDeviceInfo(
                        id=f"alsa_plughw_{card_num}",
                        display_name=f"plughw:{card_num},0 ({card_id})",
                        backend="alsa",
                        device_string=f"alsasink device=plughw:{card_num},0",
                        card_index=int(card_num) if card_num.isdigit() else -1,
                        is_hw=False, is_plug=True, is_usb=is_usb,
                        is_dac_candidate=is_dac or is_usb,
                        description="ALSA plughw — conversión posible" + (" — DAC" if is_dac else ""),
                    )
                    if not any(d.id == plughw.id for d in devices):
                        devices.append(plughw)
    except FileNotFoundError:
        pass

    return devices


def get_device(device_id: str) -> AudioDeviceInfo | None:
    for d in list_devices():
        if d.id == device_id:
            return d
    return next((d for d in BUILTIN_DEVICES if d.id == device_id), None)
