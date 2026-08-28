import QtQuick
import "../theme"

Item {
    id: root
    property var artist: null
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            MichiAccessibility.notePointer()
            menu.popup()
        }
    }
    ArtistContextMenu { id: menu; artist: root.artist }
}
