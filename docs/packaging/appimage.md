# AppImage packaging for Michi Music Player

## Status

⚠️ Not recommended for Michi Music Player

## Limitations with AppImage

AppImage bundles all dependencies into a single executable, which presents challenges:

1. **GStreamer plugins** — require system-level registration (`gst-inspect-1.0`) and shared library paths that AppImage cannot easily provide
2. **PyGObject/GI** — Python bindings for GObject require compiled GLib/GStreamer typelibs that depend on the host system
3. **Audio integration** — PulseAudio/PipeWire socket paths and ALSA device nodes vary between systems
4. **Qt themes** — Breeze/Qt6 theme integration depends on the host system's theme engine
5. **System tray** — DBus and KDE/Plasma tray integration paths vary

## Recommendation

Use **Flatpak** instead. Flatpak provides:
- Sandboxed runtime with consistent GStreamer/GLib/Qt6 versions
- Standardized audio, DBus, and filesystem permissions
- Cross-distribution compatibility without bundling system libraries

If an AppImage is strictly needed, consider:
- Bundling a complete GStreamer installation inside the AppImage
- Using `linuxdeploy` with Qt and GStreamer plugins
- Testing on each target distribution

## Resources

- [linuxdeploy](https://github.com/linuxdeploy/linuxdeploy)
- [linuxdeploy-plugin-qt](https://github.com/linuxdeploy/linuxdeploy-plugin-qt)
- [AppImage documentation](https://docs.appimage.org/)
