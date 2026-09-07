import QtQuick
import "../theme"

Item {
    id: root
    property var artist: null
    // Fail-closed: el host decide si "Add Artist to Playlist" tiene
    // consumer productivo (fase R4). Por defecto FALSE.
    property bool canAddToPlaylist: false
    property bool canCreatePlaylist: false
    signal contextRequested()
    function openMenu() {
        if (!root.artist)
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
    ArtistContextMenu {
        id: menu
        artist: root.artist
        canAddToPlaylist: root.canAddToPlaylist
        canCreatePlaylist: root.canCreatePlaylist
    }
}
