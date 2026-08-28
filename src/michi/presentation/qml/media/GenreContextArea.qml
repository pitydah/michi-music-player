import QtQuick
import "../theme"

Item {
    id: root
    property var genre: null
    signal contextRequested()
    function openMenu() {
        if (!root.genre)
            return
        if (root.parent && root.parent.forceActiveFocus)
            root.parent.forceActiveFocus()
        root.contextRequested()
        menu.popup()
    }
    function handleContextKey(event) {
        if (event.key === Qt.Key_Menu
                || (event.key === Qt.Key_F10
                    && (event.modifiers & Qt.ShiftModifier))) {
            openMenu()
            event.accepted = true
            return true
        }
        return false
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            MichiAccessibility.notePointer()
            root.openMenu()
        }
    }
    GenreContextMenu { id: menu; genre: root.genre }
}
