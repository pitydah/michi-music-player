# Flatpak packaging for Michi Music Player

Flatpak is the recommended way to distribute Michi Music Player universally across Linux distributions.

## Status

🚧 Planning — draft manifest available

## Dependencies

### Runtime
- `org.kde.Platform` SDK for Qt6/PySide6
- Python 3.11+ with `--system-site-packages` access to GStreamer

### Python modules (bundled)
- PySide6 >= 6.7
- mutagen >= 1.47
- numpy >= 1.24

### System libraries (from runtime/SDK)
- GStreamer 1.0 + plugins (base, good, bad, ugly, libav)
- PyGObject / GI
- dbus-python
- chromaprint (fpcalc)
- avahi
- portaudio (pyaudio)
- snapcast (snapserver + snapclient)

### Permissions
- `--socket=wayland --socket=x11`
- `--device=dri` (GPU acceleration)
- `--share=network`
- `--filesystem=home` or `--filesystem=xdg-music`
- `--socket=pulseaudio`
- `--talk-name=org.freedesktop.DBus`
- `--talk-name=org.mpris.MediaPlayer2.*`

## Manifest draft

```yaml
app-id: io.github.pitydah.MichiMusicPlayer
runtime: org.kde.Platform
runtime-version: "6.7"
sdk: org.kde.Sdk
command: michi-music-player
finish-args:
  - --socket=wayland
  - --socket=x11
  - --share=ipc
  - --device=dri
  - --share=network
  - --filesystem=home
  - --socket=pulseaudio
  - --talk-name=org.freedesktop.DBus
  - --talk-name=org.mpris.MediaPlayer2.*

modules:
  - name: michi-music-player
    buildsystem: simple
    build-commands:
      - pip3 install --no-deps --prefix=/app .
    sources:
      - type: git
        url: https://github.com/pitydah/michi-music-player.git
```

## Building

```bash
flatpak-builder --user --install build-dir packaging/flatpak/io.github.pitydah.MichiMusicPlayer.yml
flatpak run io.github.pitydah.MichiMusicPlayer
```
