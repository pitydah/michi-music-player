import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
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
    property bool _detailReady: false
    Component.onCompleted: root._detailReady = true
    property string playlistId: ""
    property string selectedTrackPath: ""
    property int selectedIndex: -1
    onPlaylistIdChanged: {
        // R3-07: el estado transitorio NUNCA se filtra entre playlists.
        // El reset corre tras el layout (la página puede estar montándose).
        root.selectedTrackPath = ""
        root.selectedIndex = -1
        if (root._detailReady)
            trackList.resetForPlaylist()
    }
    signal backRequested()
    signal playRequested()
    signal shuffleRequested()
    signal togglePinRequested()
    signal customizeAppearanceRequested(string playlistId)
    signal renameRequested(string playlistId, string playlistName)
    signal deleteRequested(string playlistId, string playlistName)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)
    signal playTrackRequested(int index)
    signal addMusicRequested()

    // Hero occupies ~30-40% of the first visible screen
    readonly property real heroHeight: Math.max(240, Math.min(300, root.height * 0.36))
    // Sticky column header — completely hidden over the hero (the in-flow
    // header below the hero shows the labels there); fades in with the
    // backplane once the hero scrolls away
    readonly property real stickyHeaderOpacity: trackList
        ? Math.max(0, Math.min(1, (trackList.contentY - (root.heroHeight - 44)) / 44)) : 0
    readonly property bool showArtist: root.width >= 700
    readonly property bool showAlbum: root.width >= 900
    readonly property bool showFormat: root.width > 1200

    // Hero as a Component (ListView.header requires QQmlComponent — an
    // instantiated Item cannot be assigned). The wrapper scrolls away as a
    // unit: the editorial hero on top, the quiet column header below it
    // (it only "sticks" via the separate overlay once the hero leaves).
    // Bindings are null-safe: the header can be instantiated before the
    // bridge context resolves, and they re-evaluate on playlists_changed.
    Component {
        id: heroComponent
        Item {
            id: heroHeader
            objectName: "playlistHeroHeader"
            readonly property var appearance: playlists
                ? playlists.selectedPlaylistAppearance : ({})
            // ListView does not guarantee the implicit dimensions of an
            // arbitrary Item header. Explicit geometry is mandatory: the
            // previous implicit-only wrapper produced a zero-width/height
            // hero whose children leaked into the page without its cover or
            // background.
            width: root.width
            height: root.heroHeight + MichiMetrics.controlSmall
            implicitWidth: width
            implicitHeight: height

            PlaylistHero {
                id: heroItem
                objectName: "playlistHero"
                width: parent.width
                height: root.heroHeight
                playlistName: playlists ? playlists.selectedPlaylistName : ""
                trackCount: playlists ? playlists.playlistTracks.length : 0
                durationMs: playlists ? playlists.selectedPlaylistDurationMs : 0
                description: playlists ? (playlists.selectedPlaylistDescription || "") : ""
                // R2 P1-11: EFFECTIVE cover — a vanished managed asset
                // renders the automatic mosaic, never a dead box.
                customCoverPath: playlists ? (playlists.effectiveCustomCoverPath || "") : ""
                mosaicArtworkPaths: playlists ? (playlists.selectedPlaylistMosaicArtworkPaths || []) : []
                // R2 P1-11: effective hero mode — a persisted image whose
                // managed asset vanished degrades to auto (never a dead
                // render); persisted intent stays untouched.
                heroMode: playlists ? playlists.effectiveHeroMode : "auto"
                heroSolidColor: parent.appearance.heroSolidColor || MichiPalette.playlistHeroTop
                heroGradientColors: parent.appearance.heroGradientColors || [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid]
                heroGradientAngle: parent.appearance.heroGradientAngle === undefined
                    ? 135 : parent.appearance.heroGradientAngle
                heroImagePath: parent.appearance.effectiveHeroImagePath || ""
                autoHeroColors: playlists ? playlists.selectedPlaylistAutoHeroColors : [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid, MichiPalette.playlistHeroBottom]

                // R2.1-07: signals wired INLINE (the ListView headerItem is
                // this wrapper Item, NOT the hero — a Connections on
                // headerItem never matches the hero's signals)
                onPlayRequested: root.playRequested()
                onShuffleRequested: root.shuffleRequested()
                onMoreRequested: detailMenu.popup()
                onCustomizeAppearanceRequested: root.customizeAppearanceRequested(root.playlistId)

                onAddTracksRequested: root.addMusicRequested()
            }

            PlaylistColumnHeader {
                anchors.top: heroItem.bottom
                width: parent.width
                showArtist: width >= 700
                showAlbum: width >= 900
                showFormat: width > 1200
            }
        }
    }

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

            // Sticky column header — fades in (labels + backplane) only
            // while the hero scrolls away; hidden over the hero itself
            Rectangle {
                id: columnHeaderBar
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 34
                z: 5
                color: MichiSemanticColors.backplane
                opacity: root.stickyHeaderOpacity
                clip: true
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                }

                PlaylistColumnHeader {
                    anchors.fill: parent
                    showArtist: root.showArtist
                    showAlbum: root.showAlbum
                    showFormat: root.showFormat
                }
            }

            PlaylistTrackList {
                id: trackList
                anchors.fill: parent
                rows: playlists.playlistTrackRows
                selectedTrackPath: root.selectedTrackPath
                selectedIndex: root.selectedIndex
                showArtistColumn: root.width >= 700
                showAlbumColumn: root.width >= 900
                showFormatColumn: root.width > 1200
                narrow: root.width < 700
                heroComponent: heroComponent

                onTrackSelected: path => {
                    root.selectedTrackPath = path
                    root.selectedIndex = -1
                }
                onPlayTrackRequested: index => playlists.play_playlist_track(index)
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
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
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
            text: qsTr("Add tracks…")
            onTriggered: root.addMusicRequested()
        }
        MenuItem {
            text: qsTr("Customize appearance…")
            onTriggered: root.customizeAppearanceRequested(root.playlistId)
        }
        MenuItem {
            text: playlists.selectedPlaylistPinned ? qsTr("Unpin") : qsTr("Pin")
            onTriggered: root.togglePinRequested()
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
