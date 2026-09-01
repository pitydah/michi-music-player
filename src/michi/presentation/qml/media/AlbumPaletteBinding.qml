import QtQuick

QtObject {
    id: root

    property var album: null
    property var value: album && album.artworkPalette
        ? album.artworkPalette : ({})
    readonly property string albumKey: album && album.key ? album.key : ""

    function synchronize() {
        value = album && album.artworkPalette ? album.artworkPalette : ({})
        if (albumKey.length > 0 && typeof library !== "undefined" && library
                && typeof library.request_album_palette === "function")
            library.request_album_palette(albumKey)
    }

    Component.onCompleted: synchronize()
    onAlbumChanged: synchronize()

    property QtObject paletteConnection: Connections {
        target: typeof library !== "undefined" ? library : null
        ignoreUnknownSignals: true
        function onAlbumPaletteChanged(key, palette) {
            if (key === root.albumKey)
                root.value = palette
        }
    }
}
