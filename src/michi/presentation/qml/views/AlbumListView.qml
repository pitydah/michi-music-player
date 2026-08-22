import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../media"
import "../theme"

ListView {
    id: root
    objectName: "albumListView"

    property var albumModel: library.albums
    property string sortMode: "title"
    property bool sortDescending: false
    signal sortRequested(string mode)
    readonly property bool showArtistColumn: width >= 620
    readonly property bool showYearColumn: width >= 500
    readonly property bool showTrackCountColumn: width >= 760
    readonly property bool showDurationColumn: width >= 680
    readonly property bool showTechnicalColumn: width >= 1040
        && MichiThemeState.precisionMode

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    cacheBuffer: height
    reuseItems: true
    headerPositioning: ListView.OverlayHeader
    Accessible.role: Accessible.Table
    Accessible.name: qsTr("Albums in list view")

    header: AlbumTableHeader {
        width: root.width
        showArtist: root.showArtistColumn
        showYear: root.showYearColumn
        showTrackCount: root.showTrackCountColumn
        showDuration: root.showDurationColumn
        showTechnical: root.showTechnicalColumn
        sortMode: root.sortMode
        sortDescending: root.sortDescending
        onSortRequested: mode => root.sortRequested(mode)
    }

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }

    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: MichiSpacing.sm
    }

    delegate: MichiAlbumRow {
        required property int index
        required property var modelData
        width: root.width
        album: modelData
        selected: ListView.isCurrentItem
        showArtist: root.showArtistColumn
        showYear: root.showYearColumn
        showTrackCount: root.showTrackCountColumn
        showDuration: root.showDurationColumn
        showTechnical: root.showTechnicalColumn
        onActiveFocusChanged: {
            if (activeFocus)
                root.currentIndex = index
        }
        onActivated: {
            root.currentIndex = index
            library.select_album(modelData.key)
        }
    }
}
