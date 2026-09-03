import QtQuick
import "../theme"

Item {
    id: root
    property var album: null
    // Explicit host capabilities. Defaults are fail-closed so reconnecting
    // the historical context surface can never resurrect a dead action.
    property bool canAddToPlaylist: false
    property bool canCreatePlaylist: false
    property bool canShowProperties: false
    signal contextRequested()

    function openMenu() {
        if (!root.album)
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
    AlbumContextMenu {
        id: menu
        album: root.album
        canAddToPlaylist: root.canAddToPlaylist
        canCreatePlaylist: root.canCreatePlaylist
        canShowProperties: root.canShowProperties
    }
}
