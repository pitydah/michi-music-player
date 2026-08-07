"""DeviceProfileResolver — capabilities and profiles by protocol + brand hints.

Protocols are decided by the discovery adapters; brand names ONLY
contribute capability profiles (pairing/playlist support for dedicated
players). A brand hint never changes the protocol of a device.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.device_sync.models import (
    AUDIO_EXTENSIONS,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceProtocol,
)

# Brand hints contribute profiles only — never protocol classification.
_BRAND_PROFILES = {
    "hiby": {"pairing": True, "trust": True, "playlists": True},
    "fiio": {"pairing": False, "trust": True, "playlists": True},
    "sony": {"pairing": False, "trust": True, "playlists": True},
    "ruizu": {"pairing": False, "trust": False, "playlists": True},
}


@dataclass
class DeviceProfile:
    profile_id: str = ""
    name: str = ""
    protocol: str = ""
    vendor: str = ""
    supports_pairing: bool = False
    supports_authorization: bool = False
    supports_trust: bool = False
    supports_playlists: bool = False
    supports_transcode: bool = True
    music_directory: str = "Music"
    supported_formats: set = field(default_factory=lambda: set(AUDIO_EXTENSIONS))
    transcode_target: str = ".flac"


class DeviceProfileResolver:
    """Resolve a capability profile from identity + optional brand hint."""

    def resolve_capabilities(self, identity: DeviceIdentity) -> DeviceCapabilities:
        profile = self.resolve_profile(identity)
        return DeviceCapabilities(
            supports_pairing=profile.supports_pairing,
            supports_authorization=profile.supports_authorization,
            supports_trust=profile.supports_trust,
            supports_progress=True,
            supports_cancel=True,
            supports_retry=True,
            supports_playlists=profile.supports_playlists,
            max_filename_length=255,
            max_path_length=4096,
            supported_formats=set(profile.supported_formats),
            music_directory=profile.music_directory,
        )

    def resolve_profile(self, identity: DeviceIdentity) -> DeviceProfile:
        proto = identity.protocol
        vendor = (identity.vendor or "").lower()
        hint = _BRAND_PROFILES.get(vendor, {})
        base = DeviceProfile(
            profile_id=f"{proto.value}:{vendor or 'generic'}",
            name=(identity.model or identity.label or "Device"),
            protocol=proto.value,
            vendor=vendor,
            supports_transcode=True,
            music_directory="Music",
            supported_formats=set(AUDIO_EXTENSIONS),
            transcode_target=".flac",
        )

        if proto == DeviceProtocol.ANDROID_MTP:
            base.supports_pairing = True
            base.supports_authorization = True
            base.supports_trust = True
            base.supports_playlists = True
            base.music_directory = "Music"
            return base

        if proto in (
            DeviceProtocol.USB_MASS_STORAGE,
            DeviceProtocol.GENERIC_DEDICATED,
        ):
            if vendor in ("hiby", "fiio", "sony"):
                base.supports_pairing = bool(hint.get("pairing"))
                base.supports_trust = bool(hint.get("trust"))
                base.supports_playlists = bool(hint.get("playlists"))
            elif vendor == "ruizu":
                # Legacy: Ruizu UMS supports playlists; dedicated build does not.
                base.supports_playlists = (
                    proto == DeviceProtocol.USB_MASS_STORAGE
                )
            else:
                base.supports_playlists = False
            return base

        if proto == DeviceProtocol.MICHI_LINK:
            base.supports_pairing = True
            base.supports_authorization = True
            base.supports_trust = True
            base.supports_playlists = True
            return base

        if proto == DeviceProtocol.NETWORK_FILESYSTEM:
            base.supports_playlists = True
            return base

        return base
