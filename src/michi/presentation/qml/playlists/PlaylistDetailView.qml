import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// PlaylistDetailView — PLAYLISTS + playlist_id. Header (back, name, count,
// pin, play), track list with remove/reorder, rename and delete flows.
// Delete requires confirmation; wording never implies file deletion.
Item {
    id: root

    objectName: "playlistDetailView"
    property string playlistId: ""
    signal backRequested()
    signal playRequested()
    signal togglePinRequested()
    signal renameRequested(string playlistId, string newName)
    signal deleteRequested(string playlistId)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)

    readonly property bool _selected: playlists.selectedPlaylistId === root.playlistId

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.md
            MichiIconButton {
                iconName: "back"
                accessibleName: qsTr("Back to All Playlists")
                onClicked: root.backRequested()
            }
            Rectangle {
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
                radius: MichiRadius.lg
                color: MichiSemanticColors.auroraPurpleSurface
                border.width: 1
                border.color: MichiSemanticColors.auroraPurpleBorder
                MichiIcon {
                    anchors.centerIn: parent
                    name: "playlist"
                    width: 30
                    height: 30
                    iconColor: MichiPalette.auroraCyan
                }
            }
            ColumnLayout {
                spacing: 2
                MichiText {
                    id: titleText
                    text: playlists.selectedPlaylistName
                    role: "section"
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    color: MichiPalette.textPrimary
                }
                MichiText {
                    text: playlists.playlistTracks.length + " tracks"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
            }
            Item { Layout.fillWidth: true }
            MichiIconButton {
                iconName: "pin"
                accessibleName: {
                    var pinned = playlists.playlists.length > 0
                        && playlists.playlists[0].playlistId === root.playlistId
                        && playlists.playlists[0].pinned
                    return pinned ? qsTr("Unpin playlist") : qsTr("Pin playlist")
                }
                onClicked: root.togglePinRequested()
            }
            MichiButton {
                text: qsTr("Play")
                variant: "primary"
                iconName: "play"
                enabled: playlists.playlistTracks.length > 0
                accessibleName: qsTr("Play playlist")
                onClicked: root.playRequested()
            }
            MichiIconButton {
                iconName: "sliders"
                accessibleName: qsTr("More options")
                onClicked: detailMenu.popup()
            }
        }

        PlaylistTrackList {
            Layout.fillWidth: true
            Layout.fillHeight: true
            rows: playlists.playlistTrackRows
            onRemoveTrackRequested: index => root.removeTrackRequested(index)
            onMoveTrackRequested: (f, t) => root.moveTrackRequested(f, t)
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlistTracks.length === 0
            title: qsTr("Empty playlist")
            message: qsTr("Add tracks from your library to start collecting them here.")
            iconName: "playlist"
        }
    }

    MichiMenu {
        id: detailMenu
        MenuItem {
            text: qsTr("Rename")
            onTriggered: renameDialog.open()
        }
        MenuItem {
            text: qsTr("Delete playlist")
            onTriggered: deleteDialog.open()
        }
    }

    MichiDialog {
        id: renameDialog
        objectName: "playlistRenameDialog"
        title: qsTr("Rename playlist")
        property string errorText: ""
        width: 420
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiTextField {
                id: renameField
                objectName: "playlistRenameField"
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
            root.renameRequested(root.playlistId, name)
            renameDialog.close()
        }
    }

    MichiDialog {
        id: deleteDialog
        objectName: "playlistDeleteDialog"
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
                    accessibleName: qsTr("Delete playlist")
                    onClicked: {
                        root.deleteRequested(root.playlistId)
                        deleteDialog.close()
                    }
                }
            }
        }
    }
}
