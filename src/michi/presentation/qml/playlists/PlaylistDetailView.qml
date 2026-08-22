import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// PlaylistDetailView — PLAYLISTS + playlist_id. Header with real artwork mosaic / custom cover,
// honest Play Now & Add to Queue buttons, total duration, and track list.
Item {
    id: root

    objectName: "playlistDetailView"
    property string playlistId: ""
    signal backRequested()
    signal playRequested()
    signal togglePinRequested()
    signal renameRequested(string playlistId, string playlistName)
    signal deleteRequested(string playlistId, string playlistName)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)

    function formatTotalDuration(ms) {
        if (!ms || ms <= 0) return ""
        var totalSec = Math.round(ms / 1000)
        var hours = Math.floor(totalSec / 3600)
        var minutes = Math.floor((totalSec % 3600) / 60)
        var seconds = totalSec % 60
        if (hours > 0)
            return hours + " hr " + minutes + " min"
        return minutes + " min " + (seconds > 0 ? (seconds + " sec") : "")
    }

    FileDialog {
        id: coverDialog
        title: qsTr("Select Playlist Cover Image")
        nameFilters: ["Image files (*.png *.jpg *.jpeg *.webp)"]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.indexOf("file://") === 0) {
                path = path.substring(7)
            }
            playlists.set_custom_cover(root.playlistId, path)
        }
    }

    // Atmospheric Ambient Glow on top
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 240
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiSemanticColors.contentAmbientBlue }
            GradientStop { position: 0.6; color: MichiSemanticColors.contentAmbientPurple }
            GradientStop { position: 1; color: "transparent" }
        }
        z: 0
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg
        z: 1

        // Top Navigation Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiIconButton {
                iconName: "back"
                accessibleName: qsTr("Back to All Playlists")
                onClicked: root.backRequested()
            }

            Item { Layout.fillWidth: true }
        }

        // Hero Header (Mockup Composition)
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xl

            Item {
                Layout.preferredWidth: 160
                Layout.preferredHeight: 160

                // Drop Shadow
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -4
                    radius: MichiRadius.lg + 4
                    color: MichiSemanticColors.glassShadowFar
                    opacity: 0.8
                    z: -1
                }

                PlaylistArtwork {
                    id: heroArtwork
                    anchors.fill: parent
                    customCoverPath: playlists.selectedPlaylistCustomCoverPath || ""
                    mosaicArtworkPaths: playlists.selectedPlaylistMosaicArtworkPaths || []
                    fallbackText: playlists.selectedPlaylistName
                    radius: MichiRadius.lg

                    MouseArea {
                        id: coverMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: coverDialog.open()

                        Rectangle {
                            anchors.fill: parent
                            radius: MichiRadius.lg
                            color: MichiPalette.obsidianDeep
                            opacity: coverMouseArea.containsMouse ? 0.65 : 0
                            Behavior on opacity {
                                NumberAnimation { duration: MichiMotion.micro }
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                visible: coverMouseArea.containsMouse
                                MichiIcon {
                                    name: "sliders"
                                    width: 24
                                    height: 24
                                    iconColor: MichiPalette.textPrimary
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                MichiText {
                                    text: qsTr("Change cover")
                                    role: "technical"
                                    technical: true
                                    color: MichiPalette.textPrimary
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                spacing: MichiSpacing.sm
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter

                MichiText {
                    text: qsTr("PLAYLIST")
                    role: "technical"
                    technical: true
                    color: MichiPalette.auroraCyan
                    font.weight: Font.Bold
                    font.letterSpacing: 1.2
                }

                MichiText {
                    id: titleText
                    text: playlists.selectedPlaylistName
                    role: "display"
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    color: MichiPalette.textPrimary
                }

                MichiText {
                    text: playlists.playlistTracks.length + (playlists.playlistTracks.length === 1 ? " track" : " tracks")
                        + (playlists.selectedPlaylistDurationMs > 0 ? " · " + root.formatTotalDuration(playlists.selectedPlaylistDurationMs) : "")
                        + " · " + qsTr("Local Collection")
                    role: "secondary"
                    color: MichiPalette.textSecondary
                }

                Item { Layout.preferredHeight: MichiSpacing.xs }

                // Quick Actions Row
                RowLayout {
                    spacing: MichiSpacing.md

                    MichiButton {
                        text: qsTr("Play")
                        variant: "primary"
                        iconName: "play"
                        enabled: playlists.playlistTracks.length > 0
                        accessibleName: qsTr("Play playlist now")
                        onClicked: root.playRequested()
                    }

                    MichiButton {
                        text: qsTr("Add to Queue")
                        variant: "secondary"
                        iconName: "queue"
                        enabled: playlists.playlistTracks.length > 0
                        accessibleName: qsTr("Add playlist to queue")
                        onClicked: playlists.queue_selected_playlist()
                    }

                    MichiIconButton {
                        iconName: "pin"
                        selected: playlists.selectedPlaylistPinned
                        accessibleName: playlists.selectedPlaylistPinned
                            ? qsTr("Unpin playlist") : qsTr("Pin playlist")
                        onClicked: root.togglePinRequested()
                    }

                    MichiIconButton {
                        iconName: "more"
                        accessibleName: qsTr("More options")
                        onClicked: detailMenu.popup()
                    }
                }
            }
        }

        PlaylistTrackList {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlistTrackRows.length > 0
            rows: playlists.playlistTrackRows
            onRemoveTrackRequested: index => root.removeTrackRequested(index)
            onMoveTrackRequested: (f, t) => root.moveTrackRequested(f, t)
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlistTrackRows.length === 0
            title: qsTr("Empty playlist")
            message: qsTr("Add tracks from your library to start collecting them here.")
            iconName: "playlist"
        }
    }

    MichiMenu {
        id: detailMenu
        MenuItem {
            text: qsTr("Change Cover…")
            onTriggered: coverDialog.open()
        }
        MenuItem {
            text: qsTr("Use Automatic Mosaic")
            visible: (playlists.selectedPlaylistCustomCoverPath || "") !== ""
            onTriggered: playlists.remove_custom_cover(root.playlistId)
        }
        MenuItem {
            objectName: "playlistDetailRenameAction"
            text: qsTr("Rename")
            onTriggered: root.renameRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
        MenuItem {
            objectName: "playlistDetailDeleteAction"
            text: qsTr("Delete playlist")
            onTriggered: root.deleteRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
    }
}
