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
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0
    property var viewPreferences: ({})
    property var browseState: null
    property var _content: null
    signal scanRequested()
    signal sortModeRequested(string mode)
    signal sortDirectionRequested(bool descending)

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
            || (library.scanStatus === "FAILED"
                && library.libraryTrackCount === 0)
        title: library.hasDiagnostic ? qsTr("Library unavailable") : qsTr("Scan failed")
        message: library.hasDiagnostic
            ? library.diagnosticMessage
            : qsTr("The library could not be scanned. Check your music folder and try again.")
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
                        var added = playlists.add_track_to_playlist(
                            modelData.playlistId, addTargetPath)
                        addTargetPath = ""
                        if (added === "added")
                            window.showToast(qsTr("Added to %1").arg(modelData.name))
                        else if (added === "already_present")
                            window.showToast(qsTr("Already in %1").arg(modelData.name))
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

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 30 : 0
        visible: library.genreFilterActive
            && library.libraryTrackCount > 0
        color: MichiSemanticColors.surfaceHover
        radius: MichiRadius.sm
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.md
            anchors.rightMargin: MichiSpacing.xs
            spacing: MichiSpacing.sm

            MichiText {
                text: qsTr("Genre")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            MichiText {
                text: library.selectedGenreName
                role: "body"
                font.weight: Font.DemiBold
                color: MichiPalette.textPrimary
            }
            Item {
                Layout.fillWidth: true
            }
            MichiIconButton {
                objectName: "clearGenreFilterButton"
                iconName: "close"
                accessibleName: qsTr("Clear genre filter")
                Layout.preferredWidth: 26
                Layout.preferredHeight: 26
                onClicked: library.clear_genre_selection()
            }
        }
    }

    Item {
        id: contentArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.libraryTrackCount > 0
    }

    EmptyState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.libraryTrackCount === 0
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
        visible: library.libraryTrackCount === 0
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
            viewPreferences: root.viewPreferences
            browseState: root.browseState
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
