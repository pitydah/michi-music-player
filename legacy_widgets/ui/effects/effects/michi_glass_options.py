"""MichiGlass presets — visual options for glass surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MichiGlassOptions:
    blur_radius: int = 0
    tint_color: str = ""
    tint_opacity: float = 0.0
    brightness: float = 1.0
    noise_opacity: float = 0.0
    border_opacity: float = 0.0
    shadow_blur: int = 0
    shadow_offset: int = 0
    shadow_opacity: int = 0

    presets: ClassVar[dict[str, MichiGlassOptions]] = {}

    @classmethod
    def register(cls, name: str, **kwargs):
        cls.presets[name] = cls(**kwargs)
        return cls.presets[name]

    @classmethod
    def get(cls, name: str) -> MichiGlassOptions:
        return cls.presets.get(name, cls())


MichiGlassOptions.register("window", blur_radius=0)
MichiGlassOptions.register("sidebar", blur_radius=0)
MichiGlassOptions.register("card",
    border_opacity=0.055, shadow_blur=18, shadow_offset=4, shadow_opacity=50)
MichiGlassOptions.register("compact_card",
    border_opacity=0.045, shadow_blur=12, shadow_offset=3, shadow_opacity=40)
MichiGlassOptions.register("hero",
    border_opacity=0.070, shadow_blur=28, shadow_offset=6, shadow_opacity=65)
MichiGlassOptions.register("popup",
    border_opacity=0.090, shadow_blur=32, shadow_offset=8, shadow_opacity=75)
MichiGlassOptions.register("dialog",
    border_opacity=0.100, shadow_blur=40, shadow_offset=10, shadow_opacity=85)
MichiGlassOptions.register("action_card",
    border_opacity=0.065, shadow_blur=20, shadow_offset=5, shadow_opacity=55)
