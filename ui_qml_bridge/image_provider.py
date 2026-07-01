"""Cover image provider for QML.

PySide6 does not export QQuickImageProvider (only QQmlImageProviderBase which
cannot be instantiated from Python). Cover images are handled via QML fallback:

  - AlbumCard uses Text + Rectangle for fallback covers
  - Future: implement via QQuickPaintedItem or custom C++ provider
  - Or: use Canvas/ShaderEffect in QML to generate covers

For now, all covers are premium fallbacks rendered in QML.
"""


def register_image_provider(engine):
    """Placeholder. QML uses built-in fallback covers.

    In a future phase, a C++ extension or QQuickPaintedItem subclass
    can be used to deliver real cover art from Python to QML.
    """
    pass
