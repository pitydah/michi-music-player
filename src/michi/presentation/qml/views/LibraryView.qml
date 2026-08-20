import QtQuick
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property string currentTab: "songs"
    // M6-PRODUCTION-INTEGRATION: albumMode lives HERE (the root survives
    // the tab recreation) — AlbumsView is recreated on every tab switch and
    // must never be the source of a preference we want to preserve.
    property string albumMode: "grid"

    function syncEntitySelection() {
        if (library.selectedAlbumKey !== "")
            currentTab = "albums"
        else if (library.selectedArtistKey !== "")
            currentTab = "artists"
        else if (library.selectedPlaylistName !== "")
            currentTab = "playlists"
    }

    Connections {
        target: library
        function onLibrary_changed() { root.syncEntitySelection() }
    }

    Component.onCompleted: syncEntitySelection()

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiThemeState.contentGap

        LibraryHeader { Layout.fillWidth: true }

        LibraryToolbar { Layout.fillWidth: true }

        LibraryTabs {
            Layout.fillWidth: true
            currentTab: root.currentTab
            onCurrentTabChanged: root.currentTab = currentTab
        }

        LibraryContentHost {
            currentTab: root.currentTab
            albumMode: root.albumMode
            onAlbumModeChanged: root.albumMode = albumMode
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
