"""MPD Config Builder — generates mpd.conf for local isolated instances."""

import os
import logging
from dataclasses import dataclass, field

from core.settings_manager import get

logger = logging.getLogger("michi.mpd.config")


@dataclass
class MpdConfig:
    music_directory: str = ""
    playlist_directory: str = ""
    db_file: str = ""
    state_file: str = ""
    sticker_file: str = ""
    log_file: str = ""
    bind_to_address: str = "127.0.0.1"
    port: int = 6600
    auto_update: str = "yes"
    restore_paused: str = "yes"
    audio_outputs: list[dict] = field(default_factory=list)


def default_data_dir() -> str:
    return os.path.expanduser("~/.local/share/michi-music-player/mpd")


def build_mpd_config(
    data_dir: str = "",
    music_dir: str = "",
    device: str = "hw:0,0",
    dop: bool = False,
    mixer_type: str = "none",
    port: int = 6600,
) -> MpdConfig:
    """Build an MpdConfig for a local isolated MPD instance."""
    data_dir = data_dir or default_data_dir()
    music_dir = music_dir or get("audio/mpd/music_directory") or os.path.expanduser("~/Música")

    os.makedirs(data_dir, exist_ok=True)

    config = MpdConfig(
        music_directory=music_dir,
        playlist_directory=os.path.join(data_dir, "playlists"),
        db_file=os.path.join(data_dir, "database"),
        state_file=os.path.join(data_dir, "state"),
        sticker_file=os.path.join(data_dir, "sticker.sql"),
        log_file=os.path.join(data_dir, "mpd.log"),
        bind_to_address="127.0.0.1",
        port=port,
        auto_update="yes",
        restore_paused="yes",
        audio_outputs=[
            {
                "type": "alsa",
                "name": "Michi DAC Bit-Perfect",
                "device": device,
                "mixer_type": mixer_type,
                "dop": "yes" if dop else None,
            },
        ],
    )
    return config


def render_mpd_conf(config: MpdConfig) -> str:
    """Render MpdConfig to mpd.conf text."""
    lines = [
        f'music_directory\t\t"{config.music_directory}"',
        f'playlist_directory\t"{config.playlist_directory}"',
        f'db_file\t\t\t"{config.db_file}"',
        f'state_file\t\t"{config.state_file}"',
        f'sticker_file\t\t"{config.sticker_file}"',
        f'log_file\t\t"{config.log_file}"',
        "",
        f'bind_to_address\t\t"{config.bind_to_address}"',
        f"port\t\t\t\"{config.port}\"",
        f'restore_paused\t\t"{config.restore_paused}"',
        f'auto_update\t\t"{config.auto_update}"',
        "",
    ]

    for output in config.audio_outputs:
        lines.append("audio_output {")
        lines.append(f'\ttype\t\t"{output.get("type", "alsa")}"')
        lines.append(f'\tname\t\t"{output.get("name", "Michi DAC")}"')
        lines.append(f'\tdevice\t\t"{output.get("device", "hw:0,0")}"')
        lines.append(f'\tmixer_type\t"{output.get("mixer_type", "none")}"')
        if output.get("dop"):
            lines.append(f'\tdop\t\t"{output["dop"]}"')
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def write_mpd_conf(config: MpdConfig, path: str = "") -> str:
    """Write mpd.conf to disk and return the path."""
    path = path or os.path.join(default_data_dir(), "mpd.conf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = render_mpd_conf(config)
    with open(path, "w") as f:
        f.write(content)
    logger.info("Wrote MPD config to %s", path)
    return path
