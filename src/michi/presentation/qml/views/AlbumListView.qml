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
    readonly property var columnPlan: resolveColumnPlan(width, viewPreferences)
    readonly property bool showArtistColumn: columnPlan.artist
    readonly property bool showYearColumn: columnPlan.year
    readonly property bool showTrackCountColumn: columnPlan.tracks
    readonly property bool showDurationColumn: columnPlan.duration
    readonly property bool showTechnicalColumn: columnPlan.format

    function resolveColumnPlan(availableWidth, preferences) {
        var remaining = Math.max(0, availableWidth - 360)
        var result = { artist: false, year: false, tracks: false,
            duration: false, format: false }
        var ordered = [
            { key: "artist", pref: "artistColumn", cost: 210 },
            { key: "year", pref: "yearColumn", cost: 70 },
            { key: "tracks", pref: "tracksColumn", cost: 64 },
            { key: "duration", pref: "durationColumn", cost: 74 },
            { key: "format", pref: "formatColumn", cost: 170 }
        ]
        for (var index = 0; index < ordered.length; ++index) {
            var column = ordered[index]
            if (preferences[column.pref] === false)
                continue
            if (remaining < column.cost)
                break
            result[column.key] = true
            remaining -= column.cost
        }
        return result
    }

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

    Component.onCompleted: if (browseState) Qt.callLater(function() {
        var restoredIndex = browseState.listIndex
        if (browseState.currentKey) {
            for (var i = 0; i < albumModel.length; ++i) {
                if (albumModel[i].key === browseState.currentKey) {
                    restoredIndex = i
                    break
                }
            }
        }
        root.currentIndex = restoredIndex
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
        collectionFocus: root.activeFocus && ListView.isCurrentItem
        showArtist: root.showArtistColumn
        showYear: root.showYearColumn
        showTrackCount: root.showTrackCountColumn
        showDuration: root.showDurationColumn
        showTechnical: root.showTechnicalColumn
        precisionMetadata: root.viewPreferences.precisionMetadata !== false
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
