import QtQuick
import QtQuick.Layouts
import "../patterns"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root

    property string currentTab: "songs"
    property string addTargetPath: ""
    // M6-PRODUCTION-INTEGRATION: albumMode passes through to AlbumsView
    // (two-way like addTargetPath); the source lives in LibraryView so the
    // mode survives the AlbumsView recreation on tab switches.
    property string albumMode: "grid"
    property var _content: null   // the current tab view

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
            case "playlists": component = playlistsViewComponent; break
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
        title: "Library unavailable"
        message: library.diagnosticMessage
        actionText: ""
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
                text: "ADD TRACK TO"
                role: "technical"
                technical: true
                color: MichiPalette.auroraPurple
                font.weight: Font.DemiBold
            }

            Repeater {
                model: library.playlists
                delegate: MichiButton {
                    text: modelData.name
                    variant: "secondary"
                    onClicked: {
                        library.add_to_playlist(modelData.name, addTargetPath)
                        addTargetPath = ""
                    }
                }
            }

            Item { Layout.fillWidth: true }
            MichiIconButton {
                iconName: "close"
                accessibleName: "Cancel playlist selection"
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
        title: "No music yet"
        message: "Choose a music directory above and scan it to build your local library."
    }

    LoadingState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.fileCount === 0
            && library.scanStatus !== "" && library.scanStatus !== "IDLE"
        message: "Building your library…"
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
            onAlbumModeChanged: root.albumMode = albumMode
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

    Component {
        id: playlistsViewComponent
        PlaylistsView {
            anchors.fill: parent
            addTargetPath: root.addTargetPath
            onAddTargetPathChanged: root.addTargetPath = addTargetPath
        }
    }
}
