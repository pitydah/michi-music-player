import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// PlaylistDetailView — PLAYLISTS + playlist_id editorial page.
// One continuous surface: atmospheric hero (cover + identity + compact
// actions) that scrolls away, a sticky quiet column header, and a dense
// track table below. The playlist is a persistent collection — selecting
// and playing a track never requires queue operations (play_track).
Item {
    id: root

    objectName: "playlistDetailView"
    property string playlistId: ""
    property int selectedIndex: -1
    signal backRequested()
    signal playRequested()
    signal shuffleRequested()
    signal togglePinRequested()
    signal renameRequested(string playlistId, string playlistName)
    signal deleteRequested(string playlistId, string playlistName)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)
    signal playTrackRequested(int index)
    signal addMusicRequested()

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

    // Hero occupies ~30-40% of the first visible screen
    readonly property real heroHeight: Math.max(240, Math.min(300, root.height * 0.36))
    // Sticky column header fades in as the hero scrolls away (null-safe:
    // trackList is constructed after the sticky bar, so the binding must
    // tolerate the early evaluation window).
    readonly property real stickyHeaderOpacity: trackList
        ? Math.max(0, Math.min(1, trackList.contentY / Math.max(1, root.heroHeight))) : 0
    readonly property bool showArtist: root.width >= 700
    readonly property bool showAlbum: root.width >= 900

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Top bar (fixed) — quiet back affordance only
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Layout.leftMargin: MichiSpacing.xl
            Layout.rightMargin: MichiSpacing.xl
            spacing: MichiSpacing.sm
            z: 6

            MichiIconButton {
                iconName: "back"
                accessibleName: qsTr("Back to All Playlists")
                onClicked: root.backRequested()
            }
            Item { Layout.fillWidth: true }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            // Sticky column header — fades in as the hero scrolls away
            Rectangle {
                id: columnHeaderBar
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 34
                z: 5
                color: "transparent"
                opacity: root.stickyHeaderOpacity
                clip: true

                // Backplane so rows never show through once sticky
                Rectangle {
                    anchors.fill: parent
                    color: MichiSemanticColors.backplane
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiSpacing.md
                    anchors.rightMargin: MichiSpacing.sm
                    spacing: MichiSpacing.md
                    Item { Layout.preferredWidth: 36 }
                    Item { Layout.preferredWidth: 36 }
                    MichiText {
                        Layout.preferredWidth: root.width * 0.36
                        Layout.minimumWidth: 120
                        text: qsTr("TITLE")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textSecondary
                        opacity: 0.45
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }
                    MichiText {
                        visible: root.showArtist
                        Layout.preferredWidth: root.width * 0.2
                        Layout.minimumWidth: 90
                        Layout.maximumWidth: 240
                        text: qsTr("ARTIST")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textSecondary
                        opacity: 0.45
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }
                    MichiText {
                        visible: root.showAlbum
                        Layout.preferredWidth: root.width * 0.2
                        Layout.minimumWidth: 90
                        Layout.maximumWidth: 240
                        text: qsTr("ALBUM")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textSecondary
                        opacity: 0.45
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }
                    MichiText {
                        Layout.preferredWidth: 54
                        text: qsTr("TIME")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textSecondary
                        opacity: 0.45
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                        horizontalAlignment: Text.AlignRight
                    }
                    Item { Layout.preferredWidth: MichiMetrics.controlSmall }
                }
            }

            PlaylistTrackList {
                id: trackList
                anchors.fill: parent
                rows: playlists.playlistTrackRows
                selectedIndex: root.selectedIndex
                showArtistColumn: root.width >= 700
                showAlbumColumn: root.width >= 900
                narrow: root.width < 700

                heroHeader: PlaylistHero {
                    width: trackList.width
                    playlistName: playlists.selectedPlaylistName
                    trackCount: playlists.playlistTracks.length
                    durationMs: playlists.selectedPlaylistDurationMs
                    description: playlists.selectedPlaylistDescription || ""
                    customCoverPath: playlists.selectedPlaylistCustomCoverPath || ""
                    mosaicArtworkPaths: playlists.selectedPlaylistMosaicArtworkPaths || []
                    pinned: playlists.selectedPlaylistPinned
                    onPlayRequested: root.playRequested()
                    onShuffleRequested: root.shuffleRequested()
                    onMoreRequested: detailMenu.popup()
                    onChangeCoverRequested: coverDialog.open()
                    onTogglePinRequested: root.togglePinRequested()
                }

                onTrackSelected: index => root.selectedIndex = index
                onPlayTrackRequested: index => root.playTrackRequested(index)
                onRemoveTrackRequested: index => root.removeTrackRequested(index)
                onMoveTrackRequested: (f, t) => root.moveTrackRequested(f, t)
            }

            // Empty state — hero stays, tracks area shows a quiet prompt
            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: root.heroHeight
                anchors.bottomMargin: MichiSpacing.xl
                visible: playlists.playlistTrackRows.length === 0
                spacing: MichiSpacing.sm

                Item { Layout.fillHeight: true }
                MichiIcon {
                    Layout.alignment: Qt.AlignHCenter
                    width: 34
                    height: 34
                    name: "playlist"
                    iconColor: MichiPalette.textMuted
                }
                MichiText {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("This playlist is empty")
                    role: "section"
                    color: MichiPalette.textPrimary
                }
                MichiText {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Add music from your library to start listening.")
                    role: "secondary"
                    color: MichiPalette.textSecondary
                    opacity: 0.65
                }
                Item { Layout.preferredHeight: MichiSpacing.xs }
                MichiButton {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Add Music")
                    iconName: "plus"
                    variant: "secondary"
                    implicitHeight: MichiMetrics.controlMedium
                    onClicked: root.addMusicRequested()
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    MichiMenu {
        id: detailMenu
        MenuItem {
            text: qsTr("Shuffle Play")
            onTriggered: root.shuffleRequested()
        }
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
            text: qsTr("Rename…")
            onTriggered: root.renameRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
        MenuItem {
            objectName: "playlistDetailDeleteAction"
            text: qsTr("Delete…")
            onTriggered: root.deleteRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
    }
}
