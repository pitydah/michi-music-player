import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../theme"

ListView {
    id: root
    objectName: "albumListView"

    property var albumModel: library.albums
    property string sortMode: "title"
    property bool sortDescending: false
    property var browseState: null
    property var viewPreferences: ({})
    signal sortRequested(string mode)
    readonly property bool showArtistColumn: viewPreferences.artistColumn !== false
        && width >= 620
    readonly property bool showYearColumn: viewPreferences.yearColumn !== false
        && width >= 500
    readonly property bool showTrackCountColumn: viewPreferences.tracksColumn !== false
        && width >= 760
    readonly property bool showDurationColumn: viewPreferences.durationColumn !== false
        && width >= 680
    readonly property bool showTechnicalColumn: width >= 1040
        && viewPreferences.formatColumn !== false
        && viewPreferences.precisionMetadata !== false

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

    function restoredIndex() {
        if (browseState && browseState.currentKey) {
            for (var i = 0; i < albumModel.length; ++i)
                if (albumModel[i].key === browseState.currentKey) return i
        }
        return browseState ? browseState.listIndex : -1
    }
    Component.onCompleted: if (browseState) Qt.callLater(function() {
        root.currentIndex = restoredIndex()
        root.contentY = browseState.listContentY
    })
    onContentYChanged: if (browseState) browseState.listContentY = contentY
    onCurrentIndexChanged: if (browseState) {
        browseState.listIndex = currentIndex
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            browseState.remember(albumModel[currentIndex].key)
    }

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
    Keys.onSpacePressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.play_album(albumModel[currentIndex].key)
    }

    ScrollBar.vertical: MichiScrollBar { }

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
        artworkSize: root.viewPreferences.artworkSize || "small"
        rowDensity: root.viewPreferences.density || "standard"
        onActiveFocusChanged: {
            if (activeFocus)
                root.currentIndex = index
        }
        onSelectedRequested: {
            root.currentIndex = index
        }
        onOpenRequested: {
            root.currentIndex = index
            library.select_album(modelData.key)
        }
        onPlayRequested: library.play_album(modelData.key)
    }
}
