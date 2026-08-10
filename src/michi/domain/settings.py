"""Domain layer — application settings. No Qt/infrastructure."""

from dataclasses import dataclass, field


@dataclass
class SettingsState:
    volume: int = 80  # 0-100
    muted: bool = False
    last_directory: str = ""
    recent_files: list[str] = field(default_factory=list)
