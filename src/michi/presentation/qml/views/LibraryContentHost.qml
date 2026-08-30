import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../playlists"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root

    property string currentTab: "songs"
    property string addTargetTrackId: ""
    // LibraryView owns presentation preferences; recreated tab content only
    // receives their current projection so controls cannot break bindings.
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0
    property var _content: null   // the current tab view
    signal scanRequested()
    signal sortModeRequested(string mode)
    signal sortDirectionRequested(bool descending)

    // M6.7: explicit per-tab management. The object tree must NOT keep the
    // previous tab alive after a switch (the findChild unload contract in
    // the offscreen harness only spins processEvents, which does not flush
    // deferred deletes, and QML parent= does not detach the QObject parent)
    // — so clear the objectName synchronously (removes it from
    // findChild(QObject, name) matching), then detach + schedule the delete
    // for memory hygiene. The component FILE keeps its objectName
    // declaration (structural tests read files, unaffected).
    function _loadTab(tab) {
        if (_content) {
            _content.objectName = ""
            _content.parent = null
            _content.destroy()
            _content = null
        }
        var component = null
        switch (tab) {
            case "songs": component = songsViewComponent; break
            case "albums": component = albumsViewComponent; break
            case "artists": component = artistsViewComponent; break
            case "genres": component = genresViewComponent; break
            case "folders": component = foldersViewComponent; break
            case "favorites": component = favoritesViewComponent; break
            case "history": component = historyViewComponent; break
            case "recently": component = recentlyViewComponent; break
        }
        if (component)
            _content = component.createObject(contentArea)
    }

    onCurrentTabChanged: _loadTab(currentTab)
    Component.onCompleted: _loadTab(currentTab)

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    ErrorState {
        objectName: "libraryErrorState"
        visible: library.hasDiagnostic
            || (library.scanStatus === "FAILED" && library.fileCount === 0)
        title: library.hasDiagnostic ? "Library unavailable" : "Scan failed"
        message: library.hasDiagnostic
            ? library.diagnosticMessage
            : (library.scanDiagnostic.length > 0
                ? library.scanDiagnostic
                : "The library could not be scanned. Check your music folder and try again.")
        actionText: qsTr("Retry scan")
        onActionRequested: root.scanRequested()
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? implicitHeight : 0
    }

    Item {
        id: contentArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.fileCount > 0
    }

    EmptyState {
        objectName: "libraryEmptyState"
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.fileCount === 0
            && !library.scanActive
            && (
                library.scanStatus === ""
                || library.scanStatus === "IDLE"
                || library.scanStatus === "COMPLETED"
                || library.scanStatus === "CANCELLED"
            )
        title: qsTr("No music yet")
        message: qsTr("Scan a music folder to build your local library. Everything stays on your device.")
        actionText: qsTr("Choose Music Folder")
        iconName: "folder"
        onActionRequested: root.scanRequested()
    }

    LoadingState {
        objectName: "libraryLoadingState"
        Layout.fillWidth: true
        Layout.fillHeight: true
        // 10/10 FINAL SEAL P1-02: scanActive is the ONLY operational
        // authority — the Bridge owns the state machine; this surface
        // never reconstructs it from status strings.
        visible: library.fileCount === 0
            && library.scanActive
        message: qsTr("Building your library…")
    }

    TrackPropertiesView {
        id: trackPropertiesView
    }

    Component {
        id: songsViewComponent
        SongsView {
            anchors.fill: parent
            addTargetTrackId: root.addTargetTrackId
            onAddTargetTrackIdChanged: root.addTargetTrackId = addTargetTrackId
            onPropertiesRequested: track => trackPropertiesView.inspect(track)
        }
    }

    Component {
        id: albumsViewComponent
        AlbumsView {
            anchors.fill: parent
            onAddToPlaylistRequested: trackId =>
                library.request_tracks_playlist_target([trackId])
            albumMode: root.albumMode
            albumSortMode: root.albumSortMode
            albumSortDescending: root.albumSortDescending
            albumFilterMode: root.albumFilterMode
            albumTimelineGrouping: root.albumTimelineGrouping
            albumZoom: root.albumZoom
            onSortModeRequested: mode => root.sortModeRequested(mode)
            onSortDirectionRequested: descending => root.sortDirectionRequested(descending)
        }
    }

    Component {
        id: artistsViewComponent
        ArtistsView {
            anchors.fill: parent
            onAddToPlaylistRequested: trackId =>
                library.request_tracks_playlist_target([trackId])
        }
    }

    Component {
        id: genresViewComponent
        GenresView {
            anchors.fill: parent
        }
    }

    Component {
        id: foldersViewComponent
        FoldersView {
            anchors.fill: parent
        }
    }

    Component {
        id: favoritesViewComponent
        FavoritesView {
            anchors.fill: parent
            addTargetTrackId: root.addTargetTrackId
            onAddTargetTrackIdChanged: root.addTargetTrackId = addTargetTrackId
            onPropertiesRequested: track => trackPropertiesView.inspect(track)
        }
    }

    Component {
        id: historyViewComponent
        HistoryView {
            anchors.fill: parent
            addTargetTrackId: root.addTargetTrackId
            onAddTargetTrackIdChanged: root.addTargetTrackId = addTargetTrackId
            onPropertiesRequested: track => trackPropertiesView.inspect(track)
        }
    }

    Component {
        id: recentlyViewComponent
        RecentlyAddedView {
            anchors.fill: parent
            addTargetTrackId: root.addTargetTrackId
            onAddTargetTrackIdChanged: root.addTargetTrackId = addTargetTrackId
            onPropertiesRequested: track => trackPropertiesView.inspect(track)
        }
    }

    onAddTargetTrackIdChanged: {
        if (addTargetTrackId !== "") {
            library.request_tracks_playlist_target([addTargetTrackId])
            addTargetTrackId = ""
        }
    }
}
