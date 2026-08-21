import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../playlists"
import "../primitives"
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""
    signal createPlaylistRequested()

    function routeIndex(route) {
        switch (route) {
        case "now_playing": return 0
        case "library":     return 1
        case "queue":       return 2
        case "settings":    return 3
        case "playlists":   return 4
        default:            return 1
        }
    }

    // PLAYLIST-HIERARCHY-04: detail = PLAYLISTS + playlist_id; All
    // Playlists = PLAYLISTS + None. One route, two content surfaces.
    readonly property bool _playlistDetail: root.currentRoute === "playlists"
        && playlists.selectedPlaylistId !== ""

    MichiSurface { anchors.fill: parent; level: "content"; radius: MichiRadius.floating }

    StackLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        currentIndex: root.routeIndex(root.currentRoute)

        NowPlayingView { }
        LibraryView { }
        QueueView { }
        SettingsView { }

        // PLAYLISTS route host: All Playlists or Detail by playlist target.
        Item {
            id: playlistsRouteHost
            objectName: "playlistsRouteHost"

            PlaylistsView {
                id: allPlaylistsView
                objectName: "allPlaylistsView"
                anchors.fill: parent
                visible: !root._playlistDetail
                onCreatePlaylistRequested: root.createPlaylistRequested()
                onOpenPlaylistRequested: playlistId => playlists.open_playlist(playlistId)
                onPlayPlaylistRequested: playlistId => playlists.play_playlist(playlistId)
                onPinPlaylistRequested: (playlistId, pinned) => {
                    if (pinned) playlists.pin_playlist(playlistId)
                    else playlists.unpin_playlist(playlistId)
                }
                onRenamePlaylistRequested: playlistId => {
                    playlists.select_playlist(playlistId)
                    renameDialog.open()
                }
                onDeletePlaylistRequested: playlistId => {
                    playlists.select_playlist(playlistId)
                    deleteDialog.open()
                }
            }

            PlaylistDetailView {
                id: playlistDetail
                objectName: "playlistDetailView"
                anchors.fill: parent
                visible: root._playlistDetail
                playlistId: playlists.selectedPlaylistId
                onBackRequested: playlists.open_all_playlists()
                onPlayRequested: playlists.play_selected_playlist()
                onTogglePinRequested: {
                    var row = _pinnedRow()
                    if (row) playlists.unpin_playlist(row.playlistId)
                    else playlists.pin_playlist(playlists.selectedPlaylistId)
                }
                onRenameRequested: (playlistId, newName) => {
                    playlists.rename_playlist(playlistId, newName)
                }
                onDeleteRequested: playlistId => playlists.delete_playlist(playlistId)
                onRemoveTrackRequested: index => playlists.remove_track(index)
                onMoveTrackRequested: (fromIndex, toIndex) => {
                    playlists.move_track(fromIndex, toIndex)
                }
            }
        }
    }

    // Rename / delete dialogs shared by All Playlists cards and Detail.
    MichiDialog {
        id: renameDialog
        objectName: "renamePlaylistDialog"
        title: qsTr("Rename playlist")
        width: 420
        property string errorText: ""
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiTextField {
                id: renameField
                Layout.fillWidth: true
                placeholderText: qsTr("Playlist name")
                text: playlists.selectedPlaylistName
                onAccepted: renameDialog._submit()
            }
            MichiText {
                visible: renameDialog.errorText !== ""
                text: renameDialog.errorText
                role: "technical"
                technical: true
                color: MichiPalette.error
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancel")
                    variant: "ghost"
                    onClicked: renameDialog.close()
                }
                MichiButton {
                    text: qsTr("Rename")
                    variant: "primary"
                    onClicked: renameDialog._submit()
                }
            }
        }
        function _submit() {
            var name = renameField.text.trim()
            if (name === "") {
                renameDialog.errorText = qsTr("Playlist name must not be empty")
                return
            }
            playlists.rename_playlist(playlists.selectedPlaylistId, name)
            renameDialog.close()
        }
        onOpened: renameField.text = playlists.selectedPlaylistName
    }

    MichiDialog {
        id: deleteDialog
        objectName: "deletePlaylistDialog"
        title: qsTr("Delete \u201C" + playlists.selectedPlaylistName + "\u201D?")
        width: 440
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiText {
                text: qsTr("The playlist will be removed. Music files will remain in your library.")
                role: "secondary"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                color: MichiPalette.textSecondary
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancel")
                    variant: "ghost"
                    onClicked: deleteDialog.close()
                }
                MichiButton {
                    text: qsTr("Delete")
                    variant: "danger"
                    onClicked: {
                        playlists.delete_playlist(playlists.selectedPlaylistId)
                        deleteDialog.close()
                    }
                }
            }
        }
    }

    function _pinnedRow() {
        var rows = playlists.playlists
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].playlistId === playlists.selectedPlaylistId)
                return rows[i].pinned ? rows[i] : null
        }
        return null
    }
}
