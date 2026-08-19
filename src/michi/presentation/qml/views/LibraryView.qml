import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

MichiPanel {
    id: root

    property string currentTab: "songs"
    // M6-PRODUCTION-INTEGRATION: albumMode lives HERE (the root survives
    // the tab recreation) — AlbumsView is recreated on every tab switch and
    // must never be the source of a preference we want to preserve.
    property string albumMode: "grid"

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space8

        LibraryHeader {}

        LibraryToolbar {}

        LibraryTabs {
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
