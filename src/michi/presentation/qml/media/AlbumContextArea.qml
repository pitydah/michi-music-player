import QtQuick
import "../theme"

Item {
    id: root
    property var album: null

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            MichiAccessibility.notePointer()
            menu.popup()
        }
    }
    AlbumContextMenu { id: menu; album: root.album }
}
