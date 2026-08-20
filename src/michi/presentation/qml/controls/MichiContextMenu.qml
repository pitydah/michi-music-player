import QtQuick
import QtQuick.Controls.Basic

MichiMenu {
    id: root
    property bool canPlay: true
    property bool canFavorite: false
    property bool favorite: false
    property bool canAddToPlaylist: false
    property bool canInspect: false
    property bool canRemove: false
    signal playRequested()
    signal favoriteRequested()
    signal addToPlaylistRequested()
    signal inspectRequested()
    signal removeRequested()

    MenuItem {
        text: "Play"
        enabled: root.canPlay
        onTriggered: root.playRequested()
    }
    MenuSeparator { visible: root.canFavorite || root.canAddToPlaylist }
    MenuItem {
        text: root.favorite ? "Remove from favorites" : "Add to favorites"
        visible: root.canFavorite
        onTriggered: root.favoriteRequested()
    }
    MenuItem {
        text: "Add to playlist"
        visible: root.canAddToPlaylist
        onTriggered: root.addToPlaylistRequested()
    }
    MenuSeparator { visible: root.canInspect || root.canRemove }
    MenuItem {
        text: "Properties"
        visible: root.canInspect
        onTriggered: root.inspectRequested()
    }
    MenuItem {
        text: "Remove"
        visible: root.canRemove
        onTriggered: root.removeRequested()
    }
}
