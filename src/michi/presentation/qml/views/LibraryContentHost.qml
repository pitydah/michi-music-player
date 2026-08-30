import QtQuick
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root

    property string currentTab: "songs"
    property string addTargetPath: ""
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
        visible: library.hasDiagnostic
            || (library.scanStatus === "FAILED" && library.fileCount === 0)
        title: library.hasDiagnostic ? "Library unavailable" : "Scan failed"
        message: library.hasDiagnostic
            ? library.diagnosticMessage
            : "The library could not be scanned. Check your music folder and try again."
        actionText: qsTr("Retry scan")
        onActionRequested: root.scanRequested()
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? implicitHeight : 0
    }

    MichiGlassSurface {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 48 : 0
        visible: addTargetPath !== ""
        elevation: "subtle"
        contentPadding: MichiSpacing.sm
        accented: true
        accentColor: MichiPalette.auroraPurple

        RowLayout {
            anchors.fill: parent
            spacing: MichiSpacing.sm
            MichiText {
                text: qsTr("ADD TRACK TO")
                role: "technical"
                technical: true
                color: MichiPalette.auroraPurple
                font.weight: Font.DemiBold
            }

            Repeater {
                model: playlists.playlists
                delegate: MichiButton {
                    text: modelData.name
                    variant: "secondary"
                    onClicked: {
                        // M9-R1 cross-feature: Library sends tracks to
                        // Playlists by canonical id (PLAINTLIST-HIERARCHY-02).
                        // R2 P1-12: success feedback ONLY on durable add;
                        // an already-present track is never "Added".
                        // R4: los result codes NO son truthy — comparación exacta.
                        var added = playlists.add_track_to_playlist(
                            modelData.playlistId, addTargetPath)
                        addTargetPath = ""
                        if (added === "added")
                            window.showToast(qsTr("Added to %1").arg(modelData.name))
                        else if (added === "already_present")
                            window.showToast(qsTr("Already in %1").arg(modelData.name))
                        // "persistence_failed": el persistence Connections informa.
                    }
                }
            }

            Item { Layout.fillWidth: true }
            MichiIconButton {
                iconName: "close"
                accessibleName: qsTr("Cancel playlist selection")
                onClicked: addTargetPath = ""
            }
        }
    }

    Item {
        id: contentArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.fileCount > 0
    }

    EmptyState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.fileCount === 0
            && (library.scanStatus === "" || library.scanStatus === "IDLE")
        title: qsTr("No music yet")
        message: qsTr("Scan a music folder to build your local library. Everything stays on your device.")
        actionText: qsTr("Choose Music Folder")
        iconName: "folder"
        onActionRequested: root.scanRequested()
    }

    LoadingState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        // FAILED/CANCELLED must NOT spin forever: the ErrorState (above)
        // covers FAILED with a retry, and CANCELLED returns to the
        // EmptyState prompt.
        visible: library.fileCount === 0
            && library.scanStatus !== "" && library.scanStatus !== "IDLE"
            && library.scanStatus !== "FAILED" && library.scanStatus !== "CANCELLED"
        message: qsTr("Building your library…")
    }

    Component {
        id: songsViewComponent
        SongsView {
            anchors.fill: parent
            addTargetPath: root.addTargetPath
            onAddTargetPathChanged: root.addTargetPath = addTargetPath
        }
    }

    Component {
        id: albumsViewComponent
        AlbumsView {
            anchors.fill: parent
            addTargetPath: root.addTargetPath
            onAddTargetPathChanged: root.addTargetPath = addTargetPath
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
            addTargetPath: root.addTargetPath
            onAddTargetPathChanged: root.addTargetPath = addTargetPath
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
        }
    }

    Component {
        id: historyViewComponent
        HistoryView {
            anchors.fill: parent
        }
    }

    Component {
        id: recentlyViewComponent
        RecentlyAddedView {
            anchors.fill: parent
        }
    }
}
